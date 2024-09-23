package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/aws/aws-sdk-go-v2/feature/ec2/imds"
	"github.com/prometheus/procfs"
)

const (
  USAGE_URL = "http://127.0.0.1:8080/instance/%s/usage"
  INIT_URL = "http://127.0.0.1:8080/instance"
  FINISHED_URL = "http://127.0.0.1:8080/container/%s/finish"
)

// /mnt1/yarn/usercache/hadoop/appcache/application_1697720075274_7464/container_1697720075274_7464_01_000036 <nil>

type Usage struct {
  PID int `json:"pid"`
  App string `json:"app"`
  Container string `json:"container"`
  Start float64 `json:"start"`
  ProcessTime float64 `json:"process_time"`
  CPUTime float64 `json:"cpu_time"`
  CPUUsage float64 `json:"cpu_usage"`
  Time int64 `json:"time"`
}

type Instance struct {
  InstanceId string `json:"instance_id"`
  Hostname string `json:"hostname"`
  Kind string `json:"kind"`
  InstanceType string `json:"instance_type"`
  PrivateIP string `json:"private_ip"`
  Region string `json:"region"`
  AvailabilityZone string `json:"az"`
  ImageId string `json:"image_id"`
  LaunchTime time.Time `json:"launch_time"`
  Architecture string `json:"architecture"`
}

func totalCPUTime(s *procfs.ProcStat) float64 {
  c := s.CPUTotal
  user := c.User - c.Guest
  nice := c.Nice - c.GuestNice
  idleall := c.Idle + c.Iowait
  systemall := c.System + c.IRQ + c.SoftIRQ
  virtall := c.Guest + c.GuestNice

  total := user + nice + systemall + idleall + c.Steal + virtall;
  return total
}

func appName(p *procfs.Proc) (string, string) {
  cwd, _ := p.Cwd()
  parts := strings.Split(cwd, "/")
  return parts[6], parts[7]
}

func monitor(fs *procfs.FS, pid int, fc chan Usage, uc chan Usage) {
  p, err := fs.Proc(pid)
  if err != nil {
    log.Printf("ERROR: Process %d not found. Assuming exit.", pid)
    return
  }

  app, container := appName(&p)
  pstat, _ := p.Stat()
  start, _ := pstat.StartTime()
  totalCPU := totalCPUTime(pstat)
  u := Usage{
    PID: p.PID,
    App: app,
    Container: container,
    Start: start,
    ProcessTime: pstat.CPUTime(),
    CPUTime: totalCPU,
    CPUUsage: pstat.CPUTime() / totalCPU * 100,
    Time: time.Now().Unix(),
  }

  for {
    time.Sleep(2 * time.Second)
    p, err := fs.Proc(pid); if err != nil {
      log.Printf("Process PID: %d not present in procfs. Assuming exit.", pid)
      fc <- u
      return
    }

    pstat, _ := p.Stat()
    elapsedTotal := totalCPUTime(fs) - u.CPUTime
    elapsedProcess := pstat.CPUTime() - u.ProcessTime
    u.CPUTime = totalCPUTime(fs)
    u.ProcessTime = pstat.CPUTime()
    u.CPUUsage = elapsedProcess / elapsedTotal * 100
    u.Time = time.Now().Unix()
    uc <- u
  }
}

func hadoopProcs(fs *procfs.FS) (pids []int) {
  ps, _ := fs.AllProcs()
  for _, p := range ps {
    cmd, err := p.Comm(); if err != nil || cmd != "java" {
      continue
    }
    cwd, err := p.Cwd(); if err != nil {
      continue
    }
    if !(strings.Contains(cwd, "application") && strings.Contains(cwd, "container")) {
      continue
    }
    pids = append(pids, p.PID)
  }
  return
}

func gc(i string, f chan Usage, p map[int]struct{}) {
  for {
    u := <- f
    go postUsageData(i, u, true)
    delete(p, u.PID)
  } 
}

func logUsage(u Usage) {
  //if (u.Container != "container_1697720075274_17494_01_000003") { return }
  fmt.Printf("PID: %d\n", u.PID)
  fmt.Printf("App: %s\n", u.App)
  fmt.Printf("Container: %s\n", u.Container)
  fmt.Printf("CPU time: %.2f\n", u.ProcessTime)
  fmt.Printf("Total CPU time: %.2f\n", u.CPUTime)
  fmt.Printf("CPU usage: %.2f%%\n", u.CPUUsage)
  fmt.Println("---------------------------------")
}

func handleUsage(i string, uc chan Usage) {
  for {
    u := <- uc
    logUsage(u)
    go postUsageData(i, u, false)
  }
}

func postUsageData(i string, u Usage, finished bool) {
  url := fmt.Sprintf(USAGE_URL, i)
  data, err := json.Marshal(u); if err != nil {
    log.Printf("ERROR: could not marshal process %d data: %s Skipping.\n", u.PID, err)
    return
  }
  r, err := http.Post(url, "application/json", bytes.NewBuffer(data)); if err != nil {
    log.Printf("ERROR: could not send HTTP request: %s\n", err)
    return
  }
  if finished {
    postContainerFinished(u.Container)
  }
  defer r.Body.Close()
  return
}

func postContainerFinished(c string) {
  url := fmt.Sprintf(FINISHED_URL, c)
  r, err := http.Post(url, "text/plain", bytes.NewBufferString("finished")); if err != nil {
    log.Printf("ERROR: could not send HTTP request: %s\n", err)
    return
  }

  defer r.Body.Close()
  return
}

func postMetadata(c *imds.Client) (string, error) {
  host := &Instance{}

  id, err := c.GetInstanceIdentityDocument(context.Background(), &imds.GetInstanceIdentityDocumentInput{})
  if err != nil {
    return "", fmt.Errorf("ERROR: could not initialize Instance Metadata client: %s", err)
  }
  host.InstanceId = id.InstanceID
  host.InstanceType = id.InstanceType
  host.PrivateIP = id.PrivateIP
  host.ImageId = id.ImageID
  host.LaunchTime = id.PendingTime
  host.Region = id.Region
  host.AvailabilityZone = id.AvailabilityZone
  host.Architecture = id.Architecture

  var hostname, kind string
  var res *imds.GetMetadataOutput
  var b strings.Builder

  res, err = c.GetMetadata(context.Background(), &imds.GetMetadataInput{Path: "hostname"})
  if _, err = io.Copy(&b, res.Content); err == nil {
    hostname = b.String()
  }
  b.Reset()
  res, err = c.GetMetadata(context.Background(), &imds.GetMetadataInput{Path: "instance-life-cycle"})
  if _, err = io.Copy(&b, res.Content); err == nil {
    kind = b.String()
  }
  
  host.Hostname = hostname
  host.Kind = kind

  data, err := json.Marshal(host)
  if err != nil {
    return "", fmt.Errorf("ERROR: could not marshal instance metadata: %s", err)
  }
  
  r, err := http.Post(INIT_URL, "application/json", bytes.NewBuffer(data))
  if err != nil {
    return "", fmt.Errorf("Could not send HTTP POST request: %s", err)
  }
  defer r.Body.Close()
  return id.InstanceID, nil
}

func main() {
  fs, _ := procfs.NewDefaultFS()
  finishedChan := make(chan Usage)
  usageChan := make(chan Usage)
  procs := make(map[int]struct{})
  imdsClient := imds.New(imds.Options{})
  
  i, err := postMetadata(imdsClient)
  if err != nil {
    log.Fatalf("ERROR: could not instance metadata: %s", err)
  }

  // handle usage produced in monitors
  go handleUsage(i, usageChan)
  
  // garbage collect dead procs
  go gc(i, finishedChan, procs)
  
  for {
    for _, pid := range hadoopProcs(&fs) {
      _, ok := procs[pid]; if ok {
        continue
      }
      // start monitoring
      procs[pid] = struct{}{}
      go monitor(&fs, pid, finishedChan, usageChan)
    }
    time.Sleep(1 * time.Second)
  }
}


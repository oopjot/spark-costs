#!/usr/bin/env python3

import requests as r
import random
import time
from datetime import datetime
from uuid import uuid4 as uuid
from threading import Thread

"""
const (
  USAGE_URL = "http://127.0.0.1:8000/instance/%s/usage"
  INIT_URL = "http://127.0.0.1:8000/instance"
  FINISHED_URL = "http://127.0.0.1:8000/container/%s/finished"
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
"""


USAGE_URL = "http://127.0.0.1:8000/instance/{}/usage"
INIT_URL = "http://127.0.0.1:8000/instance"
FINISHED_URL = "http://127.0.0.1:8000/container/{}/finish"

NODE_TYPES = ["m5.8xlarge", "m5.16xlarge", "m5.4xlarge"]
NODE_KINDS = ["on-demand", "spot"]

def generate_nodes(n=16):
    for _ in range(n):
        instance_id = f"i-{uuid().hex[:17]}"
        node_data = {
            "instance_id": instance_id,
            "hostname": instance_id,
            "kind": random.choice(NODE_KINDS),
            "instance_type": random.choice(NODE_TYPES),
            "private_ip": f"10.1.1.{random.randint(2, 254)}",
            "region": "us-west-2",
            "az": "us-west-2a",
            "image_id": "imageid",
            "launch_time": str(datetime.now()),
            "architecture": "x86_64",
        }
        r.post(INIT_URL, json=node_data)
        print(instance_id, "initialized")
        yield instance_id

def generate_applications(n=5):
    for _ in range(n):
        app_number = random.randint(10**12, 10**13 - 1)
        name = f"application_{app_number}_1"
        yield name, app_number

def generate_containers(app_number, n=8):
    for i in range(n):
        name = f"container_{app_number}_1_1_{i}"
        yield name

def generate_container_usage(instance_id, app_name, container_name):
    running = True
    avg_cpu = random.randint(10, 40)
    pid = random.randint(2000, 8000)
    process_time = 0
    start = datetime.now()
    then = start
    count = 0
    print(container_name, "started")
    while running:
        now = datetime.now()
        process_time += (now - then).microseconds / 1000
        then = now

        usage_data = {
            "pid": pid,
            "app": app_name,
            "container": container_name,
            "start": time.mktime(start.timetuple()),
            "process_time": process_time,
            "cpu_time": process_time / avg_cpu,
            "cpu_usage": avg_cpu,
            "time": time.mktime(now.timetuple()),
        }
        print(now, container_name, usage_data)
        r.post(USAGE_URL.format(instance_id), json=usage_data)

        time.sleep(2)
        count += 1
        if count == 10:
            res = r.post(FINISHED_URL.format(container_name))
            print(res.json())
            running = False


if __name__ == "__main__":
    instance_ids = list(generate_nodes())
    applications = generate_applications()
    for app_name, app_number in applications:
        containers = generate_containers(app_number, random.randint(5, 8)) 
        for cname in containers:
            instance = random.choice(instance_ids) 
            t = Thread(target=generate_container_usage, args=(instance, app_name, cname))
            t.start()
            print(cname, "finished")

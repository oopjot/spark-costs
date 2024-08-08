from datetime import datetime
from pydantic import BaseModel

from model import Kind

class InstanceCreate(BaseModel):
    instance_id: str
    hostname: str
    kind: str
    instance_type: str
    private_ip: str
    region: str
    az: str
    image_id: str
    launch_time: datetime
    architecture: str

class Instance(BaseModel):
    id: int
    instance_id: str
    name: str
    instance_type: str
    private_ip: str
    kind: Kind
    
    class Config:
        orm_mode = True

class UsageCreate(BaseModel):
    pid: int
    app: str
    container: str
    start: float
    process_time: float
    cpu_time: float
    cpu_usage: float
    time: int


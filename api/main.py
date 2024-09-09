from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from database import get_db
import schema
import crud
import worker

app = FastAPI()

@app.post("/instance")
async def register_instance(instance_data: schema.InstanceCreate, db: Session = Depends(get_db)):
    instance = crud.create_instance(db, instance_data)
    db.commit()
    return {"id": instance.id}

@app.post("/instance/{instance_id}/usage")
async def handle_usage(instance_id: str, usage_data: schema.UsageCreate, db: Session = Depends(get_db)):
    usage = crud.create_usage(db, instance_id, usage_data)
    db.commit()
    return {"id": usage.id}

@app.post("/container/{container_name}/finish")
async def handle_container_finished(container_name: str, db: Session = Depends(get_db)):
    container = crud.mark_container_finished(db, container_name)
    app_finished = True
    for c in container.application.containers:
        app_finished = c.finished
    if app_finished:
        container.application.finished = True
    db.commit()
    worker.calculate_container_cost.delay(container_name)
    return {"id": container.id}

@app.get("/applications")
async def list_applications(db: Session = Depends(get_db)):
    applications = crud.list_applications(db)
    return list(applications)

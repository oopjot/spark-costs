from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from database import get_db
import schema
import crud

app = FastAPI()

@app.post("/instance")
async def register_instance(instance_data: schema.InstanceCreate, db: Session = Depends(get_db)):
    instance = crud.create_instance(db, instance_data)
    db.commit()
    return {"message": f"Instance {instance.instance_id} registered."}

@app.post("/instance/{instance_id}/usage")
async def handle_usage(instance_id: str, usage_data: schema.UsageCreate, db: Session = Depends(get_db)):
    usage = crud.create_usage(db, instance_id, usage_data)
    db.commit()
    return {"message": f"Usage for container {usage.container.name} saved."}

@app.post("/container/{container_name}/finish")
async def handle_container_finished(container_name: str, db: Session = Depends(get_db)):
    container = crud.mark_container_finished(db, container_name)
    db.commit()
    return {"message": f"Marked container {container.name} finished."}


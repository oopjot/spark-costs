from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
import schema
import crud
import worker

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

@app.post("/instance")
async def register_instance(instance_data: schema.InstanceCreate, db: Session = Depends(get_db)):
    instance = crud.create_instance(db, instance_data)
    db.commit()
    db.close()
    return {"id": instance.id}

@app.post("/instance/{instance_id}/usage")
async def handle_usage(instance_id: str, usage_data: schema.UsageCreate, db: Session = Depends(get_db)):
    usage = crud.create_usage(db, instance_id, usage_data)
    db.commit()
    db.close()
    return {"id": usage.id}

@app.post("/container/{container_name}/finish")
async def handle_container_finished(container_name: str, db: Session = Depends(get_db)):
    container = crud.mark_container_finished(db, container_name)
    db.commit()
    db.close()
    worker.calculate_container_cost.delay(container_name)
    return {"id": container.id}

@app.get("/", response_class=HTMLResponse)
async def app_list_view(request: Request, db: Session = Depends(get_db)):
    apps = crud.list_applications(db)
    return templates.TemplateResponse(
        request=request,
        name="list.html",
        context={"applications": list(apps)}
    )

@app.get("/{name}", response_class=HTMLResponse)
async def app_detail_view(request: Request, name: str, db: Session = Depends(get_db)):
    app = crud.get_application_by_name(db, name)
    cost = crud.get_application_cost_by_name(db, name)
    
    return templates.TemplateResponse(
        request=request,
        name="detail.html",
        context={"app": app, "cost": cost}
    )

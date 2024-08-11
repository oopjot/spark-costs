from sqlalchemy import select 
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from model import Usage, Container, Application, Instance, ContainerCost
import schema
from datetime import datetime

def get_application_by_name(session: Session, name: str):
    stmt = select(Application).where(Application.name == name)
    app = session.scalar(stmt)
    return app

def get_container_by_name(session: Session, name: str):
    stmt = select(Container).where(Container.name == name)
    container = session.scalar(stmt)
    return container

def get_instance_by_instance_id(session: Session, instance_id: str):
    stmt = select(Instance).where(Instance.instance_id == instance_id)
    instance = session.scalar(stmt)
    return instance

def create_instance(session: Session, instance_schema: schema.InstanceCreate):
    instance = Instance(**instance_schema.model_dump())
    session.add(instance)
    return instance

def create_application(session: Session, name: str):
    app = Application(name=name)
    session.add(app)
    return app

def create_container(session: Session, name: str, instance: Instance, application: Application):
    container = Container(name=name, instance=instance, application=application)
    session.add(container)
    return container

def create_usage(session: Session, instance_id: str, usage_schema: schema.UsageCreate):
    data = usage_schema.model_dump()
    # retrieve instance if exists
    instance = get_instance_by_instance_id(session, instance_id)
    if instance is None:
        # TODO: custom exception
        raise Exception("Instance not found")

    app_name = data.pop("app")
    app = get_application_by_name(session, app_name)
    if app is None:
        app = create_application(session, app_name)
    session.add(app)

    container_name = data.pop("container")
    container = get_container_by_name(session, container_name)
    if container is None:
        container = create_container(session, container_name, instance, app)
    session.add(container)

    data["start"] = datetime.utcfromtimestamp(data.pop("start"))
    usage = Usage(container=container, **data)
    session.add(usage)
    return usage

def mark_container_finished(session: Session, container_name: str):
    container = get_container_by_name(session, container_name)
    if container is None:
        print(container_name)
        # TODO: custom excetpion
        raise Exception("Container not found.")
    container.finished = True
    session.add(container)
    return container

def get_container_first_usage(session: Session, container: Container):
    stmt = select(Usage).where(Container.id == container.id).order_by(Usage.time.asc())
    usage = session.scalars(stmt)
    if not usage:
        raise Exception("Usage not found")
    return usage.one()

def get_container_last_usage(session: Session, container: Container):
    stmt = select(Usage).where(Container.id == container.id).order_by(Usage.time.desc())
    usage = session.scalars(stmt)
    if not usage:
        raise Exception("Usage not found")
    return usage.one()

def get_container_average_cpu_usage(session: Session, container: Container):
    stmt = select(func.avg(Usage.cpu_usage)).where(Container.id == container.id)
    average_usage = session.scalar(stmt)
    return average_usage

def create_container_cost(session: Session, container: Container, amount: int):
    cost = ContainerCost(amount=amount, container_id=container.id)
    session.add(cost)
    return cost

def maybe_mark_application_finished(session: Session, application_id: int):
    stmt = select(func.bool_and(Container.finished)).where(Container.application_id == application_id)
    finished = session.scalar(stmt)
    if not finished:
        return False
    stmt = select(Application).where(Application.id == application_id)
    app = session.scalar(stmt)
    if app is None:
        # TODO: Custom exception
        raise Exception("Application not found.")
    app.finished = True
    session.add(app)
    return finished

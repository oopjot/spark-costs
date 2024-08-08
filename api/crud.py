from sqlalchemy import select
from sqlalchemy.orm import Session
from model import Usage, Container, Application, Instance
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
        # TODO: custom excetpion
        raise Exception("Container not found.")
    container.finished = True
    session.add(container)
    return container


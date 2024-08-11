from datetime import datetime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Instance(Base):
    __tablename__ = "instance"

    id: Mapped[int] = mapped_column(primary_key=True)
    instance_id: Mapped[str]
    hostname: Mapped[str]
    kind: Mapped[str]
    instance_type: Mapped[str]
    private_ip: Mapped[str]
    region: Mapped[str]
    az: Mapped[str]
    image_id: Mapped[str]
    launch_time: Mapped[datetime]
    architecture: Mapped[str]

    containers: Mapped[list["Container"]] = relationship()

class Application(Base):
    __tablename__ = "application"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    finished: Mapped[bool] = mapped_column(default=False)

    containers: Mapped[list["Container"]] = relationship(back_populates="application")

class Container(Base):
    __tablename__ = "container"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    finished: Mapped[bool] = mapped_column(default=False)
    
    instance_id: Mapped[int] = mapped_column(ForeignKey("instance.id"))
    instance: Mapped[Instance] = relationship(back_populates="containers")
    usages: Mapped[list["Usage"]] = relationship(back_populates="container")
    
    application_id: Mapped[int] = mapped_column(ForeignKey("application.id"))
    application: Mapped[Application] = relationship(back_populates="containers")

    cost: Mapped["ContainerCost"] = relationship(back_populates="container")

class Usage(Base):
    __tablename__ = "usage"

    id: Mapped[int] = mapped_column(primary_key=True)
    pid: Mapped[int]
    start: Mapped[datetime]
    process_time: Mapped[float]
    cpu_time: Mapped[float]
    cpu_usage: Mapped[float]
    time: Mapped[int]
    
    container_id: Mapped[int] = mapped_column(ForeignKey("container.id"))
    container: Mapped[Container] = relationship(back_populates="usages")

class ContainerCost(Base):
    __tablename__ = "container_cost"

    id: Mapped[int] = mapped_column(primary_key=True)
    amount: Mapped[int]

    container_id: Mapped[int] = mapped_column(ForeignKey("container.id"))
    container: Mapped[Container] = relationship(back_populates="cost")


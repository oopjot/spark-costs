import os
import json
from datetime import datetime, timedelta

import boto3
from celery import Celery

import config
import crud
import database
from enums import Kind
from model import ContainerCost


celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379")
celery.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379")

AWS_REGION_MAP = config.load_region_map()

def get_elapsed_hours(first_ts, last_ts):
    first_dt = datetime.fromtimestamp(first_ts)
    last_dt = datetime.fromtimestamp(last_ts)
    elapsed_td = first_dt - last_dt
    return elapsed_td.days * 24 + elapsed_td.seconds / 3600


def get_region_name(region):
    aws_region_map = config.load_region_map()

    region_name = aws_region_map[region]["description"]
    region_name = region_name.replace("Europe", "EU")
    return region_name


def get_hourly_price(instance_type, region="us-west-2"):
    region_name = get_region_name(region)
    capacity_status = "Used"

    filters = [
        {"Field": "tenancy", "Value": "Shared", "Type": "TERM_MATCH"},
        {"Field": "operatingSystem", "Value": "Linux", "Type": "TERM_MATCH"},
        {"Field": "preInstalledSw", "Value": "NA", "Type": "TERM_MATCH"},
        {"Field": "instanceType", "Value": instance_type, "Type": "TERM_MATCH"},
        {"Field": "location", "Value": region_name, "Type": "TERM_MATCH"},
        {"Field": "capacitystatus", "Value": capacity_status, "Type": "TERM_MATCH"},
    ]
    
    client = boto3.client("pricing", region_name="us-east-1")
    response = client.get_products(ServiceCode="AmazonEC2", Filters=filters)
    for price in response["PriceList"]:
        price = json.loads(price)
        price_value = None
        
        for on_demand in price["terms"]["OnDemand"].values():
            for price_dimensions in on_demand["priceDimensions"].values():
                price_value = price_dimensions["pricePerUnit"]["USD"]

        if price_value is not None:
            return float(price_value)

    return None

def process_on_demand_container(session, container):
    first_usage = crud.get_container_first_usage(session, container)
    last_usage = crud.get_container_last_usage(session, container)
    elapsed_hours = get_elapsed_hours(first_usage.time, last_usage.time)
    price = get_hourly_price(container.instance.kind, container.instance.region)
    if price is None:
        # TODO: Custom exception
        raise Exception("Price for instance not found.")

    average_cpu_usage = crud.get_container_average_cpu_usage(session, container)
    container_cost_amount = int(price * elapsed_hours * average_cpu_usage * 100)
    crud.create_container_cost(session, container, container_cost_amount)
    
def process_spot_container(session, container):
    pass

@celery.task(name="calculate_container_cost")
def calculate_container_cost(container_name):
    # TODO: Logging
    session = next(database.get_db())
    container = crud.get_container_by_name(session, container_name)
    if container is None:
        # TODO: custom exception
        raise Exception("Container not found.")
    if container.instance.kind == Kind.ON_DEMAND.value:
        print("-----CALCULATING ON DEMAND-----")
        process_on_demand_container(session, container)
    else:
        process_spot_container(session, container)

    _ = crud.maybe_mark_application_finished(session, container.application_id)
    # TODO: logging
    session.commit()
    session.close()
    return True


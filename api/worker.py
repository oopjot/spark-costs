import os
import json
from datetime import datetime

import boto3
from celery import Celery

import config
import crud
import database
from enums import Kind


celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379")
celery.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379")

AWS_REGION_MAP = config.load_region_map()

def calculate_cost(price, elapsed_hours, avg_cpu_usage_percent):
    return price * elapsed_hours * avg_cpu_usage_percent / 100


def get_elapsed_hours(first_ts, last_ts):
    first_dt = datetime.fromtimestamp(first_ts)
    last_dt = datetime.fromtimestamp(last_ts)
    elapsed_td = last_dt - first_dt
    return elapsed_td.days * 24 + elapsed_td.seconds / 3600


def get_region_name(region):
    aws_region_map = config.load_region_map()

    region_name = aws_region_map[region]["description"]
    region_name = region_name.replace("Europe", "EU")
    return region_name


def get_on_demand_hourly_price(instance_type, region="us-west-2"):
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

def calculate_container_cost_amount(session, container, price):
    first_usage = crud.get_container_first_usage(session, container)
    last_usage = crud.get_container_last_usage(session, container)
    elapsed_hours = get_elapsed_hours(first_usage.time, last_usage.time)
    average_cpu_usage = crud.get_container_average_cpu_usage(session, container)
    container_cost_amount = calculate_cost(price, elapsed_hours, average_cpu_usage)
    return container_cost_amount
    

def process_on_demand_container(session, container):
    price = get_on_demand_hourly_price(container.instance.instance_type, container.instance.region)
    if price is None:
        # TODO: Custom exception
        raise Exception("Price for instance not found.")
    
    container_cost_amount = calculate_container_cost_amount(session, container, price)
    crud.create_container_cost(session, container, container_cost_amount)
    crud.maybe_update_application_finish_time(session, container)

def get_spot_prices(instance_type, az, start_ts, end_ts, region="us-west-2"):
    start_dt = datetime.fromtimestamp(start_ts)
    end_dt = datetime.fromtimestamp(end_ts)

    client = boto3.client("ec2", region_name=region)
    response = client.describe_spot_price_history(
        StartTime=start_dt,
        EndTime=end_dt,
        AvailabilityZone=az,
        InstanceTypes=[instance_type],
        ProductDescriptions=["Linux/UNIX"]
    )
    items = response["SpotPriceHistory"][::-1]
    return [{"timestamp": datetime.timestamp(i["Timestamp"]), "price": float(i["SpotPrice"])} for i in items]

def process_spot_container(session, container):
    first_usage = crud.get_container_first_usage(session, container)
    last_usage = crud.get_container_last_usage(session, container)
    spot_prices = get_spot_prices(
        container.instance.instance_type, 
        container.instance.az,
        first_usage.time,
        last_usage.time
    )
    if len(spot_prices) == 1:
        price = spot_prices[0]["price"]
        container_cost_amount = calculate_container_cost_amount(session, container, price)
    else:
        container_cost_amount = 0
        i = 0
        for i in range(0, len(spot_prices) - 1):
            current_price = spot_prices[i]
            start_ts = current_price["timestamp"]
            end_ts =  spot_prices[i + 1]["timestamp"]
            average_cpu_usage = crud.get_container_average_cpu_usage_for_time_range(session, container, start_ts, end_ts)
            elapsed_hours = get_elapsed_hours(start_ts, end_ts)
            container_cost_amount += calculate_cost(current_price["price"], elapsed_hours, average_cpu_usage)
            i += 1
        
    crud.create_container_cost(session, container, container_cost_amount)
    crud.maybe_update_application_finish_time(session, container, last_usage)

@celery.task(name="calculate_container_cost")
def calculate_container_cost(container_name):
    # TODO: Logging
    session = next(database.get_db())
    container = crud.get_container_by_name(session, container_name)
    if container is None:
        # TODO: custom exception
        raise Exception("Container not found.")
    if container.instance.kind == Kind.ON_DEMAND.value:
        process_on_demand_container(session, container)
    else:
        process_spot_container(session, container)

    crud.maybe_mark_application_finished(session, container.application_id)
    # TODO: logging
    session.commit()
    session.close()
    return True


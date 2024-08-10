import os
import json
import time

import boto3
from celery import Celery

import config


celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379")
celery.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379")

AWS_REGION_MAP = config.load_region_map()

def get_region_name(region):
    if AWS_REGION_MAP is None:
        AWS_REGION_MAP = config.load_region_map()

    region_name = AWS_REGION_MAP[region]["description"]
    region_name = region_name.replace("Europe", "EU")
    return region_name


def get_price(instance_type, region="us-west-2"):
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
        
        print(price["terms"]["OnDemand"].values())
        for on_demand in price["terms"]["OnDemand"].values():
            for price_dimensions in on_demand["priceDimensions"].values():
                price_value = price_dimensions["pricePerUnit"]["USD"]

        if price_value is not None:
            return float(price_value)

    return None

@celery.task(name="calculate_cost")
def calculate_container_cost(container_name):
    print(f"Calculating cost for {container_name}")
    time.sleep(5)
    print("Done.")
    return True


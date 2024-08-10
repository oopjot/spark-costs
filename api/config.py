import os
import json
from pkg_resources import resource_filename

def get_postgres_uri():
    host = os.environ.get("DB_HOST")
    port = os.environ.get("DB_PORT")
    password = os.environ.get("DB_PASSWORD")
    user = os.environ.get("DB_USER")
    db_name = os.environ.get("DB_NAME")
    return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"


def get_secret_api_key():
    return os.environ.get("SECRET_API_KEY", "")

def load_region_map():
    endpoint_file = resource_filename("botocore", "data/endpoints.json")
    with open(endpoint_file, "r") as f:
        endpoint_data = json.load(f)

    return endpoint_data["partitions"][0]["regions"]

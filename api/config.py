import os

def get_postgres_uri():
    host = os.environ.get("DB_HOST")
    port = os.environ.get("DB_PORT")
    password = os.environ.get("DB_PASSWORD")
    user = os.environ.get("DB_USER")
    db_name = os.environ.get("DB_NAME")
    return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"


def get_secret_api_key():
    return os.environ.get("SECRET_API_KEY", "")


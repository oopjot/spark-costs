from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import config
from model import Base

postgres_uri = config.get_postgres_uri()

engine = create_engine(postgres_uri, echo=True)
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from src.app.core.config.config import settings
from src.app.models import Base

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    all_tables = Base.metadata.tables.keys()
    created_tables = []

    for table_name in all_tables:
        if table_name not in existing_tables:
            Base.metadata.create_all(
                bind=engine, tables=[Base.metadata.tables[table_name]]
            )
            created_tables.append(table_name)

    return created_tables

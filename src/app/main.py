from fastapi import FastAPI
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Welcome to Messenger API!"}

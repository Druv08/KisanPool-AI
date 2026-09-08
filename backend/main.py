from fastapi import FastAPI
from models import create_tables
from database import get_db_connection

app = FastAPI()

# Create database tables
create_tables()


@app.get("/")
def home():
    return {"message": "KisanPool AI Backend is running!"}


@app.get("/farmers")
def get_farmers():
    connection = get_db_connection()

    farmers = connection.execute(
        "SELECT * FROM farmers"
    ).fetchall()

    connection.close()

    return [dict(farmer) for farmer in farmers]





@app.get("/resources")
def get_resources():
    connection = get_db_connection()

    resources = connection.execute(
        "SELECT * FROM resources"
    ).fetchall()

    connection.close()

    return [dict(resource) for resource in resources]

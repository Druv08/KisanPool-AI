from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

try:
    from .database import get_db_connection
    from .models import create_tables
    from .services.planner_service import build_plan_from_database
except ImportError:  # Direct execution from the backend directory.
    from database import get_db_connection
    from models import create_tables
    from services.planner_service import build_plan_from_database

app = FastAPI()


class PlanRequest(BaseModel):
    farmer_id: int
    message: str = Field(min_length=1)


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


@app.post("/plan")
def create_backend_plan(request: PlanRequest):
    connection = get_db_connection()
    try:
        return build_plan_from_database(
            farmer_id=request.farmer_id,
            message=request.message,
            connection=connection,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        connection.close()

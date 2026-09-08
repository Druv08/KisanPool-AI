from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from .database import get_db_connection
    from .models import create_tables
    from .services.planner_service import build_plan_from_database
except ImportError:
    from database import get_db_connection
    from models import create_tables
    from services.planner_service import build_plan_from_database

from services.pipeline import process_message
from services.resource_adapter import get_optimizer_resources


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PlanRequest(BaseModel):
    farmer_id: int
    message: str = Field(min_length=1)


class AIChatRequest(BaseModel):
    message: str
    farmer_id: int = 1


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
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    finally:
        connection.close()


@app.post("/ai/chat")
def ai_chat(request: AIChatRequest):

    resources = get_optimizer_resources()

    # For the current MVP, farmer 1 is Ravi Kumar.
    farmer_location = {
        "latitude": 12.823,
        "longitude": 80.044,
    }

    result = process_message(
        message=request.message,
        farmer_id=request.farmer_id,
        resources=resources,
        farmer_location=farmer_location,
    )

    return result
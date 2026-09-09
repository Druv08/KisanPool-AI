from urllib import request

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from models import create_tables
from database import get_db_connection

from services.pipeline import process_message
from services.resource_adapter import get_optimizer_resources
from services.session import ConversationSession


app = FastAPI()

# --------------------------------------------------
# CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# Database
# --------------------------------------------------

create_tables()


# --------------------------------------------------
# Conversation sessions
# --------------------------------------------------


# --------------------------------------------------
# Request model
# --------------------------------------------------

class PlanRequest(BaseModel):
    message: str
    farmer_id: int = 1


# --------------------------------------------------
# Farmer location
# --------------------------------------------------

VILLAGE_COORDINATES = {
    "Kattankulathur": {
        "latitude": 12.823,
        "longitude": 80.044,
    },
    "Potheri": {
        "latitude": 12.828,
        "longitude": 80.046,
    },
    "Maraimalai Nagar": {
        "latitude": 12.820,
        "longitude": 80.040,
    },
}


def get_farmer_location(farmer_id: int):
    connection = get_db_connection()

    farmer = connection.execute(
        "SELECT village FROM farmers WHERE id = ?",
        (farmer_id,),
    ).fetchone()

    connection.close()

    if farmer is None:
        return None

    village = farmer["village"]

    return VILLAGE_COORDINATES.get(
        village,
        {
            "latitude": 12.823,
            "longitude": 80.044,
        },
    )


# --------------------------------------------------
# Home
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "KisanPool AI Backend is running!"
    }


# --------------------------------------------------
# Farmers
# --------------------------------------------------

@app.get("/farmers")
def get_farmers():
    connection = get_db_connection()

    farmers = connection.execute(
        "SELECT * FROM farmers"
    ).fetchall()

    connection.close()

    return [dict(farmer) for farmer in farmers]


# --------------------------------------------------
# Resources
# --------------------------------------------------

@app.get("/resources")
def get_resources():
    connection = get_db_connection()

    resources = connection.execute(
        "SELECT * FROM resources"
    ).fetchall()

    connection.close()

    return [dict(resource) for resource in resources]


# --------------------------------------------------
# Main AI Plan endpoint
# --------------------------------------------------

@app.post("/plan")
def create_plan(request: PlanRequest):

    farmer_location = get_farmer_location(
        request.farmer_id
    )

    if farmer_location is None:
        return {
            "status": "error",
            "message": "Farmer could not be found.",
        }

    resources = get_optimizer_resources()

    session = ConversationSession(request.farmer_id)

    result = process_message(
        message=request.message,
        farmer_id=request.farmer_id,
        resources=resources,
        farmer_location=farmer_location,
        session=None,
    )

    return result


# --------------------------------------------------
# Backward-compatible chatbot endpoint
# --------------------------------------------------

@app.post("/ai/chat")
def ai_chat(request: PlanRequest):

    return create_plan(request)
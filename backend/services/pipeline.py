"""End-to-end KisanPool AI request pipeline."""

from __future__ import annotations

print("🔥 NEW PIPELINE.PY LOADED 🔥")

from typing import Any

from services.recommendation import generate_recommendation
from services.session import ConversationSession
from services.conversation import merge_requests
from services.optimizer import create_plan
from services.parser import parse_request
from services.validator import (
    get_missing_questions,
    validate_request,
)


def process_message(
    message: str,
    farmer_id: int,
    resources: list[dict[str, Any]],
    farmer_location: dict[str, float],
    session: ConversationSession | None = None,
    current_request: dict[str, Any] | None = None,
) -> dict[str, Any]:

    """Process a farmer message.

    Parses the new message, retrieves the previous request from
    the persistent session, merges both, validates the combined
    request, and runs the optimizer when enough information exists.
    """

    # --------------------------------
    # LOAD PREVIOUS SESSION
    # --------------------------------

    if session is not None:
        current_request = session.get()

    # --------------------------------
    # PARSE NEW MESSAGE
    # --------------------------------

    new_request = parse_request(
        message,
        farmer_id=farmer_id,
    )

    # --------------------------------
    # MERGE OLD + NEW REQUEST
    # --------------------------------

    if current_request is not None:
        request_data = merge_requests(
            current_request,
            new_request,
        )
    else:
        request_data = new_request

    # --------------------------------
    # DEBUG
    # --------------------------------

    print("====================================")
    print("========== PIPELINE DEBUG ==========")
    print("CURRENT REQUEST:", current_request)
    print("NEW REQUEST:", new_request)
    print("MERGED REQUEST:", request_data)
    print("MESSAGE:", message)
    print("====================================")

    # --------------------------------
    # SAVE SESSION
    # --------------------------------

    if session is not None:
        print("SAVING SESSION:", request_data)

        session.update(request_data)

        print("SESSION AFTER SAVE:", session.get())

    # --------------------------------
    # VALIDATE
    # --------------------------------

    validation = validate_request(request_data)

    if not validation["valid"]:
        return {
            "status": "needs_information",
            "request": request_data,
            "questions": get_missing_questions(validation),
        }

    # --------------------------------
    # CREATE OPTIMIZED PLAN
    # --------------------------------

    plan = create_plan(
        request_data,
        resources,
        farmer_location,
    )

    # --------------------------------
    # RECOMMENDATION
    # --------------------------------

    recommendation = generate_recommendation(plan)

    return {
        "status": "optimized",
        "request": request_data,
        "plan": plan,
        "recommendation": recommendation,
    }
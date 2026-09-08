"""Validation layer for parsed KisanPool AI requests."""

from __future__ import annotations

from typing import Any


def validate_request(request: dict[str, Any]) -> dict[str, Any]:
    """Check whether a parsed request contains enough information to optimize."""

    missing: list[str] = []

    # Crop is required to understand what the farmer is growing.
    if not request.get("crop"):
        missing.append("crop")

    # Farm area is required for machinery/time estimation.
    if request.get("area") is None:
        missing.append("area")

    requirements = request.get("requirements", {})

    # At least one resource must be requested.
    resource_requested = any(
        value is True
        for key, value in requirements.items()
        if key in {"tractor", "solar_pump"}
    )

    # Seed requirements also count as a resource request.
    seed_requested = any(
        key.endswith("_seed_kg") and value is not None
        for key, value in requirements.items()
    )

    if not resource_requested and not seed_requested:
        missing.append("resource")

    return {
        "valid": len(missing) == 0,
        "missing": missing,
    }

def get_missing_questions(validation: dict[str, Any]) -> list[str]:
    """Convert missing fields into questions for the farmer."""

    questions = []

    for field in validation.get("missing", []):
        if field == "crop":
            questions.append("What crop are you growing?")

        elif field == "area":
            questions.append("How many acres is your farm?")

        elif field == "resource":
            questions.append(
                "What do you need help arranging, such as a tractor, "
                "irrigation, or seeds?"
            )

    return questions
"""Natural-language request parser for KisanPool AI.

Converts simple farmer messages into the structured request format
expected by services.optimizer.create_plan().
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any


def _parse_date(text: str, today: date | None = None) -> str | None:
    """Extract a requested date from natural language."""
    today = today or date.today()
    lowered = text.lower()

    if "day after tomorrow" in lowered:
        return (today + timedelta(days=2)).isoformat()

    if "tomorrow" in lowered:
        return (today + timedelta(days=1)).isoformat()

    if "today" in lowered:
        return today.isoformat()

    # Explicit YYYY-MM-DD date
    match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if match:
        return match.group(1)

    # "next week" means 7 days from today
    if "next week" in lowered:
        return (today + timedelta(days=7)).isoformat()

    # "this <weekday>" means the next occurrence of that weekday
    weekdays = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    for name, weekday in weekdays.items():
        if f"this {name}" in lowered:
            days_ahead = (weekday - today.weekday()) % 7

            # If today is that weekday, use today.
            return (today + timedelta(days=days_ahead)).isoformat()

    # Default to today if no date was mentioned.
    return None

def parse_request(
    message: str,
    farmer_id: int = 1,
    today: date | None = None,
) -> dict[str, Any]:
    """Convert a simple farmer message into an optimizer request."""

    if not isinstance(message, str) or not message.strip():
        raise ValueError("message must be a non-empty string")

    text = message.strip()
    lowered = text.lower()

    # Crop
    crop = None
    crops = [
        "tomato",
        "rice",
        "wheat",
        "maize",
        "corn",
        "potato",
        "onion",
        "groundnut",
        "sugarcane",
    ]

    for candidate in crops:
        if candidate in lowered:
            crop = "maize" if candidate == "corn" else candidate
            break

    # Farm area
    area = None
    area_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:acre|acres|ac)",
        lowered,
    )
    if area_match:
        area = float(area_match.group(1))
        if area.is_integer():
            area = int(area)

    # Tractor / machinery
    tractor_requested = bool(
        re.search(r"\btractor\b", lowered)
        or re.search(r"\bmachine\b", lowered)
        or re.search(r"\bmachinery\b", lowered)
    )

    # Irrigation / solar pump
    irrigation_requested = bool(
        re.search(r"\birrigat(?:e|ion|ing)\b", lowered)
        or re.search(r"\bwater(?:ing)?\b", lowered)
        or re.search(r"\bpump\b", lowered)
        or re.search(r"\bsolar\s+pump\b", lowered)
    )

    # Seed quantity
    seed_quantity = None
    seed_match = re.search(
        r"(\d+(?:\.\d+)?)\s*"
        r"(?:kg|kgs|kilo|kilos|kilogram|kilograms)\s*"
        r"(?:of\s+)?"
        r"(?:[\w-]+\s+)?"
        r"seeds?\b",
        lowered,
    )

    if seed_match:
        seed_quantity = float(seed_match.group(1))
        if seed_quantity.is_integer():
            seed_quantity = int(seed_quantity)

    requirements: dict[str, Any] = {
        "tractor": tractor_requested,
        "solar_pump": irrigation_requested,
    }

    if crop and seed_quantity is not None:
        requirements[f"{crop}_seed_kg"] = seed_quantity

    return {
        "farmer_id": farmer_id,
        "crop": crop,
        "area": area,
        "date": _parse_date(text, today),
        "requirements": requirements,
    }
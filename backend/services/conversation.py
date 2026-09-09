from __future__ import annotations

from typing import Any


def merge_requests(
    current: dict[str, Any],
    new: dict[str, Any],
) -> dict[str, Any]:
    """Merge newly provided information into the existing request."""

    merged = current.copy()

    # Keep existing farmer ID unless a new one is provided
    if new.get("farmer_id") is not None:
        merged["farmer_id"] = new["farmer_id"]

    # Only replace crop when the new message actually contains one
    if new.get("crop") is not None:
        merged["crop"] = new["crop"]

    # Only replace area when the new message actually contains one
    if new.get("area") is not None:
        merged["area"] = new["area"]

    # Keep the previously detected date unless a new one was provided
    if new.get("date") is not None:
        merged["date"] = new["date"]

    # Merge resource requirements
    current_requirements = merged.get("requirements", {}).copy()
    new_requirements = new.get("requirements", {})

    for key, value in new_requirements.items():

        # Boolean resource requirements
        if value is True:
            current_requirements[key] = True

        # Seed quantities
        elif key.endswith("_seed_kg") and value is not None:
            current_requirements[key] = value

    merged["requirements"] = current_requirements

    return merged
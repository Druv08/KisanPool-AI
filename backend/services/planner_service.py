"""Application service joining backend-shaped data to the pure optimizer."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from .optimizer import create_plan
from .resource_adapter import normalize_resources, village_location


def _row_dict(row: Any) -> dict[str, Any]:
    if isinstance(row, Mapping):
        return dict(row)
    try:
        return dict(row)
    except (TypeError, ValueError) as exc:
        raise ValueError("farmer row must be mapping-like") from exc


def build_plan_from_backend_data(
    request: Mapping[str, Any],
    farmers: Iterable[Any],
    resources: Iterable[Any],
    bookings: Iterable[Any],
) -> dict[str, Any]:
    """Build a plan from plain backend rows, without accessing the database."""

    if not isinstance(request, Mapping):
        raise ValueError("request must be a mapping")
    farmer_id = request.get("farmer_id")
    if farmer_id is None:
        raise ValueError("request.farmer_id is required")

    farmer_rows = [_row_dict(farmer) for farmer in farmers]
    requesting_farmer = next(
        (
            farmer
            for farmer in farmer_rows
            if str(farmer.get("id")) == str(farmer_id)
        ),
        None,
    )
    if requesting_farmer is None:
        raise ValueError(f"farmer {farmer_id!r} was not found")

    if (
        requesting_farmer.get("latitude") is not None
        and requesting_farmer.get("longitude") is not None
    ):
        farmer_location = {
            "latitude": requesting_farmer["latitude"],
            "longitude": requesting_farmer["longitude"],
        }
    else:
        farmer_location = village_location(requesting_farmer.get("village"))

    normalized_resources = normalize_resources(
        resources,
        farmer_rows,
        bookings,
    )
    return create_plan(request, normalized_resources, farmer_location)


__all__ = ["build_plan_from_backend_data"]

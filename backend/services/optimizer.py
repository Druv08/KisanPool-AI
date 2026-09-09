"""Deterministic resource matching for the KisanPool MVP.

This module deliberately has no web-framework, database, maps, or LLM
dependency.  Costs and impact figures are estimates derived from the resource
prices and the transparent baseline rates declared below; they are not
measured real-world outcomes.
"""

from __future__ import annotations

from datetime import datetime
from itertools import combinations
from math import asin, cos, isfinite, radians, sin, sqrt
from typing import Any, Iterable, Mapping, Sequence


EARTH_RADIUS_KM = 6371.0088
MACHINE_HOURS_PER_ACRE = {"tractor": 1.25, "rotavator": 1.0, "harvester": 1.0}
DEFAULT_MACHINE_HOURS = 2.5
DEFAULT_SOLAR_HOURS = 1.5
SOLAR_WINDOW = ("10:00", "16:00")

MACHINE_SCORE_WEIGHTS = {"cost": 0.40, "distance": 0.35, "schedule": 0.25}
SOLAR_SCORE_WEIGHTS = {
    "cost": 0.35,
    "distance": 0.30,
    "schedule": 0.20,
    "sustainability": 0.15,
}

# Reference market rates used only for clearly labelled estimated impact.
BASELINE_MACHINE_RATE_PER_HOUR = {
    "tractor": 900.0,
    "rotavator": 700.0,
    "harvester": 1200.0,
}
BASELINE_IRRIGATION_RATE_PER_HOUR = 200.0
BASELINE_INPUT_RATE_PER_KG = 60.0
BASELINE_TRAVEL_KM_PER_PROVIDER = 10.0

_UNAVAILABLE_STATUSES = {"reserved", "unavailable", "inactive", "maintenance"}
_ACTIVE_BOOKING_STATUSES = {"reserved", "confirmed", "booked", "active"}


def _number(value: Any, field_name: str) -> float:
    """Convert a value to a finite float or raise a useful ValueError."""

    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if not isfinite(result):
        raise ValueError(f"{field_name} must be finite")
    return result


def distance_km(
    farmer_lat: float,
    farmer_lon: float,
    resource_lat: float,
    resource_lon: float,
) -> float:
    """Return the Haversine great-circle distance between two coordinates."""

    lat1 = _number(farmer_lat, "farmer_lat")
    lon1 = _number(farmer_lon, "farmer_lon")
    lat2 = _number(resource_lat, "resource_lat")
    lon2 = _number(resource_lon, "resource_lon")
    if not -90 <= lat1 <= 90 or not -90 <= lat2 <= 90:
        raise ValueError("latitude must be between -90 and 90")
    if not -180 <= lon1 <= 180 or not -180 <= lon2 <= 180:
        raise ValueError("longitude must be between -180 and 180")

    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    haversine = (
        sin(delta_lat / 2) ** 2
        + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * asin(sqrt(haversine))


def _location(location: Any) -> tuple[float, float]:
    if isinstance(location, Mapping):
        return (
            _number(location.get("latitude"), "farmer latitude"),
            _number(location.get("longitude"), "farmer longitude"),
        )
    if isinstance(location, Sequence) and not isinstance(location, (str, bytes)):
        if len(location) == 2:
            return (
                _number(location[0], "farmer latitude"),
                _number(location[1], "farmer longitude"),
            )
    raise ValueError("farmer_location must contain latitude and longitude")


def _resource_distance(resource: Mapping[str, Any], farmer_location: Any) -> float:
    farmer_lat, farmer_lon = _location(farmer_location)
    return distance_km(
        farmer_lat,
        farmer_lon,
        resource.get("latitude"),
        resource.get("longitude"),
    )


def _minutes(value: Any) -> int:
    if not isinstance(value, str):
        raise ValueError("time must be a HH:MM string")
    try:
        parsed = datetime.strptime(value, "%H:%M")
    except ValueError as exc:
        raise ValueError(f"invalid time: {value!r}") from exc
    return parsed.hour * 60 + parsed.minute


def _clock(total_minutes: int) -> str:
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02d}:{minutes:02d}"


def _clean_number(value: float, digits: int = 2) -> int | float:
    rounded = round(value, digits)
    return int(rounded) if rounded.is_integer() else rounded


def _is_available(resource: Mapping[str, Any], requested_date: str | None) -> bool:
    status = str(resource.get("status", "available")).strip().lower()
    if status in _UNAVAILABLE_STATUSES:
        return False
    if status != "available":
        return False

    resource_date = resource.get("date")
    if resource_date is not None and requested_date is not None:
        if str(resource_date) != requested_date:
            return False

    available_dates = resource.get("available_dates")
    if available_dates is not None and requested_date is not None:
        if isinstance(available_dates, (str, bytes)):
            available_dates = [available_dates]
        try:
            if requested_date not in {str(value) for value in available_dates}:
                return False
        except TypeError:
            return False

    unavailable_dates = resource.get("unavailable_dates", [])
    if isinstance(unavailable_dates, (str, bytes)):
        unavailable_dates = [unavailable_dates]
    try:
        if requested_date is not None and requested_date in {
            str(value) for value in unavailable_dates
        }:
            return False
    except TypeError:
        return False
    return True


def _booking_intervals(
    resource: Mapping[str, Any], requested_date: str | None
) -> list[tuple[int, int]]:
    intervals: list[tuple[int, int]] = []
    bookings = resource.get("bookings", [])
    if not isinstance(bookings, Iterable) or isinstance(bookings, (str, bytes, Mapping)):
        return intervals
    for booking in bookings:
        if not isinstance(booking, Mapping):
            continue
        status = str(booking.get("status", "confirmed")).lower()
        if status not in _ACTIVE_BOOKING_STATUSES:
            continue
        booking_date = booking.get("date")
        if booking_date is not None and requested_date is not None:
            if str(booking_date) != requested_date:
                continue
        try:
            start = _minutes(booking.get("start"))
            end = _minutes(booking.get("end"))
        except ValueError:
            continue
        if start < end:
            intervals.append((start, end))
    return sorted(intervals)


def _free_intervals(
    start: int, end: int, blocked: Iterable[tuple[int, int]]
) -> list[tuple[int, int]]:
    free: list[tuple[int, int]] = []
    cursor = start
    for blocked_start, blocked_end in blocked:
        if blocked_end <= cursor or blocked_start >= end:
            continue
        if blocked_start > cursor:
            free.append((cursor, min(blocked_start, end)))
        cursor = max(cursor, blocked_end)
        if cursor >= end:
            break
    if cursor < end:
        free.append((cursor, end))
    return free


def _find_slot(
    resource: Mapping[str, Any],
    requested_date: str | None,
    duration_hours: float,
    preferred_start: int,
    *,
    allowed_start: int | None = None,
    allowed_end: int | None = None,
    exact_start: bool = False,
) -> tuple[int, int, float] | None:
    duration_minutes = int(round(duration_hours * 60))
    if duration_minutes <= 0:
        return None
    available_start = _minutes(resource.get("available_from"))
    available_end = _minutes(resource.get("available_until"))
    if allowed_start is not None:
        available_start = max(available_start, allowed_start)
    if allowed_end is not None:
        available_end = min(available_end, allowed_end)
    if available_end - available_start < duration_minutes:
        return None

    free = _free_intervals(
        available_start,
        available_end,
        _booking_intervals(resource, requested_date),
    )
    choices: list[tuple[float, int, int]] = []
    for free_start, free_end in free:
        latest_start = free_end - duration_minutes
        if latest_start < free_start:
            continue
        if exact_start:
            if not free_start <= preferred_start <= latest_start:
                continue
            slot_start = preferred_start
        else:
            slot_start = min(max(preferred_start, free_start), latest_start)
        delay_hours = abs(slot_start - preferred_start) / 60
        spare_hours = (free_end - free_start - duration_minutes) / 60
        # A small tight-window penalty prefers resources with scheduling slack.
        schedule_penalty = delay_hours + (0.1 / (1 + max(spare_hours, 0)))
        choices.append((schedule_penalty, slot_start, slot_start + duration_minutes))
    if not choices:
        return None
    penalty, slot_start, slot_end = min(choices)
    return slot_start, slot_end, penalty


def _first_time(
    request: Mapping[str, Any], keys: Sequence[str], default: str
) -> tuple[int, bool]:
    requirements = request.get("requirements", {})
    sources = [request]
    if isinstance(requirements, Mapping):
        sources.append(requirements)
    for source in sources:
        for key in keys:
            if key in source and source[key] is not None:
                return _minutes(source[key]), True
    return _minutes(default), False


def _optional_time(
    request: Mapping[str, Any], keys: Sequence[str]
) -> int | None:
    requirements = request.get("requirements", {})
    sources = [request]
    if isinstance(requirements, Mapping):
        sources.append(requirements)
    for source in sources:
        for key in keys:
            if key in source and source[key] is not None:
                return _minutes(source[key])
    return None


def _normalised(values: Sequence[float]) -> list[float]:
    if not values:
        return []
    lowest, highest = min(values), max(values)
    if highest == lowest:
        return [0.0 for _ in values]
    if highest <= 0:
        return [0.0 for _ in values]
    # Scale against the observed maximum instead of stretching the smallest
    # difference to the full 0..1 range.  This preserves the meaning of a
    # tractor being only slightly dearer but dramatically closer.
    return [max(value, 0.0) / highest for value in values]


def _weighted_scores(
    candidates: list[dict[str, Any]], weights: Mapping[str, float]
) -> None:
    if not candidates:
        return
    normalised_by_factor = {
        factor: _normalised([float(candidate[f"_{factor}"]) for candidate in candidates])
        for factor in weights
    }
    for index, candidate in enumerate(candidates):
        candidate["score"] = round(
            sum(
                float(weight) * normalised_by_factor[factor][index]
                for factor, weight in weights.items()
            ),
            6,
        )


def _unavailable(reason: str) -> dict[str, str]:
    return {"status": "unavailable", "reason": reason}


def _machine_duration(request: Mapping[str, Any], machine_type: str) -> float:
    requirements = request.get("requirements", {})
    if isinstance(requirements, Mapping):
        for key in (f"{machine_type}_hours", "machinery_hours"):
            if key in requirements:
                return _number(requirements[key], key)
    area = _number(request.get("area", 2), "area")
    return area * MACHINE_HOURS_PER_ACRE.get(
        machine_type, DEFAULT_MACHINE_HOURS / 2
    )


def find_best_machine(
    request: Mapping[str, Any],
    resources: Iterable[Mapping[str, Any]],
    farmer_location: Any,
    machine_type: str = "tractor",
    weights: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Select a machine using normalized cost, distance, and schedule scores."""

    requested_date = str(request.get("date")) if request.get("date") else None
    duration = _machine_duration(request, machine_type)
    preferred_start, exact_start = _first_time(
        request,
        (f"{machine_type}_start", "machinery_start", "requested_start"),
        "09:00",
    )
    requested_end = _optional_time(
        request, (f"{machine_type}_end", "machinery_end", "requested_end")
    )
    candidates: list[dict[str, Any]] = []

    for resource in resources:
        if not isinstance(resource, Mapping):
            continue
        if resource.get("id") is None:
            continue
        if resource.get("type") != machine_type:
            continue
        if not _is_available(resource, requested_date):
            continue
        try:
            rate = _number(resource.get("price_per_hour"), "price_per_hour")
            if rate < 0:
                continue
            resource_distance = _resource_distance(resource, farmer_location)
            slot = _find_slot(
                resource,
                requested_date,
                duration,
                preferred_start,
                allowed_end=requested_end,
                exact_start=exact_start,
            )
        except (TypeError, ValueError):
            continue
        if slot is None:
            continue
        start, end, schedule_penalty = slot
        cost = rate * duration
        candidates.append(
            {
                "resource_id": resource.get("id"),
                "name": str(resource.get("name", machine_type.replace("_", " ").title())),
                "owner": str(resource.get("owner_name", "Unknown")),
                "start": _clock(start),
                "end": _clock(end),
                "cost": _clean_number(cost),
                "distance_km": _clean_number(resource_distance),
                "_cost": cost,
                "_distance": resource_distance,
                "_schedule": schedule_penalty,
            }
        )

    if not candidates:
        return _unavailable(f"No suitable {machine_type} is available")
    _weighted_scores(candidates, weights or MACHINE_SCORE_WEIGHTS)
    winner = min(candidates, key=lambda candidate: (candidate["score"], candidate["_distance"], candidate["_cost"], str(candidate["resource_id"])))
    return {key: value for key, value in winner.items() if not key.startswith("_")}


def _sustainability_penalty(resource: Mapping[str, Any]) -> float:
    if resource.get("type") == "solar_pump":
        return 0.0
    energy_source = str(resource.get("energy_source", "unknown")).lower()
    return {"solar": 0.0, "electric": 0.35, "hybrid": 0.5, "diesel": 1.0}.get(
        energy_source, 0.75
    )


def find_best_solar_pump(
    request: Mapping[str, Any],
    resources: Iterable[Mapping[str, Any]],
    farmer_location: Any,
    weights: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Select a solar pump, preferring a slot near 13:00 within 10:00-16:00."""

    requirements = request.get("requirements", {})
    duration_value = (
        requirements.get("solar_pump_hours", DEFAULT_SOLAR_HOURS)
        if isinstance(requirements, Mapping)
        else DEFAULT_SOLAR_HOURS
    )
    duration = _number(duration_value, "solar_pump_hours")
    requested_date = str(request.get("date")) if request.get("date") else None
    preferred_start, exact_start = _first_time(
        request,
        ("solar_pump_start", "irrigation_start", "requested_start"),
        "13:00",
    )
    requested_end = _optional_time(
        request, ("solar_pump_end", "irrigation_end", "requested_end")
    )
    solar_start, solar_end = map(_minutes, SOLAR_WINDOW)
    if requested_end is not None:
        solar_end = min(solar_end, requested_end)
    candidates: list[dict[str, Any]] = []

    for resource in resources:
        if not isinstance(resource, Mapping):
            continue
        if resource.get("id") is None:
            continue
        if resource.get("type") != "solar_pump":
            continue
        if not _is_available(resource, requested_date):
            continue
        try:
            rate = _number(resource.get("price_per_hour"), "price_per_hour")
            if rate < 0:
                continue
            resource_distance = _resource_distance(resource, farmer_location)
            slot = _find_slot(
                resource,
                requested_date,
                duration,
                preferred_start,
                allowed_start=solar_start,
                allowed_end=solar_end,
                exact_start=exact_start,
            )
        except (TypeError, ValueError):
            continue
        if slot is None:
            continue
        start, end, schedule_penalty = slot
        cost = rate * duration
        candidates.append(
            {
                "resource_id": resource.get("id"),
                "name": str(resource.get("name", "Solar Pump")),
                "owner": str(resource.get("owner_name", "Unknown")),
                "start": _clock(start),
                "end": _clock(end),
                "cost": _clean_number(cost),
                "distance_km": _clean_number(resource_distance),
                "_cost": cost,
                "_distance": resource_distance,
                "_schedule": schedule_penalty,
                "_sustainability": _sustainability_penalty(resource),
            }
        )

    if not candidates:
        return _unavailable("No suitable solar pump is available")
    _weighted_scores(candidates, weights or SOLAR_SCORE_WEIGHTS)
    winner = min(candidates, key=lambda candidate: (candidate["score"], candidate["_distance"], candidate["_cost"], str(candidate["resource_id"])))
    return {key: value for key, value in winner.items() if not key.startswith("_")}


def _allocate_inputs(
    candidates: Sequence[dict[str, Any]], requested: float
) -> tuple[list[dict[str, Any]], float, float]:
    remaining = requested
    allocations: list[dict[str, Any]] = []
    total_cost = 0.0
    for candidate in sorted(
        candidates,
        key=lambda item: (item["price_per_unit"], item["distance_km"], str(item["resource_id"])),
    ):
        if remaining <= 0:
            break
        quantity = min(candidate["quantity"], remaining)
        if quantity <= 0:
            continue
        allocations.append({**candidate, "quantity": quantity})
        total_cost += quantity * candidate["price_per_unit"]
        remaining -= quantity
    return allocations, requested - remaining, total_cost


def find_input_suppliers(
    request: Mapping[str, Any],
    resources: Iterable[Mapping[str, Any]],
    farmer_location: Any,
    item_subtype: str = "tomato_seed",
    requested_quantity: float | None = None,
    unit: str = "kg",
) -> dict[str, Any]:
    """Pool an input across suppliers using a lexicographic MVP objective.

    The priority order is maximum fulfillment, then fewer suppliers, then lower
    summed supplier distance, and finally lower allocated cost.
    """

    if requested_quantity is None:
        requirements = request.get("requirements", {})
        requirement_key = f"{item_subtype}_kg"
        requested_quantity = (
            requirements.get(requirement_key, 0)
            if isinstance(requirements, Mapping)
            else 0
        )
    requested = _number(requested_quantity, "requested_quantity")
    if requested < 0:
        raise ValueError("requested_quantity cannot be negative")
    requested_date = str(request.get("date")) if request.get("date") else None
    candidates: list[dict[str, Any]] = []

    for resource in resources:
        if not isinstance(resource, Mapping):
            continue
        if resource.get("id") is None:
            continue
        if resource.get("type") not in {"seed", "input"}:
            continue
        if resource.get("subtype") != item_subtype:
            continue
        if str(resource.get("unit", "")).lower() != unit.lower():
            continue
        if not _is_available(resource, requested_date):
            continue
        try:
            quantity = _number(resource.get("quantity"), "quantity")
            price = _number(resource.get("price_per_unit"), "price_per_unit")
            resource_distance = _resource_distance(resource, farmer_location)
        except (TypeError, ValueError):
            continue
        if quantity <= 0 or price < 0:
            continue
        candidates.append(
            {
                "resource_id": resource.get("id"),
                "owner": str(resource.get("owner_name", "Unknown")),
                "quantity": quantity,
                "unit": unit,
                "price_per_unit": price,
                "distance_km": resource_distance,
            }
        )

    if requested == 0:
        return {"requested": 0, "fulfilled": 0, "unmet": 0, "suppliers": [], "total_cost": 0}

    total_available = sum(candidate["quantity"] for candidate in candidates)
    selected: Sequence[dict[str, Any]] = candidates
    if total_available >= requested:
        selected = []
        for supplier_count in range(1, len(candidates) + 1):
            eligible: list[tuple[tuple[float, float, tuple[str, ...]], Sequence[dict[str, Any]]]] = []
            for group in combinations(candidates, supplier_count):
                if sum(candidate["quantity"] for candidate in group) < requested:
                    continue
                _, _, allocated_cost = _allocate_inputs(group, requested)
                rank = (
                    sum(candidate["distance_km"] for candidate in group),
                    allocated_cost,
                    tuple(sorted(str(candidate["resource_id"]) for candidate in group)),
                )
                eligible.append((rank, group))
            if eligible:
                selected = min(eligible, key=lambda item: item[0])[1]
                break

    allocations, fulfilled, total_cost = _allocate_inputs(selected, requested)
    suppliers = [
        {
            "resource_id": allocation["resource_id"],
            "owner": allocation["owner"],
            "quantity": _clean_number(allocation["quantity"]),
            "unit": allocation["unit"],
            "cost": _clean_number(
                allocation["quantity"] * allocation["price_per_unit"]
            ),
            "distance_km": _clean_number(allocation["distance_km"]),
        }
        for allocation in allocations
    ]
    return {
        "requested": _clean_number(requested),
        "fulfilled": _clean_number(fulfilled),
        "unmet": _clean_number(max(requested - fulfilled, 0)),
        "suppliers": suppliers,
        "total_cost": _clean_number(total_cost),
    }


def _input_requirements(request: Mapping[str, Any]) -> list[tuple[str, float, str]]:
    requirements = request.get("requirements", {})
    if not isinstance(requirements, Mapping):
        return []
    found: list[tuple[str, float, str]] = []
    for key, value in requirements.items():
        if key.endswith("_kg") and not isinstance(value, bool):
            found.append((key[:-3], _number(value, key), "kg"))
    return found


def _item_label(subtype: str) -> str:
    words = subtype.replace("_", " ").title()
    if words.endswith(" Seed"):
        words += "s"
    return words


def _selected_machine_type(request: Mapping[str, Any]) -> str | None:
    requirements = request.get("requirements", {})
    if not isinstance(requirements, Mapping):
        return None
    for machine_type in ("tractor", "rotavator", "harvester"):
        if requirements.get(machine_type) is True:
            return machine_type
    return None


def _estimated_impact(
    request: Mapping[str, Any],
    machinery: Mapping[str, Any],
    irrigation: Mapping[str, Any],
    input_results: Sequence[tuple[str, dict[str, Any]]],
) -> dict[str, int | float]:
    machine_type = _selected_machine_type(request)
    machine_hours = _machine_duration(request, machine_type) if machine_type else 0.0
    requirements = request.get("requirements", {})
    solar_hours = (
        _number(requirements.get("solar_pump_hours", DEFAULT_SOLAR_HOURS), "solar_pump_hours")
        if isinstance(requirements, Mapping) and requirements.get("solar_pump") is True
        else 0.0
    )
    requested_input_kg = sum(
        _number(result["requested"], "requested input") for _, result in input_results
    )

    normal_cost = 0.0
    if machine_type:
        normal_cost += BASELINE_MACHINE_RATE_PER_HOUR.get(
            machine_type, BASELINE_MACHINE_RATE_PER_HOUR["tractor"]
        ) * machine_hours
    if isinstance(requirements, Mapping) and requirements.get("solar_pump") is True:
        normal_cost += BASELINE_IRRIGATION_RATE_PER_HOUR * solar_hours
    normal_cost += BASELINE_INPUT_RATE_PER_KG * requested_input_kg

    optimized_cost = 0.0
    distances: list[float] = []
    if machinery.get("status") != "unavailable" and machinery.get("status") != "not_requested":
        optimized_cost += _number(machinery.get("cost", 0), "machinery cost")
        distances.append(_number(machinery.get("distance_km", 0), "machinery distance"))
    if irrigation.get("status") != "unavailable" and irrigation.get("status") != "not_requested":
        optimized_cost += _number(irrigation.get("cost", 0), "irrigation cost")
        distances.append(_number(irrigation.get("distance_km", 0), "irrigation distance"))
    for _, result in input_results:
        optimized_cost += _number(result.get("total_cost", 0), "input cost")
        for supplier in result.get("suppliers", []):
            distances.append(_number(supplier.get("distance_km", 0), "input distance"))

    fulfilled_input_kg = sum(
        _number(result["fulfilled"], "fulfilled input") for _, result in input_results
    )
    distance_saved = max(
        BASELINE_TRAVEL_KM_PER_PROVIDER * len(distances) - sum(distances), 0
    )
    actual_solar_hours = (
        solar_hours
        if irrigation.get("status") not in {"unavailable", "not_requested"}
        else 0.0
    )
    return {
        "normal_cost": _clean_number(normal_cost),
        "optimized_cost": _clean_number(optimized_cost),
        "savings": _clean_number(max(normal_cost - optimized_cost, 0)),
        "distance_saved_km": _clean_number(distance_saved),
        "solar_hours": _clean_number(actual_solar_hours),
        "input_reused_kg": _clean_number(fulfilled_input_kg),
    }


def create_plan(
    request: Mapping[str, Any],
    resources: Iterable[Mapping[str, Any]],
    farmer_location: Any,
) -> dict[str, Any]:
    """Create one JSON-serializable resource plan for a structured request."""

    if not isinstance(request, Mapping):
        raise ValueError("request must be a mapping")
    resource_list = list(resources)
    machine_type = _selected_machine_type(request)
    machinery = (
        find_best_machine(request, resource_list, farmer_location, machine_type)
        if machine_type
        else {"status": "not_requested"}
    )
    machinery.pop("score", None)
    requirements = request.get("requirements", {})
    solar_requested = (
        isinstance(requirements, Mapping) and requirements.get("solar_pump") is True
    )
    irrigation = (
        find_best_solar_pump(request, resource_list, farmer_location)
        if solar_requested
        else {"status": "not_requested"}
    )
    irrigation.pop("score", None)

    input_results: list[tuple[str, dict[str, Any]]] = []
    inputs: list[dict[str, Any]] = []
    for subtype, quantity, unit in _input_requirements(request):
        result = find_input_suppliers(
            request,
            resource_list,
            farmer_location,
            item_subtype=subtype,
            requested_quantity=quantity,
            unit=unit,
        )
        input_results.append((subtype, result))
        for supplier in result["suppliers"]:
            inputs.append(
                {
                    "resource_id": supplier["resource_id"],
                    "owner": supplier["owner"],
                    "item": _item_label(subtype),
                    "quantity": supplier["quantity"],
                    "unit": supplier["unit"],
                }
            )

    plan: dict[str, Any] = {
        "plan_id": request.get("plan_id", 101),
        "parsed_request": {
            "crop": request.get("crop"),
            "area": request.get("area"),
            "date": request.get("date"),
        },
        "machinery": machinery,
        "irrigation": irrigation,
        "inputs": inputs,
        "impact": _estimated_impact(
            request, machinery, irrigation, input_results
        ),
    }

    partial = [
        {
            "item": _item_label(subtype),
            "requested": result["requested"],
            "fulfilled": result["fulfilled"],
            "unmet": result["unmet"],
            "unit": "kg",
        }
        for subtype, result in input_results
        if result["unmet"] > 0
    ]
    if partial:
        # The successful-plan contract remains unchanged.  This additive field
        # is emitted only when callers need explicit partial-fulfillment data.
        plan["input_fulfillment"] = partial
    return plan

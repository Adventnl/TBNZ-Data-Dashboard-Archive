from typing import Any

from fastapi import APIRouter

from app.models import Customer

router = APIRouter(prefix="/map", tags=["map"])


def _normalize_gender(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower()
    if normalized in {"m", "male", "man"}:
        return "male"
    if normalized in {"f", "female", "woman"}:
        return "female"
    return normalized


@router.get("/users")
async def get_map_users() -> dict[str, list[dict[str, Any]]]:
    """Return map-ready user points from userdata_map collection."""
    collection = Customer.get_pymongo_collection().database.get_collection("userdata_map")
    records = await collection.find({}, {"_id": 0}).to_list(length=10000)
    map_users: list[dict[str, Any]] = []

    for item in records:
        latitude = item.get("latitude")
        longitude = item.get("longitude")
        if latitude is None or longitude is None:
            continue

        activity_date = item.get("activity_date")
        year = None
        if isinstance(activity_date, str) and len(activity_date) >= 4:
            year = activity_date[:4]

        uid = item.get("uid") or item.get("user_id")
        map_users.append(
            {
                "uid": str(uid) if uid is not None else None,
                "user_id": item.get("user_id"),
                "name": item.get("name"),
                "city": item.get("city"),
                "region": item.get("region"),
                "area": item.get("area"),
                "address": item.get("address"),
                "latitude": latitude,
                "longitude": longitude,
                "gender": _normalize_gender(item.get("gender")),
                "age": item.get("age"),
                "age_range": item.get("age_range"),
                "user_type": item.get("user_type"),
                "year": year,
                "month": item.get("month"),
                "activity_date": activity_date,
                "login_count": item.get("login_count"),
                "session_count": item.get("session_count"),
            }
        )

    return {"map_users": map_users}

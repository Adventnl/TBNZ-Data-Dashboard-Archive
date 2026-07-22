from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.models import Activity, ActivityTracking

router = APIRouter(prefix="/activities", tags=["activities"])

TRACKING_SORT_FIELDS = {
    "sequence": "sequence",
    "registration_date": "registration_date",
    "registration_amount": "registration_amount",
    "channel_source": "channel_source",
    "client_uid": "client_uid",
    "deposit_status": "deposit_status",
}

ACTIVITY_SEARCH_FIELDS = ["name", "description", "location", "status", "activity_id"]
TRACKING_SEARCH_FIELDS = [
    "channel_source",
    "invite_code",
    "channel",
    "client_type",
    "client_name",
    "client_uid",
    "deposit_status",
    "attribution_result",
]


def _to_float(value: Any, default: float = 0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _to_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        try:
            return datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(cleaned[:10], fmt)
            except ValueError:
                continue
    return None


def _to_iso_date(value: Any) -> str | None:
    parsed = _to_datetime(value)
    if parsed is None:
        return None
    return parsed.date().isoformat()


def _to_mmdd(value: Any) -> str | None:
    parsed = _to_datetime(value)
    if parsed is None:
        return None
    return parsed.strftime("%m-%d")


def _normalize_sort_order(value: str) -> int:
    normalized = str(value or "asc").strip().lower()
    if normalized in {"desc", "descend", "descending"}:
        return -1
    return 1


def _normalize_status(value: Any) -> str:
    text = str(value or "planned").strip()
    return text if text else "planned"


def _resolve_activity_metrics(
    activity_doc: dict[str, Any],
    tracking_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    metrics = activity_doc.get("metrics") or {}
    total_visitors = _to_int(metrics.get("total_visitors"))
    new_signups = _to_int(metrics.get("new_signups"))

    if new_signups <= 0 and tracking_rows:
        valid_rows = [
            row
            for row in tracking_rows
            if row.get("client_uid")
            or row.get("client_name")
            or row.get("registration_date")
        ]
        new_signups = len(valid_rows) if valid_rows else len(tracking_rows)

    if total_visitors <= 0 and new_signups > 0:
        total_visitors = new_signups

    conversion_rate = _to_float(metrics.get("conversion_rate"))
    if conversion_rate <= 0 and total_visitors > 0:
        conversion_rate = new_signups / total_visitors * 100

    return {
        "total_visitors": total_visitors,
        "new_signups": new_signups,
        "conversion_rate": round(conversion_rate, 2),
    }


def _serialize_activity_row(
    activity_doc: dict[str, Any],
    metrics: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": activity_doc.get("activity_id"),
        "activity_id": activity_doc.get("activity_id"),
        "name": activity_doc.get("name") or "",
        "description": activity_doc.get("description") or "",
        "date_start": _to_iso_date(activity_doc.get("date_start")),
        "date_end": _to_iso_date(activity_doc.get("date_end")),
        "location": activity_doc.get("location") or "",
        "status": _normalize_status(activity_doc.get("status")),
        "total_visitors": metrics["total_visitors"],
        "new_signups": metrics["new_signups"],
        "conversion_rate": metrics["conversion_rate"],
        "metrics": metrics,
    }


def _build_daily_trend_points(
    activity_doc: dict[str, Any],
    tracking_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    raw_daily_trend = activity_doc.get("daily_trend") or []

    parsed_points: list[dict[str, Any]] = []
    for row in raw_daily_trend:
        point_date = _to_datetime(row.get("date"))
        if point_date is None:
            continue
        parsed_points.append(
            {
                "date": point_date.date(),
                "new_signups": _to_int(row.get("new_signups")),
                "cumulative_visitors": _to_int(row.get("cumulative_visitors")),
            }
        )

    if parsed_points:
        parsed_points.sort(key=lambda item: item["date"])
        result: list[dict[str, Any]] = []
        running_signups = 0
        last_cumulative = 0
        for index, point in enumerate(parsed_points, start=1):
            running_signups += point["new_signups"]
            cumulative_visitors = point["cumulative_visitors"]
            if cumulative_visitors <= 0:
                cumulative_visitors = max(
                    last_cumulative + point["new_signups"], running_signups
                )
            last_cumulative = max(last_cumulative, cumulative_visitors)
            result.append(
                {
                    "day": index,
                    "date": point["date"].isoformat(),
                    "label": point["date"].strftime("%m-%d"),
                    "cumulative_visitors": last_cumulative,
                    "new_signups": point["new_signups"],
                }
            )
        return result

    registrations_by_day: dict[date, int] = defaultdict(int)
    for row in tracking_rows:
        registration_date = _to_datetime(row.get("registration_date"))
        if registration_date is None:
            continue
        registrations_by_day[registration_date.date()] += 1

    if not registrations_by_day:
        start_date = _to_datetime(activity_doc.get("date_start"))
        if start_date is None:
            return []
        metrics = _resolve_activity_metrics(activity_doc, tracking_rows)
        return [
            {
                "day": 1,
                "date": start_date.date().isoformat(),
                "label": start_date.strftime("%m-%d"),
                "cumulative_visitors": metrics["total_visitors"],
                "new_signups": metrics["new_signups"],
            }
        ]

    sorted_days = sorted(registrations_by_day.keys())
    total_signups = sum(registrations_by_day.values())
    metrics = _resolve_activity_metrics(activity_doc, tracking_rows)
    total_visitors_target = (
        metrics["total_visitors"] if metrics["total_visitors"] > 0 else total_signups
    )

    result: list[dict[str, Any]] = []
    running_signups = 0
    for index, one_day in enumerate(sorted_days, start=1):
        new_signups = registrations_by_day[one_day]
        running_signups += new_signups
        if total_signups > 0:
            cumulative_visitors = round(
                total_visitors_target * running_signups / total_signups
            )
        else:
            cumulative_visitors = running_signups
        if index == len(sorted_days):
            cumulative_visitors = total_visitors_target

        result.append(
            {
                "day": index,
                "date": one_day.isoformat(),
                "label": one_day.strftime("%m-%d"),
                "cumulative_visitors": cumulative_visitors,
                "new_signups": new_signups,
            }
        )

    return result


def _serialize_tracking_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "sequence": _to_int(row.get("sequence")),
        "channel_source": row.get("channel_source") or "",
        "invite_code": row.get("invite_code") or "",
        "channel": row.get("channel") or "",
        "client_type": row.get("client_type") or "",
        "client_name": row.get("client_name") or "",
        "client_uid": row.get("client_uid") or "",
        "registration_date": _to_iso_date(row.get("registration_date")),
        "registration_amount": round(_to_float(row.get("registration_amount")), 2),
        "deposit_status": row.get("deposit_status") or "",
        "attribution_result": row.get("attribution_result") or "",
    }


def _build_tracking_query(
    *,
    activity_id: str,
    keyword: str | None,
    channel_source: str | None,
    channel: str | None,
    client_type: str | None,
    deposit_status: str | None,
    attribution_result: str | None,
    start_date: str | None,
    end_date: str | None,
) -> dict[str, Any]:
    query: dict[str, Any] = {"activity_id": activity_id}

    normalized_keyword = str(keyword or "").strip()
    if normalized_keyword:
        regex = {"$regex": normalized_keyword, "$options": "i"}
        query["$or"] = [{field: regex} for field in TRACKING_SEARCH_FIELDS]

    if channel_source and channel_source != "all":
        query["channel_source"] = channel_source
    if channel and channel != "all":
        query["channel"] = channel
    if client_type and client_type != "all":
        query["client_type"] = client_type
    if deposit_status and deposit_status != "all":
        query["deposit_status"] = deposit_status
    if attribution_result and attribution_result != "all":
        query["attribution_result"] = attribution_result

    start_datetime = _to_datetime(start_date)
    end_datetime = _to_datetime(end_date)
    if start_datetime or end_datetime:
        date_filter: dict[str, Any] = {}
        if start_datetime:
            date_filter["$gte"] = start_datetime
        if end_datetime:
            date_filter["$lt"] = end_datetime + timedelta(days=1)
        query["registration_date"] = date_filter

    return query


async def _get_activity_or_404(activity_id: str) -> dict[str, Any]:
    collection = Activity.get_pymongo_collection()
    activity = await collection.find_one(
        {"activity_id": activity_id},
        {
            "_id": 0,
            "activity_id": 1,
            "name": 1,
            "description": 1,
            "date_start": 1,
            "date_end": 1,
            "location": 1,
            "status": 1,
            "metrics": 1,
            "daily_trend": 1,
        },
    )
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


async def _get_activity_tracking_rows(activity_id: str) -> list[dict[str, Any]]:
    collection = ActivityTracking.get_pymongo_collection()
    cursor = collection.find(
        {"activity_id": activity_id},
        {
            "_id": 0,
            "sequence": 1,
            "channel_source": 1,
            "invite_code": 1,
            "channel": 1,
            "client_type": 1,
            "client_name": 1,
            "client_uid": 1,
            "registration_date": 1,
            "registration_amount": 1,
            "deposit_status": 1,
            "attribution_result": 1,
        },
    ).sort("sequence", 1)
    return await cursor.to_list(length=None)


@router.get("")
async def get_activities(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
):
    """活动列表（分页、按日期倒序，支持状态与关键词筛选）"""
    query: dict[str, Any] = {}
    if status and status != "all":
        query["status"] = status

    normalized_keyword = str(keyword or "").strip()
    if normalized_keyword:
        regex = {"$regex": normalized_keyword, "$options": "i"}
        query["$or"] = [{field: regex} for field in ACTIVITY_SEARCH_FIELDS]

    collection = Activity.get_pymongo_collection()
    total = await collection.count_documents(query)

    cursor = (
        collection.find(
            query,
            {
                "_id": 0,
                "activity_id": 1,
                "name": 1,
                "description": 1,
                "date_start": 1,
                "date_end": 1,
                "location": 1,
                "status": 1,
                "metrics": 1,
            },
        )
        .sort([("date_start", -1), ("activity_id", 1)])
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    rows = await cursor.to_list(length=None)

    items = [
        _serialize_activity_row(
            row,
            {
                "total_visitors": _to_int(
                    (row.get("metrics") or {}).get("total_visitors")
                ),
                "new_signups": _to_int((row.get("metrics") or {}).get("new_signups")),
                "conversion_rate": round(
                    _to_float((row.get("metrics") or {}).get("conversion_rate")), 2
                ),
            },
        )
        for row in rows
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{activity_id}")
async def get_activity_detail(activity_id: str):
    """活动详情（含指标与趋势数据）"""
    activity = await _get_activity_or_404(activity_id)
    tracking_rows = await _get_activity_tracking_rows(activity_id)
    metrics = _resolve_activity_metrics(activity, tracking_rows)
    trend_points = _build_daily_trend_points(activity, tracking_rows)

    detail = _serialize_activity_row(activity, metrics)
    detail["daily_trend"] = trend_points
    detail["tracking_count"] = len(tracking_rows)
    return detail


@router.get("/{activity_id}/trend")
async def get_activity_trend(activity_id: str):
    """活动执行趋势（按天）"""
    activity = await _get_activity_or_404(activity_id)
    tracking_rows = await _get_activity_tracking_rows(activity_id)
    return _build_daily_trend_points(activity, tracking_rows)


@router.get("/{activity_id}/tracking")
async def get_activity_tracking(
    activity_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None),
    channel_source: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    client_type: str | None = Query(default=None),
    deposit_status: str | None = Query(default=None),
    attribution_result: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    sort_by: str = Query(default="sequence"),
    sort_order: str = Query(default="ascend"),
):
    """活动获客追踪表（支持分页、筛选、排序）"""
    await _get_activity_or_404(activity_id)

    query = _build_tracking_query(
        activity_id=activity_id,
        keyword=keyword,
        channel_source=channel_source,
        channel=channel,
        client_type=client_type,
        deposit_status=deposit_status,
        attribution_result=attribution_result,
        start_date=start_date,
        end_date=end_date,
    )

    sort_field = TRACKING_SORT_FIELDS.get(sort_by, "sequence")
    sort_direction = _normalize_sort_order(sort_order)

    collection = ActivityTracking.get_pymongo_collection()
    total = await collection.count_documents(query)
    cursor = (
        collection.find(
            query,
            {
                "_id": 0,
                "sequence": 1,
                "channel_source": 1,
                "invite_code": 1,
                "channel": 1,
                "client_type": 1,
                "client_name": 1,
                "client_uid": 1,
                "registration_date": 1,
                "registration_amount": 1,
                "deposit_status": 1,
                "attribution_result": 1,
            },
        )
        .sort(sort_field, sort_direction)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    rows = await cursor.to_list(length=None)

    return {
        "items": [_serialize_tracking_row(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "sort_by": sort_field,
        "sort_order": "desc" if sort_direction < 0 else "asc",
    }

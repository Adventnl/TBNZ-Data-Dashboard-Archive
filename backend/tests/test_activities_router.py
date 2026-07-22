from datetime import datetime

from app.routers.activities import (
    _build_daily_trend_points,
    _build_tracking_query,
    _normalize_sort_order,
    _resolve_activity_metrics,
)


def test_resolve_activity_metrics_falls_back_to_tracking_rows_when_metrics_missing():
    activity_doc = {
        "metrics": {
            "total_visitors": 0,
            "new_signups": 0,
            "conversion_rate": 0,
        }
    }
    tracking_rows = [
        {"client_uid": "1001", "registration_date": datetime(2026, 3, 10)},
        {"client_uid": "1002", "registration_date": datetime(2026, 3, 10)},
        {"client_uid": "1003", "registration_date": datetime(2026, 3, 11)},
    ]

    metrics = _resolve_activity_metrics(activity_doc, tracking_rows)

    assert metrics["new_signups"] == 3
    assert metrics["total_visitors"] == 3
    assert metrics["conversion_rate"] == 100.0


def test_build_daily_trend_uses_activity_daily_trend_when_present():
    activity_doc = {
        "daily_trend": [
            {
                "date": datetime(2026, 3, 11),
                "cumulative_visitors": 200,
                "new_signups": 120,
            },
            {
                "date": datetime(2026, 3, 10),
                "cumulative_visitors": 80,
                "new_signups": 80,
            },
        ]
    }

    points = _build_daily_trend_points(activity_doc, tracking_rows=[])

    assert len(points) == 2
    assert points[0]["day"] == 1
    assert points[0]["date"] == "2026-03-10"
    assert points[0]["new_signups"] == 80
    assert points[1]["day"] == 2
    assert points[1]["cumulative_visitors"] == 200


def test_build_daily_trend_derives_from_tracking_when_no_daily_trend():
    activity_doc = {
        "date_start": datetime(2026, 3, 10),
        "metrics": {
            "total_visitors": 120,
            "new_signups": 3,
            "conversion_rate": 2.5,
        },
        "daily_trend": [],
    }
    tracking_rows = [
        {"registration_date": datetime(2026, 3, 10), "client_uid": "1001"},
        {"registration_date": datetime(2026, 3, 10), "client_uid": "1002"},
        {"registration_date": datetime(2026, 3, 11), "client_uid": "1003"},
    ]

    points = _build_daily_trend_points(activity_doc, tracking_rows)

    assert len(points) == 2
    assert points[0]["new_signups"] == 2
    assert points[0]["cumulative_visitors"] == 80
    assert points[1]["new_signups"] == 1
    assert points[1]["cumulative_visitors"] == 120


def test_build_tracking_query_includes_filters_keyword_and_date_range():
    query = _build_tracking_query(
        activity_id="ACT001",
        keyword="alice",
        channel_source="offline",
        channel="expo",
        client_type="New",
        deposit_status="已入金",
        attribution_result="匹配完成",
        start_date="2026-03-10",
        end_date="2026-03-12",
    )

    assert query["activity_id"] == "ACT001"
    assert query["channel_source"] == "offline"
    assert query["channel"] == "expo"
    assert query["client_type"] == "New"
    assert query["deposit_status"] == "已入金"
    assert query["attribution_result"] == "匹配完成"
    assert "$or" in query
    assert "registration_date" in query
    assert "$gte" in query["registration_date"]
    assert "$lt" in query["registration_date"]


def test_normalize_sort_order_supports_descend():
    assert _normalize_sort_order("desc") == -1
    assert _normalize_sort_order("descend") == -1
    assert _normalize_sort_order("ascend") == 1

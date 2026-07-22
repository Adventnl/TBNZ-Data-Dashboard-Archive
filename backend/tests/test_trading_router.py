from datetime import date

from app.routers.trading import (
    _aggregate_summary,
    _build_category_distribution,
    _build_trend_series,
    _normalize_transactions,
    _sort_top_contributors,
)


def test_normalize_transactions_parses_dates_and_amounts():
    transactions = [
        {
            "uid": "U1",
            "trade_date": "2026-03-01",
            "trade_amount": 1000,
            "currency": "NZD",
            "trade_type": "stock",
            "market": "NZ",
        },
        {
            "uid": "U1",
            "month": "2026-03",
            "trade_amount": 0,
            "trading_volume": 500,
            "currency": "USD",
            "trade_category": "option",
            "market": "US",
        },
    ]

    rows = _normalize_transactions(transactions)

    assert len(rows) == 2
    assert rows[0]["date"].isoformat() == "2026-03-01"
    assert rows[0]["amount"] == 1000
    assert rows[1]["amount"] == 500
    assert rows[1]["trade_type"] == "option"


def test_aggregate_summary_counts_amount_usd_and_records():
    records = [
        {"date": date(2026, 3, 1), "amount": 1000.0, "usd_amount": 610.0},
        {"date": date(2026, 3, 3), "amount": 500.0, "usd_amount": 500.0},
        {"date": date(2026, 2, 27), "amount": 800.0, "usd_amount": 488.0},
    ]

    summary = _aggregate_summary(records, date(2026, 3, 1), date(2026, 3, 31))

    assert summary["amount"] == 1500.0
    assert summary["usd_amount"] == 1110.0
    assert int(summary["count"]) == 2


def test_build_trend_series_for_30d_aligns_current_previous_points():
    records = [
        {"date": date(2026, 3, 15), "amount": 1000.0},
        {"date": date(2026, 3, 16), "amount": 1500.0},
        {"date": date(2026, 2, 13), "amount": 800.0},
        {"date": date(2026, 2, 14), "amount": 700.0},
    ]

    current, previous, granularity = _build_trend_series(
        records,
        end_day=date(2026, 3, 16),
        period="30d",
    )

    assert granularity == "day"
    assert len(current) == 30
    assert len(previous) == 30
    assert any(point["value"] > 0 for point in current)
    assert any(point["value"] > 0 for point in previous)


def test_build_category_distribution_returns_percentages():
    records = [
        {"trade_type": "stock", "amount": 60.0},
        {"trade_type": "option", "amount": 40.0},
    ]

    categories = _build_category_distribution(records)

    assert len(categories) == 2
    assert categories[0]["percentage"] == 60.0
    assert categories[1]["percentage"] == 40.0


def test_sort_top_contributors_supports_numeric_desc():
    rows = [
        {
            "rank": 1,
            "uid": "U1",
            "name": "A",
            "market": "NZ",
            "volume": 500,
            "contribution_pct": 20,
            "change_pct": 1,
        },
        {
            "rank": 2,
            "uid": "U2",
            "name": "B",
            "market": "US",
            "volume": 1200,
            "contribution_pct": 40,
            "change_pct": 5,
        },
    ]

    sorted_rows = _sort_top_contributors(rows, sort_by="volume", order="desc")

    assert sorted_rows[0]["uid"] == "U2"
    assert sorted_rows[1]["uid"] == "U1"

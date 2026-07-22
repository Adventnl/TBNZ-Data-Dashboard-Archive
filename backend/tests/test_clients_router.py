from datetime import date, timedelta

from app.routers.clients import (
    _build_asset_stats,
    _build_ranking_overview,
    _build_transaction_stats,
    _derive_signal,
)


def test_build_transaction_stats_prefers_trade_amount_and_tracks_latest_date():
    transactions = [
        {
            "uid": "U1",
            "trade_date": "2026-03-01",
            "trade_amount": 1200,
            "trading_volume": 9999,
        },
        {
            "uid": "U1",
            "trade_date": "2026-03-05",
            "trade_amount": 0,
            "trading_volume": 800,
        },
    ]

    monthly, latest = _build_transaction_stats(transactions)

    assert monthly["U1"]["2026-03"] == 2000
    assert latest["U1"].isoformat() == "2026-03-05"


def test_build_asset_stats_summarizes_monthly_totals():
    assets = [
        {"uid": "U1", "month": "2026-02", "net_assets": 100000},
        {"uid": "U1", "month": "2026-03", "net_assets": 120000},
        {"uid": "U2", "month": "2026-03", "net_assets": 30000},
    ]

    by_uid, monthly_totals = _build_asset_stats(assets)

    assert by_uid["U1"] == [("2026-02", 100000.0), ("2026-03", 120000.0)]
    assert monthly_totals["2026-03"] == 150000.0


def test_derive_signal_prefers_inactive_for_long_idle_user():
    today = date(2026, 3, 16)
    customer = {
        "uid": "U1",
        "name": "Alice",
        "client_type": "HNW",
        "tags": ["HNW"],
        "monthly_trade_count": 2,
        "monthly_net_assets_usd": 150000,
    }

    signal = _derive_signal(
        customer,
        monthly_volumes={"2026-03": 8000.0},
        latest_trade_date=today - timedelta(days=75),
        asset_points=[("2026-02", 140000.0), ("2026-03", 150000.0)],
        today=today,
    )

    assert signal is not None
    assert signal["signal_type"] == "inactive"
    assert signal["urgent"] is True


def test_derive_signal_detects_hnw_growth_when_assets_increase():
    today = date(2026, 3, 16)
    customer = {
        "uid": "U2",
        "name": "Bob",
        "client_type": "HNW",
        "tags": ["HNW"],
        "monthly_trade_count": 12,
        "monthly_net_assets_usd": 180000,
    }

    signal = _derive_signal(
        customer,
        monthly_volumes={"2026-03": 12000.0, "2026-02": 10000.0},
        latest_trade_date=today - timedelta(days=3),
        asset_points=[("2026-02", 150000.0), ("2026-03", 180000.0)],
        today=today,
    )

    assert signal is not None
    assert signal["signal_type"] == "hnw_deposit_growth"
    assert signal["urgent"] is False


def test_build_ranking_overview_returns_best_rank_with_change():
    rankings = [
        {"month": "2026-02", "dimension": "auc", "rank": 15, "previous_rank": 20},
        {"month": "2026-03", "dimension": "auc", "rank": 12, "previous_rank": 15},
        {"month": "2026-03", "dimension": "auc", "rank": 18, "previous_rank": 16},
    ]

    overview = _build_ranking_overview(rankings)

    assert overview["value"] == 12
    assert overview["change"] == 3
    assert overview["month"] == "2026-03"

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Query

from app.models import Customer, Transaction

router = APIRouter(prefix="/trading", tags=["trading"])


SUPPORTED_PERIODS = {"7d": 7, "30d": 30, "1y": 365}

FX_TO_USD = {
    "USD": 1.0,
    "NZD": 0.61,
    "AUD": 0.66,
    "HKD": 0.128,
    "CNY": 0.14,
    "CNH": 0.14,
}

CATEGORY_LABELS = {
    "stock": "股票",
    "stocks": "股票",
    "option": "期权",
    "options": "期权",
    "futures": "期货",
    "future": "期货",
    "fund": "基金",
    "funds": "基金",
    "etf": "ETF",
}

REGIONAL_TO_CN_PREFIX = {
    "HK": "CN - HK",
    "HKG": "CN - HK",
    "HONG KONG": "CN - HK",
    "HONGKONG": "CN - HK",
    "HK SAR": "CN - HK",
    "HONG KONG SAR": "CN - HK",
    "TW": "CN - TW",
    "TWN": "CN - TW",
    "TAIWAN": "CN - TW",
    "MAC": "CN - MAC",
    "MO": "CN - MAC",
    "MACAU": "CN - MAC",
    "MACAO": "CN - MAC",
}


def _normalize_nationality(value: Any) -> str:
    raw_text = str(value or "").strip()
    if not raw_text:
        return ""

    upper_text = raw_text.upper().replace("_", " ").replace("-", " ")
    upper_text = " ".join(upper_text.split())

    if upper_text.startswith("CN"):
        if "HK" in upper_text or "HONG KONG" in upper_text:
            return "CN - HK"
        if "TW" in upper_text or "TAIWAN" in upper_text:
            return "CN - TW"
        if "MAC" in upper_text or "MO" == upper_text or "MACAU" in upper_text or "MACAO" in upper_text:
            return "CN - MAC"

    mapped = REGIONAL_TO_CN_PREFIX.get(upper_text)
    if mapped:
        return mapped
    return raw_text


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


def _parse_date_value(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        try:
            return datetime.fromisoformat(cleaned.replace("Z", "+00:00")).date()
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(cleaned[:10], fmt).date()
            except ValueError:
                continue
    return None


def _parse_month_value(value: Any) -> date | None:
    if value is None:
        return None
    month_text = str(value).strip()
    if len(month_text) < 7:
        return None
    try:
        return datetime.strptime(month_text[:7], "%Y-%m").date()
    except ValueError:
        return None


def _effective_trade_date(transaction: dict[str, Any]) -> date | None:
    trade_date = _parse_date_value(transaction.get("trade_date"))
    if trade_date is not None:
        return trade_date
    return _parse_month_value(transaction.get("month"))


def _normalize_period(period: str) -> str:
    normalized = (period or "30d").strip().lower()
    return normalized if normalized in SUPPORTED_PERIODS else "30d"


def _pct_change(current: float, previous: float) -> float:
    if previous == 0:
        return 0 if current == 0 else 100
    return (current - previous) / previous * 100


def _month_key(day: date) -> str:
    return day.strftime("%Y-%m")


def _shift_month(day: date, delta: int) -> date:
    year = day.year
    month = day.month + delta
    while month <= 0:
        year -= 1
        month += 12
    while month > 12:
        year += 1
        month -= 12
    return date(year, month, 1)


def _windows(end_day: date, period: str) -> dict[str, date]:
    days = SUPPORTED_PERIODS[_normalize_period(period)]
    current_start = end_day - timedelta(days=days - 1)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=days - 1)
    pre_previous_end = previous_start - timedelta(days=1)
    pre_previous_start = pre_previous_end - timedelta(days=days - 1)
    return {
        "current_start": current_start,
        "current_end": end_day,
        "previous_start": previous_start,
        "previous_end": previous_end,
        "pre_previous_start": pre_previous_start,
        "pre_previous_end": pre_previous_end,
    }


def _normalize_trade_type(raw_type: Any, raw_category: Any) -> str:
    trade_type = str(raw_category or raw_type or "unknown").strip()
    return trade_type if trade_type else "unknown"


def _to_usd(amount: float, currency: Any) -> float:
    currency_text = str(currency or "USD").strip().upper()
    return amount * FX_TO_USD.get(currency_text, 1.0)


def _normalize_transactions(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for transaction in transactions:
        trade_day = _effective_trade_date(transaction)
        if trade_day is None:
            continue

        amount = _to_float(transaction.get("trade_amount"))
        if amount <= 0:
            amount = _to_float(transaction.get("trading_volume"))
        if amount < 0:
            continue

        normalized.append(
            {
                "uid": str(transaction.get("uid") or "").strip(),
                "date": trade_day,
                "amount": amount,
                "usd_amount": _to_usd(amount, transaction.get("currency")),
                "market": str(transaction.get("market") or "N/A").strip() or "N/A",
                "trade_type": _normalize_trade_type(
                    transaction.get("trade_type"), transaction.get("trade_category")
                ),
            }
        )
    return normalized


def _aggregate_summary(
    records: list[dict[str, Any]], start: date, end: date
) -> dict[str, float]:
    total_amount = 0.0
    total_usd_amount = 0.0
    count = 0
    for record in records:
        record_date = record["date"]
        if start <= record_date <= end:
            total_amount += record["amount"]
            total_usd_amount += record["usd_amount"]
            count += 1
    return {
        "amount": total_amount,
        "usd_amount": total_usd_amount,
        "count": float(count),
    }


def _build_trend_series(
    records: list[dict[str, Any]],
    *,
    end_day: date,
    period: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    normalized_period = _normalize_period(period)
    if normalized_period == "1y":
        current_months = [
            _shift_month(date(end_day.year, end_day.month, 1), idx)
            for idx in range(-11, 1)
        ]
        previous_months = [
            _shift_month(date(end_day.year, end_day.month, 1), idx)
            for idx in range(-23, -11)
        ]

        current_map = defaultdict(float)
        previous_map = defaultdict(float)
        previous_month_keys = {_month_key(month) for month in previous_months}

        for record in records:
            month = _month_key(record["date"])
            if month in {_month_key(item) for item in current_months}:
                current_map[month] += record["amount"]
            if month in previous_month_keys:
                previous_map[month] += record["amount"]

        current_series: list[dict[str, Any]] = []
        previous_series: list[dict[str, Any]] = []
        for index, current_month in enumerate(current_months):
            current_month_key = _month_key(current_month)
            previous_month_key = _month_key(previous_months[index])
            label = current_month_key
            current_series.append(
                {"date": label, "value": round(current_map[current_month_key], 2)}
            )
            previous_series.append(
                {"date": label, "value": round(previous_map[previous_month_key], 2)}
            )

        return current_series, previous_series, "month"

    window = _windows(end_day, normalized_period)
    days = SUPPORTED_PERIODS[normalized_period]
    current_days = [
        window["current_start"] + timedelta(days=index) for index in range(days)
    ]
    previous_days = [
        window["previous_start"] + timedelta(days=index) for index in range(days)
    ]

    current_map = defaultdict(float)
    previous_map = defaultdict(float)
    previous_day_set = {day.isoformat() for day in previous_days}

    for record in records:
        record_key = record["date"].isoformat()
        if window["current_start"] <= record["date"] <= window["current_end"]:
            current_map[record_key] += record["amount"]
        if record_key in previous_day_set:
            previous_map[record_key] += record["amount"]

    current_series: list[dict[str, Any]] = []
    previous_series: list[dict[str, Any]] = []
    for index, current_day in enumerate(current_days):
        previous_day = previous_days[index]
        label = current_day.strftime("%m-%d")
        current_series.append(
            {"date": label, "value": round(current_map[current_day.isoformat()], 2)}
        )
        previous_series.append(
            {"date": label, "value": round(previous_map[previous_day.isoformat()], 2)}
        )

    return current_series, previous_series, "day"


def _build_category_distribution(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    category_amount = defaultdict(float)
    for record in records:
        category_amount[record["trade_type"].lower()] += record["amount"]

    total = sum(category_amount.values())
    if total == 0:
        return []

    rows: list[dict[str, Any]] = []
    for raw_name, amount in category_amount.items():
        label = CATEGORY_LABELS.get(raw_name, raw_name.title())
        rows.append(
            {
                "name": label,
                "value": round(amount, 2),
                "percentage": round(amount / total * 100, 2),
            }
        )
    rows.sort(key=lambda item: item["value"], reverse=True)
    return rows


def _most_common_market(records: list[dict[str, Any]]) -> str:
    if not records:
        return "N/A"
    counter = Counter(record["market"] for record in records)
    return counter.most_common(1)[0][0]


def _sort_top_contributors(
    rows: list[dict[str, Any]],
    sort_by: str,
    order: str,
) -> list[dict[str, Any]]:
    allowed = {
        "rank": "rank",
        "market": "market",
        "nationality": "nationality",
        "name": "name",
        "uid": "uid",
        "volume": "volume",
        "contribution_pct": "contribution_pct",
        "change_pct": "change_pct",
    }
    field_name = allowed.get(sort_by, "rank")
    reverse = order.lower() == "desc"

    if field_name in {"market", "nationality", "name", "uid"}:
        return sorted(
            rows, key=lambda row: str(row[field_name]).lower(), reverse=reverse
        )
    return sorted(rows, key=lambda row: _to_float(row[field_name]), reverse=reverse)


async def _fetch_transactions(
    market: str = "all", trade_type: str = "all"
) -> list[dict[str, Any]]:
    query: dict[str, Any] = {}
    if market and market != "all":
        query["market"] = market
    if trade_type and trade_type != "all":
        query["$or"] = [{"trade_type": trade_type}, {"trade_category": trade_type}]

    projection = {
        "_id": 0,
        "uid": 1,
        "trade_date": 1,
        "month": 1,
        "trade_type": 1,
        "trade_category": 1,
        "market": 1,
        "trade_amount": 1,
        "trading_volume": 1,
        "currency": 1,
    }
    collection = Transaction.get_pymongo_collection()
    return await collection.find(query, projection).to_list(length=None)


async def _fetch_customer_profiles(uids: list[str]) -> dict[str, dict[str, str]]:
    normalized = sorted({uid.strip() for uid in uids if uid and uid.strip()})
    if not normalized:
        return {}
    collection = Customer.get_pymongo_collection()
    rows = await collection.find(
        {"uid": {"$in": normalized}},
        {"_id": 0, "uid": 1, "name": 1, "nationality": 1, "raw_data": 1},
    ).to_list(length=None)
    profile_map: dict[str, dict[str, str]] = {}
    for row in rows:
        uid = str(row.get("uid") or "")
        raw_data = row.get("raw_data") or {}
        nationality = _normalize_nationality(row.get("nationality") or "")
        if not nationality and isinstance(raw_data, dict):
            for key in (
                "nationality",
                "country",
                "citizenship",
                "nation",
                "country_region",
                "countryregion",
                "国籍",
                "国家",
                "国家_地区",
                "国家地区",
            ):
                value = _normalize_nationality(raw_data.get(key) or "")
                if value:
                    nationality = value
                    break
        profile_map[uid] = {
            "name": str(row.get("name") or ""),
            "nationality": nationality or "-",
        }
    return profile_map


@router.get("/overview")
async def get_overview(
    period: str = "30d",
    market: str = "all",
    trade_type: str = "all",
):
    """交易指标概览"""
    records = _normalize_transactions(
        await _fetch_transactions(market=market, trade_type=trade_type)
    )

    end_day = max((record["date"] for record in records), default=date.today())
    window = _windows(end_day, period)

    current = _aggregate_summary(
        records, window["current_start"], window["current_end"]
    )
    previous = _aggregate_summary(
        records, window["previous_start"], window["previous_end"]
    )
    pre_previous = _aggregate_summary(
        records, window["pre_previous_start"], window["pre_previous_end"]
    )

    current_count = int(current["count"])
    previous_count = int(previous["count"])

    current_aov = current["amount"] / current_count if current_count else 0
    previous_aov = previous["amount"] / previous_count if previous_count else 0

    return {
        "period": _normalize_period(period),
        "market": market,
        "trade_type": trade_type,
        "total_volume": {
            "value": round(current["amount"], 2),
            "currency": "NZD",
            "usd_equiv": round(current["usd_amount"], 2),
        },
        "change_pct": round(_pct_change(current["amount"], previous["amount"]), 2),
        "previous_volume": {
            "value": round(previous["amount"], 2),
            "change_pct": round(
                _pct_change(previous["amount"], pre_previous["amount"]), 2
            ),
        },
        "pre_previous_volume": {
            "value": round(pre_previous["amount"], 2),
        },
        "aov": {
            "value": round(current_aov, 2),
            "change_pct": round(_pct_change(current_aov, previous_aov), 2),
        },
    }


@router.get("/trends")
async def get_trends(
    period: str = "30d",
    market: str = "all",
    trade_type: str = "all",
):
    """交易趋势数据（当前周期 vs 上一周期）"""
    records = _normalize_transactions(
        await _fetch_transactions(market=market, trade_type=trade_type)
    )
    end_day = max((record["date"] for record in records), default=date.today())
    current, previous, granularity = _build_trend_series(
        records, end_day=end_day, period=period
    )

    return {
        "period": _normalize_period(period),
        "granularity": granularity,
        "current": current,
        "previous": previous,
    }


@router.get("/categories")
async def get_categories(
    period: str = "30d",
    market: str = "all",
    trade_type: str = "all",
):
    """交易类型分布"""
    all_records = _normalize_transactions(
        await _fetch_transactions(market=market, trade_type=trade_type)
    )
    end_day = max((record["date"] for record in all_records), default=date.today())
    window = _windows(end_day, period)
    current_records = [
        record
        for record in all_records
        if window["current_start"] <= record["date"] <= window["current_end"]
    ]
    return _build_category_distribution(current_records)


@router.get("/top-contributors")
async def get_top_contributors(
    period: str = "30d",
    market: str = "all",
    trade_type: str = "all",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    sort_by: str = "rank",
    order: str = "asc",
):
    """头部贡献者列表（支持分页与排序）"""
    all_records = _normalize_transactions(
        await _fetch_transactions(market=market, trade_type=trade_type)
    )
    end_day = max((record["date"] for record in all_records), default=date.today())
    window = _windows(end_day, period)

    current_records = [
        record
        for record in all_records
        if window["current_start"] <= record["date"] <= window["current_end"]
    ]
    previous_records = [
        record
        for record in all_records
        if window["previous_start"] <= record["date"] <= window["previous_end"]
    ]

    current_by_uid: dict[str, list[dict[str, Any]]] = defaultdict(list)
    previous_by_uid: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in current_records:
        if record["uid"]:
            current_by_uid[record["uid"]].append(record)
    for record in previous_records:
        if record["uid"]:
            previous_by_uid[record["uid"]].append(record)

    customer_profiles = await _fetch_customer_profiles(list(current_by_uid.keys()))

    total_current_volume = sum(
        sum(item["amount"] for item in rows) for rows in current_by_uid.values()
    )
    rows: list[dict[str, Any]] = []

    sorted_uids = sorted(
        current_by_uid.keys(),
        key=lambda uid: sum(item["amount"] for item in current_by_uid[uid]),
        reverse=True,
    )
    for index, uid in enumerate(sorted_uids, start=1):
        user_current_rows = current_by_uid[uid]
        current_volume = sum(item["amount"] for item in user_current_rows)
        previous_volume = sum(item["amount"] for item in previous_by_uid.get(uid, []))
        contribution_pct = (
            0
            if total_current_volume == 0
            else current_volume / total_current_volume * 100
        )

        rows.append(
            {
                "rank": index,
                "market": _most_common_market(user_current_rows),
                "nationality": customer_profiles.get(uid, {}).get("nationality") or "-",
                "name": customer_profiles.get(uid, {}).get("name") or uid,
                "uid": uid,
                "volume": round(current_volume, 2),
                "contribution_pct": round(contribution_pct, 2),
                "change_pct": round(_pct_change(current_volume, previous_volume), 2),
            }
        )

    sorted_rows = _sort_top_contributors(rows, sort_by=sort_by, order=order)
    total = len(sorted_rows)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "items": sorted_rows[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
    }

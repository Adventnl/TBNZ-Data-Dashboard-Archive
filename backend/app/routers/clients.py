from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.models import Customer, CustomerAsset, Transaction
from app.routers.rankings import _build_dynamic_dimension_docs, _get_available_months

router = APIRouter(prefix="/clients", tags=["clients"])


SIGNAL_DEFINITIONS: dict[str, dict[str, Any]] = {
    "hnw_deposit_growth": {
        "title": "HNW 持续入金",
        "default_description": "高净值客户资产与交易活跃度同步增长。",
        "recommended_action": "建议安排高级顾问在 24 小时内完成回访。",
        "urgent": False,
        "priority": 70,
    },
    "inactive": {
        "title": "沉睡客户",
        "default_description": "客户近期无交易行为，存在活跃流失风险。",
        "recommended_action": "建议触发召回活动并由销售一对一跟进。",
        "urgent": True,
        "priority": 100,
    },
    "volume_spike": {
        "title": "交易量激增",
        "default_description": "客户交易量较历史均值显著放大。",
        "recommended_action": "建议确认交易意图并评估风险偏好变化。",
        "urgent": True,
        "priority": 95,
    },
    "new_large_deposit": {
        "title": "新客户大额入金",
        "default_description": "新客在短周期内出现大额入金行为。",
        "recommended_action": "建议分配专属服务并推进首次建仓。",
        "urgent": True,
        "priority": 90,
    },
    "asset_decline": {
        "title": "资产持续下滑",
        "default_description": "客户资产连续下滑，需关注留存风险。",
        "recommended_action": "建议快速联系客户，确认资金流出原因。",
        "urgent": True,
        "priority": 92,
    },
}


class PushToSalesRequest(BaseModel):
    operator: str = Field(default="system")
    note: str | None = None
    signal_type: str | None = None


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


def _parse_month(month_value: Any) -> date | None:
    if month_value is None:
        return None
    month_text = str(month_value).strip()
    if len(month_text) < 7:
        return None
    try:
        return datetime.strptime(month_text[:7], "%Y-%m").date()
    except ValueError:
        return None


def _effective_trade_date(doc: dict[str, Any]) -> date | None:
    trade_date = _parse_date_value(doc.get("trade_date"))
    if trade_date is not None:
        return trade_date
    return _parse_month(doc.get("month"))


def _month_key(day: date) -> str:
    return day.strftime("%Y-%m")


def _shift_month(month_key: str, delta: int) -> str:
    year, month = [int(part) for part in month_key.split("-")]
    month += delta
    while month <= 0:
        year -= 1
        month += 12
    while month > 12:
        year += 1
        month -= 12
    return f"{year:04d}-{month:02d}"


def _pct_change(current: float, previous: float) -> float:
    if previous == 0:
        return 0 if current == 0 else 100
    return (current - previous) / previous * 100


def _normalize_tags(tags: Any) -> list[str]:
    if tags is None:
        return []
    if isinstance(tags, list):
        return [str(tag).strip() for tag in tags if str(tag).strip()]
    text = str(tags).strip()
    if not text:
        return []
    return [part.strip() for part in text.replace(";", ",").split(",") if part.strip()]


def _normalize_client_type(value: Any) -> str:
    return str(value or "").strip()


def _normalize_signal_type(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    alias_map = {
        "hnw_growth": "hnw_deposit_growth",
        "urgent": "volume_spike",
        "warning": "inactive",
        "success": "hnw_deposit_growth",
        "info": "new_large_deposit",
    }
    return alias_map.get(normalized, normalized)


def _signal_payload(
    *,
    signal_type: str,
    description: str | None = None,
    recommended_action: str | None = None,
    score: int | None = None,
) -> dict[str, Any]:
    signal_type = _normalize_signal_type(signal_type)
    definition = SIGNAL_DEFINITIONS.get(signal_type, SIGNAL_DEFINITIONS["volume_spike"])
    return {
        "signal_type": signal_type,
        "signal_title": definition["title"],
        "signal_description": description or definition["default_description"],
        "recommended_action": recommended_action or definition["recommended_action"],
        "urgent": bool(definition["urgent"]),
        "score": score if score is not None else int(definition["priority"]),
    }


def _build_transaction_stats(
    transactions: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, float]], dict[str, date]]:
    monthly_volume_by_uid: dict[str, dict[str, float]] = defaultdict(
        lambda: defaultdict(float)
    )
    latest_trade_date_by_uid: dict[str, date] = {}

    for transaction in transactions:
        uid = str(transaction.get("uid") or "").strip()
        if not uid:
            continue

        trade_day = _effective_trade_date(transaction)
        if trade_day is None:
            continue

        amount = _to_float(transaction.get("trade_amount"))
        if amount <= 0:
            amount = _to_float(transaction.get("trading_volume"))

        monthly_volume_by_uid[uid][_month_key(trade_day)] += amount

        previous_date = latest_trade_date_by_uid.get(uid)
        if previous_date is None or trade_day > previous_date:
            latest_trade_date_by_uid[uid] = trade_day

    return monthly_volume_by_uid, latest_trade_date_by_uid


def _build_asset_stats(
    assets: list[dict[str, Any]],
) -> tuple[dict[str, list[tuple[str, float]]], dict[str, float]]:
    assets_by_uid: dict[str, list[tuple[str, float]]] = defaultdict(list)
    monthly_totals: dict[str, float] = defaultdict(float)

    for asset in assets:
        uid = str(asset.get("uid") or "").strip()
        if not uid:
            continue

        month_value = str(asset.get("month") or "").strip()
        if not month_value:
            parsed_snapshot = _parse_date_value(asset.get("snapshot_date"))
            if parsed_snapshot is None:
                continue
            month_value = _month_key(parsed_snapshot)
        elif len(month_value) >= 7:
            month_value = month_value[:7]

        net_assets = _to_float(asset.get("net_assets"))
        assets_by_uid[uid].append((month_value, net_assets))
        monthly_totals[month_value] += net_assets

    for uid in assets_by_uid:
        assets_by_uid[uid] = sorted(assets_by_uid[uid], key=lambda item: item[0])

    return assets_by_uid, monthly_totals


def _derive_signal(
    customer: dict[str, Any],
    *,
    monthly_volumes: dict[str, float],
    latest_trade_date: date | None,
    asset_points: list[tuple[str, float]],
    today: date,
) -> dict[str, Any] | None:
    explicit_signal = customer.get("signal") or {}
    if isinstance(explicit_signal, dict) and any(explicit_signal.values()):
        signal_type = str(explicit_signal.get("type") or "volume_spike")
        return _signal_payload(
            signal_type=signal_type,
            description=str(explicit_signal.get("description") or "").strip() or None,
            recommended_action=str(
                explicit_signal.get("recommended_action") or ""
            ).strip()
            or None,
        )

    tags = _normalize_tags(customer.get("tags"))
    tag_set = {tag.lower() for tag in tags}
    client_type = _normalize_client_type(customer.get("client_type"))
    client_type_lower = client_type.lower()

    month_now = today.strftime("%Y-%m")
    previous_month = _shift_month(month_now, -1)
    current_volume = _to_float(monthly_volumes.get(month_now))

    previous_values = [
        value
        for month, value in sorted(monthly_volumes.items(), key=lambda item: item[0])
        if month < month_now
    ]
    previous_avg = sum(previous_values) / len(previous_values) if previous_values else 0

    latest_assets = (
        asset_points[-1][1]
        if asset_points
        else _to_float(customer.get("monthly_net_assets_usd"))
    )
    prev_assets = asset_points[-2][1] if len(asset_points) >= 2 else 0

    candidates: list[dict[str, Any]] = []

    if (
        ("hnw" in tag_set or client_type_lower in {"hnw", "s-class", "s_class"})
        and latest_assets >= 100000
        and prev_assets > 0
        and latest_assets >= prev_assets * 1.1
    ):
        candidates.append(
            _signal_payload(
                signal_type="hnw_deposit_growth",
                description=f"近两期资产由 {prev_assets:,.0f} 增至 {latest_assets:,.0f}。",
                score=80,
            )
        )

    if latest_trade_date is not None and (today - latest_trade_date).days >= 60:
        idle_days = (today - latest_trade_date).days
        candidates.append(
            _signal_payload(
                signal_type="inactive",
                description=f"客户已连续 {idle_days} 天未产生交易行为。",
                score=100,
            )
        )

    if current_volume > 0 and previous_avg > 0 and current_volume >= previous_avg * 3:
        candidates.append(
            _signal_payload(
                signal_type="volume_spike",
                description=(
                    f"本月交易量 {current_volume:,.0f}，约为历史均值 {previous_avg:,.0f} 的 "
                    f"{current_volume / previous_avg:.1f} 倍。"
                ),
                score=95,
            )
        )

    if (
        ("new" in tag_set or client_type_lower == "new")
        and latest_assets >= 50000
        and current_volume >= 0
    ):
        candidates.append(
            _signal_payload(
                signal_type="new_large_deposit",
                description=f"新客当前净资产约 {latest_assets:,.0f}，可优先推进首笔交易。",
                score=90,
            )
        )

    if prev_assets > 0 and latest_assets <= prev_assets * 0.8:
        decline_pct = (prev_assets - latest_assets) / prev_assets * 100
        candidates.append(
            _signal_payload(
                signal_type="asset_decline",
                description=f"近两期资产下降 {decline_pct:.1f}%（{prev_assets:,.0f} -> {latest_assets:,.0f}）。",
                score=92,
            )
        )

    if not candidates:
        monthly_trade_count = _to_int(customer.get("monthly_trade_count"))
        if latest_assets >= 100000:
            return _signal_payload(
                signal_type="hnw_deposit_growth",
                description=f"当前净资产 {latest_assets:,.0f}，建议持续跟进。",
                score=60,
            )
        if monthly_trade_count >= 15:
            return _signal_payload(
                signal_type="volume_spike",
                description=f"月交易次数 {monthly_trade_count} 次，处于高活跃区间。",
                score=55,
            )
        if _to_float(monthly_volumes.get(previous_month)) == 0 and current_volume == 0:
            return None
        return _signal_payload(signal_type="new_large_deposit", score=40)

    candidates.sort(key=lambda item: (item["score"], item["urgent"]), reverse=True)
    return candidates[0]


async def _build_ranking_overview() -> dict[str, Any]:
    available_months = await _get_available_months()
    if not available_months:
        return {"value": 0, "total": 100, "change": 0}

    latest_month = available_months[0]
    rows = await _build_dynamic_dimension_docs(
        month=latest_month,
        dimension="auc",
        include_previous=True,
    )
    if not rows:
        return {"value": 0, "total": 100, "change": 0}

    best = min(rows, key=lambda row: _to_int(row.get("rank"), default=999999))
    rank_value = _to_int(best.get("rank"), default=0)
    previous_rank = _to_int(best.get("previous_rank"), default=rank_value)
    return {
        "value": rank_value,
        "total": len(rows),
        "change": previous_rank - rank_value,
        "month": latest_month,
    }


async def _get_latest_dynamic_ranking(uid: str) -> dict[str, Any] | None:
    target_uid = str(uid or "").strip()
    if not target_uid:
        return None

    available_months = await _get_available_months()
    for month in available_months:
        for dimension in ("auc", "trading"):
            rows = await _build_dynamic_dimension_docs(
                month=month,
                dimension=dimension,
                include_previous=True,
            )
            matched = next(
                (row for row in rows if str(row.get("uid") or "").strip() == target_uid),
                None,
            )
            if matched:
                return matched
    return None


async def _fetch_customers() -> list[dict[str, Any]]:
    projection = {
        "_id": 0,
        "name": 1,
        "uid": 1,
        "age": 1,
        "gender": 1,
        "location": 1,
        "nationality": 1,
        "client_type": 1,
        "tags": 1,
        "monthly_net_assets_usd": 1,
        "monthly_trade_count": 1,
        "trade_category": 1,
        "asset_allocation": 1,
        "monthly_snapshots": 1,
        "signal": 1,
        "raw_data": 1,
    }
    collection = Customer.get_pymongo_collection()
    return await collection.find({}, projection).to_list(length=None)


async def _fetch_transactions(
    market: str = "all", uid: str | None = None
) -> list[dict[str, Any]]:
    query: dict[str, Any] = {}
    if market and market != "all":
        query["market"] = market
    if uid:
        query["uid"] = uid
    projection = {
        "_id": 0,
        "uid": 1,
        "trade_date": 1,
        "month": 1,
        "trade_amount": 1,
        "trading_volume": 1,
        "trade_type": 1,
        "trade_category": 1,
        "market": 1,
        "currency": 1,
    }
    collection = Transaction.get_pymongo_collection()
    return await collection.find(query, projection).to_list(length=None)


async def _fetch_assets(uid: str | None = None) -> list[dict[str, Any]]:
    query = {"uid": uid} if uid else {}
    projection = {
        "_id": 0,
        "uid": 1,
        "month": 1,
        "net_assets": 1,
        "deposit_amount": 1,
        "withdrawal_amount": 1,
        "trading_volume": 1,
        "currency": 1,
        "snapshot_date": 1,
    }
    collection = CustomerAsset.get_pymongo_collection()
    return await collection.find(query, projection).to_list(length=None)


@router.get("/overview")
async def get_overview(market: str = "all"):
    """客户概览指标（交易量、AUC、排名）"""
    today = date.today()
    transactions = await _fetch_transactions(market=market)
    assets = await _fetch_assets()

    monthly_trading: dict[str, float] = defaultdict(float)
    for transaction in transactions:
        trade_day = _effective_trade_date(transaction)
        if trade_day is None:
            continue
        amount = _to_float(transaction.get("trade_amount"))
        if amount <= 0:
            amount = _to_float(transaction.get("trading_volume"))
        monthly_trading[_month_key(trade_day)] += amount

    current_month = (
        max(monthly_trading.keys()) if monthly_trading else today.strftime("%Y-%m")
    )
    previous_month = _shift_month(current_month, -1)
    current_trading = monthly_trading.get(current_month, 0)
    previous_trading = monthly_trading.get(previous_month, 0)

    _, monthly_auc_totals = _build_asset_stats(assets)
    current_auc = monthly_auc_totals.get(current_month, 0)
    previous_auc = monthly_auc_totals.get(previous_month, 0)

    ranking = await _build_ranking_overview()

    return {
        "trading_volume": {
            "value": round(current_trading, 2),
            "currency": "NZD",
            "change_pct": round(_pct_change(current_trading, previous_trading), 2),
            "month": current_month,
        },
        "auc": {
            "value": round(current_auc, 2),
            "currency": "USD",
            "change_pct": round(_pct_change(current_auc, previous_auc), 2),
            "month": current_month,
        },
        "ranking": ranking,
    }


@router.get("/signals")
async def get_signals(
    signal_type: str = "all",
    client_type: str = "all",
    market: str = "all",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """客户信号列表（支持类型、客户分层、市场筛选与分页）"""
    today = date.today()
    customers = await _fetch_customers()
    transactions = await _fetch_transactions(market=market)
    assets = await _fetch_assets()

    monthly_volume_by_uid, latest_trade_date_by_uid = _build_transaction_stats(
        transactions
    )
    assets_by_uid, _ = _build_asset_stats(assets)

    normalized_signal_type = signal_type.strip().lower()
    normalized_client_type = client_type.strip().lower()

    rows: list[dict[str, Any]] = []
    for customer in customers:
        uid = str(customer.get("uid") or "").strip()
        name = str(customer.get("name") or "").strip()
        if not uid or not name:
            continue

        customer_type_text = _normalize_client_type(customer.get("client_type"))
        if (
            normalized_client_type not in {"", "all"}
            and customer_type_text.lower() != normalized_client_type
        ):
            continue

        signal = _derive_signal(
            customer,
            monthly_volumes=monthly_volume_by_uid.get(uid, {}),
            latest_trade_date=latest_trade_date_by_uid.get(uid),
            asset_points=assets_by_uid.get(uid, []),
            today=today,
        )
        if signal is None:
            continue

        if (
            normalized_signal_type not in {"", "all"}
            and signal["signal_type"].lower() != normalized_signal_type
        ):
            continue

        rows.append(
            {
                "name": name,
                "uid": uid,
                "tags": _normalize_tags(customer.get("tags")),
                "client_type": customer_type_text,
                "signal_type": signal["signal_type"],
                "signal_title": signal["signal_title"],
                "signal_description": signal["signal_description"],
                "recommended_action": signal["recommended_action"],
                "urgent": signal["urgent"],
                "score": signal["score"],
            }
        )

    rows.sort(
        key=lambda item: (
            item["urgent"],
            item["score"],
            item["signal_type"],
            item["uid"],
        ),
        reverse=True,
    )

    total = len(rows)
    start = (page - 1) * page_size
    end = start + page_size
    items = rows[start:end]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/{uid}/push-to-sales")
async def push_to_sales(uid: str, payload: PushToSalesRequest):
    """推送客户给 Sales（记录最后一次推送信息）"""
    timestamp = datetime.utcnow()
    collection = Customer.get_pymongo_collection()
    result = await collection.update_one(
        {"uid": uid},
        {
            "$set": {
                "raw_data.push_to_sales": {
                    "operator": payload.operator,
                    "note": payload.note,
                    "signal_type": payload.signal_type,
                    "pushed_at": timestamp,
                },
                "updated_at": timestamp,
            }
        },
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")

    return {
        "status": "ok",
        "uid": uid,
        "pushed_at": timestamp,
        "operator": payload.operator,
    }


@router.get("/{uid}/detail")
async def get_client_detail(uid: str):
    """获取客户详细信息"""
    customer_collection = Customer.get_pymongo_collection()
    customer = await customer_collection.find_one(
        {"uid": uid},
        {
            "_id": 0,
            "name": 1,
            "uid": 1,
            "age": 1,
            "gender": 1,
            "location": 1,
            "nationality": 1,
            "client_type": 1,
            "tags": 1,
            "monthly_net_assets_usd": 1,
            "monthly_trade_count": 1,
            "trade_category": 1,
            "asset_allocation": 1,
            "monthly_snapshots": 1,
            "signal": 1,
            "raw_data": 1,
        },
    )
    if customer is None:
        raise HTTPException(status_code=404, detail="Client not found")

    transactions = await _fetch_transactions(uid=uid)
    assets = await _fetch_assets(uid=uid)
    latest_ranking = await _get_latest_dynamic_ranking(uid)

    today = date.today()
    thirty_days_ago = today - timedelta(days=30)

    normalized_transactions: list[dict[str, Any]] = []
    total_trade_30d = 0.0
    for transaction in transactions:
        trade_day = _effective_trade_date(transaction)
        if trade_day is None:
            continue
        amount = _to_float(transaction.get("trade_amount"))
        if amount <= 0:
            amount = _to_float(transaction.get("trading_volume"))
        if trade_day >= thirty_days_ago:
            total_trade_30d += amount
        normalized_transactions.append(
            {
                "trade_date": trade_day.isoformat(),
                "trade_type": transaction.get("trade_type")
                or transaction.get("trade_category"),
                "market": transaction.get("market"),
                "amount": round(amount, 2),
                "currency": transaction.get("currency") or "USD",
            }
        )

    normalized_transactions.sort(key=lambda item: item["trade_date"], reverse=True)

    assets_trend: list[dict[str, Any]] = []
    for asset in assets:
        month_value = str(asset.get("month") or "").strip()
        if not month_value:
            snapshot_day = _parse_date_value(asset.get("snapshot_date"))
            if snapshot_day is None:
                continue
            month_value = _month_key(snapshot_day)
        assets_trend.append(
            {
                "month": month_value[:7],
                "net_assets": round(_to_float(asset.get("net_assets")), 2),
                "deposit_amount": round(_to_float(asset.get("deposit_amount")), 2),
                "withdrawal_amount": round(
                    _to_float(asset.get("withdrawal_amount")), 2
                ),
                "trading_volume": round(_to_float(asset.get("trading_volume")), 2),
                "currency": asset.get("currency") or "USD",
            }
        )
    assets_trend.sort(key=lambda item: item["month"])

    return {
        "uid": customer.get("uid"),
        "name": customer.get("name"),
        "age": customer.get("age"),
        "gender": customer.get("gender"),
        "location": customer.get("location"),
        "nationality": customer.get("nationality"),
        "client_type": customer.get("client_type"),
        "tags": _normalize_tags(customer.get("tags")),
        "signal": customer.get("signal"),
        "asset_allocation": customer.get("asset_allocation") or {},
        "monthly_snapshots": customer.get("monthly_snapshots") or [],
        "metrics": {
            "monthly_net_assets_usd": round(
                _to_float(customer.get("monthly_net_assets_usd")), 2
            ),
            "monthly_trade_count": _to_int(customer.get("monthly_trade_count")),
            "trade_volume_30d": round(total_trade_30d, 2),
        },
        "recent_transactions": normalized_transactions[:10],
        "assets_trend": assets_trend[-12:],
        "latest_ranking": latest_ranking,
        "last_push_to_sales": (customer.get("raw_data") or {}).get("push_to_sales"),
    }

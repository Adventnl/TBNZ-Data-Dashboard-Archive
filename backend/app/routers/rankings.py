from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query

from app.models import Customer, CustomerAsset

router = APIRouter(prefix="/rankings", tags=["rankings"])

SUPPORTED_DIMENSIONS = {"auc", "trading"}

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


def _parse_month(month_text: str | None) -> datetime | None:
    if not month_text:
        return None
    try:
        return datetime.strptime(month_text[:7], "%Y-%m")
    except ValueError:
        return None


def _normalize_dimension(dimension: str | None) -> str:
    normalized = str(dimension or "auc").strip().lower()
    return normalized if normalized in SUPPORTED_DIMENSIONS else "auc"


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float = 0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_tier_level(client_type: str | None, tags: list[str] | None) -> str:
    normalized_type = str(client_type or "").strip().lower()
    normalized_tags = {str(tag).strip().lower() for tag in (tags or [])}
    if "s-class" in normalized_tags or normalized_type == "s-class":
        return "S级"
    if "hnw" in normalized_tags or normalized_type == "hnw":
        return "S级"
    return "M级"


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


async def _get_available_months() -> list[str]:
    asset_collection = CustomerAsset.get_pymongo_collection()
    asset_months = await asset_collection.distinct("month")

    parsed = [m for m in asset_months if isinstance(m, str) and _parse_month(m)]
    parsed.sort(key=lambda value: _parse_month(value) or datetime.min, reverse=True)
    return list(dict.fromkeys(parsed))


def _get_previous_month(available_months: list[str], current_month: str) -> str | None:
    if current_month not in available_months:
        return None
    current_index = available_months.index(current_month)
    next_index = current_index + 1
    if next_index >= len(available_months):
        return None
    return available_months[next_index]


async def _resolve_month(selected_month: str | None) -> tuple[str, list[str]]:
    available_months = await _get_available_months()
    if selected_month and selected_month in available_months:
        return selected_month, available_months
    if available_months:
        return available_months[0], available_months
    fallback_month = selected_month or datetime.now().strftime("%Y-%m")
    return fallback_month, []


async def _load_dimension_docs(month: str, dimension: str) -> list[dict[str, Any]]:
    return await _build_dynamic_dimension_docs(month=month, dimension=dimension, include_previous=True)


def _resolve_channel_source(customer: dict[str, Any], asset_row: dict[str, Any]) -> str:
    for source in (customer, customer.get("raw_data") or {}, asset_row.get("raw_data") or {}):
        if not isinstance(source, dict):
            continue
        for key in ("channel_source", "channel", "invite_code"):
            value = str(source.get(key) or "").strip()
            if value:
                return value
    return "-"


def _build_rank_rows(
    *,
    month: str,
    dimension: str,
    ranked_items: list[tuple[str, float, float, float]],
    customer_map: dict[str, dict[str, Any]],
    previous_rank_map: dict[str, int] | None,
    total_auc: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rank, (uid, score, auc_value, trading_volume) in enumerate(ranked_items, start=1):
        customer = customer_map.get(uid, {})
        rows.append(
            {
                "uid": uid,
                "month": month,
                "dimension": dimension,
                "rank": rank,
                "previous_rank": previous_rank_map.get(uid) if previous_rank_map else None,
                "client_type": customer.get("client_type") or "Unknown",
                "channel_source": _resolve_channel_source(customer, {}),
                "auc_share_pct": round((auc_value / total_auc * 100) if total_auc > 0 else 0, 4),
                "trading_volume": round(trading_volume, 2),
                "auc_value": round(auc_value, 2),
                "raw_data": {
                    "computed": True,
                    "computed_source": "customer_assets",
                },
            }
        )
    return rows


async def _build_dynamic_dimension_docs(
    *,
    month: str,
    dimension: str,
    include_previous: bool,
) -> list[dict[str, Any]]:
    collection = CustomerAsset.get_pymongo_collection()
    cursor = collection.find(
        {"month": month},
        {"_id": 0, "uid": 1, "net_assets": 1, "trading_volume": 1, "raw_data": 1},
    )
    assets = await cursor.to_list(length=None)
    if not assets:
        return []

    ranked_items: list[tuple[str, float, float, float]] = []
    total_auc = 0.0
    for row in assets:
        uid = str(row.get("uid") or "").strip()
        if not uid:
            continue
        auc_value = max(0.0, _to_float(row.get("net_assets"), 0.0))
        trading_volume = max(0.0, _to_float(row.get("trading_volume"), 0.0))
        total_auc += auc_value
        score = auc_value if dimension == "auc" else trading_volume
        if score <= 0:
            continue
        ranked_items.append((uid, score, auc_value, trading_volume))

    ranked_items.sort(key=lambda item: (-item[1], item[0]))
    if not ranked_items:
        return []

    uid_list = [item[0] for item in ranked_items]
    customer_map = await _load_customers(uid_list)

    previous_rank_map: dict[str, int] = {}
    if include_previous:
        available_months = await _get_available_months()
        previous_month = _get_previous_month(available_months, month)
        if previous_month:
            previous_docs = await _build_dynamic_dimension_docs(
                month=previous_month,
                dimension=dimension,
                include_previous=False,
            )
            previous_rank_map = {
                str(row.get("uid") or ""): _to_int(row.get("rank"), 0)
                for row in previous_docs
                if row.get("uid")
            }

    return _build_rank_rows(
        month=month,
        dimension=dimension,
        ranked_items=ranked_items,
        customer_map=customer_map,
        previous_rank_map=previous_rank_map,
        total_auc=total_auc,
    )


async def _load_customers(uid_list: list[str]) -> dict[str, dict[str, Any]]:
    if not uid_list:
        return {}
    collection = Customer.get_pymongo_collection()
    cursor = collection.find(
        {"uid": {"$in": uid_list}},
        {"_id": 0, "uid": 1, "name": 1, "client_type": 1, "tags": 1, "nationality": 1, "deposit_amount": 1, "raw_data": 1},
    )
    rows = await cursor.to_list(length=None)
    return {str(row.get("uid") or ""): row for row in rows}


def _resolve_customer_nationality(customer: dict[str, Any]) -> str | None:
    direct = str(customer.get("nationality") or "").strip()
    if direct:
        normalized_direct = _normalize_nationality(direct)
        return normalized_direct or None

    raw_data = customer.get("raw_data") or {}
    if not isinstance(raw_data, dict):
        return None

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
        value = str(raw_data.get(key) or "").strip()
        if value:
            normalized_value = _normalize_nationality(value)
            return normalized_value or None
    return None


def _normalize_selected_nationality(value: str | None) -> str | None:
    normalized_value = str(value or "").strip()
    if not normalized_value or normalized_value.lower() == "all":
        return None
    normalized_nationality = _normalize_nationality(normalized_value)
    return normalized_nationality or None


async def _get_all_nationality_options() -> list[str]:
    collection = Customer.get_pymongo_collection()
    normalized: set[str] = set()

    def _append_values(values: list[Any]) -> None:
        for value in values:
            text = _normalize_nationality(value)
            if text:
                normalized.add(text)

    _append_values(await collection.distinct("nationality"))
    _append_values(await collection.distinct("raw_data.nationality"))
    _append_values(await collection.distinct("raw_data.country"))
    _append_values(await collection.distinct("raw_data.citizenship"))
    _append_values(await collection.distinct("raw_data.nation"))
    _append_values(await collection.distinct("raw_data.country_region"))
    _append_values(await collection.distinct("raw_data.countryregion"))
    _append_values(await collection.distinct("raw_data.国籍"))
    _append_values(await collection.distinct("raw_data.国家"))
    _append_values(await collection.distinct("raw_data.国家_地区"))
    _append_values(await collection.distinct("raw_data.国家地区"))

    return sorted(normalized)


def _movement_item(
    *,
    uid: str,
    current_rank: int,
    from_rank: int,
    customer_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    customer = customer_map.get(uid, {})
    return {
        "uid": uid,
        "name": customer.get("name") or uid,
        "rank": current_rank,
        "from": from_rank,
    }


async def _build_month_context(
    *,
    selected_month: str | None,
    dimension: str,
    nationality: str | None = None,
    top_n: int = 200,
) -> dict[str, Any]:
    month, available_months = await _resolve_month(selected_month)
    previous_month = _get_previous_month(available_months, month)

    current_docs = await _load_dimension_docs(month, dimension)
    previous_docs = await _load_dimension_docs(previous_month, dimension) if previous_month else []

    current_map = {
        str(row.get("uid") or ""): row
        for row in current_docs
        if row.get("uid")
    }
    previous_map = {
        str(row.get("uid") or ""): row
        for row in previous_docs
        if row.get("uid")
    }

    all_uids = list(set(current_map.keys()) | set(previous_map.keys()))
    customer_map = await _load_customers(all_uids)

    target_nationality = _normalize_selected_nationality(nationality)
    if target_nationality:
        current_docs = [
            row
            for row in current_docs
            if _normalize_nationality(
                _resolve_customer_nationality(customer_map.get(str(row.get("uid") or ""), {})) or ""
            )
            == target_nationality
        ]
        previous_docs = [
            row
            for row in previous_docs
            if _normalize_nationality(
                _resolve_customer_nationality(customer_map.get(str(row.get("uid") or ""), {})) or ""
            )
            == target_nationality
        ]
        current_map = {
            str(row.get("uid") or ""): row
            for row in current_docs
            if row.get("uid")
        }
        previous_map = {
            str(row.get("uid") or ""): row
            for row in previous_docs
            if row.get("uid")
        }

    current_top_uids = {
        uid for uid, row in current_map.items() if 0 < _to_int(row.get("rank")) <= top_n
    }
    previous_top_uids = {
        uid for uid, row in previous_map.items() if 0 < _to_int(row.get("rank")) <= top_n
    }

    new_entry_uids = sorted(
        current_top_uids - previous_top_uids,
        key=lambda uid: _to_int(current_map.get(uid, {}).get("rank"), 9999),
    )

    dropped_out_uids = sorted(
        previous_top_uids - current_top_uids,
        key=lambda uid: _to_int(previous_map.get(uid, {}).get("rank"), 9999),
    )

    big_jump_uids: list[str] = []
    for uid in current_top_uids & previous_top_uids:
        current_rank = _to_int(current_map.get(uid, {}).get("rank"), 9999)
        previous_rank = _to_int(previous_map.get(uid, {}).get("rank"), 9999)
        if previous_rank - current_rank > 20:
            big_jump_uids.append(uid)
    big_jump_uids.sort(key=lambda uid: _to_int(current_map.get(uid, {}).get("rank"), 9999))

    rank_changed_uids = {
        uid
        for uid in (current_top_uids & previous_top_uids)
        if _to_int(current_map.get(uid, {}).get("rank")) != _to_int(previous_map.get(uid, {}).get("rank"))
    }

    changed_uids = set(new_entry_uids) | set(dropped_out_uids) | rank_changed_uids

    new_entries = [
        _movement_item(
            uid=uid,
            current_rank=_to_int(current_map.get(uid, {}).get("rank"), 0),
            from_rank=_to_int(previous_map.get(uid, {}).get("rank"), top_n + 1),
            customer_map=customer_map,
        )
        for uid in new_entry_uids
    ]
    dropped_out = [
        _movement_item(
            uid=uid,
            current_rank=_to_int(current_map.get(uid, {}).get("rank"), top_n + 1),
            from_rank=_to_int(previous_map.get(uid, {}).get("rank"), 0),
            customer_map=customer_map,
        )
        for uid in dropped_out_uids
    ]
    big_jumps = [
        _movement_item(
            uid=uid,
            current_rank=_to_int(current_map.get(uid, {}).get("rank"), 0),
            from_rank=_to_int(previous_map.get(uid, {}).get("rank"), 0),
            customer_map=customer_map,
        )
        for uid in big_jump_uids
    ]

    return {
        "month": month,
        "previous_month": previous_month,
        "available_months": available_months[:12],
        "top_n": top_n,
        "current_docs": current_docs,
        "current_map": current_map,
        "customer_map": customer_map,
        "new_entries": new_entries,
        "dropped_out": dropped_out,
        "big_jumps": big_jumps,
        "changed_count": len(changed_uids),
    }


@router.get("/overview")
async def get_overview(
    month: str | None = Query(default=None, description="查询月份，例如 '2026-03'"),
    dimension: str = Query(default="auc", description="排名维度：auc/trading"),
    nationality: str | None = Query(default=None, description="国籍过滤"),
    top_n: int = Query(default=200, ge=1, le=500, description="统计前 N 名，最大 500"),
) -> dict[str, Any]:
    """排名概览统计（本月变动、新进、跌出、大幅跃升）"""
    normalized_dimension = _normalize_dimension(dimension)
    context = await _build_month_context(
        selected_month=month,
        dimension=normalized_dimension,
        nationality=nationality,
        top_n=top_n,
    )

    return {
        "month": context["month"],
        "previous_month": context["previous_month"],
        "dimension": normalized_dimension,
        "top_n": context["top_n"],
        "available_months": context["available_months"],
        "nationality": _normalize_selected_nationality(nationality) or "all",
        "nationality_options": await _get_all_nationality_options(),
        "summary": {
            "changed_count": context["changed_count"],
            "new_entry_count": len(context["new_entries"]),
            "dropped_out_count": len(context["dropped_out"]),
            "big_jump_count": len(context["big_jumps"]),
        },
    }


@router.get("/movements")
async def get_movements(
    month: str | None = Query(default=None, description="查询月份，例如 '2026-03'"),
    dimension: str = Query(default="auc", description="排名维度：auc/trading"),
    nationality: str | None = Query(default=None, description="国籍过滤"),
    top_n: int = Query(default=200, ge=1, le=500, description="统计前 N 名，最大 500"),
    limit: int = Query(default=6, ge=1, le=50, description="每类返回条数"),
) -> dict[str, Any]:
    """排名变动卡片数据（新进/跌出/大幅跃升）"""
    normalized_dimension = _normalize_dimension(dimension)
    context = await _build_month_context(
        selected_month=month,
        dimension=normalized_dimension,
        nationality=nationality,
        top_n=top_n,
    )

    return {
        "month": context["month"],
        "previous_month": context["previous_month"],
        "dimension": normalized_dimension,
        "top_n": context["top_n"],
        "nationality": _normalize_selected_nationality(nationality) or "all",
        "new_entries": context["new_entries"][:limit],
        "dropped_out": context["dropped_out"][:limit],
        "big_jumps": context["big_jumps"][:limit],
        "counts": {
            "new_entry_count": len(context["new_entries"]),
            "dropped_out_count": len(context["dropped_out"]),
            "big_jump_count": len(context["big_jumps"]),
        },
    }


async def _get_top_n_response(
    *,
    selected_month: str | None,
    dimension: str,
    page: int,
    page_size: int,
    sort_by: str,
    sort_order: str,
    keyword: str | None,
    client_type: str | None,
    limit_rank: int = 200,
    nationality: str | None = None,
) -> dict[str, Any]:
    normalized_dimension = _normalize_dimension(dimension)
    context = await _build_month_context(selected_month=selected_month, dimension=normalized_dimension)

    rows: list[dict[str, Any]] = []
    client_type_options: set[str] = set()
    nationality_options: set[str] = set()
    all_nationality_options = await _get_all_nationality_options()
    
    for ranking_doc in context["current_docs"]:
        rank = _to_int(ranking_doc.get("rank"))
        if rank <= 0 or rank > limit_rank:
            continue
        uid = str(ranking_doc.get("uid") or "").strip()
        if not uid:
            continue

        customer = context["customer_map"].get(uid, {})
        resolved_client_type = (
            ranking_doc.get("client_type")
            or customer.get("client_type")
            or "Unknown"
        )
        if resolved_client_type:
            client_type_options.add(str(resolved_client_type))
        
        customer_nationality = _resolve_customer_nationality(customer)
        if customer_nationality:
            nationality_options.add(str(customer_nationality))
            
        previous_rank = _to_int(ranking_doc.get("previous_rank"), 0)
        rank_change = previous_rank - rank if previous_rank > 0 else 0

        row = {
            "rank": rank,
            "uid": uid,
            "name": customer.get("name") or uid,
            "channel_source": ranking_doc.get("channel_source") or "-",
            "tier_level": _to_tier_level(resolved_client_type, customer.get("tags") or []),
            "client_type": resolved_client_type,
            "rank_change": rank_change,
            "previous_rank": previous_rank,
            "auc_share_pct": round(_to_float(ranking_doc.get("auc_share_pct")), 2),
            "trading_volume": round(_to_float(ranking_doc.get("trading_volume")), 2),
            "auc_value": round(_to_float(ranking_doc.get("auc_value")), 2),
            "nationality": customer_nationality or "-",
            "deposit_amount": _to_float(customer.get("deposit_amount"), 0),
        }
        rows.append(row)

    normalized_keyword = str(keyword or "").strip().lower()
    if normalized_keyword:
        rows = [
            row
            for row in rows
            if normalized_keyword in str(row["uid"]).lower()
            or normalized_keyword in str(row["name"]).lower()
            or normalized_keyword in str(row["channel_source"]).lower()
            or normalized_keyword in str(row["client_type"]).lower()
        ]

    normalized_client_type = str(client_type or "all").strip()
    if normalized_client_type and normalized_client_type != "all":
        rows = [
            row
            for row in rows
            if str(row.get("client_type") or "") == normalized_client_type
        ]

    normalized_nationality = str(nationality or "").strip()
    if normalized_nationality and normalized_nationality.lower() != "all":
        target_nationality = _normalize_nationality(normalized_nationality)
        rows = [
            row
            for row in rows
            if _normalize_nationality(row.get("nationality") or "") == target_nationality
        ]

    has_active_filters = bool(
        normalized_keyword
        or (normalized_client_type and normalized_client_type != "all")
        or (normalized_nationality and normalized_nationality.lower() != "all")
    )

    rows_by_overall_rank = sorted(rows, key=lambda row: row.get("rank") or 0)
    for index, row in enumerate(rows_by_overall_rank, start=1):
        row["filtered_rank"] = index

    reverse = str(sort_order or "ascend").lower() in {"desc", "descend"}
    valid_sort_fields = {
        "filtered_rank",
        "rank",
        "rank_change",
        "auc_share_pct",
        "trading_volume",
        "auc_value",
        "uid",
        "name",
        "client_type",
        "channel_source",
        "nationality",
        "deposit_amount",
    }
    effective_sort_by = sort_by if sort_by in valid_sort_fields else "rank"
    rows.sort(key=lambda row: row.get(effective_sort_by), reverse=reverse)

    total = len(rows)
    start = (page - 1) * page_size
    end = start + page_size
    page_rows = rows[start:end]

    return {
        "month": context["month"],
        "previous_month": context["previous_month"],
        "available_months": context["available_months"],
        "client_type_options": sorted(client_type_options),
        "nationality_options": sorted(set(all_nationality_options) | nationality_options),
        "dimension": normalized_dimension,
        "has_active_filters": has_active_filters,
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": page_rows,
    }
@router.get("/top500-trading")
async def get_top500_trading(
    month: str | None = Query(default=None, description="查询月份，例如 '2026-03'"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    top_n: int = Query(default=500, ge=1, le=500, description="返回前 N 名，最大 500"),
    sort_by: str = Query(default="rank"),
    sort_order: str = Query(default="ascend"),
    keyword: str | None = Query(default=None),
    client_type: str | None = Query(default="all"),
    nationality: str | None = Query(default=None, description="国籍过滤"),
) -> dict[str, Any]:
    """Top N 交易排名（分页/排序/月份筛选/国籍过滤）"""
    return await _get_top_n_response(
        selected_month=month,
        dimension="trading",
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        keyword=keyword,
        client_type=client_type,
        limit_rank=top_n,
        nationality=nationality,
    )


@router.get("/top500-auc")
async def get_top500_auc(
    month: str | None = Query(default=None, description="查询月份，例如 '2026-03'"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    top_n: int = Query(default=500, ge=1, le=500, description="返回前 N 名，最大 500"),
    sort_by: str = Query(default="rank"),
    sort_order: str = Query(default="ascend"),
    keyword: str | None = Query(default=None),
    client_type: str | None = Query(default="all"),
    nationality: str | None = Query(default=None, description="国籍过滤"),
) -> dict[str, Any]:
    """Top N AUC 排名（分页/排序/月份筛选/国籍过滤）"""
    return await _get_top_n_response(
        selected_month=month,
        dimension="auc",
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        keyword=keyword,
        client_type=client_type,
        limit_rank=top_n,
        nationality=nationality,
    )

from fastapi import APIRouter, Query
from typing import Any, Dict
from datetime import datetime

from app.models import CustomerAsset, Customer

router = APIRouter(prefix="/auc", tags=["auc"])


def _parse_month(month_text: str | None) -> datetime | None:
    if not month_text:
        return None
    try:
        return datetime.strptime(str(month_text).strip()[:7], "%Y-%m")
    except ValueError:
        return None


def _to_month_text(value: datetime) -> str:
    return value.strftime("%Y-%m")


def _to_month_label(month_text: str) -> str:
    parsed = _parse_month(month_text)
    return parsed.strftime("%b %Y") if parsed else month_text


def _get_previous_month(month_text: str) -> str | None:
    parsed = _parse_month(month_text)
    if not parsed:
        return None
    if parsed.month == 1:
        return f"{parsed.year - 1}-12"
    return f"{parsed.year}-{parsed.month - 1:02d}"


async def _get_available_months() -> list[str]:
    collection = CustomerAsset.get_pymongo_collection()
    distinct_months = await collection.distinct("month")
    normalized: list[str] = []
    for month in distinct_months:
        if not isinstance(month, str):
            continue
        parsed = _parse_month(month)
        if not parsed:
            continue
        normalized.append(_to_month_text(parsed))

    normalized.sort(key=lambda value: _parse_month(value) or datetime.min, reverse=True)
    return list(dict.fromkeys(normalized))


async def _resolve_month(selected_month: str | None) -> tuple[str, list[str]]:
    available_months = await _get_available_months()
    normalized_selected = _to_month_text(_parse_month(selected_month)) if _parse_month(selected_month) else None

    if normalized_selected and normalized_selected in available_months:
        return normalized_selected, available_months
    if available_months:
        return available_months[0], available_months
    fallback = normalized_selected or datetime.now().strftime("%Y-%m")
    return fallback, []


def _build_month_options(available_months: list[str]) -> list[dict[str, Any]]:
    if not available_months:
        current_month = datetime.now().strftime("%Y-%m")
        return [{
            "month": current_month,
            "label": _to_month_label(current_month),
            "has_data": False,
        }]

    available_set = set(available_months)
    latest_month = _parse_month(available_months[0])
    earliest_month = _parse_month(available_months[-1])
    current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if not latest_month or not earliest_month:
        return [{
            "month": month,
            "label": _to_month_label(month),
            "has_data": month in available_set,
        } for month in available_months]

    start_month = latest_month if latest_month > current_month else current_month
    cursor = start_month
    options: list[dict[str, Any]] = []
    while cursor >= earliest_month:
        month_text = _to_month_text(cursor)
        options.append({
            "month": month_text,
            "label": _to_month_label(month_text),
            "has_data": month_text in available_set,
        })

        if cursor.month == 1:
            cursor = cursor.replace(year=cursor.year - 1, month=12)
        else:
            cursor = cursor.replace(month=cursor.month - 1)

    return options


@router.get("/month-options")
async def get_month_options(
    month: str | None = Query(default=None, description="查询月份，例如 '2026-03'"),
) -> Dict[str, Any]:
    resolved_month, available_months = await _resolve_month(month)
    return {
        "requested_month": month,
        "selected_month": resolved_month,
        "available_months": available_months,
        "options": _build_month_options(available_months),
    }


@router.get("/overview")
async def get_overview(month: str | None = Query(default=None, description="查询月份，例如 '2026-03'")) -> Dict[str, Any]:
    """
    AUC 指标概览 — 总资产、平均资产、留存率、净流入
    
    计算逻辑：
    - 总资产规模：当月 sum(net_assets)
    - 平均每客户资产：总资产 / 客户数
    - 资产留存率及变化：对比前月数据
    - 净流入：sum(deposit_amount - withdrawal_amount)
    """
    
    resolved_month, _ = await _resolve_month(month)
    collection = CustomerAsset.get_pymongo_collection()
    
    # 计算当月的汇总指标
    current_pipeline = [
        {"$match": {"month": resolved_month}},
        {"$group": {
            "_id": None,
            "total_auc": {"$sum": "$net_assets"},
            "total_deposit": {"$sum": "$deposit_amount"},
            "total_withdrawal": {"$sum": "$withdrawal_amount"},
            "client_count": {"$sum": 1}
        }}
    ]
    
    current_cursor = collection.aggregate(current_pipeline)
    current_results = await current_cursor.to_list(length=1)
    current_data = current_results[0] if current_results else {
        "total_auc": 0,
        "total_deposit": 0,
        "total_withdrawal": 0,
        "client_count": 0
    }
    
    # 计算前月数据（用于对比）
    previous_month = _get_previous_month(resolved_month)
    
    previous_data = {
        "total_auc": 0,
        "client_count": 0
    }
    if previous_month:
        previous_pipeline = [
            {"$match": {"month": previous_month}},
            {"$group": {
                "_id": None,
                "total_auc": {"$sum": "$net_assets"},
                "client_count": {"$sum": 1}
            }}
        ]

        previous_cursor = collection.aggregate(previous_pipeline)
        previous_results = await previous_cursor.to_list(length=1)
        previous_data = previous_results[0] if previous_results else previous_data
    
    # 计算指标
    total_auc = current_data.get("total_auc", 0)
    client_count = current_data.get("client_count", 0)
    avg_account = total_auc / client_count if client_count > 0 else 0
    net_inflow = current_data.get("total_deposit", 0) - current_data.get("total_withdrawal", 0)
    
    # 计算 YoY 变化（使用月环比）
    previous_auc = previous_data.get("total_auc", 0)
    yoy_change = ((total_auc - previous_auc) / previous_auc * 100) if previous_auc > 0 else 0
    
    # 计算留存率：当月客户数 / 前月客户数
    previous_client_count = previous_data.get("client_count", 0)
    retention_rate = (client_count / previous_client_count * 100) if previous_client_count > 0 else 100
    retention_change = retention_rate - 100  # 相对前月的变化
    
    # 计算净流入比率
    net_inflow_pct = (net_inflow / total_auc * 100) if total_auc > 0 else 0
    
    return {
        "month": resolved_month,
        "requested_month": month,
        "total_auc": {
            "value": total_auc,
            "yoy_change": round(yoy_change, 2),
            "formatted": f"${total_auc / 1000000:.1f}M"
        },
        "avg_account": {
            "value": round(avg_account, 2),
            "health": "Good" if avg_account > 50000 else "Fair" if avg_account > 20000 else "Attention",
        },
        "retention_rate": {
            "value": round(retention_rate, 2),
            "change": round(retention_change, 2),
            "formatted": f"{retention_rate:.1f}%"
        },
        "net_inflow": {
            "value": round(net_inflow, 2),
            "change_pct": round(net_inflow_pct, 2),
            "formatted": f"${net_inflow / 1000000:.2f}M"
        },
        "client_count": client_count
    }


@router.get("/trends")
async def get_trends(
    year: int = Query(2026, description="年份，例如 2026"),
    limit_months: int = Query(12, ge=1, le=24, description="返回多少个月的数据")
) -> Dict[str, Any]:
    """
    AUC 趋势数据 — 按月聚合的历史数据
    
    返回最近 N 个月的总资产规模和净流入数据，用于绘制趋势图
    """
    
    collection = CustomerAsset.get_pymongo_collection()
    
    # 聚合管道：按月分组，统计总资产和净流入
    pipeline = [
        {
            "$group": {
                "_id": "$month",
                "total_assets": {"$sum": "$net_assets"},
                "total_deposit": {"$sum": "$deposit_amount"},
                "total_withdrawal": {"$sum": "$withdrawal_amount"},
                "client_count": {"$sum": 1}
            }
        },
        {"$sort": {"_id": 1}},  # 按月份升序排列
        {"$limit": limit_months}  # 限制返回数据行数
    ]
    
    cursor = collection.aggregate(pipeline)
    results = await cursor.to_list(length=None)
    
    if not results:
        # 无数据时返回空结构
        return {
            "year": year,
            "months": [],
            "total_assets": [],
            "net_inflow": []
        }
    
    # 提取月份和数据
    months = []
    total_assets = []
    net_inflow = []
    
    # 月份的简短显示名称
    for record in results:
        month_str = record["_id"]  # 格式：YYYY-MM
        months.append(_to_month_label(month_str))
        total_assets.append(record["total_assets"])
        net_inflow.append(record["total_deposit"] - record["total_withdrawal"])
    
    return {
        "year": year,
        "months": months,
        "total_assets": total_assets,
        "net_inflow": net_inflow,
        "data_points": len(results)
    }


@router.get("/tier-distribution")
async def get_tier_distribution(month: str | None = Query(default=None, description="查询月份，例如 '2026-03'")) -> Dict[str, Any]:
    """
    资产分级分布 — 利用 MongoDB $bucket 操作符进行分箱统计
    
    分级定义：
    - Mass: < $10k
    - Core: $10k - $99,999
    - Affluent: $100k - $999,999
    - HNW: >= $1M
    """
    
    # 分箱边界（左闭右开）
    boundaries = [0, 10000, 100000, 1000000]
    
    resolved_month, _ = await _resolve_month(month)

    # MongoDB 聚合管道
    pipeline = [
        # 第一步：按月份筛选
        {"$match": {"month": resolved_month}},
        
        # 第二步：利用 $bucket 进行分箱聚合
        {"$bucket": {
            "groupBy": "$net_assets",      # 按净资产（修正：CustomerAsset 中的字段名）
            "boundaries": boundaries,
            "default": "HNW",              # >= 1,000,000 的放到 HNW
            "output": {
                "count": {"$sum": 1}       # 统计每个箱子里的文档数
            }
        }}
    ]
    
    # 获取 MongoDB 原生集合（Motor 异步驱动）
    collection = CustomerAsset.get_pymongo_collection()
    
    # 执行聚合查询
    cursor = collection.aggregate(pipeline)
    buckets = await cursor.to_list(length=None)
    
    # 初始化标准化输出（防止某个分段无数据）
    distribution = {
        "< $10k (Mass)": 0,
        "$10k - $100k (Core)": 0,
        "$100k - $1M (Affluent)": 0,
        "> $1M (HNW)": 0
    }
    
    # 填充结果
    for bucket in buckets:
        bucket_id = bucket["_id"]
        count = bucket["count"]
        
        if bucket_id == 0:
            distribution["< $10k (Mass)"] = count
        elif bucket_id == 10000:
            distribution["$10k - $100k (Core)"] = count
        elif bucket_id == 100000:
            distribution["$100k - $1M (Affluent)"] = count
        elif bucket_id == "HNW":
            distribution["> $1M (HNW)"] = count
    
    return {
        "month": resolved_month,
        "requested_month": month,
        "data": distribution
    }


@router.get("/asset-allocation")
async def get_asset_allocation(month: str | None = Query(default=None, description="查询月份，例如 '2026-03'")) -> Dict[str, Any]:
    """
    资产配置比例 — 统计所有客户的资产在各类别的占比

    数据源优先使用 customer_assets 的月度快照字段（stocks_pct/options_pct/futures_pct/funds_pct），
    若快照缺失则回退到 customers.asset_allocation。
    通过当月 net_assets 加权聚合，支持多币种。
    """

    def _to_pct(value: Any) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return 0.0
        if numeric <= 0:
            return 0.0
        normalized = numeric / 100.0 if numeric > 1 else numeric
        return max(0.0, min(normalized, 1.0))

    resolved_month, _ = await _resolve_month(month)

    assets_collection = CustomerAsset.get_pymongo_collection()
    customers_collection = Customer.get_pymongo_collection()

    asset_docs = await assets_collection.find(
        {"month": resolved_month},
        {
            "uid": 1,
            "currency": 1,
            "net_assets": 1,
            "raw_data": 1,
        },
    ).to_list(length=None)

    if not asset_docs:
        return {
            "month": resolved_month,
            "requested_month": month,
            "data": [
                {"name": "股票", "percentage": 0, "amount": 0, "currency": "USD"},
                {"name": "期权", "percentage": 0, "amount": 0, "currency": "USD"},
                {"name": "期货", "percentage": 0, "amount": 0, "currency": "USD"},
                {"name": "基金", "percentage": 0, "amount": 0, "currency": "USD"},
            ],
        }

    uid_list = list({str(doc.get("uid") or "").strip() for doc in asset_docs if doc.get("uid")})
    customer_docs = await customers_collection.find(
        {"uid": {"$in": uid_list}},
        {"uid": 1, "asset_allocation": 1},
    ).to_list(length=None)
    customer_alloc_map = {
        str(doc.get("uid") or "").strip(): doc.get("asset_allocation") or {}
        for doc in customer_docs
    }

    category_specs = [
        ("股票", "stocks_pct"),
        ("期权", "options_pct"),
        ("期货", "futures_pct"),
        ("基金", "funds_pct"),
    ]

    currency_totals: dict[str, dict[str, float]] = {}
    for asset_doc in asset_docs:
        uid = str(asset_doc.get("uid") or "").strip()
        currency = str(asset_doc.get("currency") or "USD").strip().upper() or "USD"
        net_assets = float(asset_doc.get("net_assets") or 0)
        if net_assets <= 0:
            continue

        snapshot_alloc = (asset_doc.get("raw_data") or {})
        customer_alloc = customer_alloc_map.get(uid, {})

        pct_map: dict[str, float] = {}
        pct_sum = 0.0
        for category_name, pct_key in category_specs:
            raw_value = snapshot_alloc.get(pct_key)
            if raw_value is None:
                raw_value = customer_alloc.get(pct_key)
            pct_value = _to_pct(raw_value)
            pct_map[category_name] = pct_value
            pct_sum += pct_value

        if pct_sum <= 0:
            continue

        currency_totals.setdefault(currency, {name: 0.0 for name, _ in category_specs})
        for category_name, _ in category_specs:
            currency_totals[currency][category_name] += net_assets * pct_map[category_name]

    all_data: list[dict[str, Any]] = []
    for currency, totals in currency_totals.items():
        total_amount = sum(totals.values())
        for category_name, _ in category_specs:
            amount = totals.get(category_name, 0.0)
            percentage = round(amount / total_amount * 100, 2) if total_amount > 0 else 0
            all_data.append(
                {
                    "name": category_name,
                    "percentage": percentage,
                    "amount": round(amount, 2),
                    "currency": currency,
                }
            )

    if not all_data:
        all_data = [
            {"name": "股票", "percentage": 0, "amount": 0, "currency": "USD"},
            {"name": "期权", "percentage": 0, "amount": 0, "currency": "USD"},
            {"name": "期货", "percentage": 0, "amount": 0, "currency": "USD"},
            {"name": "基金", "percentage": 0, "amount": 0, "currency": "USD"},
        ]

    return {
        "month": resolved_month,
        "requested_month": month,
        "data": all_data,
    }


@router.get("/top-clients")
async def get_top_clients(
    month: str | None = Query(default=None, description="查询月份，例如 '2026-03'"),
    client_type: str = Query("all", description="客户类型筛选：HNW/S-Class/all"),
    limit: int = Query(20, ge=1, le=200, description="返回前 N 条")
) -> Dict[str, Any]:
    """
    按客户资产规模排行 — Top N 客户
    
    支持按客户类型筛选
    """
    
    resolved_month, _ = await _resolve_month(month)

    # 基础过滤：只按月份匹配（customer_assets 集合无 client_type 字段）
    match_stage = {"$match": {"month": resolved_month}}
    
    # client_type 过滤需要在 $lookup 之后应用
    client_type_filter = []
    if client_type != "all":
        client_type_filter = [{"$match": {"customer_info.client_type": client_type}}]
    
    # 聚合管道
    pipeline = [
        match_stage,
        {"$lookup": {
            "from": "customers",
            "localField": "uid",
            "foreignField": "uid",
            "as": "customer_info"
        }},
        {"$unwind": {
            "path": "$customer_info", 
            "preserveNullAndEmptyArrays": True
        }},
        {"$addFields": {
            "customer_info": {
                "$ifNull": ["$customer_info", {
                    "name": {"$concat": ["客户", {"$substr": ["$uid", 2, -1]}]},
                    "client_type": "Unknown",
                    "tags": ["Unknown"],
                    "monthly_trade_count": 0
                }]
            }
        }},
        *client_type_filter,
        {"$sort": {"net_assets": -1}},
        {"$limit": limit},
        {"$project": {
            "_id": 0,  # 排除 MongoDB 的 ObjectId，防止序列化错误
            "uid": 1,
            "name": "$customer_info.name",
            "net_assets": 1,
            "client_type": "$customer_info.client_type",
            "tags": "$customer_info.tags",
            "monthly_trade_count": "$customer_info.monthly_trade_count"
        }}
    ]
    
    collection = CustomerAsset.get_pymongo_collection()
    cursor = collection.aggregate(pipeline)
    clients = await cursor.to_list(length=None)
    
    return {
        "month": resolved_month,
        "requested_month": month,
        "client_type": client_type,
        "total": len(clients),
        "data": clients
    }

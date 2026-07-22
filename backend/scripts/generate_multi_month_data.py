"""
生成多月份、多客户的大样本联调数据。

主要用途：
- AUC 趋势与资产分布动态联调
- Rankings Top200 场景联调（新进/跌出/大幅跃升）
"""

from __future__ import annotations

import json
import math
import subprocess
import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


LOCATIONS = [
    "Auckland",
    "Wellington",
    "Christchurch",
    "Hamilton",
    "Tauranga",
    "Dunedin",
]

CLIENT_TYPES = ["HNW", "S-Class", "Frequent Trader", "Core", "New"]

CHANNEL_SOURCES = ["wechat", "invitation", "webinar", "offline", "referral", "ads"]

CURRENCIES = ["USD", "USD", "USD", "NZD", "AUD", "HKD", "CNY", "EUR"]

TRADE_TYPES = ["stock", "option", "futures", "fund"]

GEO_SOURCE_GIT_PATH = "leoBranch:frontend/src/data/activity_with_geo_2024.json"
GEO_SOURCE_FILE_PATH = Path("frontend") / "src" / "data" / "activity_with_geo_2024.json"

GEO_USER_TYPE_TO_CLIENT_TYPE = {
    "高净值用户": "HNW",
    "完成第一笔交易用户": "Frequent Trader",
    "已成功入金用户": "S-Class",
    "注册用户": "New",
}

NATIONALITY_WEIGHTS: list[tuple[str, float]] = [
    ("NZ", 0.60),
    ("CN", 0.10),
    ("AU", 0.08),
    ("CN - HK", 0.04),
    ("CN - TW", 0.02),
    ("CN - MAC", 0.02),
    ("US", 0.06),
    ("SG", 0.04),
    ("MY", 0.03),
    ("IN", 0.03),
]


def add_months(base_date: datetime, months: int) -> datetime:
    year = base_date.year + (base_date.month - 1 + months) // 12
    month = (base_date.month - 1 + months) % 12 + 1
    return datetime(year, month, 1)


def normalize_allocation(stocks: float, options: float, futures: float, funds: float) -> tuple[float, float, float, float]:
    values = [max(1.0, stocks), max(1.0, options), max(1.0, futures), max(1.0, funds)]
    total = sum(values)
    pct = [round(v / total * 100, 2) for v in values]
    pct[-1] = round(100 - pct[0] - pct[1] - pct[2], 2)
    return pct[0], pct[1], pct[2], pct[3]


def build_customer_name(index: int) -> str:
    english_first = [
        "Alex", "Ben", "Chris", "Dylan", "Eva", "Frank", "Grace", "Helen", "Iris", "Jack",
        "Kevin", "Luna", "Mason", "Nina", "Oscar", "Penny", "Quinn", "Ryan", "Sophie", "Tony",
        "Uma", "Victor", "Wendy", "Zoe",
    ]
    english_last = [
        "Wang", "Chen", "Li", "Liu", "Zhang", "Yang", "Huang", "Xu", "Sun", "Zhao",
        "Guo", "Lin", "Ma", "Qian", "Shen", "Tang", "Wu", "Xie", "Yuan", "Cai",
        "Deng", "Feng", "Gao", "He",
    ]

    first_idx = (index - 1) % len(english_first)
    last_idx = ((index - 1) // len(english_first)) % len(english_last)
    base_name = f"{english_first[first_idx]} {english_last[last_idx]}"

    unique_capacity = len(english_first) * len(english_last)
    if index <= unique_capacity:
        return base_name

    round_no = ((index - 1) // unique_capacity) + 1
    return f"{base_name} {round_no}"


def sample_nationality(rng: random.Random) -> str:
    roll = rng.random()
    cumulative = 0.0
    for code, weight in NATIONALITY_WEIGHTS:
        cumulative += weight
        if roll <= cumulative:
            return code
    return NATIONALITY_WEIGHTS[-1][0]


def classify_client_type(index: int, total: int) -> str:
    ratio = index / total
    if ratio < 0.12:
        return "HNW"
    if ratio < 0.28:
        return "S-Class"
    if ratio < 0.6:
        return "Frequent Trader"
    if ratio < 0.85:
        return "Core"
    return "New"


def build_tags(client_type: str) -> str:
    if client_type == "HNW":
        return "HNW,S-Class"
    if client_type == "S-Class":
        return "S-Class"
    if client_type == "Frequent Trader":
        return "Frequent Trader"
    if client_type == "New":
        return "New"
    return "Core"


def map_geo_gender(value: object) -> str:
    normalized = str(value or "").strip().lower()
    return "F" if normalized == "female" else "M"


def build_geo_customer_name(user_id: str, city: str) -> str:
    city_name = city or "NZ"
    return f"Map User {user_id} {city_name}"


def load_geo_seed_records(project_root: Path) -> list[dict[str, object]]:
    current_branch_path = project_root / GEO_SOURCE_FILE_PATH
    if current_branch_path.exists():
        return json.loads(current_branch_path.read_text(encoding="utf-8"))

    try:
        payload = subprocess.check_output(
            ["git", "show", GEO_SOURCE_GIT_PATH],
            cwd=project_root,
            text=True,
            encoding="utf-8",
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            "Unable to load geo seed data from leoBranch. Ensure leoBranch exists locally."
        ) from exc

    return json.loads(payload)


def build_geo_customer_base(
    geo_records: list[dict[str, object]],
    *,
    start_index: int,
    max_customers: int,
    existing_uids: set[str],
) -> tuple[pd.DataFrame, dict[str, dict[str, object]]]:
    rows: list[dict[str, object]] = []
    customer_meta: dict[str, dict[str, object]] = {}

    for geo_record in geo_records:
        if len(rows) >= max_customers:
            break

        uid = str(geo_record.get("user_id") or "").strip()
        if not uid or uid in existing_uids:
            continue

        index = start_index + len(rows)
        user_type = str(geo_record.get("user_type") or "").strip()
        city = str(geo_record.get("city") or LOCATIONS[index % len(LOCATIONS)])
        age = int(geo_record.get("age") or 0)
        login_count = int(geo_record.get("login_count") or 0)
        session_count = int(geo_record.get("session_count") or 0)
        currency = "NZD"
        channel_source = CHANNEL_SOURCES[index % len(CHANNEL_SOURCES)]
        style = index % 4

        client_type = GEO_USER_TYPE_TO_CLIENT_TYPE.get(user_type, classify_client_type(index, 2000))

        base_net_assets = 6_000 + age * 180 + login_count * 1_150 + session_count * 720
        if user_type == "高净值用户":
            base_net_assets *= 18
        elif user_type == "完成第一笔交易用户":
            base_net_assets *= 4.5
        elif user_type == "已成功入金用户":
            base_net_assets *= 2.8
        else:
            base_net_assets *= 1.45

        if city == "Auckland":
            base_net_assets *= 1.08
        elif city == "Wellington":
            base_net_assets *= 1.04

        base_net_assets = max(3_000, base_net_assets)
        base_trade_count = max(2, min(48, login_count + max(1, session_count // 2)))
        tags = build_tags(client_type)

        if style == 0:
            stocks_pct, options_pct, futures_pct, funds_pct = normalize_allocation(64, 16, 14, 6)
            trade_category = "stock"
        elif style == 1:
            stocks_pct, options_pct, futures_pct, funds_pct = normalize_allocation(44, 32, 16, 8)
            trade_category = "option"
        elif style == 2:
            stocks_pct, options_pct, futures_pct, funds_pct = normalize_allocation(40, 18, 34, 8)
            trade_category = "futures"
        else:
            stocks_pct, options_pct, futures_pct, funds_pct = normalize_allocation(48, 14, 18, 20)
            trade_category = "fund"

        name = build_geo_customer_name(uid, city)
        rows.append(
            {
                "client_id": f"C{index:04d}",
                "name": name,
                "uid": uid,
                "age": age,
                "gender": map_geo_gender(geo_record.get("gender")),
                "location": city,
                "nationality": "NZ",
                "client_type": client_type,
                "monthly_net_assets_usd": round(base_net_assets, 2),
                "monthly_trade_count": int(base_trade_count),
                "trade_category": trade_category,
                "tags": tags,
                "stocks_pct": stocks_pct,
                "options_pct": options_pct,
                "futures_pct": futures_pct,
                "funds_pct": funds_pct,
                "region": geo_record.get("region"),
                "address": geo_record.get("address"),
                "latitude": geo_record.get("latitude"),
                "longitude": geo_record.get("longitude"),
                "activity_date": geo_record.get("activity_date"),
                "activity_month": geo_record.get("month"),
                "login_count": login_count,
                "session_count": session_count,
                "source_user_id": uid,
                "source_user_type": user_type,
            }
        )

        customer_meta[uid] = {
            "index": index,
            "client_type": client_type,
            "name": name,
            "base_net_assets": base_net_assets,
            "base_trade_count": base_trade_count,
            "location": city,
            "currency": currency,
            "channel_source": channel_source,
            "style": style,
        }
        existing_uids.add(uid)

    return pd.DataFrame(rows), customer_meta


def enrich_seed_customers_with_geo(
    customers: pd.DataFrame,
    customer_meta: dict[str, dict[str, object]],
    geo_records: list[dict[str, object]],
) -> tuple[pd.DataFrame, dict[str, dict[str, object]]]:
    enriched = customers.copy()

    for column in [
        "age",
        "region",
        "address",
        "latitude",
        "longitude",
        "activity_date",
        "activity_month",
        "login_count",
        "session_count",
        "source_user_id",
        "source_user_type",
    ]:
        if column not in enriched.columns:
            enriched[column] = None

    for row_index, geo_record in enumerate(geo_records[: len(enriched)]):
        uid = str(enriched.at[row_index, "uid"])
        city = str(geo_record.get("city") or enriched.at[row_index, "location"])
        enriched.at[row_index, "age"] = int(geo_record.get("age") or 0)
        enriched.at[row_index, "gender"] = map_geo_gender(geo_record.get("gender"))
        enriched.at[row_index, "location"] = city
        enriched.at[row_index, "region"] = geo_record.get("region")
        enriched.at[row_index, "address"] = geo_record.get("address")
        enriched.at[row_index, "latitude"] = geo_record.get("latitude")
        enriched.at[row_index, "longitude"] = geo_record.get("longitude")
        enriched.at[row_index, "activity_date"] = geo_record.get("activity_date")
        enriched.at[row_index, "activity_month"] = geo_record.get("month")
        enriched.at[row_index, "login_count"] = int(geo_record.get("login_count") or 0)
        enriched.at[row_index, "session_count"] = int(geo_record.get("session_count") or 0)
        enriched.at[row_index, "source_user_id"] = str(geo_record.get("user_id") or "")
        enriched.at[row_index, "source_user_type"] = geo_record.get("user_type")

        if uid in customer_meta:
            customer_meta[uid]["location"] = city

    return enriched, customer_meta


def build_customer_base(num_customers: int) -> tuple[pd.DataFrame, dict[str, dict[str, object]]]:
    rows: list[dict[str, object]] = []
    customer_meta: dict[str, dict[str, object]] = {}
    rng = random.Random(20260330)

    for index in range(1, num_customers + 1):
        uid = str(10000 + index)
        client_type = classify_client_type(index, num_customers)
        location = LOCATIONS[index % len(LOCATIONS)]
        currency = CURRENCIES[index % len(CURRENCIES)]
        channel_source = CHANNEL_SOURCES[index % len(CHANNEL_SOURCES)]
        style = index % 4

        band_seed = (index * 37 + 13) % 100
        wave = ((index * 17) % 100) / 100
        if band_seed < 20:
            base_net_assets = 3_500 + wave * 5_800  # Mass: < 10k
        elif band_seed < 60:
            base_net_assets = 12_000 + wave * 82_000  # Core: 10k - 100k
        elif band_seed < 90:
            base_net_assets = 120_000 + wave * 780_000  # Affluent: 100k - 1M
        else:
            base_net_assets = 1_100_000 + wave * 3_900_000  # HNW: > 1M

        if client_type == "HNW":
            base_net_assets *= 1.35
        elif client_type == "New":
            base_net_assets *= 0.72

        base_net_assets = max(3_000, base_net_assets)
        base_trade_count = max(2, 26 - index // 18 + (index % 4))

        tags = build_tags(client_type)

        if style == 0:
            stocks_pct, options_pct, futures_pct, funds_pct = normalize_allocation(64, 16, 14, 6)
            trade_category = "stock"
        elif style == 1:
            stocks_pct, options_pct, futures_pct, funds_pct = normalize_allocation(44, 32, 16, 8)
            trade_category = "option"
        elif style == 2:
            stocks_pct, options_pct, futures_pct, funds_pct = normalize_allocation(40, 18, 34, 8)
            trade_category = "futures"
        else:
            stocks_pct, options_pct, futures_pct, funds_pct = normalize_allocation(48, 14, 18, 20)
            trade_category = "fund"

        rows.append(
            {
                "client_id": f"C{index:04d}",
                "name": build_customer_name(index),
                "uid": uid,
                "age": None,
                "gender": "F" if index % 2 == 0 else "M",
                "location": location,
                "nationality": sample_nationality(rng),
                "client_type": client_type,
                "monthly_net_assets_usd": round(base_net_assets, 2),
                "monthly_trade_count": int(base_trade_count),
                "trade_category": trade_category,
                "tags": tags,
                "stocks_pct": stocks_pct,
                "options_pct": options_pct,
                "futures_pct": futures_pct,
                "funds_pct": funds_pct,
            }
        )

        customer_meta[uid] = {
            "index": index,
            "client_type": client_type,
            "name": rows[-1]["name"],
            "base_net_assets": base_net_assets,
            "base_trade_count": base_trade_count,
            "location": location,
            "currency": currency,
            "channel_source": channel_source,
            "style": style,
        }

    return pd.DataFrame(rows), customer_meta


def build_customer_assets(months: list[tuple[datetime, str]], customer_meta: dict[str, dict[str, object]]) -> tuple[pd.DataFrame, dict[str, dict[str, dict[str, float]]]]:
    rows: list[dict[str, object]] = []
    month_metrics: dict[str, dict[str, dict[str, float]]] = {}

    for month_offset, (month_date, month_str) in enumerate(months):
        month_metrics[month_str] = {}

        for uid, meta in customer_meta.items():
            index = int(meta["index"])
            base_net_assets = float(meta["base_net_assets"])

            growth = 1 + month_offset * 0.018 + 0.03 * math.sin((index + month_offset) / 9)
            if (index + month_offset * 3) % 73 == 0:
                growth *= 1.24
            if (index + month_offset * 5) % 89 == 0:
                growth *= 0.78

            net_assets = max(3_000, base_net_assets * growth)
            deposit_amount = net_assets * (0.012 + (index % 5) * 0.002)
            withdrawal_amount = net_assets * (0.006 + ((index + month_offset) % 4) * 0.0015)
            trading_volume = net_assets * (0.07 + (index % 6) * 0.012 + (month_offset % 3) * 0.008)

            style = int(meta["style"])
            if style == 0:
                stocks_pct, options_pct, futures_pct, funds_pct = normalize_allocation(
                    64 - month_offset * 0.4,
                    16 + month_offset * 0.25,
                    14 + month_offset * 0.12,
                    6 + month_offset * 0.08,
                )
            elif style == 1:
                stocks_pct, options_pct, futures_pct, funds_pct = normalize_allocation(
                    45 - month_offset * 0.35,
                    31 + month_offset * 0.38,
                    16 + month_offset * 0.1,
                    8 + month_offset * 0.05,
                )
            elif style == 2:
                stocks_pct, options_pct, futures_pct, funds_pct = normalize_allocation(
                    42 - month_offset * 0.2,
                    18 + month_offset * 0.2,
                    31 + month_offset * 0.25,
                    9 + month_offset * 0.1,
                )
            else:
                stocks_pct, options_pct, futures_pct, funds_pct = normalize_allocation(
                    49 - month_offset * 0.25,
                    14 + month_offset * 0.12,
                    18 + month_offset * 0.15,
                    19 + month_offset * 0.2,
                )

            rows.append(
                {
                    "uid": uid,
                    "month": month_str,
                    "net_assets": round(net_assets, 2),
                    "deposit_amount": round(deposit_amount, 2),
                    "withdrawal_amount": round(withdrawal_amount, 2),
                    "trading_volume": round(trading_volume, 2),
                    "currency": str(meta["currency"]),
                    "snapshot_date": month_date.strftime("%Y-%m-%d"),
                    "stocks_pct": stocks_pct,
                    "options_pct": options_pct,
                    "futures_pct": futures_pct,
                    "funds_pct": funds_pct,
                }
            )

            month_metrics[month_str][uid] = {
                "net_assets": float(net_assets),
                "trading_volume": float(trading_volume),
            }

    return pd.DataFrame(rows), month_metrics


def build_transactions(months: list[tuple[datetime, str]], customer_meta: dict[str, dict[str, object]], month_metrics: dict[str, dict[str, dict[str, float]]]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    tx_id = 1

    recent_months = months[-3:]
    for month_offset, (month_date, month_str) in enumerate(recent_months):
        for uid, meta in customer_meta.items():
            index = int(meta["index"])
            metrics = month_metrics[month_str][uid]
            primary_type = TRADE_TYPES[int(meta["style"])]
            trade_amount = metrics["trading_volume"] * (0.42 + (index % 4) * 0.05)

            rows.append(
                {
                    "transaction_id": f"T{tx_id:07d}",
                    "uid": uid,
                    "trade_amount": round(trade_amount, 2),
                    "trade_type": primary_type,
                    "trade_date": (month_date + timedelta(days=(index % 20) + 2)).strftime("%Y-%m-%d"),
                    "market": "NZ" if str(meta["location"]).lower() in {"auckland", "wellington", "christchurch"} else "US",
                    "currency": str(meta["currency"]),
                    "month": month_str,
                }
            )
            tx_id += 1

            if index % 7 == 0:
                secondary_type = TRADE_TYPES[(int(meta["style"]) + 1) % len(TRADE_TYPES)]
                rows.append(
                    {
                        "transaction_id": f"T{tx_id:07d}",
                        "uid": uid,
                        "trade_amount": round(trade_amount * 0.58, 2),
                        "trade_type": secondary_type,
                        "trade_date": (month_date + timedelta(days=(index % 20) + 8)).strftime("%Y-%m-%d"),
                        "market": "US",
                        "currency": str(meta["currency"]),
                        "month": month_str,
                    }
                )
                tx_id += 1

    return pd.DataFrame(rows)


def build_rankings(months: list[tuple[datetime, str]], customer_meta: dict[str, dict[str, object]], month_metrics: dict[str, dict[str, dict[str, float]]]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    previous_rank_by_dimension: dict[str, dict[str, int]] = {"auc": {}, "trading": {}}

    for month_offset, (_, month_str) in enumerate(months):
        metrics_map = month_metrics[month_str]
        total_auc = sum(m["net_assets"] for m in metrics_map.values()) or 1.0

        auc_scored: list[tuple[str, float]] = []
        trading_scored: list[tuple[str, float]] = []

        for uid, metrics in metrics_map.items():
            index = int(customer_meta[uid]["index"])

            auc_event = 1 + 0.06 * math.sin((index + month_offset) / 11)
            if (index + month_offset * 7) % 53 == 0:
                auc_event *= 1.35
            if (index + month_offset * 5) % 61 == 0:
                auc_event *= 0.72
            if month_offset % 4 == 0 and 180 <= index <= 235 and index % 9 == 0:
                auc_event *= 1.55
            if month_offset % 5 == 0 and 150 <= index <= 210 and index % 11 == 0:
                auc_event *= 0.60

            trading_event = 1 + 0.10 * math.cos((index * 2 + month_offset) / 13)
            if (index + month_offset * 3) % 47 == 0:
                trading_event *= 1.45
            if (index + month_offset * 4) % 59 == 0:
                trading_event *= 0.68
            if month_offset % 3 == 1 and 170 <= index <= 240 and index % 10 == 0:
                trading_event *= 1.60
            if month_offset % 4 == 2 and 160 <= index <= 220 and index % 12 == 0:
                trading_event *= 0.62

            auc_scored.append((uid, metrics["net_assets"] * auc_event))
            trading_scored.append((uid, metrics["trading_volume"] * trading_event))

        auc_scored.sort(key=lambda item: item[1], reverse=True)
        trading_scored.sort(key=lambda item: item[1], reverse=True)

        current_rank_map_auc: dict[str, int] = {}
        current_rank_map_trading: dict[str, int] = {}

        for rank, (uid, _) in enumerate(auc_scored, start=1):
            current_rank_map_auc[uid] = rank
            metrics = metrics_map[uid]
            previous_rank = previous_rank_by_dimension["auc"].get(uid, rank)
            rows.append(
                {
                    "uid": uid,
                    "month": month_str,
                    "dimension": "auc",
                    "rank": rank,
                    "previous_rank": previous_rank,
                    "client_type": customer_meta[uid]["client_type"],
                    "channel_source": customer_meta[uid]["channel_source"],
                    "auc_share_pct": round(metrics["net_assets"] / total_auc * 100, 4),
                    "trading_volume": round(metrics["trading_volume"], 2),
                    "auc_value": round(metrics["net_assets"], 2),
                }
            )

        for rank, (uid, _) in enumerate(trading_scored, start=1):
            current_rank_map_trading[uid] = rank
            metrics = metrics_map[uid]
            previous_rank = previous_rank_by_dimension["trading"].get(uid, rank)
            rows.append(
                {
                    "uid": uid,
                    "month": month_str,
                    "dimension": "trading",
                    "rank": rank,
                    "previous_rank": previous_rank,
                    "client_type": customer_meta[uid]["client_type"],
                    "channel_source": customer_meta[uid]["channel_source"],
                    "auc_share_pct": round(metrics["net_assets"] / total_auc * 100, 4),
                    "trading_volume": round(metrics["trading_volume"], 2),
                    "auc_value": round(metrics["net_assets"], 2),
                }
            )

        previous_rank_by_dimension["auc"] = current_rank_map_auc
        previous_rank_by_dimension["trading"] = current_rank_map_trading

    return pd.DataFrame(rows)


def generate_multi_month_excel(output_path: Path, num_months: int = 12, num_customers: int = 2000) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    project_root = output_path.resolve().parents[1]

    now = datetime.now()
    start_year = now.year
    start_month = now.month - (num_months - 1)
    while start_month <= 0:
        start_month += 12
        start_year -= 1
    start_date = datetime(start_year, start_month, 1)

    months = []
    for month_offset in range(num_months):
        month_date = add_months(start_date, month_offset)
        months.append((month_date, month_date.strftime("%Y-%m")))

    seed_customer_count = min(260, num_customers)
    customers, customer_meta = build_customer_base(seed_customer_count)

    geo_records = load_geo_seed_records(project_root)
    customers, customer_meta = enrich_seed_customers_with_geo(customers, customer_meta, geo_records)

    remaining_customer_slots = max(0, num_customers - len(customers))
    if remaining_customer_slots > 0:
        geo_customers, geo_customer_meta = build_geo_customer_base(
            geo_records[len(customers):],
            start_index=len(customers) + 1,
            max_customers=remaining_customer_slots,
            existing_uids=set(customers["uid"].astype(str)),
        )
        customers = pd.concat([customers, geo_customers], ignore_index=True)
        customer_meta.update(geo_customer_meta)

    customer_assets, month_metrics = build_customer_assets(months, customer_meta)
    transactions = build_transactions(months, customer_meta, month_metrics)
    rankings = build_rankings(months, customer_meta, month_metrics)

    activities = pd.DataFrame([
        {
            "activity_id": "A001",
            "name": "Auckland Expo",
            "description": "Community marketing",
            "date_start": months[-1][0].strftime("%Y-%m-%d"),
            "date_end": (months[-1][0] + timedelta(days=2)).strftime("%Y-%m-%d"),
            "location": "Auckland",
            "status": "ongoing",
            "total_visitors": 3200,
            "new_signups": 230,
            "conversion_rate": 7.18,
        }
    ])

    activity_tracking = pd.DataFrame([
        {
            "tracking_id": "AT001",
            "activity_id": "A001",
            "sequence": 1,
            "channel_source": "offline",
            "invite_code": "INV001",
            "channel": "expo",
            "client_type": "New",
            "client_name": "Alex Wang",
            "client_uid": "10001",
            "registration_date": months[-1][0].strftime("%Y-%m-%d"),
            "registration_amount": 1200,
            "deposit_status": "yes",
            "attribution_result": "matched",
        }
    ])

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        customers.to_excel(writer, sheet_name="customers", index=False)
        transactions.to_excel(writer, sheet_name="transactions", index=False)
        activities.to_excel(writer, sheet_name="activities", index=False)
        activity_tracking.to_excel(writer, sheet_name="activity_tracking", index=False)
        customer_assets.to_excel(writer, sheet_name="customer_assets", index=False)
        rankings.to_excel(writer, sheet_name="rankings", index=False)

    print(f"✅ Multi-month sample Excel generated: {output_path}")
    print(f"   Months: {num_months}")
    print(f"   Customers: {num_customers}")
    print(f"   Geo seed records used: {min(len(geo_records), len(customers))}")
    print(f"   Date range: {start_date.strftime('%Y-%m')} to {months[-1][1]}")
    print("   Sheet rows:")
    print(f"   - customers: {len(customers)}")
    print(f"   - transactions: {len(transactions)}")
    print(f"   - activities: {len(activities)}")
    print(f"   - activity_tracking: {len(activity_tracking)}")
    print(f"   - customer_assets: {len(customer_assets)}")
    print(f"   - rankings: {len(rankings)}")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    target = project_root / "data" / "sample_import_multi_month.xlsx"
    generate_multi_month_excel(target, num_months=12, num_customers=2000)

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import Any, Callable

import pandas as pd
from beanie import Document
from pymongo import UpdateOne

from app.models import (
    Activity,
    ActivityMetrics,
    ActivityTracking,
    Customer,
    CustomerAsset,
    DailyTrendPoint,
    ImportLog,
    Signal,
    Transaction,
)
from app.schemas.imports import ImportSheetResult, ImportUploadResponse


MAX_ERRORS_PER_SHEET = 30


@dataclass(frozen=True)
class DatasetSpec:
    document_model: type[Document]
    required_fields: tuple[str, ...]
    key_builder: Callable[[dict[str, Any]], dict[str, Any] | None]
    transformer: Callable[[dict[str, Any]], dict[str, Any]]


def _normalize_column_name(name: str) -> str:
    raw = str(name).strip().lower()
    normalized = re.sub(r"[^\w]+", "_", raw, flags=re.UNICODE)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    if not normalized:
        normalized = re.sub(r"\s+", "", raw)
    return COLUMN_ALIASES.get(normalized, normalized)


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    try:
        return bool(pd.isna(value))
    except TypeError:
        return False


def _safe_str(value: Any) -> str | None:
    if _is_empty(value):
        return None
    return str(value).strip()


def _safe_float(value: Any, default: float = 0) -> float:
    if _is_empty(value):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if _is_empty(value):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_datetime(value: Any) -> datetime | None:
    if _is_empty(value):
        return None
    try:
        parsed = pd.to_datetime(value, errors="coerce")
    except (TypeError, ValueError):
        return None
    if pd.isna(parsed):
        return None
    if isinstance(parsed, pd.Timestamp):
        return parsed.to_pydatetime()
    if isinstance(parsed, datetime):
        return parsed
    return None


def _safe_month(value: Any) -> str | None:
    """Parse any date-like value and return a normalized 'YYYY-MM' string.

    Accepts:
    - Already-correct strings like '2026-03'
    - Variants like '2026/03', '2026-3', 'Mar 2026', 'March 2026'
    - pd.Timestamp / datetime objects
    Returns None for empty or unparseable input.
    """
    if _is_empty(value):
        return None
    # Datetime / Timestamp objects: direct format
    if isinstance(value, datetime):
        return value.strftime("%Y-%m")
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m")
    raw = str(value).strip()
    if not raw:
        return None
    # Fast path: already YYYY-MM
    if re.fullmatch(r"\d{4}-\d{2}", raw):
        try:
            datetime.strptime(raw, "%Y-%m")
            return raw
        except ValueError:
            pass
    # Try pandas general parse (covers most formats)
    try:
        parsed = pd.to_datetime(raw, errors="coerce")
        if not pd.isna(parsed):
            return parsed.strftime("%Y-%m")
    except (TypeError, ValueError):
        pass
    return None


def _parse_float_field(
    record: dict[str, Any], field: str, *, required: bool = False, default: float = 0
) -> float:
    value = record.get(field)
    if _is_empty(value):
        if required:
            raise ValueError(f"{field} is required")
        return default
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc


def _parse_int_field(
    record: dict[str, Any], field: str, *, required: bool = False, default: int = 0
) -> int:
    value = record.get(field)
    if _is_empty(value):
        if required:
            raise ValueError(f"{field} is required")
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an integer") from exc


def _parse_datetime_field(
    record: dict[str, Any], field: str, *, required: bool = False
) -> datetime | None:
    value = record.get(field)
    if _is_empty(value):
        if required:
            raise ValueError(f"{field} is required")
        return None
    parsed = _safe_datetime(value)
    if parsed is None:
        raise ValueError(f"{field} must be a valid date")
    return parsed


def _safe_tags(value: Any) -> list[str]:
    if _is_empty(value):
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if not _is_empty(v)]
    normalized = str(value).replace("|", ",").replace(";", ",")
    return [part.strip() for part in normalized.split(",") if part.strip()]


def _serialize_value(value: Any) -> Any:
    if _is_empty(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if isinstance(value, datetime):
        return value
    if isinstance(value, dict):
        serialized: dict[str, Any] = {}
        for key, child in value.items():
            child_serialized = _serialize_value(child)
            if child_serialized is not None:
                serialized[key] = child_serialized
        return serialized
    if isinstance(value, list):
        serialized_list: list[Any] = []
        for child in value:
            child_serialized = _serialize_value(child)
            if child_serialized is not None:
                serialized_list.append(child_serialized)
        return serialized_list
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return item()
        except Exception:
            return value
    return value


def _extract_raw_data(record: dict[str, Any], used_fields: set[str]) -> dict[str, Any]:
    raw_data: dict[str, Any] = {}
    for key, value in record.items():
        if key in used_fields:
            continue
        cleaned = _serialize_value(value)
        if cleaned is not None:
            raw_data[key] = cleaned
    return raw_data


def _build_signal(record: dict[str, Any]) -> dict[str, Any] | None:
    signal_type = _safe_str(record.get("signal_type") or record.get("signal"))
    description = _safe_str(
        record.get("signal_description") or record.get("description")
    )
    recommended_action = _safe_str(
        record.get("recommended_action") or record.get("action")
    )
    if not any([signal_type, description, recommended_action]):
        return None
    return Signal(
        type=signal_type or "",
        description=description or "",
        recommended_action=recommended_action or "",
    ).model_dump()


def _transform_customer(record: dict[str, Any]) -> dict[str, Any]:
    used_fields = {
        "client_id",
        "name",
        "uid",
        "age",
        "gender",
        "location",
        "nationality",
        "client_type",
        "tags",
        "monthly_net_assets_usd",
        "monthly_trade_count",
        "trade_category",
        "stocks_pct",
        "options_pct",
        "futures_pct",
        "funds_pct",
        "signal_type",
        "signal",
        "signal_description",
        "recommended_action",
        "description",
        "action",
    }

    return {
        "client_id": _safe_str(record.get("client_id")),
        "name": _safe_str(record.get("name")) or "",
        "uid": _safe_str(record.get("uid")) or "",
        "age": _safe_int(record.get("age"), default=0) or None,
        "gender": _safe_str(record.get("gender")),
        "location": _safe_str(record.get("location")),
        "nationality": _safe_str(record.get("nationality")),
        "client_type": _safe_str(record.get("client_type")),
        "tags": _safe_tags(record.get("tags")),
        "monthly_net_assets_usd": _safe_float(record.get("monthly_net_assets_usd")),
        "monthly_trade_count": _safe_int(record.get("monthly_trade_count")),
        "trade_category": _safe_str(record.get("trade_category")),
        "asset_allocation": {
            "stocks_pct": _safe_float(record.get("stocks_pct")),
            "options_pct": _safe_float(record.get("options_pct")),
            "futures_pct": _safe_float(record.get("futures_pct")),
            "funds_pct": _safe_float(record.get("funds_pct")),
        },
        "signal": _build_signal(record),
        "raw_data": _extract_raw_data(record, used_fields),
    }


def _transform_transaction(record: dict[str, Any]) -> dict[str, Any]:
    trade_date = _parse_datetime_field(record, "trade_date")
    month = _safe_month(record.get("month"))
    if month is None and trade_date is not None:
        month = trade_date.strftime("%Y-%m")

    used_fields = {
        "transaction_id",
        "uid",
        "month",
        "trade_date",
        "trade_type",
        "trade_category",
        "market",
        "trading_volume",
        "trade_amount",
        "currency",
    }

    return {
        "transaction_id": _safe_str(record.get("transaction_id")),
        "uid": _safe_str(record.get("uid")) or "",
        "month": month,
        "trade_date": trade_date,
        "trade_type": _safe_str(record.get("trade_type")),
        "trade_category": _safe_str(record.get("trade_category")),
        "market": _safe_str(record.get("market")),
        "trading_volume": _safe_float(record.get("trading_volume")),
        "trade_amount": _parse_float_field(record, "trade_amount", required=True),
        "currency": _safe_str(record.get("currency")) or "USD",
        "raw_data": _extract_raw_data(record, used_fields),
    }


def _transform_activity(record: dict[str, Any]) -> dict[str, Any]:
    trend_date = _parse_datetime_field(record, "trend_date")
    daily_trend: list[dict[str, Any]] = []
    if trend_date is not None:
        daily_trend.append(
            DailyTrendPoint(
                date=trend_date,
                cumulative_visitors=_safe_int(record.get("cumulative_visitors")),
                new_signups=_safe_int(
                    record.get("trend_new_signups") or record.get("new_signups")
                ),
            ).model_dump()
        )

    used_fields = {
        "activity_id",
        "name",
        "description",
        "date_start",
        "date_end",
        "location",
        "status",
        "total_visitors",
        "new_signups",
        "conversion_rate",
        "trend_date",
        "cumulative_visitors",
        "trend_new_signups",
    }

    return {
        "activity_id": _safe_str(record.get("activity_id")) or "",
        "name": _safe_str(record.get("name")) or "",
        "description": _safe_str(record.get("description")),
        "date_start": _parse_datetime_field(record, "date_start", required=True)
        or datetime.utcnow(),
        "date_end": _parse_datetime_field(record, "date_end"),
        "location": _safe_str(record.get("location")),
        "status": _safe_str(record.get("status")) or "planned",
        "metrics": ActivityMetrics(
            total_visitors=_safe_int(record.get("total_visitors")),
            new_signups=_safe_int(record.get("new_signups")),
            conversion_rate=_parse_float_field(record, "conversion_rate", default=0),
        ).model_dump(),
        "daily_trend": daily_trend,
        "raw_data": _extract_raw_data(record, used_fields),
    }


def _transform_activity_tracking(record: dict[str, Any]) -> dict[str, Any]:
    used_fields = {
        "tracking_id",
        "activity_id",
        "sequence",
        "channel_source",
        "invite_code",
        "channel",
        "client_type",
        "client_name",
        "client_uid",
        "uid",
        "registration_date",
        "registration_amount",
        "deposit_status",
        "attribution_result",
    }

    client_uid = _safe_str(record.get("client_uid")) or _safe_str(record.get("uid"))

    return {
        "tracking_id": _safe_str(record.get("tracking_id")),
        "activity_id": _safe_str(record.get("activity_id")) or "",
        "sequence": _parse_int_field(record, "sequence", required=True),
        "channel_source": _safe_str(record.get("channel_source")),
        "invite_code": _safe_str(record.get("invite_code")),
        "channel": _safe_str(record.get("channel")),
        "client_type": _safe_str(record.get("client_type")),
        "client_name": _safe_str(record.get("client_name")),
        "client_uid": client_uid,
        "registration_date": _safe_datetime(record.get("registration_date")),
        "registration_amount": _safe_float(record.get("registration_amount")),
        "deposit_status": _safe_str(record.get("deposit_status")),
        "attribution_result": _safe_str(record.get("attribution_result")),
        "raw_data": _extract_raw_data(record, used_fields),
    }


def _transform_customer_asset(record: dict[str, Any]) -> dict[str, Any]:
    used_fields = {
        "uid",
        "month",
        "net_assets",
        "deposit_amount",
        "withdrawal_amount",
        "trading_volume",
        "currency",
        "snapshot_date",
    }

    return {
        "uid": _safe_str(record.get("uid")) or "",
        "month": _safe_month(record.get("month")) or "",
        "net_assets": _safe_float(record.get("net_assets")),
        "deposit_amount": _safe_float(record.get("deposit_amount")),
        "withdrawal_amount": _safe_float(record.get("withdrawal_amount")),
        "trading_volume": _safe_float(record.get("trading_volume")),
        "currency": _safe_str(record.get("currency")) or "USD",
        "snapshot_date": _safe_datetime(record.get("snapshot_date")),
        "raw_data": _extract_raw_data(record, used_fields),
    }


def _transform_ranking(record: dict[str, Any]) -> dict[str, Any]:
    used_fields = {
        "uid",
        "month",
        "dimension",
        "rank",
        "previous_rank",
        "client_type",
        "channel_source",
        "auc_share_pct",
        "trading_volume",
        "auc_value",
    }

    return {
        "uid": _safe_str(record.get("uid")) or "",
        "month": _safe_month(record.get("month")) or "",
        "dimension": _safe_str(record.get("dimension")) or "auc",
        "rank": _parse_int_field(record, "rank", required=True),
        "previous_rank": _parse_int_field(record, "previous_rank", default=0) or None,
        "client_type": _safe_str(record.get("client_type")),
        "channel_source": _safe_str(record.get("channel_source")),
        "auc_share_pct": _safe_float(record.get("auc_share_pct")),
        "trading_volume": _safe_float(record.get("trading_volume")),
        "auc_value": _safe_float(record.get("auc_value")),
        "raw_data": _extract_raw_data(record, used_fields),
    }


def _build_key_by_fields(
    *fields: str,
) -> Callable[[dict[str, Any]], dict[str, Any] | None]:
    def builder(document: dict[str, Any]) -> dict[str, Any] | None:
        key: dict[str, Any] = {}
        for field in fields:
            value = document.get(field)
            if _is_empty(value):
                return None
            key[field] = value
        return key

    return builder


def _build_transaction_key(document: dict[str, Any]) -> dict[str, Any] | None:
    transaction_id = document.get("transaction_id")
    if not _is_empty(transaction_id):
        return {"transaction_id": transaction_id}

    uid = document.get("uid")
    month = document.get("month")
    trade_date = document.get("trade_date")
    trade_type = document.get("trade_type")
    trade_amount = document.get("trade_amount")
    if not _is_empty(uid) and not _is_empty(trade_date) and not _is_empty(trade_type):
        return {
            "uid": uid,
            "trade_date": trade_date,
            "trade_type": trade_type,
            "trade_amount": trade_amount,
        }

    if not _is_empty(uid) and not _is_empty(month):
        return {
            "uid": uid,
            "month": month,
            "trade_type": trade_type or "unknown",
            "trade_amount": trade_amount,
        }

    return None


def _build_activity_tracking_key(document: dict[str, Any]) -> dict[str, Any] | None:
    tracking_id = document.get("tracking_id")
    if not _is_empty(tracking_id):
        return {"tracking_id": tracking_id}

    activity_id = document.get("activity_id")
    sequence = document.get("sequence")
    client_uid = document.get("client_uid")
    if _is_empty(activity_id) or _is_empty(sequence):
        return None
    key = {
        "activity_id": activity_id,
        "sequence": sequence,
    }
    if not _is_empty(client_uid):
        key["client_uid"] = client_uid
    return key


DATASET_SPECS: dict[str, DatasetSpec] = {
    "customers": DatasetSpec(
        document_model=Customer,
        required_fields=("uid", "name"),
        key_builder=_build_key_by_fields("uid"),
        transformer=_transform_customer,
    ),
    "transactions": DatasetSpec(
        document_model=Transaction,
        required_fields=("uid", "trade_amount"),
        key_builder=_build_transaction_key,
        transformer=_transform_transaction,
    ),
    "activities": DatasetSpec(
        document_model=Activity,
        required_fields=("activity_id", "name", "date_start"),
        key_builder=_build_key_by_fields("activity_id"),
        transformer=_transform_activity,
    ),
    "activity_tracking": DatasetSpec(
        document_model=ActivityTracking,
        required_fields=("activity_id", "sequence"),
        key_builder=_build_activity_tracking_key,
        transformer=_transform_activity_tracking,
    ),
    "customer_assets": DatasetSpec(
        document_model=CustomerAsset,
        required_fields=("uid", "month"),
        key_builder=_build_key_by_fields("uid", "month"),
        transformer=_transform_customer_asset,
    ),
}


DATASET_HINTS: dict[str, tuple[str, ...]] = {
    "activity_tracking": ("activity_tracking", "tracking", "attribution"),
    "activities": ("activities", "activity", "campaign"),
    "customers": ("customers", "customer", "clients", "client"),
    "transactions": ("transactions", "transaction", "trading", "trades"),
    "customer_assets": ("customer_assets", "assets", "asset", "portfolio"),
    "rankings": ("rankings", "ranking", "top200", "top_200"),
}


COLUMN_ALIASES: dict[str, str] = {
    "customer_id": "client_id",
    "client_uid": "uid",
    "customer_uid": "uid",
    "user_id": "uid",
    "user_uid": "uid",
    "client_name": "name",
    "customer_name": "name",
    "trade_id": "transaction_id",
    "order_id": "transaction_id",
    "amount": "trade_amount",
    "trade_value": "trade_amount",
    "trade_volume": "trading_volume",
    "volume": "trading_volume",
    "registration_time": "registration_date",
    "register_date": "registration_date",
    "start_date": "date_start",
    "end_date": "date_end",
    "visitors": "total_visitors",
    "signup_count": "new_signups",
    "signups": "new_signups",
    "conversion": "conversion_rate",
    "portfolio_value": "net_assets",
    "account_balance": "net_assets",
    "net_asset": "net_assets",
    "asset_value": "auc_value",
    "rank_change": "previous_rank",
    "country": "nationality",
    "nation": "nationality",
    "citizenship": "nationality",
    "national": "nationality",
    "nationality_code": "nationality",
    "country_code": "nationality",
    "country_region": "nationality",
    "countryregion": "nationality",
    "国籍": "nationality",
    "国家": "nationality",
    "国家_地区": "nationality",
    "国家地区": "nationality",
}


def _normalize_dataframe(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    normalized = normalized.dropna(axis=0, how="all").dropna(axis=1, how="all")
    normalized.columns = [_normalize_column_name(col) for col in normalized.columns]
    return normalized


def _normalize_hint_text(text: str) -> str:
    lowered = text.lower()
    return re.sub(r"[^0-9a-z]+", "_", lowered)


def _infer_dataset(sheet_name: str, file_name: str, columns: set[str]) -> str | None:
    if {"activity_id", "sequence"}.issubset(columns) and (
        "client_uid" in columns or "uid" in columns
    ):
        return "activity_tracking"
    if {"activity_id", "name", "date_start"}.issubset(columns):
        return "activities"
    if {"uid", "name"}.issubset(columns):
        return "customers"
    if {"uid", "month", "net_assets"}.issubset(columns):
        return "customer_assets"
    if {"uid", "month", "rank"}.issubset(columns):
        return "rankings"
    if {"uid", "trade_amount"}.issubset(columns):
        return "transactions"

    hint_text = _normalize_hint_text(f"{sheet_name}_{file_name}")
    for dataset, hints in DATASET_HINTS.items():
        if any(hint in hint_text for hint in hints):
            return dataset
    return None


def _freeze_filter(filter_data: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    frozen: list[tuple[str, str]] = []
    for key in sorted(filter_data.keys()):
        value = filter_data[key]
        if isinstance(value, datetime):
            frozen.append((key, value.isoformat()))
        else:
            frozen.append((key, str(value)))
    return tuple(frozen)


def _truncate_errors(errors: list[str]) -> list[str]:
    if len(errors) <= MAX_ERRORS_PER_SHEET:
        return errors
    remain = len(errors) - MAX_ERRORS_PER_SHEET
    return errors[:MAX_ERRORS_PER_SHEET] + [f"... and {remain} more errors"]


async def _import_sheet(
    dataset: str, sheet_name: str, frame: pd.DataFrame
) -> ImportSheetResult:
    spec = DATASET_SPECS[dataset]
    total_rows = len(frame)
    missing_columns = [
        field for field in spec.required_fields if field not in frame.columns
    ]
    if missing_columns:
        return ImportSheetResult(
            sheet_name=sheet_name,
            dataset=dataset,
            total_rows=total_rows,
            skipped_rows=total_rows,
            errors=[f"Missing required columns: {', '.join(missing_columns)}"],
        )

    errors: list[str] = []
    skipped_rows = 0
    duplicate_rows = 0
    staged_documents: dict[
        tuple[tuple[str, str], ...], tuple[dict[str, Any], dict[str, Any]]
    ] = {}

    for row_number, row in enumerate(frame.to_dict(orient="records"), start=2):
        missing_fields = [
            field for field in spec.required_fields if _is_empty(row.get(field))
        ]
        if missing_fields:
            skipped_rows += 1
            errors.append(
                f"Row {row_number}: missing required values in {', '.join(missing_fields)}"
            )
            continue

        try:
            document = spec.transformer(row)
            key_filter = spec.key_builder(document)
            if key_filter is None:
                skipped_rows += 1
                errors.append(f"Row {row_number}: cannot build unique key")
                continue
            signature = _freeze_filter(key_filter)
            if signature in staged_documents:
                duplicate_rows += 1
            staged_documents[signature] = (key_filter, document)
        except Exception as exc:
            skipped_rows += 1
            errors.append(f"Row {row_number}: {exc}")

    operations: list[UpdateOne] = []
    timestamp = datetime.utcnow()
    for key_filter, document in staged_documents.values():
        payload = dict(document)
        payload["updated_at"] = timestamp
        operations.append(
            UpdateOne(
                key_filter,
                {
                    "$set": payload,
                    "$setOnInsert": {"created_at": timestamp},
                },
                upsert=True,
            )
        )

    imported_rows = 0
    if operations:
        collection = spec.document_model.get_pymongo_collection()
        await collection.bulk_write(operations, ordered=False)
        imported_rows = len(operations)

    valid_rows = total_rows - skipped_rows
    return ImportSheetResult(
        sheet_name=sheet_name,
        dataset=dataset,
        total_rows=total_rows,
        valid_rows=valid_rows,
        imported_rows=imported_rows,
        duplicate_rows=duplicate_rows,
        skipped_rows=skipped_rows,
        errors=_truncate_errors(errors),
    )


async def import_excel_file(
    file_bytes: bytes,
    file_name: str,
    content_type: str | None = None,
) -> ImportUploadResponse:
    try:
        excel_file = pd.ExcelFile(BytesIO(file_bytes), engine="openpyxl")
    except Exception as exc:
        raise ValueError(f"Invalid Excel file: {exc}") from exc

    if not excel_file.sheet_names:
        raise ValueError("Excel file does not contain any worksheet")

    summary: list[ImportSheetResult] = []
    total_rows = 0
    imported_rows = 0
    duplicate_rows = 0
    error_rows = 0

    for sheet_name in excel_file.sheet_names:
        frame = excel_file.parse(sheet_name)
        normalized = _normalize_dataframe(frame)
        row_count = len(normalized)
        total_rows += row_count

        if row_count == 0:
            summary.append(
                ImportSheetResult(
                    sheet_name=sheet_name,
                    dataset="unknown",
                    total_rows=0,
                    valid_rows=0,
                    imported_rows=0,
                    duplicate_rows=0,
                    skipped_rows=0,
                    errors=[],
                )
            )
            continue

        dataset = _infer_dataset(sheet_name, file_name, set(normalized.columns))
        if dataset is None:
            summary.append(
                ImportSheetResult(
                    sheet_name=sheet_name,
                    dataset="unknown",
                    total_rows=row_count,
                    valid_rows=0,
                    imported_rows=0,
                    duplicate_rows=0,
                    skipped_rows=row_count,
                    errors=["Unable to infer dataset type from sheet name and columns"],
                )
            )
            error_rows += row_count
            continue

        if dataset == "rankings":
            summary.append(
                ImportSheetResult(
                    sheet_name=sheet_name,
                    dataset="rankings_ignored",
                    total_rows=row_count,
                    valid_rows=row_count,
                    imported_rows=0,
                    duplicate_rows=0,
                    skipped_rows=0,
                    errors=[],
                )
            )
            continue

        result = await _import_sheet(dataset, sheet_name, normalized)
        summary.append(result)
        imported_rows += result.imported_rows
        duplicate_rows += result.duplicate_rows
        error_rows += result.skipped_rows

    status = "success"
    if imported_rows == 0 and error_rows > 0:
        status = "failed"
    elif error_rows > 0:
        status = "partial_success"

    await ImportLog(
        file_name=file_name,
        content_type=content_type,
        status=status,
        total_rows=total_rows,
        imported_rows=imported_rows,
        duplicate_rows=duplicate_rows,
        error_rows=error_rows,
        summary=[item.model_dump() for item in summary],
    ).insert()

    return ImportUploadResponse(
        file_name=file_name,
        status=status,
        total_rows=total_rows,
        imported_rows=imported_rows,
        duplicate_rows=duplicate_rows,
        error_rows=error_rows,
        summary=summary,
    )

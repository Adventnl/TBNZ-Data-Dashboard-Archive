from datetime import datetime
from typing import Any, Optional

from beanie import Document
from pydantic import BaseModel, Field
from pymongo import ASCENDING, DESCENDING, IndexModel


class AssetAllocation(BaseModel):
    stocks_pct: float = 0
    options_pct: float = 0
    futures_pct: float = 0
    funds_pct: float = 0


class MonthlySnapshot(BaseModel):
    month: str
    net_assets: float = 0
    trade_count: int = 0
    deposit_amount: float = 0
    withdrawal_amount: float = 0
    trading_volume: float = 0
    last_login_date: Optional[datetime] = None


class Signal(BaseModel):
    type: str = ""
    description: str = ""
    recommended_action: str = ""


class ActivityMetrics(BaseModel):
    total_visitors: int = 0
    new_signups: int = 0
    conversion_rate: float = 0


class DailyTrendPoint(BaseModel):
    date: datetime
    cumulative_visitors: int = 0
    new_signups: int = 0


class ImportSheetSummary(BaseModel):
    sheet_name: str
    dataset: str
    total_rows: int = 0
    valid_rows: int = 0
    imported_rows: int = 0
    duplicate_rows: int = 0
    skipped_rows: int = 0
    errors: list[str] = Field(default_factory=list)


class User(Document):
    username: str
    email: str
    hashed_password: str
    role: str = "user"
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"
        indexes = [
            IndexModel([("username", ASCENDING)], unique=True),
            IndexModel([("email", ASCENDING)], unique=True),
            IndexModel([("role", ASCENDING)]),
            IndexModel([("updated_at", DESCENDING)]),
        ]


class Customer(Document):
    client_id: Optional[str] = None
    name: str
    uid: str
    age: Optional[int] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    nationality: Optional[str] = None
    client_type: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    monthly_net_assets_usd: float = 0
    monthly_trade_count: int = 0
    trade_category: Optional[str] = None
    asset_allocation: AssetAllocation = Field(default_factory=AssetAllocation)
    monthly_snapshots: list[MonthlySnapshot] = Field(default_factory=list)
    signal: Optional[Signal] = None
    raw_data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "customers"
        indexes = [
            IndexModel([("uid", ASCENDING)], unique=True),
            IndexModel([("client_id", ASCENDING)]),
            IndexModel([("client_type", ASCENDING)]),
            IndexModel([("location", ASCENDING)]),
            IndexModel([("updated_at", DESCENDING)]),
        ]


class Transaction(Document):
    transaction_id: Optional[str] = None
    uid: str
    month: Optional[str] = None
    trade_date: Optional[datetime] = None
    trade_type: Optional[str] = None
    trade_category: Optional[str] = None
    market: Optional[str] = None
    trading_volume: float = 0
    trade_amount: float = 0
    currency: str = "USD"
    raw_data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "transactions"
        indexes = [
            IndexModel([("transaction_id", ASCENDING)], unique=True, sparse=True),
            IndexModel([("uid", ASCENDING), ("trade_date", DESCENDING)]),
            IndexModel([("month", ASCENDING)]),
        ]


class Activity(Document):
    activity_id: str
    name: str
    description: Optional[str] = None
    date_start: datetime
    date_end: Optional[datetime] = None
    location: Optional[str] = None
    status: str = "planned"
    metrics: ActivityMetrics = Field(default_factory=ActivityMetrics)
    daily_trend: list[DailyTrendPoint] = Field(default_factory=list)
    raw_data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "activities"
        indexes = [
            IndexModel([("activity_id", ASCENDING)], unique=True),
            IndexModel([("date_start", DESCENDING)]),
            IndexModel([("status", ASCENDING)]),
        ]


class ActivityTracking(Document):
    tracking_id: Optional[str] = None
    activity_id: str
    sequence: int = 0
    channel_source: Optional[str] = None
    invite_code: Optional[str] = None
    channel: Optional[str] = None
    client_type: Optional[str] = None
    client_name: Optional[str] = None
    client_uid: Optional[str] = None
    registration_date: Optional[datetime] = None
    registration_amount: float = 0
    deposit_status: Optional[str] = None
    attribution_result: Optional[str] = None
    raw_data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "activity_tracking"
        indexes = [
            IndexModel([("tracking_id", ASCENDING)], unique=True, sparse=True),
            IndexModel([("activity_id", ASCENDING), ("sequence", ASCENDING)]),
            IndexModel([("client_uid", ASCENDING)]),
        ]


class CustomerAsset(Document):
    uid: str
    month: str
    net_assets: float = 0
    deposit_amount: float = 0
    withdrawal_amount: float = 0
    trading_volume: float = 0
    currency: str = "USD"
    snapshot_date: Optional[datetime] = None
    raw_data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "customer_assets"
        indexes = [
            IndexModel([("uid", ASCENDING), ("month", ASCENDING)], unique=True),
            IndexModel([("month", ASCENDING)]),
        ]


class Ranking(Document):
    uid: str
    month: str
    dimension: str = "auc"
    rank: int = 0
    previous_rank: Optional[int] = None
    client_type: Optional[str] = None
    channel_source: Optional[str] = None
    auc_share_pct: float = 0
    trading_volume: float = 0
    auc_value: float = 0
    raw_data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "rankings"
        indexes = [
            IndexModel(
                [("uid", ASCENDING), ("month", ASCENDING), ("dimension", ASCENDING)],
                unique=True,
            ),
            IndexModel(
                [("month", ASCENDING), ("dimension", ASCENDING), ("rank", ASCENDING)]
            ),
        ]


class ImportLog(Document):
    file_name: str
    content_type: Optional[str] = None
    status: str = "success"
    imported_at: datetime = Field(default_factory=datetime.utcnow)
    total_rows: int = 0
    imported_rows: int = 0
    duplicate_rows: int = 0
    error_rows: int = 0
    summary: list[ImportSheetSummary] = Field(default_factory=list)
    message: Optional[str] = None

    class Settings:
        name = "import_logs"
        indexes = [
            IndexModel([("imported_at", DESCENDING)]),
            IndexModel([("file_name", ASCENDING)]),
            IndexModel([("status", ASCENDING)]),
        ]


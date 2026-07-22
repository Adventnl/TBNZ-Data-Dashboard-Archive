from pathlib import Path

import pandas as pd


def build_sample_excel(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    customers = pd.DataFrame(
        [
            {
                "client_id": "C001",
                "name": "Alice Wang",
                "uid": "10001",
                "gender": "F",
                "location": "Auckland",
                "client_type": "HNW",
                "monthly_net_assets_usd": 125000,
                "monthly_trade_count": 12,
                "tags": "HNW,S-Class",
            },
            {
                "client_id": "C002",
                "name": "Bob Chen",
                "uid": "10002",
                "gender": "M",
                "location": "Wellington",
                "client_type": "Frequent Trader",
                "monthly_net_assets_usd": 58000,
                "monthly_trade_count": 20,
                "tags": "Frequent Trader",
            },
        ]
    )

    transactions = pd.DataFrame(
        [
            {
                "transaction_id": "T001",
                "uid": "10001",
                "trade_amount": 12000,
                "trade_type": "stock",
                "trade_date": "2026-03-01",
                "market": "NZ",
                "currency": "NZD",
            },
            {
                "transaction_id": "T002",
                "uid": "10002",
                "trade_amount": 8300,
                "trade_type": "option",
                "trade_date": "2026-03-02",
                "market": "US",
                "currency": "USD",
            },
        ]
    )

    activities = pd.DataFrame(
        [
            {
                "activity_id": "A001",
                "name": "Auckland Expo",
                "description": "Community marketing",
                "date_start": "2026-03-10",
                "date_end": "2026-03-12",
                "location": "Auckland",
                "status": "ongoing",
                "total_visitors": 1200,
                "new_signups": 80,
                "conversion_rate": 6.67,
            }
        ]
    )

    activity_tracking = pd.DataFrame(
        [
            {
                "tracking_id": "AT001",
                "activity_id": "A001",
                "sequence": 1,
                "channel_source": "offline",
                "invite_code": "INV001",
                "channel": "expo",
                "client_type": "New",
                "client_name": "Alice Wang",
                "client_uid": "10001",
                "registration_date": "2026-03-10",
                "registration_amount": 500,
                "deposit_status": "yes",
                "attribution_result": "matched",
            }
        ]
    )

    customer_assets = pd.DataFrame(
        [
            {
                "uid": "10001",
                "month": "2026-03",
                "net_assets": 125000,
                "deposit_amount": 10000,
                "withdrawal_amount": 2000,
                "trading_volume": 15000,
                "currency": "USD",
            },
            {
                "uid": "10002",
                "month": "2026-03",
                "net_assets": 58000,
                "deposit_amount": 3000,
                "withdrawal_amount": 500,
                "trading_volume": 9000,
                "currency": "USD",
            },
        ]
    )

    rankings = pd.DataFrame(
        [
            {
                "uid": "10001",
                "month": "2026-03",
                "dimension": "auc",
                "rank": 12,
                "previous_rank": 16,
                "auc_value": 125000,
                "trading_volume": 15000,
            },
            {
                "uid": "10002",
                "month": "2026-03",
                "dimension": "trading",
                "rank": 25,
                "previous_rank": 30,
                "auc_value": 58000,
                "trading_volume": 9000,
            },
        ]
    )

    users = pd.DataFrame(
        [
            {
                "username": "admin",
                "email": "admin@tigerbrokers.co.nz",
                "password": "admin123",
                "role": "admin",
                "is_active": True,
            },
            {
                "username": "manager",
                "email": "manager@tigerbrokers.co.nz",
                "password": "manager123",
                "role": "manager",
                "is_active": True,
            },
            {
                "username": "user1",
                "email": "user1@tigerbrokers.co.nz",
                "password": "user123",
                "role": "user",
                "is_active": True,
            },
        ]
    )

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        customers.to_excel(writer, sheet_name="customers", index=False)
        transactions.to_excel(writer, sheet_name="transactions", index=False)
        activities.to_excel(writer, sheet_name="activities", index=False)
        activity_tracking.to_excel(writer, sheet_name="activity_tracking", index=False)
        customer_assets.to_excel(writer, sheet_name="customer_assets", index=False)
        rankings.to_excel(writer, sheet_name="rankings", index=False)
        users.to_excel(writer, sheet_name="users", index=False)


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    target = project_root / "data" / "sample_import.xlsx"
    build_sample_excel(target)
    print(f"Sample Excel generated: {target}")

import json
import os

from pymongo import MongoClient


def main() -> None:
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    mongo_db = os.getenv("MONGODB_DB", "growth_analytics")

    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    db = client[mongo_db]

    collections = [
        "customers",
        "transactions",
        "activities",
        "activity_tracking",
        "customer_assets",
        "rankings",
        "import_logs",
    ]

    result = {
        "mongo_uri": mongo_uri,
        "mongo_db": mongo_db,
        "counts": {name: db[name].count_documents({}) for name in collections},
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

import random

from pymongo import MongoClient, UpdateOne


def rebalance_nationality(nz_ratio: float = 0.6, seed: int = 20260330) -> None:
    client = MongoClient("mongodb://localhost:27017")
    collection = client["growth_analytics"]["customers"]

    docs = list(collection.find({}, {"_id": 1, "uid": 1}))
    total = len(docs)
    if total == 0:
        print("No customers found.")
        return

    rng = random.Random(seed)
    rng.shuffle(docs)

    nz_target = round(total * nz_ratio)
    other_pool = ["CN", "AU", "CN - HK", "CN - TW", "CN - MAC", "US", "SG", "MY", "IN"]
    other_weights = [0.21, 0.18, 0.11, 0.08, 0.06, 0.13, 0.09, 0.07, 0.07]

    operations: list[UpdateOne] = []
    for index, doc in enumerate(docs):
        nationality = "NZ" if index < nz_target else rng.choices(other_pool, weights=other_weights, k=1)[0]
        operations.append(
            UpdateOne({"_id": doc["_id"]}, {"$set": {"nationality": nationality}})
        )

    if operations:
        collection.bulk_write(operations, ordered=False)

    print(f"Updated customers: {total}")
    print(f"NZ target count: {nz_target} ({nz_ratio * 100:.2f}%)")


if __name__ == "__main__":
    rebalance_nationality(nz_ratio=0.6, seed=20260330)

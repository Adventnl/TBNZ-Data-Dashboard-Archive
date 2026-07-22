from typing import Optional

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.models import (
    Activity,
    ActivityTracking,
    Customer,
    CustomerAsset,
    ImportLog,
    Ranking,
    Transaction,
    User,
)


_client: Optional[AsyncIOMotorClient] = None


async def init_db() -> None:
    global _client

    if _client is not None:
        return

    _client = AsyncIOMotorClient(settings.mongodb_uri)
    database = _client[settings.mongodb_db]

    await init_beanie(
        database=database,
        document_models=[
            Customer,
            Transaction,
            Activity,
            ActivityTracking,
            CustomerAsset,
            Ranking,
            ImportLog,
            User,
        ],
    )


async def close_db() -> None:
    global _client

    if _client is None:
        return

    _client.close()
    _client = None

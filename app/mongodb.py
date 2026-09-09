from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings

_client: AsyncIOMotorClient | None = None


def obtenir_client_mongo() -> AsyncIOMotorClient:
    global _client

    if _client is None:
        if not settings.mongodb_url:
            raise ValueError(
                "MONGODB_URL n'est pas configuré."
            )
        _client = AsyncIOMotorClient(settings.mongodb_url)

    return _client


def obtenir_base_mongo():
    client = obtenir_client_mongo()
    return client[settings.mongodb_database]
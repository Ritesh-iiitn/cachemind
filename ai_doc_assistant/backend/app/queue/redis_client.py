import logging
import asyncio
from typing import Optional, Any
from backend.app.core.config import settings

logger = logging.getLogger("cachemind.queue.redis_client")


class RedisClientManager:
    """
    Manages async Redis connection pool with automated fallback to fakeredis
    in isolated local testing environments where no standalone Redis daemon is running.
    """
    _instance = None
    _redis_client = None
    _is_fake = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisClientManager, cls).__new__(cls)
        return cls._instance

    async def get_client(self) -> Any:
        if self._redis_client is not None:
            return self._redis_client

        try:
            import redis.asyncio as aioredis
            client = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=2.0,
                socket_connect_timeout=2.0
            )
            # Test ping
            await client.ping()
            self._redis_client = client
            self._is_fake = False
            logger.info(f"Connected to standalone Redis broker at {settings.REDIS_URL}")
            return self._redis_client
        except Exception as e:
            logger.warning(
                f"External Redis broker unreachable ({e}). Initializing embedded in-memory Redis broker (fakeredis)..."
            )
            try:
                import fakeredis.aioredis
                self._redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
                self._is_fake = True
                logger.info("Embedded in-memory Redis broker active. Zero external dependencies required.")
                return self._redis_client
            except Exception as fe:
                logger.error(f"Failed to initialize in-memory Redis broker: {fe}")
                raise fe

    async def is_healthy(self) -> bool:
        try:
            client = await self.get_client()
            await client.ping()
            return True
        except Exception:
            return False

    async def close(self) -> None:
        if self._redis_client is not None:
            try:
                await self._redis_client.aclose()
            except Exception:
                pass
            self._redis_client = None

    @property
    def is_fallback(self) -> bool:
        return self._is_fake


redis_manager = RedisClientManager()

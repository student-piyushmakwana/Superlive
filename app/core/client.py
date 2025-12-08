import httpx
import logging
from app.core.config import config

logger = logging.getLogger("superlive.core.client")

class SuperliveClient:
    _instance = None
    
    @classmethod
    def get_client(cls):
        if cls._instance is None:
            # Default initialization without proxy if not set
            cls.init_client()
        return cls._instance

    @classmethod
    def init_client(cls, proxy: str = None):
        """Initializes or re-initializes the shared client, optionally with a proxy."""
        if cls._instance:
            pass

        logger.info(f"Initializing shared HTTP client with proxy: {proxy}")
        
        cls._instance = httpx.AsyncClient(
            timeout=config.REQUEST_TIMEOUT,
            follow_redirects=True,
            proxy=proxy,
            verify=False,
            headers={
                "accept": "application/json",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": "en-US,en;q=0.9",
                "content-type": "application/json",
                "device-id": config.DEVICE_ID,
                "origin": config.ORIGIN,
                "priority": "u=1, i",
                "referer": config.REFERER,
                "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "cross-site",
                "user-agent": config.USER_AGENT
            },
        )
        return cls._instance

    @classmethod
    async def close_client(cls):
        if cls._instance:
            await cls._instance.aclose()
            cls._instance = None
            logger.info("Shared HTTP client closed.")

    @classmethod
    def update_device_id(cls, device_id: str):
        """Updates the device-id header in the shared client."""
        if cls._instance:
            cls._instance.headers["device-id"] = device_id
            logger.info(f"Updated shared client device-id to {device_id}")

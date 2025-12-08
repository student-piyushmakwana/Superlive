import asyncio
import logging
import random
import string
import uuid
import httpx
from datetime import datetime

logger = logging.getLogger("superlive.core.device")

def generate_random_string(length):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_uuid():
    return str(uuid.uuid4())

async def register_device(proxy: str = None) -> str:
    """
    Registers a new device with the Superlive API and returns the device GUID.
    """
    url = "https://api.spl-web.link/api/web/device/register"
    
    # Generate dynamic payload values
    installation_id = generate_uuid()
    adjust_web_uuid = generate_uuid()
    # uuid_c1 seems to be a 32 char random string based on the example "07iJJjsCOXYEBDTewjpWbdfNRagztYl5"
    uuid_c1 = generate_random_string(32)
    ga_session_id = str(random.randint(1000000000, 9999999999))
    
    payload = {
        "client_params": {
            "os_type": "web",
            "ad_nationality": None,
            "app_build": "3.16.8",
            "app": "superlive",
            "build_code": "640-2941844-prod",
            "app_language": "en",
            "device_language": "en",
            "device_preferred_languages": ["en-US"],
            "source_url": "https://superlive.chat/",
            "session_source_url": "https://superlive.chat/",
            "referrer": "",
            "adjust_attribution_data": None,
            "adjust_web_uuid": adjust_web_uuid,
            "firebase_analytics_id": None,
            "incognito": True,
            "installation_id": installation_id,
            "uuid_c1": uuid_c1,
            "vl_cid": None,
            "ttp": "01KBXQA3JH6C8GENR7V3GS9WWY_.tt.1", # Keeping this constant as it might be a tracker template or similar
            "twclid": None,
            "tdcid": None,
            "fbc": None,
            "fbp": None,
            "ga_session_id": ga_session_id,
            "web_type": 1
        }
    }

    headers = {
        "authority": "api.spl-web.link",
        "accept": "application/json",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json",
        "origin": "https://superlive.chat",
        "priority": "u=1, i",
        "referer": "https://superlive.chat/",
        "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
    }

    logger.info(f"Registering new device... (Proxy: {proxy})")
    
    async with httpx.AsyncClient(proxy=proxy, verify=False) as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if "guid" in data:
                logger.info(f"Device registered successfully. GUID: {data['guid']}")
                return data["guid"]
            else:
                logger.error(f"Registration response did not contain 'guid': {data}")
                raise Exception("Invalid registration response")
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP Error during device registration: {e}")
            raise
        except Exception as e:
            logger.error(f"Error during device registration: {e}")
            raise

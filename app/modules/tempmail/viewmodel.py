import logging
import httpx
from app.core.config import config

logger = logging.getLogger("superlive.modules.tempmail.viewmodel")

class TempMailViewModel:
    BASE_URL = "https://tempmail.so/us/api"

    async def get_inbox(self, request_time: int, lang: str = "us", cookies: dict = None):
        """
        Fetch inbox from tempmail.so
        """
        url = f"{self.BASE_URL}/inbox"
        
        params = {
            "requestTime": request_time,
            "lang": lang
        }
        
        headers = {
            "authority": "tempmail.so",
            "accept": "application/json",
            "accept-encoding": "gzip, deflate", # No br/zstd to avoid decoding issues
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/json",
            "origin": "https://tempmail.so",
            "referer": "https://tempmail.so/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "x-inbox-lifespan": "600"
        }

        # If cookies are provided, add them to the request
        # Note: In a real scenario, we might need to parse the raw cookie string if passed that way,
        # but httpx accepts a dict or CookieJar.
        
        async with httpx.AsyncClient(headers=headers, cookies=cookies) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                logger.error(f"TempMail API error: {e.response.text}")
                raise Exception(f"TempMail API error: {e.response.status_code}")
            except Exception as e:
                logger.error(f"Unexpected TempMail error: {e}")
                raise

    def extract_otp(self, inbox_data: dict) -> str:
        """
        Extract 6-digit OTP from the inbox.
        Returns the code if found, else None.
        """
        import re
        
        if not inbox_data or "data" not in inbox_data or "inbox" not in inbox_data["data"]:
            return None
            
        messages = inbox_data["data"]["inbox"]
        if not messages:
            return None
            
        # Look for the most recent message from SuperLive
        for msg in messages:
            if "SuperLive" in msg.get("senderName", "") or "SuperLive" in msg.get("subject", ""):
                text_body = msg.get("textBody", "")
                # Search for 6 digit code
                # The example shows it on a line by itself or surrounded by whitespace
                match = re.search(r'\b(\d{6})\b', text_body)
                if match:
                    return match.group(1)
        
        return None

    async def delete_inbox(self, cookies: dict, request_time: int, lang: str = "us"):
        """
        Delete inbox from tempmail.so
        """
        url = f"{self.BASE_URL}/inbox"
        
        params = {
            "requestTime": request_time,
            "lang": lang
        }
        
        headers = {
            "authority": "tempmail.so",
            "accept": "application/json",
            "accept-encoding": "gzip, deflate", # No br/zstd to avoid decoding issues
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/json",
            "origin": "https://tempmail.so",
            "referer": "https://tempmail.so/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "x-inbox-lifespan": "600"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.delete(
                    url, 
                    params=params, 
                    headers=headers, 
                    cookies=cookies
                )
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                logger.error(f"TempMail delete inbox failed: {e.response.text}")
                raise Exception(f"TempMail delete inbox failed: {e.response.status_code}")
            except Exception as e:
                logger.error(f"Unexpected TempMail delete inbox error: {e}")
                raise

temp_mail_viewmodel = TempMailViewModel()

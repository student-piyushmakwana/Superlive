import logging
import asyncio
import httpx
import uuid
import secrets
from app.core.client import SuperliveClient
from app.core.config import config

logger = logging.getLogger("superlive.modules.api.viewmodel")

class SuperliveError(Exception):
    def __init__(self, message: str, status_code: int = 500, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)

class ApiViewModel:
    
    async def _make_request(self, method: str, endpoint: str, client, error_context: str = "Request failed", **kwargs):
        """
        Helper method to make requests with fallback to backup URL on network errors or specific status codes.
        """
        urls = [
            f"{config.API_BASE_URL}{endpoint}",
            f"{config.API_BASE_URL_BACKUP}{endpoint}"
        ]
        
        last_exception = None
        
        for i, url in enumerate(urls):
            is_backup = i > 0
            try:
                if is_backup:
                    logger.warning(f"Retrying with backup URL: {url}")
                    
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                # If it's a 5xx or 403, we might want to try backup
                # Also adding 404 just in case the primary API routing is broken
                # The user mentioned "code 12", but we catch standard HTTP connection issues
                if e.response.status_code in [403, 502, 503, 504] and not is_backup:
                    logger.warning(f"Primary URL failed with status {e.response.status_code}. Attempting backup.")
                    last_exception = e
                    continue
                
                logger.error(f"{error_context}: {e.response.text}")
                try:
                    details = e.response.json()
                except:
                    details = {"error": e.response.text}
                raise SuperliveError(error_context, e.response.status_code, details)
                
            except (httpx.NetworkError, httpx.TimeoutException) as e:
                if not is_backup:
                    logger.warning(f"Network error on primary URL: {e}. Attempting backup.")
                    last_exception = e
                    continue
                
                logger.error(f"Unexpected {error_context.lower()} error: {e}")
                # If we have a last_exception from primary, maybe we should mention that too?
                # But usually the last error (backup failed) is the one to raise
                raise SuperliveError(f"Unexpected error: {str(e)}")
                
            except Exception as e:
                logger.error(f"Unexpected {error_context.lower()} error: {e}")
                raise SuperliveError(f"Unexpected error: {str(e)}")
                
        # Should not reach here if loop works correctly
        raise SuperliveError(f"Unexpected error: {str(last_exception)}")

    async def login(self, email, password, client=None):
        if client is None:
            client = SuperliveClient.get_client()
        
        payload = {
            "client_params": self._get_client_params(),
            "email": email,
            "password": password
        }
        
        # Fixed: Removed undefined 'headers' variable usage
        return await self._make_request(
            "POST", 
            "/signup/email_signin", 
            client, 
            json=payload, 
            error_context="Login failed"
        )

    async def get_profile(self, token, client=None):
        if client is None:
            client = SuperliveClient.get_client()
        
        headers = client.headers.copy()
        headers["authorization"] = f"Token {token}"
        
        payload = {
            "client_params": self._get_client_params()
        }
        
        return await self._make_request(
            "POST", 
            "/own_profile", 
            client, 
            headers=headers, 
            json=payload, 
            error_context="Get profile failed"
        )

    async def send_gift(self, token, gift_details, client=None):
        if client is None:
            client = SuperliveClient.get_client()
        
        headers = client.headers.copy()
        headers["authorization"] = f"Token {token}"
        
        livestream_id = gift_details.get('livestream_id')
        
        # Generate guid if not provided
        guids = gift_details.get("guids", [])
        if not guids:
            guids = [str(uuid.uuid4())]
        
        payload = {
            "client_params": self._get_client_params(livestream_id),
            "gift_context": gift_details.get("gift_context", 1),
            "livestream_id": livestream_id,
            "gift_id": gift_details.get("gift_id"),
            "guids": guids
        }
        
        return await self._make_request(
            "POST", 
            "/livestream/chat/send_gift", 
            client, 
            headers=headers, 
            json=payload, 
            error_context="Send gift failed"
        )

    async def get_livestream(self, token, livestream_id, client=None):
        if client is None:
            client = SuperliveClient.get_client()
        
        headers = client.headers.copy()
        headers["authorization"] = f"Token {token}"
        
        payload = {
            "client_params": self._get_client_params(livestream_id),
            "livestream_id": livestream_id
        }
        
        return await self._make_request(
            "POST", 
            "/livestream/retrieve", 
            client, 
            headers=headers, 
            json=payload, 
            error_context="Get livestream failed"
        )

    async def send_verification_code(self, email, client=None):
        if client is None:
            client = SuperliveClient.get_client()
        
        payload = {
            "client_params": self._get_client_params(),
            "email": email,
            "force_new": False
        }
        
        return await self._make_request(
            "POST", 
            "/signup/send_email_verification_code", 
            client, 
            json=payload, 
            error_context="Send verification code failed"
        )

    async def verify_email(self, email_verification_id, code, client=None):
        if client is None:
            client = SuperliveClient.get_client()
        
        payload = {
            "client_params": self._get_client_params(),
            "email_verification_id": email_verification_id,
            "code": int(code)
        }
        
        return await self._make_request(
            "POST", 
            "/signup/verify_email", 
            client, 
            json=payload, 
            error_context="Verify email failed"
        )

    async def complete_signup(self, email, password, client=None):
        if client is None:
            client = SuperliveClient.get_client()
        
        payload = {
            "client_params": self._get_client_params(),
            "email": email,
            "password": password
        }
        
        return await self._make_request(
            "POST", 
            "/signup/email", 
            client, 
            json=payload, 
            error_context="Complete signup failed"
        )

    async def logout(self, token, client=None):
        if client is None:
            client = SuperliveClient.get_client()
        
        headers = client.headers.copy()
        headers["authorization"] = f"Token {token}"
        
        payload = {
            "client_params": self._get_client_params()
        }
        
        return await self._make_request(
            "POST", 
            "/user/logout", 
            client, 
            headers=headers, 
            json=payload, 
            error_context="Logout failed"
        )

    async def update_profile(self, token, client=None):
        if client is None:
            client = SuperliveClient.get_client()
            
        headers = client.headers.copy()
        headers["authorization"] = f"Token {token}"
        
        # Random Heart Logic
        import random
        hearts = ["❤️", "🩷","🧡","💛","💚","💙","🩵","💜","🤎","🖤","🩶","🤍"]
        random_heart = random.choice(hearts)
        name_with_heart = f"Piyush {random_heart}" 
        
        # Use specific client params for profile update
        client_params = self._get_client_params()
        client_params["source_url"] = "https://superlive.chat/profile/edit-profile"
        
        payload = {
            "client_params": client_params,
            "name": name_with_heart,
            "bio": "SDE 🖥️"
        }
        
        return await self._make_request(
            "POST", 
            "/users/update", 
            client, 
            headers=headers, 
            json=payload, 
            error_context="Update profile failed"
        )

    def _get_client_params(self, livestream_id=None):
        source_url = "https://superlive.chat/profile/myprofile"
        if livestream_id:
            source_url = f"https://superlive.chat/livestream/{livestream_id}"
            
        return {
            "os_type": "web",
            "ad_nationality": None,
            "app_build": "3.16.8",
            "app": "superlive",
            "build_code": "639-2941571-prod",
            "app_language": "en",
            "device_language": "en",
            "device_preferred_languages": ["en-US"],
            "source_url": source_url,
            "session_source_url": "https://superlive.chat/discover",
            "referrer": "https://superlive.chat/discover",
            "adid": "466f7443143a3df42868339f73e53887",
            "adjust_attribution_data": {
                "adid": "466f7443143a3df42868339f73e53887",
                "tracker_token": "mii5ej6",
                "tracker_name": "Organic",
                "network": "Organic"
            },
            "adjust_web_uuid": "7db60b38-4a09-44af-82be-ecbbdb651c3e",
            "firebase_analytics_id": "1134312538.1765088771",
            "incognito": True,
            "installation_id": "cbfd66d2-202d-4e61-89c4-3fd6e0986af9",
            "rtc_id": "3455648103",
            "uuid_c1": "PDTmQ51-ZSyxszb4a9Lr2jVJosWRKfgp",
            "vl_cid": None,
            "ttp": "01KBVQTFYEQNYS9BNY68FRVXTV_.tt.1",
            "twclid": None,
            "tdcid": None,
            "fbc": None,
            "fbp": "fb.1.1765088773919.96546003186470457",
            "ga_session_id": "1765088771",
            "web_type": 1
        }

api_viewmodel = ApiViewModel()

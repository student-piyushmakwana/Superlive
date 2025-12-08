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
    
    async def login(self, email, password, client=None):
        url = f"{config.API_BASE_URL}/signup/email_signin"
        if client is None:
            client = SuperliveClient.get_client()
        
        payload = {
            "client_params": self._get_client_params(),
            "email": email,
            "password": password
        }
        
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Login failed: {e.response.text}")
            try:
                details = e.response.json()
            except:
                details = {"error": e.response.text}
            raise SuperliveError("Login failed", e.response.status_code, details)
        except Exception as e:
            logger.error(f"Unexpected login error: {e}")
            raise SuperliveError(f"Unexpected error: {str(e)}")

    async def get_profile(self, token, client=None):
        url = f"{config.API_BASE_URL}/own_profile"
        if client is None:
            client = SuperliveClient.get_client()
        
        headers = client.headers.copy()
        headers["authorization"] = f"Token {token}"
        
        payload = {
            "client_params": self._get_client_params()
        }
        
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Get profile failed: {e.response.text}")
            try:
                details = e.response.json()
            except:
                details = {"error": e.response.text}
            raise SuperliveError("Get profile failed", e.response.status_code, details)
        except Exception as e:
            logger.error(f"Unexpected profile error: {e}")
            raise SuperliveError(f"Unexpected error: {str(e)}")

    async def send_gift(self, token, gift_details, client=None):
        url = f"{config.API_BASE_URL}/livestream/chat/send_gift"
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
        
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Send gift failed: {e.response.text}")
            try:
                details = e.response.json()
            except:
                details = {"error": e.response.text}
            raise SuperliveError("Send gift failed", e.response.status_code, details)
        except Exception as e:
            logger.error(f"Unexpected send gift error: {e}")
            raise SuperliveError(f"Unexpected error: {str(e)}")

    async def get_livestream(self, token, livestream_id, client=None):
        url = f"{config.API_BASE_URL}/livestream/retrieve"
        if client is None:
            client = SuperliveClient.get_client()
        
        headers = client.headers.copy()
        headers["authorization"] = f"Token {token}"
        
        payload = {
            "client_params": self._get_client_params(livestream_id),
            "livestream_id": livestream_id
        }
        
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Get livestream failed: {e.response.text}")
            try:
                details = e.response.json()
            except:
                details = {"error": e.response.text}
            raise SuperliveError("Get livestream failed", e.response.status_code, details)
        except Exception as e:
            logger.error(f"Unexpected livestream error: {e}")
            raise SuperliveError(f"Unexpected error: {str(e)}")

    async def send_verification_code(self, email, client=None):
        url = f"{config.API_BASE_URL}/signup/send_email_verification_code"
        if client is None:
            client = SuperliveClient.get_client()
        
        payload = {
            "client_params": self._get_client_params(),
            "email": email,
            "force_new": False
        }
        
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Send verification code failed: {e.response.text}")
            try:
                details = e.response.json()
            except:
                details = {"error": e.response.text}
            raise SuperliveError("Send verification code failed", e.response.status_code, details)
        except Exception as e:
            logger.error(f"Unexpected send verification error: {e}")
            raise SuperliveError(f"Unexpected error: {str(e)}")

    async def verify_email(self, email_verification_id, code, client=None):
        url = f"{config.API_BASE_URL}/signup/verify_email"
        if client is None:
            client = SuperliveClient.get_client()
        
        payload = {
            "client_params": self._get_client_params(),
            "email_verification_id": email_verification_id,
            "code": int(code)
        }
        
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Verify email failed: {e.response.text}")
            try:
                details = e.response.json()
            except:
                details = {"error": e.response.text}
            raise SuperliveError("Verify email failed", e.response.status_code, details)
        except Exception as e:
            logger.error(f"Unexpected verify email error: {e}")
            raise SuperliveError(f"Unexpected error: {str(e)}")

    async def complete_signup(self, email, password, client=None):
        # Note: Request URL for final signup is same as initial check but it succeeds after verification
        url = f"{config.API_BASE_URL}/signup/email"
        if client is None:
            client = SuperliveClient.get_client()
        
        payload = {
            "client_params": self._get_client_params(),
            "email": email,
            "password": password
        }
        
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Unexpected complete signup error: {e}")
            raise SuperliveError(f"Unexpected error: {str(e)}")

    async def logout(self, token, client=None):
        url = f"{config.API_BASE_URL}/user/logout"
        if client is None:
            client = SuperliveClient.get_client()
        
        headers = client.headers.copy()
        headers["authorization"] = f"Token {token}"
        
        payload = {
            "client_params": self._get_client_params()
        }
        
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Logout failed: {e.response.text}")
            # Logout failure shouldn't necessarily block the flow, but we raise for consistency
            try:
                details = e.response.json()
            except:
                details = {"error": e.response.text}
            raise SuperliveError("Logout failed", e.response.status_code, details)
        except Exception as e:
            logger.error(f"Unexpected logout error: {e}")
            raise SuperliveError(f"Unexpected error: {str(e)}")

    async def update_profile(self, token, client=None):
        url = f"{config.API_BASE_URL}/users/update"
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
        
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Update profile failed: {e.response.text}")
            try:
                details = e.response.json()
            except:
                details = {"error": e.response.text}
            raise SuperliveError("Update profile failed", e.response.status_code, details)
        except Exception as e:
            logger.error(f"Unexpected update profile error: {e}")
            raise SuperliveError(f"Unexpected error: {str(e)}")

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

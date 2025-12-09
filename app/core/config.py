import os
import secrets
import logging
from dotenv import load_dotenv

load_dotenv()

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Silence asyncio warnings
logging.getLogger("asyncio").setLevel(logging.ERROR)

logger = logging.getLogger("superlive.config")

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_urlsafe(32)
    REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", 30))
    APP_ENV = os.environ.get("APP_ENV", "development").lower()
    
    # Superlive API Constants
    API_BASE_URL = "https://api.spl-web-live.link/api/web"
    API_BASE_URL_BACKUP = "https://api.spl-web.link/api/web"
    API_BASE_URL_3 = "https://api.superlivechat.tv/api/web/"
    
    API_BASES = {
        1: API_BASE_URL,
        2: API_BASE_URL_BACKUP,
        3: API_BASE_URL_3
    }
    
    ORIGIN = "https://superlive.chat"
    REFERER = "https://superlive.chat/"
    
    DOMAINS = [
        {"origin": "https://superlive.chat", "referer": "https://superlive.chat/"},
        {"origin": "https://superlivetv.com", "referer": "https://superlivetv.com/"},
    ]
    
    DEVICE_ID = os.environ.get("DEVICE_ID", "6f085f032ee56b4880bb78584529d0b7")
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"

    PROXIES = []
    
    # Load proxies from proxy.txt if exists
    _proxy_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "proxy.txt")
    if os.path.exists(_proxy_file):
        try:
            with open(_proxy_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    parts = line.split(":")
                    if len(parts) == 4:
                        # Format: IP:PORT:USER:PASS -> http://USER:PASS@IP:PORT
                        ip, port, user, pwd = parts
                        PROXIES.append(f"http://{user}:{pwd}@{ip}:{port}")
            if PROXIES:
                print(f"✅ Loaded {len(PROXIES)} proxies from proxy.txt")
        except Exception as e:
            print(f"⚠️ Failed to load proxy.txt: {e}")
            
    if not PROXIES:
        # Fallback to hardcoded if file load failed or empty
        PROXIES = [
            "http://vamdbzsk:mrengh5k06ph@142.111.48.253:7030",
            "http://vamdbzsk:mrengh5k06ph@31.59.20.176:6754",
            "http://vamdbzsk:mrengh5k06ph@23.95.150.145:6114",
            "http://vamdbzsk:mrengh5k06ph@198.23.239.134:6540",
            "http://vamdbzsk:mrengh5k06ph@107.172.163.27:6543",
            "http://vamdbzsk:mrengh5k06ph@198.105.121.200:6462",
            "http://vamdbzsk:mrengh5k06ph@64.137.96.74:6641",
            "http://vamdbzsk:mrengh5k06ph@84.247.60.125:6095",
            "http://vamdbzsk:mrengh5k06ph@216.10.27.159:6837",
            "http://vamdbzsk:mrengh5k06ph@142.111.67.146:5611"
        ]

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

ENVIRONMENT = os.environ.get("APP_ENV", "development").lower()

if ENVIRONMENT == "development":
    config = DevelopmentConfig()
else:
    config = ProductionConfig()

logger.info(f"✅ Active configuration: {config.__class__.__name__}")

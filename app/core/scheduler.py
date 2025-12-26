import os
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import httpx

logger = logging.getLogger("superlive.scheduler")

scheduler = AsyncIOScheduler()

async def ping_self():
    """
    Pings the application itself to keep the instance active.
    Renters requires requests within 15 mins to prevent sleep.
    """
    base_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not base_url:
        # Fallback for local testing or if variable isn't set, though mostly useful on Render
        base_url = "http://127.0.0.1:5000" 
        logger.debug(f"RENDER_EXTERNAL_URL not set, using {base_url}")

    # Ensure no trailing slash
    base_url = base_url.rstrip("/")
    health_url = f"{base_url}/health"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(health_url)
            logger.info(f"⏰ Self-ping to {health_url}: Status {resp.status_code}")
    except Exception as e:
        logger.error(f"❌ Failed to ping self ({health_url}): {e}")

def start_scheduler():
    """
    Initializes and starts the scheduler.
    """
    if not scheduler.running:
        # Schedule the job to run every 10 minutes
        scheduler.add_job(ping_self, 'interval', minutes=10, id='self_ping', replace_existing=True)
        scheduler.start()
        logger.info("✅ Scheduler started: Self-ping task scheduled every 10 minutes.")

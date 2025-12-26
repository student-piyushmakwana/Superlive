from quart import Quart
from quart_cors import cors
import logging

from app.core.config import config
from app.core.client import SuperliveClient
from app.modules.api.routes import api_bp
from app.modules.tempmail.routes import temp_mail_bp

from app.core.logger import setup_logger

def create_app():
    app = Quart(__name__)
    app = cors(app, allow_origin="*")

    app.register_blueprint(api_bp)
    app.register_blueprint(temp_mail_bp)

    @app.before_serving
    async def startup():
        setup_logger()
        # Start Scheduler for self-ping logic
        from app.core.scheduler import start_scheduler
        start_scheduler()
        logging.info("🚀 Starting Superlive API...")

    @app.after_serving
    async def shutdown():
        logging.info("🛑 Shutting down Superlive API...")
        await SuperliveClient.close_client()

    return app

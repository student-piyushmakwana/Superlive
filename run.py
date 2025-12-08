import logging
from app import create_app
from app.core.config import config

# Logging is already configured in app.core.config subclass instantiation (via import)


app = create_app()

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=config.DEBUG
    )

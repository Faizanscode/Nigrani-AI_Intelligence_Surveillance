import logging
from backend.app.core.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOGGING_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

def get_logger(name: str):
    return logging.getLogger(name)

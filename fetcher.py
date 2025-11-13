"""
Zoom Recording Fetcher Entry Point
Run this to automatically fetch and transcribe Zoom recordings
"""

import logging
from logging.handlers import RotatingFileHandler
from src.workers.zoom_fetcher import start_fetcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(
            'fetcher.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
    ]
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("="*60)
    logger.info("ZOOM RECORDING FETCHER & TRANSCRIBER")
    logger.info("="*60)
    start_fetcher()

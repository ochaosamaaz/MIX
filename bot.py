"""
AI Market News Bot - Main Entry Point
Telegram bot for Crypto, US Stocks, and Forex news
with AI-powered summarization and sentiment analysis.
"""

import logging
from telegram.ext import Application

from config import settings
from handlers import register_handlers
from scheduler import setup_scheduler

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    """Start the bot."""
    # Validate settings
    missing = settings.validate()
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        logger.error("Please copy .env.example to .env and fill in the values.")
        return

    logger.info("Starting AI Market News Bot...")

    # Build the application
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    # Register command and message handlers
    register_handlers(app)

    # Setup scheduled jobs (morning & evening market updates)
    setup_scheduler(app)

    logger.info("Bot is running! Press Ctrl+C to stop.")

    # Start polling for updates
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

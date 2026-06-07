"""
AI Market News Bot - Main Entry Point
Telegram bot for Crypto, US Stocks, and Forex news
with AI-powered summarization and sentiment analysis.
"""

import asyncio
import logging
import signal

from telegram import Bot
from telegram.ext import Application, ApplicationBuilder

from config import settings
from handlers import register_handlers
from handlers.fx_handlers import register_fx_handlers
from handlers.ask_handler import register_ask_handler
from handlers.risk_calculator import register_risk_handler
from scheduler import setup_scheduler

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def main():
    """Start the bot."""
    # Validate settings
    missing = settings.validate()
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        logger.error("Please copy .env.example to .env and fill in the values.")
        return

    logger.info("Starting AI Market News Bot...")

    # Build the application
    app = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()

    # Register command and message handlers
    register_handlers(app)

    # Register FX trading feature handlers
    register_fx_handlers(app)

    # Register Ask AI handler
    register_ask_handler(app)

    # Register Risk Calculator handler
    register_risk_handler(app)

    # Setup scheduled jobs (market updates, FX signals, session updates, etc.)
    setup_scheduler(app)

    logger.info("Bot is running! Press Ctrl+C to stop.")

    # Initialize and start
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    # Keep running until interrupted
    stop_event = asyncio.Event()

    # Handle signals for graceful shutdown
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass

    try:
        await stop_event.wait()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        logger.info("Shutting down bot...")
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")

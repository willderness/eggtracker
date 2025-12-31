"""Telegram bot for tracking egg production."""

import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import sheets

load_dotenv()

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    welcome_message = (
        "Welcome to Eggegram! I'll help you track your chicken eggs.\n\n"
        "How to use:\n"
        "- Send a number to log eggs for today (e.g., '3')\n"
        "- Send /stats to see your weekly statistics\n\n"
        "Happy egg collecting!"
    )
    await update.message.reply_text(welcome_message)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /stats command - show weekly statistics."""
    try:
        today_total = sheets.get_today_total()
        week_total = sheets.get_week_total()
        breakdown = sheets.get_week_breakdown()

        # Build the breakdown string
        breakdown_lines = [f"  {date}: {count}" for date, count in breakdown]
        breakdown_str = "\n".join(breakdown_lines)

        message = (
            f"Weekly Stats\n"
            f"{'=' * 20}\n"
            f"Today: {today_total} eggs\n"
            f"Week Total: {week_total} eggs\n\n"
            f"Daily Breakdown:\n{breakdown_str}"
        )
        await update.message.reply_text(message)

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        await update.message.reply_text(
            "Sorry, I couldn't fetch the stats. Please try again later."
        )


async def handle_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle numeric messages - add eggs to today's count."""
    text = update.message.text.strip()

    try:
        count = int(text)

        if count < 0:
            await update.message.reply_text("Please send a positive number.")
            return

        if count > 100:
            await update.message.reply_text(
                "That seems like a lot of eggs! Are you sure? "
                "Please enter a number under 100."
            )
            return

        today_total, week_total = sheets.add_eggs(count)

        await update.message.reply_text(
            f"Added {count} eggs! Today: {today_total} | Week: {week_total}"
        )

    except ValueError:
        # Not a number, ignore or provide help
        await update.message.reply_text(
            "Send a number to log eggs, or /stats for weekly stats."
        )
    except Exception as e:
        logger.error(f"Error adding eggs: {e}")
        await update.message.reply_text(
            "Sorry, I couldn't log the eggs. Please try again later."
        )


def main() -> None:
    """Start the bot."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")

    # Create application
    application = Application.builder().token(token).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number)
    )

    # Run the bot
    # Check if we're in webhook mode (for production) or polling (for dev)
    webhook_url = os.environ.get("WEBHOOK_URL")
    port = int(os.environ.get("PORT", 8443))

    if webhook_url:
        # Production: use webhook
        logger.info(f"Starting webhook on port {port}")
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=token,
            webhook_url=f"{webhook_url}/{token}",
        )
    else:
        # Development: use polling
        logger.info("Starting polling mode")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

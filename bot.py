import sys
import logging
from telegram import BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    Application
)

from config import BOT_TOKEN, validate_config
from handlers.commands import start_command, help_command, about_command
from handlers.callbacks import callback_router
from handlers.messages import handle_message

# Configure logging
logging.basicConfig(
    format="%(asctime)s - [%(name)s] - %(levelname)s - %(message)s",
    level=logging.INFO
)
# Reduce noisy logs from telegram internal libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger("TikTokBot")

async def post_init(application: Application):
    """Set bot commands list in the Telegram UI menu upon startup."""
    commands = [
        BotCommand("start", "Start the bot and get instructions"),
        BotCommand("help", "How to use the bot"),
        BotCommand("about", "Information about the bot"),
    ]
    await application.bot.set_my_commands(commands)
    me = await application.bot.get_me()
    logger.info(f"Bot started successfully as @{me.username} (ID: {me.id})")

def main():
    """Start the bot application."""
    if not validate_config():
        sys.exit(1)

    logger.info("Initializing Telegram TikTok Downloader Bot...")

    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))

    # Register callback query handler for inline buttons
    application.add_handler(CallbackQueryHandler(callback_router))

    # Register message handler for text containing TikTok links
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Start long-polling
    logger.info("Bot is running and polling for updates... Press Ctrl+C to stop.")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

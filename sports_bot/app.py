# /sports_bot/app.py

import os
import threading
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from dotenv import load_dotenv

from handlers import (
    start,
    handle_menu,
    handle_sports_selection,
    handle_league_selection,
    handle_match_selection,
    handle_analysis_request,
    handle_history_request,
    setup_command,
    set_api_key,
    cancel_setup,
    admin_password_prompt,
    handle_admin_password,
    handle_text_input, # Catch-all for general text
)
from utils import TOKEN, BOT_USERNAME, SUPABASE_URL, SUPABASE_KEY, create_supabase_client

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# --- Environment & App Initialization ---
load_dotenv()
app = Flask(__name__)

# --- Bot Initialization ---
try:
    if not TOKEN:
        raise ValueError("BOT_TOKEN is not set in the environment.")

    application = Application.builder().token(TOKEN).build()
    logger.info("Telegram Bot Application initialized successfully.")

except Exception as e:
    logger.critical(f"Failed to initialize Telegram Bot: {e}")
    # If the bot fails to initialize, we should not proceed.
    # In a real-world scenario, you might have alerts here.
    exit() # Exit the script if the bot can't be created.


# --- Command & Message Handlers ---
# Register handlers for different user interactions
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("setup", setup_command))
application.add_handler(CommandHandler("cancel", cancel_setup))
application.add_handler(CallbackQueryHandler(handle_menu, pattern="^menu_"))
application.add_handler(CallbackQueryHandler(handle_sports_selection, pattern="^sport_"))
application.add_handler(CallbackQueryHandler(handle_league_selection, pattern="^league_"))
application.add_handler(CallbackQueryHandler(handle_match_selection, pattern="^match_"))
application.add_handler(CallbackQueryHandler(handle_analysis_request, pattern="^analyze_"))
application.add_handler(CallbackQueryHandler(handle_history_request, pattern="^history$"))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))


# --- Webhook Route ---
@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Webhook endpoint to receive updates from Telegram.
    This function is called by Telegram whenever a user interacts with the bot.
    """
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)

        # Using a thread to process the update to avoid blocking the webhook response.
        # This ensures we can return a 200 OK to Telegram quickly.
        threading.Thread(target=process_update, args=(update,)).start()

        logger.info("Webhook received and update is being processed in a new thread.")
        return "ok", 200
    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        return "error", 500

def process_update(update):
    """Helper function to process updates in a separate thread."""
    with application.app.app_context(): # Push an application context for the thread
        application.process_update(update)

# --- Main Execution Block ---
if __name__ == "__main__":
    # This block is for local development and debugging.
    # It uses polling instead of webhooks.
    logger.info("Starting bot in polling mode for local development...")
    application.run_polling()

import os
import asyncio
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import telegram
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

import utils
from handlers import start, button_callback_handler, setup_conversation

# --- Bootstrap Environment ---
load_dotenv()

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Telegram Bot Application Setup ---
async def main_setup():
    """
    Performs a two-stage setup:
    1. Bootstrap: Starts the bot with the essential token from the .env file.
    2. Full Config Load: Loads the rest of the config from the database into bot_data.
    """
    # Stage 1: Bootstrap with the essential token
    bootstrap_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bootstrap_token:
        raise ValueError("CRITICAL: TELEGRAM_BOT_TOKEN is not set in the .env file. The bot cannot start.")

    application = Application.builder().token(bootstrap_token).build()

    # Stage 2: Load full configuration from the database into the bot's context
    # This makes the config accessible to all handlers via context.bot_data
    full_config = utils.get_all_settings()
    application.bot_data.update(full_config)
    print("Successfully loaded configuration from the database.")

    # Register all handlers
    application.add_handler(setup_conversation)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback_handler))

    # Set the webhook
    # Use PA_USERNAME from .env for webhook setup, as it might not be in the DB yet
    pa_username = os.getenv("PA_USERNAME")
    if pa_username:
        webhook_url = f"https://{pa_username}.pythonanywhere.com/webhook"
        await application.bot.set_webhook(url=webhook_url)
        print(f"Webhook set successfully to: {webhook_url}")
    else:
        print("PA_USERNAME not found in .env, skipping webhook setup. (This is normal for local dev).")

    return application

# Initialize the application
application = asyncio.run(main_setup())

# --- Flask Routes ---
@app.route("/")
def index():
    """A simple route to confirm the web app is running."""
    return "<h1>Strategic Oracle Bot is running!</h1>"

@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Receives updates from Telegram and processes them.
    This is a synchronous endpoint that uses asyncio.run() to bridge
    to the async python-telegram-bot library.
    """
    if not application:
        print("Error: Bot application not initialized.")
        return jsonify(ok=False, error="Bot not initialized"), 500

    if request.is_json:
        update = telegram.Update.de_json(request.get_json(), application.bot)
        # Use asyncio.run() to execute the async process_update method
        asyncio.run(application.process_update(update))
        return jsonify(ok=True)
    else:
        return jsonify(ok=False, error="Bad request"), 400

import os
import asyncio
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import telegram
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

# Import bot handlers
from handlers import start, button_callback_handler

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PA_USERNAME = os.getenv("PA_USERNAME") # Your PythonAnywhere username
WEBHOOK_URL = f"https://{PA_USERNAME}.pythonanywhere.com/webhook"

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Telegram Bot Setup ---
# Initialize the bot application
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button_callback_handler))

# --- Flask Routes ---
@app.route("/")
def index():
    """A simple route to confirm the web app is running (for UptimeRobot)."""
    return "<h1>Bot is running!</h1><p>This is the endpoint for the keep-alive service.</p>"

@app.route("/webhook", methods=["POST"])
async def webhook():
    """
    This endpoint receives updates from Telegram.
    It processes the update with the python-telegram-bot library.
    """
    if request.is_json:
        update_data = request.get_json()
        update = telegram.Update.de_json(update_data, application.bot)

        # This is the recommended way to process updates asynchronously with the library
        await application.process_update(update)

        return jsonify(ok=True)
    else:
        return jsonify(ok=False, error="Bad request: expected JSON"), 400

async def setup_bot():
    """
    An asynchronous function to set up the bot, including the webhook.
    This should be run once when the application starts.
    """
    print("Setting up bot and webhook...")
    try:
        # The bot needs to be initialized before we can set the webhook
        await application.bot.initialize()

        # Set the webhook
        await application.bot.set_webhook(url=WEBHOOK_URL)
        print(f"Webhook set successfully to: {WEBHOOK_URL}")

        # Retrieve webhook info to confirm
        webhook_info = await application.bot.get_webhook_info()
        print(f"Webhook info: {webhook_info}")

    except Exception as e:
        print(f"An error occurred during bot setup: {e}")

# Note for PythonAnywhere deployment:
# PythonAnywhere's WSGI server doesn't run an asyncio event loop by default.
# The async functions in handlers.py and this webhook function will be
# handled correctly by the `python-telegram-bot` library's `process_update` method,
# which manages its own async context.

# When running this file directly for local testing (not on PythonAnywhere),
# you would typically run the setup_bot function.
if __name__ == '__main__':
    # This part is for local development and testing, not for production on PythonAnywhere.
    # On PythonAnywhere, the WSGI server runs the Flask 'app' object.

    # We use asyncio.run() to execute the async setup function
    asyncio.run(setup_bot())

    # Run the Flask app for local testing
    # Use a different port to avoid conflicts if needed
    app.run(port=5001, debug=True)

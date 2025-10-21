# /sports_bot/utils.py

import os
import logging
from supabase import create_client, Client
from dotenv import load_dotenv
import requests
from telegram import Bot
from telegram.constants import ParseMode

# --- Load Environment Variables ---
load_dotenv()

# --- Environment Variable Validation ---
# It's crucial to ensure all necessary variables are present on startup.
# We will use global variables for credentials that are frequently accessed.
TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME", "YourSportsOracleBot") # Default username
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "default_admin_pass") # Default/fallback password

# --- Logging ---
logger = logging.getLogger(__name__)

# --- Supabase Client ---
# A single, memoized Supabase client instance to be reused across the application.
_supabase_client = None

def create_supabase_client() -> Client | None:
    """
    Creates and returns a Supabase client instance.
    Returns None if credentials are not set.
    """
    global _supabase_client
    if _supabase_client:
        return _supabase_client

    if SUPABASE_URL and SUPABASE_KEY:
        try:
            _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("Supabase client initialized successfully.")
            return _supabase_client
        except Exception as e:
            logger.critical(f"Failed to initialize Supabase client: {e}")
            return None
    else:
        logger.warning("Supabase URL or Key is not configured.")
        return None

# --- API Key Management ---
def get_api_key(key_name: str) -> str | None:
    """
    Retrieves an API key from the Supabase 'config' table.
    """
    supabase = create_supabase_client()
    if not supabase:
        return None
    try:
        response = supabase.table("config").select("value").eq("key", key_name).execute()
        if response.data:
            return response.data[0]['value']
        logger.warning(f"API key '{key_name}' not found in Supabase config.")
        return None
    except Exception as e:
        logger.error(f"Error retrieving API key '{key_name}' from Supabase: {e}")
        return None

# --- Admin Verification ---
async def is_admin(user_id: int) -> bool:
    """Checks if a user_id belongs to an admin by checking the 'admins' table."""
    supabase = create_supabase_client()
    if not supabase:
        return False
    try:
        response = await supabase.table("admins").select("user_id").eq("user_id", user_id).execute()
        return bool(response.data)
    except Exception as e:
        logger.error(f"Error checking admin status for user {user_id}: {e}")
        return False

# --- Job Queue Management (in Supabase) ---
def add_job_to_queue(match_id: str, user_id: int) -> int | None:
    """Adds a new analysis job to the 'analysis_queue' table."""
    supabase = create_supabase_client()
    if not supabase:
        raise ConnectionError("Supabase client is not available.")
    try:
        response = supabase.table("analysis_queue").insert({
            "match_id": match_id,
            "user_id": user_id,
            "status": "pending"
        }).execute()
        job_id = response.data[0]['id']
        logger.info(f"Added job {job_id} to the queue for match {match_id}.")
        return job_id
    except Exception as e:
        logger.error(f"Failed to add job to queue for match {match_id}: {e}")
        return None

def get_pending_jobs(supabase: Client) -> list:
    """Fetches all jobs from the queue with 'pending' status."""
    try:
        response = supabase.table("analysis_queue").select("*").eq("status", "pending").execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching pending jobs from queue: {e}")
        return []

def update_job_status(supabase: Client, job_id: int, status: str, error_message: str = None):
    """Updates the status and optional error message of a job in the queue."""
    try:
        update_data = {"status": status, "updated_at": "now()"}
        if error_message:
            update_data["error_message"] = error_message
        supabase.table("analysis_queue").update(update_data).eq("id", job_id).execute()
        logger.info(f"Updated job {job_id} status to '{status}'.")
    except Exception as e:
        logger.error(f"Error updating status for job {job_id}: {e}")

# --- Prediction History Management ---
def save_prediction_to_history(supabase: Client, user_id: int, match_details: dict, prediction: dict):
    """Saves a completed prediction to the 'prediction_history' table."""
    try:
        history_record = {
            "user_id": user_id,
            "match_id": match_details['id'],
            "sport_key": match_details.get('sport_key'),
            "home_team": match_details['home_team'],
            "away_team": match_details['away_team'],
            "match_commence_time": match_details['commence_time'],
            "predicted_winner": prediction['predicted_winner'],
            "confidence_score": prediction['confidence_score'],
            "risk_level": prediction['risk_level'],
            "status": "Pending" # Status will be updated later by the results worker
        }
        supabase.table("prediction_history").insert(history_record).execute()
        logger.info(f"Saved prediction for match {match_details['id']} to user {user_id}'s history.")
    except Exception as e:
        logger.error(f"Error saving prediction to history: {e}")

# --- Formatting ---
def format_prediction_results(match: dict, prediction: dict) -> str:
    """Formats the AI prediction into a user-friendly message."""
    home = match['home_team']
    away = match['away_team']

    message = f"🔮 **Strategic Oracle Analysis: {home} vs. {away}** 🔮\n\n"
    message += f"**Outcome Projection:** `{prediction['predicted_winner']}`\n"
    message += f"**Confidence Score:** `{prediction['confidence_score']:.1f}%`\n"
    message += f"**Assessed Risk Level:** `{prediction['risk_level']}`\n\n"
    message += f"**Oracle's Reasoning:**\n_{prediction['reasoning']}_\n\n"
    message += "_Disclaimer: This is an AI-generated analysis and not financial advice. Please gamble responsibly._"

    return message

def format_historical_results(history_records: list) -> str:
    """Formats a user's prediction history into a readable message."""
    if not history_records:
        return "You have no prediction history."

    message = "📜 **Your Prediction History** 📜\n\n"
    # Sort records by date, newest first
    sorted_records = sorted(history_records, key=lambda r: r['created_at'], reverse=True)

    for record in sorted_records[:10]: # Show the 10 most recent predictions
        status_icon = {"Correct": "✅", "Incorrect": "❌", "Pending": "⏳"}.get(record['status'], "❓")
        match_str = f"{record['home_team']} vs {record['away_team']}"
        prediction_str = f"Your Pick: {record['predicted_winner']}"

        message += f"{status_icon} **{match_str}**\n"
        message += f"    - {prediction_str}\n"
        message += f"    - Status: `{record['status']}`\n\n"

    if len(sorted_records) > 10:
        message += f"_Showing the last 10 of {len(sorted_records)} predictions._"

    return message

# --- Telegram Bot Communication ---
# This is used by the workers to send messages outside of the user interaction flow.
def send_telegram_message(user_id: int, message: str):
    """Sends a message to a user via the Telegram Bot API."""
    if not TOKEN:
        logger.error("BOT_TOKEN not configured. Cannot send message.")
        return

    bot = Bot(token=TOKEN)
    try:
        bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info(f"Sent message to user {user_id}.")
    except Exception as e:
        logger.error(f"Failed to send message to user {user_id}: {e}")

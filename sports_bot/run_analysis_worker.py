import os
import json
import asyncio
from dotenv import load_dotenv
import telegram

# Import project modules
import utils
import wikipedia_data
import apify_scraper
import gemini_brain

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def send_telegram_message(chat_id, text):
    """Initializes the bot and sends a message to a specific chat ID."""
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN is not configured.")
        return

    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode='Markdown')
        print(f"Successfully sent message to chat_id: {chat_id}")
    except Exception as e:
        print(f"Failed to send message to {chat_id}: {e}")

def run_analysis_pipeline(match_details):
    """
    Executes the full, long-running analysis for a given match.
    This function contains the blocking I/O operations.
    """
    home_team = match_details.get("home_team", "Unknown Team")
    away_team = match_details.get("away_team", "Unknown Team")

    print(f"Processing analysis for: {home_team} vs {away_team}")

    # 1. Get historical data from Wikipedia
    historical_summary = (
        f"{wikipedia_data.get_team_history(home_team)}\n\n"
        f"{wikipedia_data.get_team_history(away_team)}"
    )

    # 2. Get Twitter sentiment summary from Apify
    search_query = f"{home_team} vs {away_team}"
    sentiment_summary = apify_scraper.get_twitter_sentiment_summary(search_query)

    # 3. Format the odds data
    odds_for_ai = utils.format_odds_for_ai(match_details.get('bookmakers', []))

    # 4. Get the final prediction from Gemini AI
    prediction = gemini_brain.get_ai_prediction(
        home_team=home_team,
        away_team=away_team,
        odds_data=odds_for_ai,
        sentiment_summary=sentiment_summary,
        historical_summary=historical_summary,
    )

    # 5. Format the final result message
    result_message = (
        f"--- **AI Analysis Result** ---\n\n"
        f"**Match:** {home_team} vs {away_team}\n\n"
        f"{prediction}"
    )

    return result_message

async def main():
    """
    The main function for the worker script.
    Fetches and processes jobs from the Supabase queue.
    """
    print("--- Analysis Worker Started ---")

    pending_jobs = utils.get_pending_jobs()

    if not pending_jobs:
        print("No pending analysis jobs found.")
        return

    print(f"Found {len(pending_jobs)} pending job(s).")

    for job in pending_jobs:
        job_id, chat_id, match_details_json, status = job

        print(f"Processing job ID: {job_id} for chat ID: {chat_id}")

        try:
            # Mark job as 'processing' to prevent other workers from picking it up
            utils.update_job_status(job_id, 'processing')

            match_details = json.loads(match_details_json)

            # Execute the long-running analysis
            final_result = run_analysis_pipeline(match_details)

            # Send the result to the user
            await send_telegram_message(chat_id, final_result)

            # Delete the job from the queue after successful completion
            utils.delete_job(job_id)
            print(f"Successfully processed and deleted job ID: {job_id}")

        except Exception as e:
            print(f"An error occurred while processing job {job_id}: {e}")
            # Mark job as 'failed' to handle it later (e.g., retry logic)
            utils.update_job_status(job_id, 'failed')
            # Optionally, notify the user of the failure
            error_message = f"Sorry, there was an error processing your analysis request for {match_details.get('home_team')} vs {match_details.get('away_team')}. Please try again later."
            await send_telegram_message(chat_id, error_message)

    print("--- Analysis Worker Finished ---")


if __name__ == "__main__":
    # This script is intended to be run as a scheduled task.
    # The asyncio.run() function executes the main async function.
    asyncio.run(main())

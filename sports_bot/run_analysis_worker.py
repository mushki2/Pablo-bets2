# /sports_bot/run_analysis_worker.py

import logging
import time
from supabase import create_client, Client

from utils import (
    get_pending_jobs,
    update_job_status,
    save_prediction_to_history,
    format_prediction_results,
    send_telegram_message,
    create_supabase_client
)
from odds_api import get_match_by_id
from wikipedia_data import get_team_history
from apify_scraper import get_twitter_sentiment
from prediction_core import get_prediction

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def process_single_job(supabase: Client, job: dict):
    """
    Processes a single analysis job.
    """
    job_id = job['id']
    match_id = job['match_id']
    user_id = job['user_id']

    logging.info(f"Processing job {job_id} for match {match_id}...")

    try:
        # 1. Update job status to 'processing'
        update_job_status(supabase, job_id, 'processing')

        # 2. Fetch all required data
        match_details = get_match_by_id(match_id)
        if not match_details:
            raise ValueError("Match details could not be found.")

        home_team = match_details['home_team']
        away_team = match_details['away_team']

        team_histories = {
            home_team: get_team_history(home_team),
            away_team: get_team_history(away_team)
        }

        sentiment_data = get_twitter_sentiment(f"{home_team} vs {away_team}")

        # 3. Get AI prediction
        prediction_result = get_prediction(match_details, team_histories, sentiment_data)

        if "error" in prediction_result:
             raise ValueError(f"AI Prediction Error: {prediction_result['error']}")

        # 4. Save the successful prediction to the history table
        save_prediction_to_history(supabase, user_id, match_details, prediction_result)

        # 5. Format the result and send to the user
        formatted_message = format_prediction_results(match_details, prediction_result)
        send_telegram_message(user_id, formatted_message)

        # 6. Update job status to 'completed'
        update_job_status(supabase, job_id, 'completed')
        logging.info(f"Successfully processed job {job_id}.")

    except Exception as e:
        logging.error(f"Error processing job {job_id}: {e}")
        update_job_status(supabase, job_id, 'failed', str(e))
        error_message = f"We encountered an error trying to analyze the match. Please try again later. (Job ID: {job_id})"
        send_telegram_message(user_id, error_message)

def main():
    """
    Main function to be run as a scheduled task.
    Fetches all pending jobs, processes them, and then exits.
    """
    logging.info("Analysis worker started a single run...")
    supabase = create_supabase_client()

    if not supabase:
        logging.error("Failed to connect to Supabase. Exiting worker.")
        return

    pending_jobs = get_pending_jobs(supabase)

    if not pending_jobs:
        logging.info("No pending analysis jobs found. Worker exiting.")
        return

    logging.info(f"Found {len(pending_jobs)} pending jobs to process.")
    for job in pending_jobs:
        process_single_job(supabase, job)
        # Small delay to avoid overwhelming APIs if processing many jobs in one run
        time.sleep(2)

    logging.info("Analysis worker finished its run.")

if __name__ == "__main__":
    main()

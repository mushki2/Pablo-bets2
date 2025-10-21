# /sports_bot/check_results_worker.py

import logging
from datetime import datetime, timedelta
import pytz
from supabase import Client

from utils import create_supabase_client
from odds_api import get_scores # Note: Assumes a get_scores function in odds_api.py

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_pending_predictions(supabase: Client):
    """Fetches all prediction history records with a 'Pending' status."""
    try:
        response = supabase.table("prediction_history").select("*").eq("status", "Pending").execute()
        return response.data
    except Exception as e:
        logging.error(f"Error fetching pending predictions: {e}")
        return []

def update_prediction_status(supabase: Client, prediction_id: int, new_status: str):
    """Updates the status of a specific prediction."""
    try:
        supabase.table("prediction_history").update({"status": new_status}).eq("id", prediction_id).execute()
        logging.info(f"Updated prediction {prediction_id} to status '{new_status}'.")
    except Exception as e:
        logging.error(f"Error updating prediction {prediction_id}: {e}")

def main():
    """
    Main function to be run as a scheduled task.
    Checks for results of completed games and updates the user's prediction history.
    """
    logging.info("Result checker worker started a single run...")
    supabase = create_supabase_client()

    if not supabase:
        logging.error("Failed to connect to Supabase. Exiting worker.")
        return

    pending_predictions = get_pending_predictions(supabase)

    if not pending_predictions:
        logging.info("No pending predictions to check. Worker exiting.")
        return

    logging.info(f"Found {len(pending_predictions)} pending predictions to check.")

    # To minimize API calls, we can group checks by sport
    sports_to_check = {pred['sport_key'] for pred in pending_predictions}
    all_scores = {}
    for sport in sports_to_check:
        # Assumes get_scores fetches recent/completed game scores for a sport
        scores = get_scores(sport)
        if scores:
            # Create a dict for easy lookup by match_id
            all_scores[sport] = {score['id']: score for score in scores}

    for pred in pending_predictions:
        prediction_id = pred['id']
        match_id = pred['match_id']
        sport_key = pred['sport_key']
        predicted_winner = pred['predicted_winner']

        # Check if the match start time has passed a reasonable threshold (e.g., 3 hours ago)
        match_time = datetime.fromisoformat(pred['match_commence_time']).replace(tzinfo=pytz.UTC)
        if datetime.now(pytz.UTC) < match_time + timedelta(hours=3):
            # Game is likely not over yet, skip for this run
            continue

        logging.info(f"Checking result for prediction {prediction_id} (Match ID: {match_id})")

        match_score = all_scores.get(sport_key, {}).get(match_id)

        if not match_score or not match_score.get('completed', False):
            logging.warning(f"No completed score data found for match {match_id} yet.")
            continue # No score data available yet

        # Determine the actual winner from the scores
        actual_winner = None
        home_score = next((s['score'] for s in match_score['scores'] if s['name'] == pred['home_team']), None)
        away_score = next((s['score'] for s in match_score['scores'] if s['name'] == pred['away_team']), None)

        if home_score is not None and away_score is not None:
            if home_score > away_score:
                actual_winner = pred['home_team']
            elif away_score > home_score:
                actual_winner = pred['away_team']
            else:
                actual_winner = "Draw"

        if actual_winner:
            # Compare and update status
            new_status = "Correct" if predicted_winner == actual_winner else "Incorrect"
            update_prediction_status(supabase, prediction_id, new_status)
        else:
            logging.error(f"Could not determine a winner for match {match_id} despite score data.")

    logging.info("Result checker worker finished its run.")

if __name__ == "__main__":
    main()

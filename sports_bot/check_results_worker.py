# /sports_bot/check_results_worker.py

import logging
from datetime import datetime, timedelta
import pytz
from supabase import Client

from utils import create_supabase_client
from scores_api import get_event_results # Use the new scores module

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

    for pred in pending_predictions:
        prediction_id = pred['id']
        home_team = pred['home_team']
        away_team = pred['away_team']
        predicted_winner = pred['predicted_winner']

        # The commence time is stored in ISO format with timezone
        match_time = datetime.fromisoformat(pred['match_commence_time']).replace(tzinfo=pytz.UTC)

        # Check if enough time has passed for the game to likely be over
        if datetime.now(pytz.UTC) < match_time + timedelta(hours=3):
            logging.info(f"Skipping prediction {prediction_id}; match is likely still in progress.")
            continue

        logging.info(f"Checking result for prediction {prediction_id} ({home_team} vs {away_team}).")

        # Format the date for TheSportsDB API
        event_date_str = match_time.strftime('%Y-%m-%d')

        # Fetch results from the new scores API
        event_result = get_event_results(team_name=home_team, event_date=event_date_str)

        if not event_result:
            logging.warning(f"No result found yet for prediction {prediction_id}. Will re-check on the next run.")
            continue

        # --- Determine the actual winner from the event result ---
        home_score_str = event_result.get('intHomeScore')
        away_score_str = event_result.get('intAwayScore')

        # Ensure scores are valid numbers
        if home_score_str is None or away_score_str is None:
            logging.warning(f"Score data is incomplete for event of prediction {prediction_id}. Skipping.")
            continue

        try:
            home_score = int(home_score_str)
            away_score = int(away_score_str)

            actual_winner = None
            if home_score > away_score:
                actual_winner = event_result.get('strHomeTeam')
            elif away_score > home_score:
                actual_winner = event_result.get('strAwayTeam')
            else:
                actual_winner = "Draw"

            # TheSportsDB might have slightly different team names.
            # We compare with the predicted winner from our own DB.
            if actual_winner:
                # Basic name normalization to account for slight differences in team names between APIs
                new_status = "Correct" if predicted_winner.lower() in actual_winner.lower() else "Incorrect"
                update_prediction_status(supabase, prediction_id, new_status)
            else:
                logging.error(f"Could not determine a winner for prediction {prediction_id} despite having score data.")

        except (ValueError, TypeError) as e:
            logging.error(f"Error parsing scores for prediction {prediction_id}: {e}")

    logging.info("Result checker worker finished its run.")

if __name__ == "__main__":
    main()

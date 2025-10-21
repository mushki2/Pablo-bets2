# /sports_bot/scores_api.py

import logging
import requests
from datetime import datetime
from utils import get_api_key

# --- Setup ---
logger = logging.getLogger(__name__)
API_BASE_URL = "https://www.thesportsdb.com/api/v1/json/"

def get_event_results(team_name: str, event_date: str) -> dict | None:
    """
    Fetches the result of a specific event from TheSportsDB by searching
    for a team's games on a given day.

    Args:
        team_name: The name of one of the teams that participated in the event.
        event_date: The date of the event in 'YYYY-MM-DD' format.

    Returns:
        A dictionary containing the event details if found, otherwise None.
    """
    api_key = get_api_key("THESPORTSDB_API_KEY")
    if not api_key:
        logger.error("TheSportsDB API key is not configured. Cannot fetch event results.")
        return None

    # TheSportsDB API for daily results is more complex.
    # A common approach is to get a team's last 5 events and then filter by date.
    url = f"{API_BASE_URL}{api_key}/eventslast.php"

    # First, we need to get the team's ID
    team_id = _get_team_id(api_key, team_name)
    if not team_id:
        logger.warning(f"Could not find a team ID for '{team_name}'.")
        return None

    params = {"id": team_id}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if not data or 'results' not in data:
            logger.info(f"No recent results found for team ID {team_id} ({team_name}).")
            return None

        # Filter the results to find the match on the specified date
        for event in data['results']:
            if event.get('dateEvent') == event_date:
                logger.info(f"Found matching event for '{team_name}' on {event_date}.")
                return event

        logger.warning(f"Could not find an event for '{team_name}' on the specific date {event_date}.")
        return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching event results from TheSportsDB for team '{team_name}': {e}")
        return None

def _get_team_id(api_key: str, team_name: str) -> str | None:
    """Helper function to find a team's ID by its name."""
    url = f"{API_BASE_URL}{api_key}/searchteams.php"
    params = {"t": team_name}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data and 'teams' in data and data['teams']:
            return data['teams'][0].get('idTeam')
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error searching for team ID for '{team_name}': {e}")
        return None

# /sports_bot/odds_api.py

import os
import json
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv

from utils import get_api_key

# --- Setup ---
load_dotenv()
logger = logging.getLogger(__name__)

# --- Constants ---
API_BASE_URL = "https://api.the-odds-api.com/v4"
SPORTS_CACHE_FILE = "data/sports_cache.json"
ODDS_CACHE_FILE = "data/odds_cache.json"

# --- Caching ---
def load_cache(file_path):
    """Loads data from a JSON cache file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def save_cache(data, file_path):
    """Saves data to a JSON cache file."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as f:
        json.dump(data, f)

# --- Core API Functions ---

def get_sports():
    """
    Fetches a list of available sports from The Odds API.
    Uses a local cache to avoid frequent API calls.
    """
    # Check cache first
    cached_data = load_cache(SPORTS_CACHE_FILE)
    if cached_data:
        # Check if cache is recent (e.g., within 24 hours)
        cache_time = datetime.fromisoformat(cached_data['timestamp'])
        if (datetime.now() - cache_time).total_seconds() < 86400: # 24 hours
            logger.info("Using cached sports list.")
            return cached_data['data']

    # If cache is old or doesn't exist, fetch from API
    api_key = get_api_key("ODDS_API_KEY")
    if not api_key:
        logger.error("Odds API key is not configured.")
        return []

    url = f"{API_BASE_URL}/sports"
    params = {"apiKey": api_key}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        sports_data = response.json()

        # Save to cache
        save_cache({"timestamp": datetime.now().isoformat(), "data": sports_data}, SPORTS_CACHE_FILE)

        return sports_data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching sports from Odds API: {e}")
        return []

def get_odds(sport_key, regions="us,uk,eu", markets="h2h"):
    """
    Fetches odds for a specific sport.
    Caches results for a short period to handle repeated requests.
    """
    # Simplified caching for odds
    cache_key = f"{sport_key}_{regions}_{markets}"
    # In a real app, you'd use a more sophisticated cache like Redis
    # For this project, we'll use a simple file-based cache.

    cached_data = load_cache(ODDS_CACHE_FILE)
    if cached_data and cache_key in cached_data:
        cache_time = datetime.fromisoformat(cached_data[cache_key]['timestamp'])
        # Cache odds for 10 minutes
        if (datetime.now() - cache_time).total_seconds() < 600:
            logger.info(f"Using cached odds for {sport_key}.")
            return cached_data[cache_key]['data']

    api_key = get_api_key("ODDS_API_KEY")
    if not api_key:
        logger.error("Odds API key is not configured.")
        return []

    url = f"{API_BASE_URL}/sports/{sport_key}/odds"
    params = {
        "apiKey": api_key,
        "regions": regions,
        "markets": markets,
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        odds_data = response.json()

        # Update cache
        if cached_data is None:
            cached_data = {}
        cached_data[cache_key] = {
            "timestamp": datetime.now().isoformat(),
            "data": odds_data
        }
        save_cache(cached_data, ODDS_CACHE_FILE)

        return odds_data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching odds from Odds API for {sport_key}: {e}")
        return []

def get_match_by_id(match_id, sport_key="upcoming"):
    """
    Fetches the details of a single match by its ID.
    This is done by fetching all odds for the sport and then filtering.
    """
    all_matches = get_odds(sport_key)
    for match in all_matches:
        if match.get('id') == match_id:
            return match
    logger.warning(f"Match with ID {match_id} not found.")
    return None

def get_scores(sport_key: str, days_from: int = 3):
    """
    Fetches completed scores for a specific sport from the last few days.

    Args:
        sport_key: The key of the sport (e.g., 'americanfootball_nfl').
        days_from: How many days ago to look for scores (1-3 is typical).

    Returns:
        A list of completed match scores, or an empty list if an error occurs.
    """
    api_key = get_api_key("ODDS_API_KEY")
    if not api_key:
        logger.error("Odds API key is not configured. Cannot fetch scores.")
        return []

    url = f"{API_BASE_URL}/sports/{sport_key}/scores"
    params = {
        "apiKey": api_key,
        "daysFrom": days_from
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        scores_data = response.json()
        logger.info(f"Successfully fetched {len(scores_data)} scores for {sport_key}.")
        return scores_data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching scores from Odds API for {sport_key}: {e}")
        return []

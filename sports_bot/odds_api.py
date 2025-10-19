import os
import requests
import json
from dotenv import load_dotenv

# A simple in-memory cache to store API responses
from utils import cache_data, get_cached_data

load_dotenv()

ODDS_API_KEY = os.getenv("ODDS_API_KEY")
API_BASE_URL = "https://api.the-odds-api.com/v4"

def get_sports():
    """
    Fetches the list of available sports from the Odds API.
    Caches the result for 24 hours to minimize API calls.
    """
    cache_key = "sports_list"
    cached_sports = get_cached_data(cache_key)
    if cached_sports:
        print("Returning cached sports list.")
        return cached_sports

    if not ODDS_API_KEY:
        print("Error: ODDS_API_KEY not found in environment variables.")
        return None

    sports_url = f"{API_BASE_URL}/sports"
    params = {"apiKey": ODDS_API_KEY}

    try:
        response = requests.get(sports_url, params=params)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
        sports_data = response.json()

        # Cache the data for 24 hours (86400 seconds)
        cache_data(cache_key, sports_data, ttl=86400)

        return sports_data

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching sports: {e}")
        return None

def get_odds(sport_key, regions="us,uk,eu", markets="h2h"):
    """
    Fetches odds for a specific sport.
    Caches the results for 5 minutes to allow for updates but prevent spamming.

    Args:
        sport_key (str): The key for the sport (e.g., 'soccer_epl').
        regions (str): Comma-separated list of regions.
        markets (str): Comma-separated list of markets.

    Returns:
        list: A list of events with their odds, or None if an error occurs.
    """
    cache_key = f"odds_{sport_key}"
    cached_odds = get_cached_data(cache_key)
    if cached_odds:
        print(f"Returning cached odds for {sport_key}.")
        return cached_odds

    if not ODDS_API_KEY:
        print("Error: ODDS_API_KEY not found in environment variables.")
        return None

    odds_url = f"{API_BASE_URL}/sports/{sport_key}/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": regions,
        "markets": markets,
    }

    try:
        response = requests.get(odds_url, params=params)
        response.raise_for_status()
        odds_data = response.json()

        # Cache for 5 minutes (300 seconds)
        cache_data(cache_key, odds_data, ttl=300)

        return odds_data

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching odds for {sport_key}: {e}")
        return None

if __name__ == '__main__':
    # Example usage:
    # Ensure you have a .env file with your ODDS_API_KEY

    print("--- Fetching Sports ---")
    available_sports = get_sports()
    if available_sports:
        print(f"Found {len(available_sports)} sports.")
        # Get the key of the first sport for the odds example
        first_sport_key = available_sports[0]['key']
        print(f"First sport: {available_sports[0]['title']} (key: {first_sport_key})")

        print(f"\n--- Fetching Odds for {first_sport_key} ---")
        sport_odds = get_odds(first_sport_key)
        if sport_odds:
            print(f"Found {len(sport_odds)} events for {first_sport_key}.")
            if sport_odds:
                # Print details of the first event
                first_event = sport_odds[0]
                print(f"  First event: {first_event['home_team']} vs {first_event['away_team']}")
                print(f"  Starts at: {first_event['commence_time']}")
        else:
            print(f"Could not fetch odds for {first_sport_key}.")
    else:
        print("Could not fetch the list of sports.")

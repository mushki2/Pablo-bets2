import requests
from utils import cache_data, get_cached_data

API_BASE_URL = "https://api.the-odds-api.com/v4"

def get_sports(config: dict):
    """
    Fetches the list of available sports from the Odds API.
    Caches the result for 24 hours.
    """
    cache_key = "sports_list"
    cached_sports = get_cached_data(cache_key)
    if cached_sports:
        return cached_sports

    odds_api_key = config.get("ODDS_API_KEY")
    if not odds_api_key:
        print("Error: ODDS_API_KEY not found in config.")
        return None

    sports_url = f"{API_BASE_URL}/sports"
    params = {"apiKey": odds_api_key}

    try:
        response = requests.get(sports_url, params=params)
        response.raise_for_status()
        sports_data = response.json()
        cache_data(cache_key, sports_data, ttl=86400)
        return sports_data
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching sports: {e}")
        return None

def test_api_key(api_key: str) -> bool:
    """Tests if the provided Odds API key is valid."""
    test_url = f"{API_BASE_URL}/sports"
    params = {"apiKey": api_key}
    try:
        response = requests.get(test_url, params=params)
        response.raise_for_status()
        # A successful response (200 OK) means the key is valid
        return True
    except requests.exceptions.RequestException:
        return False

def get_odds(sport_key: str, config: dict):
    """
    Fetches odds for a specific sport.
    Caches the results for 5 minutes.
    """
    cache_key = f"odds_{sport_key}"
    cached_odds = get_cached_data(cache_key)
    if cached_odds:
        return cached_odds

    odds_api_key = config.get("ODDS_API_KEY")
    if not odds_api_key:
        print("Error: ODDS_API_KEY not found in config.")
        return None

    odds_url = f"{API_BASE_URL}/sports/{sport_key}/odds"
    params = {"apiKey": odds_api_key, "regions": "us,uk,eu", "markets": "h2h"}

    try:
        response = requests.get(odds_url, params=params)
        response.raise_for_status()
        odds_data = response.json()
        cache_data(cache_key, odds_data, ttl=300)
        return odds_data
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching odds for {sport_key}: {e}")
        return None

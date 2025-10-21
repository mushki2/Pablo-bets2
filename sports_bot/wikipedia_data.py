# /sports_bot/wikipedia_data.py

import logging
import re
import requests

logger = logging.getLogger(__name__)

def get_team_history(team_name: str) -> str:
    """
    Fetches a concise summary of a team's history from Wikipedia.

    Args:
        team_name: The name of the team to search for.

    Returns:
        A short, clean summary of the team's history, or a message
        indicating that no data was found.
    """
    session = requests.Session()
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "titles": team_name,
        "prop": "extracts",
        "exintro": True,
        "explaintext": True,
        "redirects": 1,
    }

    try:
        response = session.get(url=url, params=params)
        response.raise_for_status()
        data = response.json()

        pages = data.get("query", {}).get("pages", {})
        if not pages:
            logger.warning(f"No Wikipedia page found for team: {team_name}")
            return f"No historical data found for {team_name}."

        # pages is a dict where keys are page IDs; we just need the first one.
        page_id = next(iter(pages))
        extract = pages[page_id].get("extract")

        if not extract or "may refer to" in extract:
            logger.info(f"Wikipedia extract for '{team_name}' is empty or a disambiguation page.")
            return f"Could not retrieve specific historical data for {team_name}."

        # Clean up the text
        # Remove extra whitespace and limit length to create a concise summary
        clean_extract = re.sub(r'\\n', ' ', extract)
        clean_extract = re.sub(r'\\s+', ' ', clean_extract).strip()

        # Truncate to a reasonable length for the AI prompt
        summary = (clean_extract[:500] + '...') if len(clean_extract) > 500 else clean_extract

        logger.info(f"Successfully fetched Wikipedia summary for {team_name}")
        return summary

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching Wikipedia data for {team_name}: {e}")
        return "Could not connect to Wikipedia to fetch historical data."
    except Exception as e:
        logger.error(f"An unexpected error occurred in get_team_history: {e}")
        return "An unexpected error occurred while fetching historical data."

if __name__ == '__main__':
    # Example usage for direct testing
    team1 = "Manchester United F.C."
    team2 = "Boston Celtics"

    print(f"--- History for {team1} ---")
    print(get_team_history(team1))
    print("\n" + "="*50 + "\n")
    print(f"--- History for {team2} ---")
    print(get_team_history(team2))

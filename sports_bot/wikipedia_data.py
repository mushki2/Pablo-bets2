import requests

WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"

def get_team_history(team_name):
    """
    Fetches the introductory paragraph of a Wikipedia article for a given team.

    Args:
        team_name (str): The name of the sports team.

    Returns:
        str: A summary of the team's history, or a message indicating no data was found.
    """
    params = {
        "action": "query",
        "format": "json",
        "titles": team_name,
        "prop": "extracts",
        "exintro": True,  # Get only the content before the first section
        "explaintext": True,  # Get plain text instead of HTML
        "redirects": 1, # Follow redirects to find the correct page
    }

    try:
        response = requests.get(WIKIPEDIA_API_URL, params=params)
        response.raise_for_status()
        data = response.json()

        pages = data.get("query", {}).get("pages", {})

        if not pages:
            return f"No Wikipedia page found for '{team_name}'."

        # The page ID is dynamic, so we get the first one.
        page_id = next(iter(pages))

        extract = pages[page_id].get("extract")

        if extract:
            # Clean up the extract if it's too short or contains common boilerplate
            if len(extract) < 50 or "may refer to" in extract:
                return f"Could not find a detailed summary for '{team_name}'. The topic might be ambiguous."
            return extract
        else:
            return f"No summary available for '{team_name}' on Wikipedia."

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching data from Wikipedia: {e}")
        return f"Error: Could not connect to Wikipedia to fetch data for '{team_name}'."

if __name__ == '__main__':
    # Example Usage

    team1 = "Manchester City F.C."
    team2 = "Real Madrid CF"
    invalid_team = "Aasdfasdfasdf FC" # An unlikely team name

    print(f"--- Fetching history for {team1} ---")
    history1 = get_team_history(team1)
    print(history1)
    print("-" * 20)

    print(f"--- Fetching history for {team2} ---")
    history2 = get_team_history(team2)
    print(history2)
    print("-" * 20)

    print(f"--- Fetching history for {invalid_team} ---")
    history3 = get_team_history(invalid_team)
    print(history3)
    print("-" * 20)

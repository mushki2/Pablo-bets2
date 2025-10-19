import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"

def get_ai_prediction(home_team, away_team, odds_data, sentiment_summary, historical_summary):
    """
    Queries the Gemini AI with structured data to get a match prediction.

    Args:
        home_team (str): The name of the home team.
        away_team (str): The name of the away team.
        odds_data (dict): A formatted string or dict of the best odds.
        sentiment_summary (str): A summary of the Twitter sentiment analysis.
        historical_summary (str): A summary of the historical data from Wikipedia.

    Returns:
        str: The AI's prediction and reasoning, or an error message.
    """
    if not GEMINI_API_KEY:
        return "Error: GEMINI_API_KEY is not configured."

    # Format the odds data for the prompt
    formatted_odds = json.dumps(odds_data, indent=2)

    prompt = f"""
    Analyze the upcoming match between {home_team} and {away_team}.

    Here is the data I've gathered:

    1.  **Live Odds:**
        {formatted_odds}

    2.  **Recent Twitter Sentiment:**
        {sentiment_summary}

    3.  **Historical Performance Summary:**
        {historical_summary}

    **Your Task:**
    Based on all the provided data (odds, public sentiment, and historical performance), please provide a confident prediction for the match outcome.
    Explain your reasoning in a clear, step-by-step manner. Conclude with a final prediction on the likely winner.
    """

    headers = {"Content-Type": "application/json"}

    data = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }

    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=data)
        response.raise_for_status()

        result = response.json()

        # Extract the text from the response
        if 'candidates' in result and result['candidates']:
            content = result['candidates'][0].get('content', {})
            if 'parts' in content and content['parts']:
                return content['parts'][0].get('text', "No text found in response.")

        return "Error: Could not parse the prediction from the Gemini API response."

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while calling the Gemini API: {e}")
        return f"Error: An exception occurred while communicating with the Gemini API. Details: {e}"

if __name__ == '__main__':
    # Example Usage (requires a valid GEMINI_API_KEY in .env)

    sample_home_team = "Manchester City"
    sample_away_team = "Real Madrid"

    sample_odds = {
        "Manchester City": {"price": 1.6, "bookmaker": "DraftKings"},
        "Real Madrid": {"price": 5.0, "bookmaker": "FanDuel"},
        "Draw": {"price": 4.5, "bookmaker": "BetMGM"}
    }

    sample_sentiment = "Slightly positive for Manchester City (65% positive tweets), with neutral to negative sentiment for Real Madrid."

    sample_history = "Manchester City has won 3 of the last 5 encounters. Real Madrid has a strong record in knockout stages but has shown defensive vulnerabilities recently."

    prediction = get_ai_prediction(sample_home_team, sample_away_team, sample_odds, sample_sentiment, sample_history)

    print("--- Gemini AI Prediction ---")
    print(prediction)
    print("--------------------------")

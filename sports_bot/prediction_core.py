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
    **Role:** You are a sophisticated sports betting analyst AI. Your task is to provide a detailed, data-driven prediction for an upcoming match.

    **Match:** {home_team} vs {away_team}

    **Input Data:**
    1.  **Live Market Odds:**
        ```json
        {formatted_odds}
        ```
    2.  **Public Sentiment Analysis (from Twitter):**
        - {sentiment_summary}
    3.  **Historical Context (from Wikipedia):**
        - {historical_summary}

    **Output Format (Strict JSON):**
    You must return your analysis in a single JSON object. Do not include any text outside of this JSON object. The structure must be exactly as follows:
    {{
      "prediction": "The team you predict will win, or 'Draw'.",
      "reasoning": "A step-by-step, data-driven explanation for your prediction. Reference the odds, sentiment, and historical context.",
      "confidence_score": "A percentage (e.g., '78%') representing your confidence in the prediction.",
      "risk_level": "Your assessment of the risk involved in this bet. Must be one of: 'Low', 'Medium', or 'High'."
    }}

    **Instructions:**
    -   **Analyze all data points:** Synthesize the market odds, public sentiment, and historical performance to form a holistic view.
    -   **Confidence Score:** Base this on the alignment of the data. High confidence comes from data points that all suggest a similar outcome. Low confidence results from conflicting data (e.g., strong history but poor odds and negative sentiment).
    -   **Risk Level:** Assess this based on the odds and the potential for an upset. Low odds on a clear favorite is 'Low' risk. Close odds or a history of upsets indicates 'Medium' or 'High' risk.
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

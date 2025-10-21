# /sports_bot/prediction_core.py

import os
import logging
import json
import google.generativeai as genai
from dotenv import load_dotenv

from utils import get_api_key

# --- Setup ---
load_dotenv()
logger = logging.getLogger(__name__)

# --- Gemini API Configuration ---
def configure_gemini():
    """Configures the Gemini API with the key from environment variables."""
    api_key = get_api_key("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY is not configured. Prediction core is disabled.")
        return False
    try:
        genai.configure(api_key=api_key)
        logger.info("Gemini API configured successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to configure Gemini API: {e}")
        return False

# --- Core Prediction Function ---

def get_prediction(match_details: dict, team_histories: dict, sentiment_data: dict) -> dict:
    """
    Generates a sports prediction using the Gemini AI model by synthesizing
    odds, historical data, and social media sentiment.

    Args:
        match_details: A dictionary containing odds and match info from Odds API.
        team_histories: A dictionary with historical summaries for both teams from Wikipedia.
        sentiment_data: A dictionary with sentiment analysis results from Apify.

    Returns:
        A dictionary containing the AI's formatted prediction, confidence score,
        and risk level, structured as JSON. Returns an error message if
        the prediction fails.
    """
    if not configure_gemini():
        return {
            "error": "The Strategic Oracle (AI) is not configured. Please contact an admin."
        }

    try:
        model = genai.GenerativeModel('gemini-pro')
        prompt = _build_prompt(match_details, team_histories, sentiment_data)

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                # temperature controls randomness: lower is more deterministic
                temperature=0.3,
                # top_p nucleus sampling
                top_p=0.95,
                # top_k sampling
                top_k=40
            )
        )

        # The response from Gemini is expected to be a JSON string.
        # We need to parse it to extract the structured data.
        return _parse_gemini_response(response.text)

    except Exception as e:
        logger.error(f"Error generating prediction from Gemini: {e}")
        return {
            "error": f"The Strategic Oracle encountered an anomaly while analyzing the data. Details: {e}"
        }

def _build_prompt(match, histories, sentiment) -> str:
    """Constructs a detailed, structured prompt for the Gemini AI."""

    home_team = match.get('home_team', 'Unknown Home Team')
    away_team = match.get('away_team', 'Unknown Away Team')

    # Extracting and formatting odds data
    odds_summary = "No clear odds data available."
    if 'bookmakers' in match and match['bookmakers']:
        # Find the best odds for each team from the first available bookmaker
        # A more robust solution would compare across all bookmakers
        bookie = match['bookmakers'][0]
        market = next((m for m in bookie.get('markets', []) if m['key'] == 'h2h'), None)
        if market and 'outcomes' in market:
            odds_list = [f"{o['name']}: {o['price']}" for o in market['outcomes']]
            odds_summary = f"Key Market Odds ({bookie['title']}): {', '.join(odds_list)}"

    prompt = f"""
    **Role:** You are a "Strategic Sports Oracle," a sophisticated AI analyst. Your task is to provide a confident, data-driven prediction for an upcoming sports match.

    **Objective:** Analyze the provided data to predict the winner, assess your confidence, and determine the risk level. You MUST return your analysis in a structured JSON format.

    **Match Data:**
    - **Match:** {home_team} vs. {away_team}
    - **Market Odds:** {odds_summary}

    **Contextual Analysis:**
    1.  **Historical Performance ({home_team}):** {histories.get(home_team, 'No data available.')}
    2.  **Historical Performance ({away_team}):** {histories.get(away_team, 'No data available.')}
    3.  **Social Media Sentiment ({home_team} vs {away_team}):**
        - Positive Sentiment Ratio: {sentiment.get('positive_ratio', 0):.1%}
        - Negative Sentiment Ratio: {sentiment.get('negative_ratio', 0):.1%}
        - Summary: {sentiment.get('summary', 'N/A')}

    **Mandatory Output Format (JSON ONLY):**
    Analyze all the data and provide your response strictly in the following JSON structure. Do not include any text or markdown formatting before or after the JSON block.

    {{
      "predicted_winner": "string (team name or 'Draw')",
      "confidence_score": "float (a percentage from 0.0 to 100.0, e.g., 75.5)",
      "risk_level": "string ('Low', 'Medium', 'High', or 'Very High')",
      "reasoning": "string (a concise, expert analysis explaining your prediction based on the provided data. Synthesize the odds, history, and sentiment.)"
    }}
    """
    return prompt

def _parse_gemini_response(response_text: str) -> dict:
    """
    Parses the JSON response from Gemini, ensuring it conforms to the expected structure.
    """
    try:
        # The Gemini API might wrap the JSON in markdown backticks. We need to strip them.
        clean_response = response_text.strip().replace('```json', '').replace('```', '')
        data = json.loads(clean_response)

        # Validate that the expected keys are present
        required_keys = ["predicted_winner", "confidence_score", "risk_level", "reasoning"]
        if not all(key in data for key in required_keys):
            logger.error(f"Gemini response was missing one or more required keys. Response: {data}")
            raise ValueError("Invalid JSON structure in AI response.")

        return data

    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON from Gemini response: {e}\nRaw response: {response_text}")
        return {
            "error": "The Oracle's response was malformed and could not be interpreted."
        }
    except ValueError as e:
         return {
            "error": f"The Oracle's response was incomplete. Details: {e}"
        }

if __name__ == '__main__':
    # Example usage for direct testing (requires .env file with GEMINI_API_KEY)

    # Mock data for a hypothetical match
    mock_match_details = {
        'home_team': 'Team Alpha',
        'away_team': 'Team Bravo',
        'bookmakers': [{
            'title': 'BestBet',
            'markets': [{
                'key': 'h2h',
                'outcomes': [
                    {'name': 'Team Alpha', 'price': 1.85},
                    {'name': 'Team Bravo', 'price': 3.5},
                    {'name': 'Draw', 'price': 3.2}
                ]
            }]
        }]
    }

    mock_histories = {
        'Team Alpha': 'A legendary team with a strong track record, but has shown inconsistency in recent away games.',
        'Team Bravo': 'A rising underdog that recently defeated a top-tier opponent, showing strong defensive capabilities.'
    }

    mock_sentiment = {
        'positive_ratio': 0.65,
        'negative_ratio': 0.20,
        'summary': 'Social media is buzzing with support for Team Bravo after their recent upset victory.'
    }

    prediction = get_prediction(mock_match_details, mock_histories, mock_sentiment)

    print("--- Strategic Oracle Prediction ---")
    print(json.dumps(prediction, indent=2))

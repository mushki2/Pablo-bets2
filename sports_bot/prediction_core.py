import requests
import json

def get_ai_prediction(home_team, away_team, odds_data, sentiment_summary, historical_summary, config: dict):
    """
    Queries the Gemini AI with structured data to get a match prediction.
    """
    gemini_api_key = config.get("GEMINI_API_KEY")
    if not gemini_api_key:
        return "Error: GEMINI_API_KEY is not configured in the database."

    gemini_api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={gemini_api_key}"
    formatted_odds = json.dumps(odds_data, indent=2)

    prompt = f"""
    **Role:** You are a sophisticated sports betting analyst AI. Your task is to provide a detailed, data-driven prediction for an upcoming match.
    **Match:** {home_team} vs {away_team}
    **Input Data:**
    1.  **Live Market Odds:** ```json {formatted_odds} ```
    2.  **Public Sentiment Analysis (from Twitter):** - {sentiment_summary}
    3.  **Historical Context (from Wikipedia):** - {historical_summary}
    **Output Format (Strict JSON):**
    You must return your analysis in a single JSON object. Do not include any text outside of this JSON object. The structure must be exactly as follows:
    {{
      "prediction": "The team you predict will win, or 'Draw'.",
      "reasoning": "A step-by-step, data-driven explanation for your prediction. Reference the odds, sentiment, and historical context.",
      "confidence_score": "A percentage (e.g., '78%') representing your confidence in the prediction.",
      "risk_level": "Your assessment of the risk involved in this bet. Must be one of: 'Low', 'Medium', or 'High'."
    }}
    **Instructions:**
    - Analyze all data points to form a holistic view.
    - Base the confidence score on the alignment of the data.
    - Assess the risk level based on the odds and potential for an upset.
    """

    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(gemini_api_url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()

        if 'candidates' in result and result['candidates']:
            content = result['candidates'][0].get('content', {})
            if 'parts' in content and content['parts']:
                return content['parts'][0].get('text', "No text found in response.")

        return "Error: Could not parse the prediction from the Gemini API response."

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while calling the Gemini API: {e}")
        return f"Error: An exception occurred while communicating with the Gemini API. Details: {e}"

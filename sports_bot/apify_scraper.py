import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
ACTOR_ID = "michelmet/twitter-scraper"

def analyze_sentiment_and_summarize(tweets):
    """
    A simple sentiment analysis function that categorizes tweets and provides a summary.
    This is a basic implementation; a more advanced version would use a library like NLTK or TextBlob.
    """
    if not tweets:
        return "No tweets were found to analyze."

    positive_count = 0
    negative_count = 0
    neutral_count = 0

    # Simple keyword-based sentiment analysis
    positive_keywords = ['win', 'great', 'amazing', 'confident', 'strong', 'betting on']
    negative_keywords = ['lose', 'poor', 'weak', 'disappointed', 'struggling', 'betting against']

    for tweet in tweets:
        text = tweet.get('text', '').lower()
        if any(keyword in text for keyword in positive_keywords):
            positive_count += 1
        elif any(keyword in text for keyword in negative_keywords):
            negative_count += 1
        else:
            neutral_count += 1

    total_tweets = len(tweets)
    positive_ratio = (positive_count / total_tweets) * 100

    summary = (
        f"Analyzed {total_tweets} tweets. "
        f"Sentiment: {positive_ratio:.1f}% positive, "
        f"{((negative_count/total_tweets)*100):.1f}% negative, "
        f"{((neutral_count/total_tweets)*100):.1f}% neutral."
    )

    return summary

def get_twitter_sentiment_summary(search_term):
    """
    Triggers an Apify actor, fetches tweets, and returns a sentiment summary.

    NOTE: This function is SYNCHRONOUS and BLOCKING. It will pause execution
    while it polls the Apify API. This is a limitation of running complex,
    long-running tasks on a simple webhook-based architecture like the
    PythonAnywhere free tier, which does not support background workers.
    For a production environment, this would ideally be handled by a
    separate worker process and a task queue (e.g., Celery, Redis Queue).
    """
    if not APIFY_API_TOKEN:
        print("Error: APIFY_API_TOKEN not found.")
        return "Apify API token is not configured."

    run_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs?token={APIFY_API_TOKEN}"

    # Reduced tweetsDesired to 25 for faster processing on the free tier.
    actor_input = {
        "searchTerms": [search_term],
        "tweetsDesired": 25,
        "language": "en"
    }

    try:
        run_response = requests.post(run_url, json=actor_input)
        run_response.raise_for_status()
        run_data = run_response.json().get("data", {})
        run_id = run_data.get("id")

        if not run_id:
            return "Failed to start Apify actor."

        status_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs/{run_id}?token={APIFY_API_TOKEN}"

        # Poll for results (with a timeout to avoid infinite loops)
        timeout_seconds = 120  # 2-minute timeout
        start_time = time.time()
        while (time.time() - start_time) < timeout_seconds:
            status_response = requests.get(status_url)
            status_response.raise_for_status()
            status_data = status_response.json().get("data", {})
            status = status_data.get("status")

            if status in ["SUCCEEDED", "FAILED", "ABORTED"]:
                break

            time.sleep(10)

        if status == "SUCCEEDED":
            dataset_url = f"https://api.apify.com/v2/datasets/{run_data.get('defaultDatasetId')}/items?token={APIFY_API_TOKEN}"
            results_response = requests.get(dataset_url)
            results_response.raise_for_status()
            tweets = results_response.json()
            return analyze_sentiment_and_summarize(tweets)
        else:
            return f"Apify actor did not succeed. Final status: {status}"

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while communicating with Apify: {e}")
        return "Error communicating with Apify API."

if __name__ == '__main__':
    search_query = "FC Barcelona vs Real Madrid"
    print(f"--- Getting Twitter Sentiment Summary for: '{search_query}' ---")
    summary = get_twitter_sentiment_summary(search_query)
    print(summary)
    print("----------------------------------------------------------")

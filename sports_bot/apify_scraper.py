import os
import requests
import time
from dotenv import load_dotenv

# This will be refactored to take config as an argument

def analyze_sentiment_and_summarize(tweets):
    """
    A simple sentiment analysis function that categorizes tweets and provides a summary.
    """
    if not tweets:
        return "No tweets were found to analyze."

    positive_count = 0
    negative_count = 0
    neutral_count = 0

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
    positive_ratio = (positive_count / total_tweets) * 100 if total_tweets > 0 else 0

    summary = (
        f"Analyzed {total_tweets} tweets. "
        f"Sentiment: {positive_ratio:.1f}% positive."
    )

    return summary

def get_twitter_sentiment_summary(search_term: str, config: dict):
    """
    Triggers an Apify actor, fetches tweets, and returns a sentiment summary.
    This function is BLOCKING and relies on the calling script for configuration.
    """
    apify_api_token = config.get("APIFY_API_TOKEN")
    if not apify_api_token:
        return "Apify API token is not configured in the database."

    actor_id = "michelmet/twitter-scraper"
    run_url = f"https://api.apify.com/v2/acts/{actor_id}/runs?token={apify_api_token}"

    actor_input = {"searchTerms": [search_term], "tweetsDesired": 25, "language": "en"}

    try:
        run_response = requests.post(run_url, json=actor_input)
        run_response.raise_for_status()
        run_data = run_response.json().get("data", {})
        run_id = run_data.get("id")

        if not run_id:
            return "Failed to start Apify actor."

        status_url = f"https://api.apify.com/v2/acts/{actor_id}/runs/{run_id}?token={apify_api_token}"

        timeout_seconds = 120
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
            dataset_url = f"https://api.apify.com/v2/datasets/{run_data.get('defaultDatasetId')}/items?token={apify_api_token}"
            results_response = requests.get(dataset_url)
            results_response.raise_for_status()
            tweets = results_response.json()
            return analyze_sentiment_and_summarize(tweets)
        else:
            return f"Apify actor did not succeed. Final status: {status}"

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while communicating with Apify: {e}")
        return "Error communicating with Apify API."

# /sports_bot/apify_scraper.py

import os
import logging
from apify_client import ApifyClient
from dotenv import load_dotenv

from utils import get_api_key

# --- Setup ---
load_dotenv()
logger = logging.getLogger(__name__)

# --- Core Scraping Function ---

def get_twitter_sentiment(search_term: str, tweet_count: int = 50) -> dict:
    """
    Scrapes Twitter for a given search term using an Apify actor and performs
    a basic sentiment analysis.

    Args:
        search_term: The keyword or phrase to search for on Twitter (e.g., "TeamA vs TeamB").
        tweet_count: The number of recent tweets to analyze.

    Returns:
        A dictionary containing the sentiment analysis results, including
        positive/negative/neutral counts and ratios. Returns a default
        error state if scraping fails.
    """
    api_key = get_api_key("APIFY_API_KEY")
    if not api_key:
        logger.error("Apify API key is not configured. Cannot perform sentiment analysis.")
        return {
            "error": "Apify API key not configured.",
            "positive_ratio": 0.0,
            "negative_ratio": 0.0,
            "neutral_ratio": 0.0,
            "summary": "Sentiment analysis could not be performed due to a configuration error."
        }

    try:
        client = ApifyClient(api_key)

        # Using a popular, reliable Twitter scraper actor from Apify's store
        # Note: The actor ID might change over time. This one is valid as of late 2023.
        actor_run_info = client.actor("microworlds/twitter-scraper").call(
            run_input={
                "searchTerms": [search_term],
                "maxTweets": tweet_count,
                "language": "en",
            }
        )

        # Fetch the results from the actor's dataset
        tweets = []
        for item in client.dataset(actor_run_info["defaultDatasetId"]).iterate_items():
            if 'text' in item:
                tweets.append(item['text'])

        if not tweets:
            logger.warning(f"No tweets found for search term: '{search_term}'")
            return {
                "error": "No tweets found.",
                "positive_ratio": 0.0, "negative_ratio": 0.0, "neutral_ratio": 0.0,
                "summary": "No recent social media sentiment could be gathered."
            }

        # Perform simple sentiment analysis
        return _analyze_sentiment(tweets)

    except Exception as e:
        logger.error(f"An error occurred during Apify scraping for '{search_term}': {e}")
        return {
            "error": str(e),
            "positive_ratio": 0.0, "negative_ratio": 0.0, "neutral_ratio": 0.0,
            "summary": "Failed to scrape social media sentiment due to an external error."
        }

def _analyze_sentiment(tweets: list) -> dict:
    """
    Performs a very basic keyword-based sentiment analysis on a list of tweets.

    Note: This is a placeholder for a more sophisticated sentiment analysis engine.
    A real-world application would use a library like NLTK, spaCy, or a dedicated
    sentiment analysis API for much higher accuracy.
    """
    positive_keywords = ['win', 'amazing', 'great', 'destroy', 'unbeatable', 'confident', 'strong']
    negative_keywords = ['lose', 'awful', 'terrible', 'choke', 'weak', 'disappointing', 'struggle']

    positive_count = 0
    negative_count = 0
    neutral_count = 0

    for tweet in tweets:
        tweet_lower = tweet.lower()
        is_positive = any(word in tweet_lower for word in positive_keywords)
        is_negative = any(word in tweet_lower for word in negative_keywords)

        if is_positive and not is_negative:
            positive_count += 1
        elif is_negative and not is_positive:
            negative_count += 1
        else:
            neutral_count += 1

    total_tweets = len(tweets)
    if total_tweets == 0:
        return {
            "positive_ratio": 0.0, "negative_ratio": 0.0, "neutral_ratio": 1.0,
            "summary": "No tweets to analyze."
        }

    positive_ratio = positive_count / total_tweets
    negative_ratio = negative_count / total_tweets
    neutral_ratio = neutral_count / total_tweets

    summary = (
        f"Sentiment Analysis ({total_tweets} posts):\n"
        f"- Positive: {positive_ratio:.1%}\n"
        f"- Negative: {negative_ratio:.1%}\n"
        f"- Neutral: {neutral_ratio:.1%}"
    )

    return {
        "positive_ratio": positive_ratio,
        "negative_ratio": negative_ratio,
        "neutral_ratio": neutral_ratio,
        "summary": summary
    }

if __name__ == '__main__':
    # Example usage for direct testing
    # Requires APIFY_API_KEY in a .env file
    search = "Man U vs Chelsea"
    print(f"--- Getting sentiment for: '{search}' ---")
    sentiment_data = get_twitter_sentiment(search)
    print(sentiment_data)

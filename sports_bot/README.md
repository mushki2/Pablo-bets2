# Strategic Oracle - AI Sports Betting Bot

The **Strategic Oracle** is a sophisticated, AI-powered Telegram bot designed to provide advanced sports betting insights. It integrates multiple real-time data streams to deliver live market odds, historical data, and AI-driven predictive analysis, all within a responsive and futuristic Telegram interface.

The bot is engineered to run on the PythonAnywhere free tier, utilizing a webhook-based Flask application and an asynchronous job queue to handle long-running analysis tasks without timing out, ensuring a seamless user experience.

## Core Capabilities

-   **Live Market Analysis:** Accesses real-time sports and odds data from The Odds API for multiple bookmakers.
-   **AI-Powered Outcome Projections:** Generates detailed match predictions by synthesizing live odds, historical team data (from Wikipedia), and public sentiment (from Twitter) using the Gemini AI.
-   **Advanced Metrics:** Each projection includes a **Confidence Score** and an **Assessed Risk Level**, providing a deeper layer of analysis.
-   **Asynchronous Processing:** Uses a robust job queue with a Supabase PostgreSQL database to manage computationally intensive tasks, ensuring the bot remains instantly responsive.
-   **Market Inefficiency Scanning:** Identifies and highlights arbitrage opportunities by comparing odds across different bookmakers for the same event.
-   **Intuitive Interface:** Employs Telegram's inline buttons for a fluid and user-friendly experience.

## Technology Architecture

| Component                  | Technology / API                                                              | Purpose                                                              |
| -------------------------- | ----------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| **Backend Core**           | Python, Flask                                                                 | Serves the Telegram webhook and core application logic.              |
| **Bot Framework**          | `python-telegram-bot`                                                         | Handles all interactions with the Telegram Bot API.                  |
| **Database & Job Queue**   | Supabase (PostgreSQL)                                                         | Provides a robust database for caching and the asynchronous job queue.|
| **Live Market Data**       | [The Odds API](https://the-odds-api.com/)                                     | Fetches live sports, events, and betting odds.                       |
| **Historical Context**     | [Wikipedia API](https://www.mediawiki.org/wiki/API:Main_page)                 | Retrieves historical context and performance data for sports teams.  |
| **Public Sentiment**       | [Apify](https://apify.com/) (Twitter Scraper)                                 | Scrapes real-time Twitter data for sentiment analysis.               |
| **Predictive Analytics**   | [Google Gemini API](https://ai.google.dev/)                                   | Generates AI-powered projections, confidence scores, and risk levels.|
| **Hosting Environment**    | [PythonAnywhere](https://www.pythonanywhere.com/)                             | Provides the hosting environment for the Flask web app.              |

---

## Setup and Installation

### 1. Clone the Repository

```bash
git clone <repository_url>
cd sports_bot
```

### 2. Create a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the `sports_bot` directory. Fill in the required API keys and your Supabase database URL.

```
# .env file

# --- API Keys and Tokens ---
ODDS_API_KEY="YOUR_ODDS_API_KEY_HERE"
APIFY_API_TOKEN="YOUR_APIFY_API_TOKEN_HERE"
GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN_HERE"

# --- Webhook Configuration ---
PA_USERNAME="your-pythonanywhere-username"

# --- Database ---
SUPABASE_DB_URL="postgresql://user:password@host:port/dbname"
```

---

## Deployment on PythonAnywhere

### 1. Create a New Web App

-   In your PythonAnywhere dashboard, go to the **Web** tab and **Add a new web app**.
-   Choose **Manual configuration** and the same Python version used for your virtual environment.

### 2. Configure the Web App

-   **Virtualenv:** Set the path to your virtual environment: `/home/<your-username>/.virtualenvs/sportsbot-venv`.
-   **WSGI File:** Edit the WSGI configuration file to point to your Flask app:

    ```python
    import sys
    path = '/home/<your-username>/sports_bot'
    if path not in sys.path:
        sys.path.insert(0, path)
    from app import app as application
    ```

### 3. Set the Telegram Webhook

-   Run the following `curl` command in a Bash console, replacing the placeholders:

    ```bash
    curl -X GET "https://api.telegram.org/bot<YOUR_TELEGRAM_BOT_TOKEN>/setWebhook?url=https://<your-username>.pythonanywhere.com/webhook"
    ```

### 4. Create the Scheduled Task for the Worker

-   Go to the **Tasks** tab.
-   Create a new **Scheduled task**.
-   Set the command to run the worker script:

    ```bash
    /home/<your-username>/.virtualenvs/sportsbot-venv/bin/python /home/<your-username>/sports_bot/run_analysis_worker.py
    ```

-   Schedule the task to run every **5-10 minutes**.

The Strategic Oracle is now deployed and operational.

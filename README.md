# Sports Betting Telegram Bot

This is a sophisticated, AI-powered Telegram bot designed to provide sports betting insights. It integrates multiple APIs to deliver live odds, historical data, and AI-driven predictions, all within a responsive Telegram interface.

The bot is built to run on the PythonAnywhere free tier, utilizing a webhook-based Flask application and an asynchronous job queue to handle long-running analysis tasks without timing out.

## Key Features

-   **Live Sports & Odds:** Fetches a list of available sports and live odds from The Odds API for multiple bookmakers.
-   **AI-Powered Predictions:** Combines live odds, historical team data from Wikipedia, and real-time Twitter sentiment to generate match predictions and reasoning using the Gemini AI.
-   **Asynchronous Analysis:** Uses a job queue with a Supabase PostgreSQL database to handle long-running tasks (like Twitter scraping), ensuring the bot remains fast and responsive.
-   **Arbitrage Detection:** Identifies arbitrage opportunities by comparing odds across different bookmakers for the same event.
-   **Interactive Interface:** Uses Telegram's inline buttons for a seamless and intuitive user experience.
-   **Efficient Caching:** Caches API responses in the Supabase database to reduce redundant calls and stay within API rate limits.

## Technology Stack

| Component             | Technology / API                                                              | Purpose                                                     |
| --------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------- |
| **Backend**           | Python, Flask                                                                 | Serves the Telegram webhook and core application logic.     |
| **Bot Framework**     | `python-telegram-bot`                                                         | Handles all interactions with the Telegram Bot API.         |
| **Database**          | Supabase (PostgreSQL)                                                         | Provides a robust database for caching and the job queue.   |
| **Live Odds**         | [The Odds API](https://the-odds-api.com/)                                     | Fetches live sports, events, and betting odds.              |
| **Historical Data**   | [Wikipedia API](https://www.mediawiki.org/wiki/API:Main_page)                 | Retrieves historical context and summaries for sports teams.|
| **Sentiment Analysis**| [Apify](https://apify.com/) (Twitter Scraper)                                 | Scrapes real-time Twitter data for sentiment analysis.      |
| **AI Reasoning**      | [Google Gemini API](https://ai.google.dev/)                                   | Generates AI-powered predictions and analysis.              |
| **Hosting**           | [PythonAnywhere](https://www.pythonanywhere.com/)                             | Provides the hosting environment for the Flask web app.     |

---

## Setup and Installation

### 1. Clone the Repository

```bash
git clone <repository_url>
cd sports_bot
```

### 2. Create a Virtual Environment

It is highly recommended to use a virtual environment to manage project dependencies.

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

Install all the required Python packages from `requirements.txt`.

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the `sports_bot` directory by copying the provided `.env.example` or creating a new one. Then, fill in the required API keys and your Supabase database URL.

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

This bot is designed to be deployed on PythonAnywhere's free tier.

### 1. Create a New Web App

-   In your PythonAnywhere dashboard, go to the **Web** tab.
-   Click **Add a new web app**.
-   Choose **Manual configuration** and the same Python version you used for your virtual environment (e.g., Python 3.10).

### 2. Configure the Web App

-   **Virtualenv:** In the "Virtualenv" section, enter the path to your virtual environment: `/home/<your-username>/.virtualenvs/sportsbot-venv`.
-   **WSGI File:** Click on the WSGI configuration file link and edit it to point to your Flask application. The file should look like this:

    ```python
    import sys
    import os

    # Add your project's path to the system path
    path = '/home/<your-username>/sports_bot'
    if path not in sys.path:
        sys.path.insert(0, path)

    # Set an environment variable to tell the app where its config is
    os.environ['FLASK_APP'] = 'app.py'

    # Import the Flask app object
    from app import app as application
    ```

-   **Environment Variables:** In the "Code" section, you can add your environment variables (from your `.env` file) to the "Environment variables" section. This is more secure than using a `.env` file in production.

### 3. Set the Telegram Webhook

-   Once your web app is running, you need to tell Telegram where to send updates. Run the following `curl` command in a Bash console on PythonAnywhere or your local machine:

    ```bash
    curl -X GET "https://api.telegram.org/bot<YOUR_TELEGRAM_BOT_TOKEN>/setWebhook?url=https://<your-username>.pythonanywhere.com/webhook"
    ```

    You should receive an `{"ok":true,"result":true,...}` response.

### 4. Create the Scheduled Task for the Worker

-   Go to the **Tasks** tab in your PythonAnywhere dashboard.
-   Create a new **Scheduled task**.
-   Set the command to run the worker script using your virtual environment's Python interpreter:

    ```bash
    /home/<your-username>/.virtualenvs/sportsbot-venv/bin/python /home/<your-username>/sports_bot/run_analysis_worker.py
    ```

-   Schedule the task to run every **5-10 minutes**. This will process the job queue and send the analysis results to your users.

Your bot is now live and fully operational!

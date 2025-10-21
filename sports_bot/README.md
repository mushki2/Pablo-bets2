# Sports Oracle Telegram Bot

Welcome to the Sports Oracle Bot, a sophisticated, AI-powered sports betting analysis bot designed for Telegram. This bot leverages multiple data sources to provide insightful predictions on upcoming matches, detects market inefficiencies (arbitrage), and tracks your prediction history.

This guide provides comprehensive instructions for deploying the bot on **PythonAnywhere's free tier**.

## Features

-   **AI-Powered Predictions**: Utilizes the Gemini AI to analyze match data, historical performance, and social media sentiment.
-   **Multi-Source Data**: Aggregates data from The Odds API, Wikipedia, and Twitter (via Apify).
-   **Market Scanner**: Detects arbitrage opportunities across various bookmakers.
-   **Prediction History**: Tracks the accuracy of your past predictions.
-   **Secure Remote Setup**: Configure API keys securely via a password-protected admin command within Telegram.
-   **Asynchronous by Design**: Built with a job queue architecture to ensure the bot remains responsive.
-   **Optimized for PythonAnywhere**: Uses scheduled tasks instead of long-running processes to comply with the free tier's limitations.

## Technology Stack

-   **Hosting**: PythonAnywhere
-   **Bot Framework**: `python-telegram-bot`
-   **Web Framework**: Flask (for the webhook)
-   **Database & Job Queue**: Supabase (PostgreSQL)
-   **AI Core**: Google Gemini
-   **Data APIs**: The Odds API, Wikipedia, Apify

---

## Deployment Guide for PythonAnywhere (Free Tier)

Follow these steps carefully to get your bot running for free.

### Step 1: Supabase Setup (Database and Auth)

This bot uses Supabase for its database and for storing configuration.

1.  **Create a Supabase Account**: Go to [supabase.com](https://supabase.com) and sign up.
2.  **Create a New Project**: Choose a name and select the free tier.
3.  **Get API Credentials**:
    -   Go to **Project Settings** > **API**.
    -   Copy the **Project URL** and the `anon` **public** key. You will need these later.
4.  **Create Tables**:
    -   Go to the **SQL Editor** in the Supabase dashboard.
    -   Run the following SQL queries one by one to create the necessary tables:

    ```sql
    -- 1. Configuration table for API keys
    CREATE TABLE config (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    );

    -- 2. Admins table for the /setup command
    CREATE TABLE admins (
      user_id BIGINT PRIMARY KEY
    );

    -- 3. Analysis job queue
    CREATE TABLE analysis_queue (
      id SERIAL PRIMARY KEY,
      user_id BIGINT NOT NULL,
      match_id TEXT NOT NULL,
      status TEXT DEFAULT 'pending', -- pending, processing, completed, failed
      error_message TEXT,
      created_at TIMESTAMPTZ DEFAULT NOW(),
      updated_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- 4. Prediction history
    CREATE TABLE prediction_history (
      id SERIAL PRIMARY KEY,
      user_id BIGINT NOT NULL,
      match_id TEXT NOT NULL,
      sport_key TEXT,
      home_team TEXT,
      away_team TEXT,
      match_commence_time TIMESTAMPTZ,
      predicted_winner TEXT,
      confidence_score FLOAT,
      risk_level TEXT,
      status TEXT DEFAULT 'Pending', -- Pending, Correct, Incorrect
      created_at TIMESTAMPTZ DEFAULT NOW()
    );
    ```

### Step 2: Get API Keys

You will need API keys from the following services:

-   **Telegram**: Talk to `@BotFather` on Telegram to create a new bot. Save the **Bot Token**.
-   **The Odds API**: Sign up at [the-odds-api.com](https://the-odds-api.com) for a free key.
-   **TheSportsDB**: Go to [TheSportsDB](https://www.thesportsdb.com/api.php) and become a $1/month Patreon sponsor to receive your full API key. This is required for the bot to check match results.
-   **Apify**: Sign up at [apify.com](https://apify.com) for a free account and get your API token.
-   **Google AI Studio**: Get your **Gemini API Key** from [Google AI Studio](https://aistudio.google.com/app/apikey).

### Step 3: PythonAnywhere Setup

1.  **Create a PythonAnywhere Account**: Sign up for a free "Beginner" account at [pythonanywhere.com](https://pythonanywhere.com).
2.  **Upload Project Files**:
    -   Go to the **Files** tab.
    -   Create a new directory for your project (e.g., `sports-oracle-bot`).
    -   Upload all the files from this repository into that directory.
3.  **Create a Virtual Environment**:
    -   Open a **Bash Console** from the **Consoles** tab.
    -   Run the following commands, making sure to use a recent Python version (e.g., 3.10):
        ```bash
        cd sports-oracle-bot
        mkvirtualenv --python=/usr/bin/python3.10 my-bot-venv
        pip install -r requirements.txt
        ```
    -   *Note*: The virtual environment will be automatically activated.

### Step 4: Configure the Web App

1.  **Go to the "Web" tab** on PythonAnywhere.
2.  **Create a new web app**:
    -   Click "Add a new web app".
    -   Select **Flask**.
    -   Select the Python version you used for the virtual environment (e.g., Python 3.10).
    -   The path will be automatically generated; no need to change it.
3.  **Configure the WSGI file**:
    -   In the "Code" section of the Web tab, click on the WSGI configuration file link.
    -   Edit the file to look like this, replacing `<your-username>` and `sports-oracle-bot` with your details:
        ```python
        import sys
        path = '/home/<your-username>/sports-oracle-bot' # Main project folder
        if path not in sys.path:
            sys.path.append(path)

        # Assuming your main Flask app file is named app.py and the app object is named 'app'
        from app import app as application
        ```
4.  **Set Environment Variables**:
    -   In the "Code" section, scroll down to **Environment variables**.
    -   Add the following variables one by one:
        -   `BOT_TOKEN`: Your token from BotFather.
        -   `SUPABASE_URL`: Your project URL from Supabase.
        -   `SUPABASE_KEY`: Your `anon` public key from Supabase.
        -   `ADMIN_PASSWORD`: A secure password of your choice for the `/setup` command.
5.  **Reload the Web App**: Click the green "Reload" button at the top of the Web tab.

### Step 5: Set the Telegram Webhook

1.  Copy your PythonAnywhere web app URL (e.g., `https://<your-username>.pythonanywhere.com`).
2.  Construct the following URL in a browser or text editor:
    ```
    https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://<your-username>.pythonanywhere.com/webhook
    ```
3.  Replace `<YOUR_BOT_TOKEN>` and `<your-username>` with your actual credentials.
4.  Visit the URL in your browser. You should see a success message. Your bot is now linked to your web app.

### Step 6: Configure the Bot via Telegram

1.  Open your bot in Telegram.
2.  Send the command `/setup`.
3.  It will ask for the admin password you set in the environment variables. Send it.
4.  Use the inline buttons to set the API keys for The Odds API, Apify, and Gemini.

### Step 7: Schedule the Worker Tasks

This is the final and most crucial step for the bot to function.

1.  Go to the **Tasks** tab on PythonAnywhere.
2.  **Create the Analysis Worker Task**:
    -   Set the time you want it to run (e.g., every 5 minutes).
    -   The command to run is:
        ```bash
        /home/<your-username>/.virtualenvs/my-bot-venv/bin/python /home/<your-username>/sports-oracle-bot/run_analysis_worker.py
        ```
    -   *Make sure to replace `<your-username>` and the virtualenv/project paths with your own.*
3.  **Create the Results Checker Task**:
    -   Set the time you want it to run (e.g., once every hour at a specific minute).
    -   The command to run is:
        ```bash
        /home/<your-username>/.virtualenvs/my-bot-venv/bin/python /home/<your-username>/sports-oracle-bot/check_results_worker.py
        ```
4.  **Enable the tasks**.

### Step 8: Keep the Web App Alive

PythonAnywhere free tier web apps "idle" if they don't receive traffic.

1.  Sign up for a free service like **UptimeRobot**.
2.  Create a new monitor.
3.  Set the type to **HTTP(s)**.
4.  Use your web app's main URL (`https://<your-username>.pythonanywhere.com/`).
5.  Set the monitoring interval to every 5-10 minutes.

This will ping your site and prevent it from going to sleep.

---

**Congratulations! Your Sports Oracle Bot is now fully deployed and operational.**

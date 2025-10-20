# Strategic Oracle - AI Sports Betting Bot

The **Strategic Oracle** is a sophisticated, AI-powered Telegram bot designed to provide advanced sports betting insights. It integrates multiple real-time data streams to deliver live market odds, historical data, and AI-driven predictive analysis, all within a responsive and futuristic Telegram interface.

## Core Capabilities

-   **Live Market Analysis:** Accesses real-time sports and odds data.
-   **AI-Powered Outcome Projections:** Generates detailed match predictions with a **Confidence Score** and an **Assessed Risk Level**.
-   **Secure, Remote Configuration:** A password-protected, admin-only `/setup` command allows for secure configuration of API keys via a private Telegram conversation.
-   **Asynchronous Processing:** Uses a robust job queue with a Supabase PostgreSQL database to manage computationally intensive tasks, ensuring the bot remains instantly responsive.
-   **Market Inefficiency Scanning:** Identifies and highlights arbitrage opportunities.
-   **Intuitive Interface:** Employs Telegram's inline buttons for a fluid and user-friendly experience.

## Technology Architecture

| Component                  | Technology / API                                                              | Purpose                                                              |
| -------------------------- | ----------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| **Backend Core**           | Python, Flask, Gunicorn                                                       | Serves the Telegram webhook and core application logic.              |
| **Bot Framework**          | `python-telegram-bot`                                                         | Handles all interactions with the Telegram Bot API.                  |
| **Database & Config**      | Supabase (PostgreSQL)                                                         | Provides a robust, secure database for caching, job queue, and config. |
| **Live Market Data**       | [The Odds API](https://the-odds-api.com/)                                     | Fetches live sports, events, and betting odds.                       |
| **Historical Context**     | [Wikipedia API](https://www.mediawiki.org/wiki/API:Main_page)                 | Retrieves historical context and performance data for sports teams.  |
| **Public Sentiment**       | [Apify](https://apify.com/) (Twitter Scraper)                                 | Scrapes real-time Twitter data for sentiment analysis.               |
| **Predictive Analytics**   | [Google Gemini API](https://ai.google.dev/)                                   | Generates AI-powered projections, confidence scores, and risk levels.|
| **Deployment**             | Docker, Nginx                                                                 | Containerizes the application for easy deployment on any VPS.        |

---

## Setup and Deployment

### 1. Bootstrap Configuration

Before deploying, you must create a `.env` file and set the essential variables required for the bot to start up.

1.  **Clone the Repository** on your local machine or server.
2.  **Create and Configure the `.env` File:** In the `sports_bot` directory, create a file named `.env` and add the following bootstrap variables:

    ```
    # .env file - BOOTSTRAP VARIABLES

    SUPABASE_DB_URL="postgresql://user:password@host:port/dbname"
    ADMIN_CHAT_ID="YOUR_PERSONAL_TELEGRAM_CHAT_ID"
    SETUP_PASSWORD="CREATE_A_SECURE_PASSWORD"
    TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
    PA_USERNAME="your-pythonanywhere-username-or-domain.com"
    ```

### 2. Secure On-Demand Configuration

After the first deployment, you must configure the bot's API keys securely via Telegram.

1.  **Start the Bot:** Follow the deployment instructions for either PythonAnywhere or VPS below.
2.  **Send the `/setup` command** to the bot from your admin account.
3.  **Provide the password and API keys** when prompted. After providing each key, press the **"🧪 Test Key"** button to validate it in real time.
4.  **Perform the Final Restart (Required):**
    -   Once all keys are provided and tested, you must perform a one-time, manual restart of the application for the new settings to be loaded into memory.
    -   On a VPS, run: `docker-compose restart`
    -   On PythonAnywhere, click the **"Reload"** button on the "Web" tab.
    -   *Why is this necessary?* A running application cannot restart itself. The restart command must be given by the hosting environment (Docker or PythonAnywhere) to ensure the application loads the new configuration cleanly and correctly. This is a standard practice for all production web applications.

---

## Deployment Guides

Choose one of the following deployment methods.

### Option A: Deployment on a VPS with Docker (Recommended)

This method is flexible, scalable, and recommended for a production environment.

1.  **Prerequisites:** A VPS with Docker, Docker Compose, Nginx, and a domain name.
2.  **Deploy:** Copy your `.env` file to the server and run `docker-compose up --build -d`.
3.  **Configure Nginx:** Set up Nginx as a reverse proxy and enable HTTPS with Certbot.
4.  **Set Webhook:** Point Telegram to your secure webhook URL: `https://your.domain.com/webhook`.
5.  **Set Cron Job:** Create a cron job on the VPS to run the worker script inside the container:
    ```
    */5 * * * * docker exec strategic-oracle-bot python run_analysis_worker.py
    ```

### Option B: Deployment on PythonAnywhere Free Tier

This method is excellent for getting started quickly without needing your own server.

1.  **Initial Setup:**
    -   In a PythonAnywhere Bash console, clone the repository.
    -   Create a virtual environment: `python3 -m venv ~/.virtualenvs/sportsbot-venv`.
    -   Install dependencies: `pip install -r requirements.txt`.
    -   Upload your `.env` file to the `sports_bot` directory via the "Files" tab.

2.  **Create a New Web App:**
    -   Go to the **Web** tab and **Add a new web app**.
    -   Choose **Manual configuration** and the same Python version as your virtual environment.

3.  **Configure the Web App:**
    -   **Virtualenv:** Set the path to `/home/<your-username>/.virtualenvs/sportsbot-venv`.
    -   **WSGI File:** Edit the file to point to your Flask app:
        ```python
        import sys
        path = '/home/<your-username>/sports_bot'
        if path not in sys.path:
            sys.path.insert(0, path)
        from app import app as application
        ```
    -   **Reload** the web app.

4.  **Set the Telegram Webhook:**
    -   Run the `curl` command to set your webhook, using your PythonAnywhere URL:
        ```bash
        curl -X GET "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<user>.pythonanywhere.com/webhook"
        ```

5.  **Run the `/setup` Command** as described in the "Secure On-Demand Configuration" section above, then **Reload your web app** again.

6.  **Create the Scheduled Task for the Worker:**
    -   Go to the **Tasks** tab.
    -   Create a new **Scheduled task**.
    -   Set the command to run the worker script with your virtualenv:
        ```bash
        /home/<your-username>/.virtualenvs/sportsbot-venv/bin/python /home/<your-username>/sports_bot/run_analysis_worker.py
        ```
    -   Schedule the task to run every **5-10 minutes**.

The Strategic Oracle is now fully deployed and operational.

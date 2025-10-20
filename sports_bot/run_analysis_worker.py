import os
import json
import asyncio
import telegram

# Import project modules
import utils
import wikipedia_data
import apify_scraper
import prediction_core
import odds_api
import market_scanner

async def send_telegram_message(chat_id, text, config: dict):
    """Initializes and sends a message via the Telegram Bot API."""
    telegram_token = config.get("TELEGRAM_BOT_TOKEN")
    if not telegram_token:
        print("Error: TELEGRAM_BOT_TOKEN not configured.")
        return

    bot = telegram.Bot(token=telegram_token)
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode='Markdown')
    except Exception as e:
        print(f"Failed to send message to {chat_id}: {e}")

# --- Job-Specific Pipeline Functions ---

def run_analysis_pipeline(job_data, config: dict):
    """Executes the full analysis pipeline for a single match."""
    home_team = job_data.get("home_team", "N/A")
    away_team = job_data.get("away_team", "N/A")

    historical_summary = f"{wikipedia_data.get_team_history(home_team)}\n\n{wikipedia_data.get_team_history(away_team)}"
    sentiment_summary = apify_scraper.get_twitter_sentiment_summary(f"{home_team} vs {away_team}", config)
    odds_for_ai = utils.format_odds_for_ai(job_data.get('bookmakers', []))

    prediction = prediction_core.get_ai_prediction(
        home_team, away_team, odds_for_ai, sentiment_summary, historical_summary, config
    )

    try:
        ai_data = json.loads(prediction.strip().replace('```json', '').replace('```', ''))
        return (
            f"--- **Outcome Projection Received** ---\n\n"
            f"**Event:** {home_team} vs {away_team}\n"
            f"**Prediction:** {ai_data.get('prediction', 'N/A')}\n"
            f"**Confidence:** {ai_data.get('confidence_score', 'N/A')}\n"
            f"**Risk:** {ai_data.get('risk_level', 'N/A')}\n\n"
            f"**Reasoning:**\n{ai_data.get('reasoning', 'N/A')}"
        )
    except (json.JSONDecodeError, AttributeError):
        return f"--- **Oracle Transmission Error** ---\n\nRaw output: {prediction}"

def run_arbitrage_scan_pipeline(config: dict):
    """Scans popular sports markets for arbitrage opportunities."""
    popular_sports = ["soccer_usa_mls", "soccer_uefa_champs_league", "americanfootball_nfl", "basketball_nba"]
    all_opportunities = []

    for sport_key in popular_sports:
        events = odds_api.get_odds(sport_key, config)
        if not events:
            continue
        for event in events:
            opportunities = market_scanner.find_arbitrage_opportunities(event.get('bookmakers', []))
            if opportunities:
                for opp in opportunities:
                    opp['event'] = f"{event['home_team']} vs {event['away_team']}"
                    all_opportunities.append(opp)

    if not all_opportunities:
        return "**Market Scan Complete:** No significant arbitrage opportunities found in popular markets."

    report = "**Market Inefficiency Report:**\n\n"
    for opp in all_opportunities:
        report += f"**Event:** {opp['event']}\n**Profit:** {opp['profit_percentage']}%\n"
        for outcome, details in opp['outcomes'].items():
            report += f"- Bet on **{outcome}** with **{details['bookmaker']}** at **{details['price']}**\n"
        report += "---\n"

    return report

async def main():
    """Main function for the worker script."""
    print("--- Analysis Worker Started ---")

    bot_config = utils.get_all_settings()
    if not bot_config:
        print("CRITICAL: Could not load configuration from database.")
        return

    pending_jobs = utils.get_pending_jobs()
    if not pending_jobs:
        print("No pending jobs found.")
        return

    for job in pending_jobs:
        job_id, chat_id, job_type, job_data_json, status = job

        try:
            utils.update_job_status(job_id, 'processing')
            job_data = json.loads(job_data_json)

            final_result = ""
            if job_type == 'analysis':
                final_result = run_analysis_pipeline(job_data, bot_config)
            elif job_type == 'arbitrage_scan':
                final_result = run_arbitrage_scan_pipeline(bot_config)

            await send_telegram_message(chat_id, final_result, bot_config)
            utils.delete_job(job_id)
        except Exception as e:
            print(f"Error processing job {job_id}: {e}")
            utils.update_job_status(job_id, 'failed')
            await send_telegram_message(chat_id, "Sorry, an error occurred while processing your request.", bot_config)

    print("--- Analysis Worker Finished ---")

if __name__ == "__main__":
    asyncio.run(main())

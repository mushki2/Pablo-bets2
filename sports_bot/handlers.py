import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from functools import wraps
import itertools

# Import custom modules
import odds_api
import market_scanner
import utils

# --- Admin & Setup Conversation ---
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
def admin_only(func):
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if str(update.effective_chat.id) != ADMIN_CHAT_ID:
            await update.message.reply_text("Access denied.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

(PASSWORD, ASK_ODDS_API, GET_ODDS_API, ASK_APIFY, GET_APIFY, ASK_GEMINI, GET_GEMINI) = range(7)

@admin_only
async def setup_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Enter setup password.")
    return PASSWORD

async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    password = update.message.text
    await update.message.delete()
    if password == os.getenv("SETUP_PASSWORD"):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Authenticated. Provide **Odds API Key**.")
        return ASK_ODDS_API
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Authentication failed.")
        return ConversationHandler.END

async def get_and_save_key(update: Update, context: ContextTypes.DEFAULT_TYPE, key_name: str, next_prompt: str, next_state: int) -> int:
    api_key = update.message.text
    await update.message.delete()
    utils.save_setting(key_name, api_key)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"{key_name} saved.")
    if next_prompt:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=next_prompt)
    return next_state

async def get_odds_api(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await get_and_save_key(update, context, "ODDS_API_KEY", "Next, **Apify API Token**.", ASK_APIFY)

async def get_apify_token(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await get_and_save_key(update, context, "APIFY_API_TOKEN", "Next, **Gemini API Key**.", ASK_GEMINI)

async def get_gemini_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    utils.save_setting("TELEGRAM_BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN"))
    utils.save_setting("PA_USERNAME", os.getenv("PA_USERNAME"))
    await get_and_save_key(update, context, "GEMINI_API_KEY", "", ConversationHandler.END)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Configuration complete! Restart the bot to apply.")
    return ConversationHandler.END

async def setup_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Setup canceled.")
    return ConversationHandler.END

setup_conversation = ConversationHandler(
    entry_points=[CommandHandler("setup", setup_start)],
    states={
        PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_password)],
        ASK_ODDS_API: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_odds_api)],
        ASK_APIFY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_apify_token)],
        ASK_GEMINI: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gemini_key)],
    },
    fallbacks=[CommandHandler("cancel", setup_cancel)],
)

# --- Main UI Flow ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_message = f"Greetings, {update.effective_user.first_name}. I am the **Strategic Oracle**."
    await update.message.reply_html(welcome_message, reply_markup=main_menu_keyboard())

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏆 Sports", callback_data='sports_menu'), InlineKeyboardButton("🔮 Prediction", callback_data='prediction_menu')],
        [InlineKeyboardButton("💹 Arbitrage", callback_data='arbitrage_menu'), InlineKeyboardButton("⚙️ Settings", callback_data='settings_menu')],
    ])

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    config = context.bot_data

    # Main Menu Router
    if data == 'main_menu':
        await query.edit_message_text(text="**Oracle Mainframe:**", reply_markup=main_menu_keyboard(), parse_mode='Markdown')
    elif data == 'sports_menu':
        await sports_menu_handler(query, config)
    elif data == 'prediction_menu':
        await prediction_menu_handler(query, config)
    elif data == 'arbitrage_menu':
        await arbitrage_menu_handler(query)
    elif data == 'settings_menu':
        await settings_menu_handler(query)
    elif data == 'run_setup':
        await query.edit_message_text("To start secure setup, send the `/setup` command.")

    # Sports Navigation
    elif data.startswith('sport_'):
        await leagues_menu_handler(query, config, data.split('_', 1)[1])
    elif data.startswith('league_'):
        _, sport_key, league_key = data.split('_', 2)
        await matches_menu_handler(query, context, config, sport_key, league_key)
    elif data.startswith('predict_'):
        _, sport_key, match_id = data.split('_', 2)
        await request_prediction_handler(query, config, sport_key, match_id)

async def sports_menu_handler(query, config):
    sports = odds_api.get_sports(config)
    if not sports:
        await query.edit_message_text("Market data unavailable.")
        return
    keyboard = [[InlineKeyboardButton(s['title'], callback_data=f"sport_{s['key']}")] for s in sports]
    keyboard.append([InlineKeyboardButton("⬅️ Main Menu", callback_data='main_menu')])
    await query.edit_message_text("**Select a Sport Market:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def leagues_menu_handler(query, config, sport_key):
    sports = odds_api.get_sports(config)
    sport = next((s for s in sports if s['key'] == sport_key), None)
    leagues = sport.get('groups', []) if sport else []
    if not leagues:
        await query.edit_message_text("No leagues found for this sport.")
        return
    keyboard = [[InlineKeyboardButton(l['title'], callback_data=f"league_{sport_key}_{l['key']}")] for l in leagues]
    keyboard.append([InlineKeyboardButton("⬅️ Back to Sports", callback_data='sports_menu')])
    await query.edit_message_text(f"**Select a League in {sport['title']}:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def matches_menu_handler(query, context, config, sport_key, league_key):
    await query.edit_message_text("Fetching matches...")
    events = odds_api.get_odds(sport_key, config)
    league_matches = [e for e in events if e.get('group') == league_key] if events else []
    if not league_matches:
        await query.edit_message_text("No upcoming matches found for this league.")
        return

    await query.delete_message()
    for match in league_matches[:5]:
        odds_text = "Odds not available"
        bookmaker = match.get('bookmakers', [])[0] if match.get('bookmakers') else {}
        market = next((m for m in bookmaker.get('markets', []) if m['key'] == 'h2h'), None)
        if market:
            outcomes = market['outcomes']
            odds_text = f"{outcomes[0]['name']}: {outcomes[0]['price']} | {outcomes[1]['name']}: {outcomes[1]['price']}"
            if len(outcomes) > 2: odds_text += f" | Draw: {outcomes[2]['price']}"

        match_text = f"**{match['home_team']} vs {match['away_team']}**\n_{odds_text}_"
        keyboard = [[InlineKeyboardButton("🔮 Predict", callback_data=f"predict_{sport_key}_{match['id']}")]]
        await context.bot.send_message(chat_id=query.effective_chat.id, text=match_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    nav_keyboard = [[InlineKeyboardButton("⬅️ Back to Leagues", callback_data=f"sport_{sport_key}")]]
    await context.bot.send_message(chat_id=query.effective_chat.id, text="---", reply_markup=InlineKeyboardMarkup(nav_keyboard))

async def request_prediction_handler(query, config, sport_key, match_id):
    await query.edit_message_text("Request acknowledged. Queuing projection...")
    events = odds_api.get_odds(sport_key, config)
    match_details = next((m for m in events if m['id'] == match_id), None)
    if not match_details:
        await query.edit_message_text("Error: Could not queue job.")
        return
    utils.add_job_to_queue(query.effective_chat.id, 'analysis', match_details)

async def prediction_menu_handler(query, config):
    """Fetches and displays a curated list of popular upcoming matches."""
    await query.edit_message_text("Fetching popular upcoming events...")

    popular_sports = [
        "soccer_usa_mls",
        "soccer_uefa_champs_league",
        "americanfootball_nfl",
        "basketball_nba",
    ]

    all_popular_matches = []
    for sport_key in popular_sports:
        events = odds_api.get_odds(sport_key, config)
        if events:
            # Add sport_key to each match for the callback
            for event in events:
                event['sport_key'] = sport_key
            all_popular_matches.extend(events)

    if not all_popular_matches:
        await query.edit_message_text("Could not fetch popular matches at this time.")
        return

    # Sort matches by commence time
    all_popular_matches.sort(key=lambda x: x['commence_time'])

    keyboard = []
    for match in all_popular_matches[:10]: # Limit to 10 most recent popular matches
        keyboard.append([
            InlineKeyboardButton(
                f"{match['home_team']} vs {match['away_team']}",
                callback_data=f"predict_{match['sport_key']}_{match['id']}"
            )
        ])

    keyboard.append([InlineKeyboardButton("⬅️ Main Menu", callback_data='main_menu')])

    await query.edit_message_text(
        "**Popular Upcoming Events:**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def arbitrage_menu_handler(query):
    utils.add_job_to_queue(query.effective_chat.id, 'arbitrage_scan', {})
    await query.edit_message_text("Request acknowledged. A market-wide arbitrage scan is in progress.")

async def settings_menu_handler(query):
    if str(query.effective_chat.id) != ADMIN_CHAT_ID:
        await query.edit_message_text("Restricted area.")
        return
    keyboard = [[InlineKeyboardButton("🔐 Run Secure Setup", callback_data='run_setup')]]
    await query.edit_message_text("Admin settings:", reply_markup=InlineKeyboardMarkup(keyboard))

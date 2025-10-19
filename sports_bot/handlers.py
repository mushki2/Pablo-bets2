import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Import our custom modules
import odds_api
import wikipedia_data
import apify_scraper
import prediction_core
import market_scanner
import utils

# --- Main Menu and Start Command ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message and the main menu when the /start command is issued."""
    user = update.effective_user
    welcome_message = (
        f"Greetings, {user.first_name}. I am the **Strategic Oracle**.\n\n"
        "I process vast amounts of market data, public sentiment, and historical records to provide advanced predictive analysis for sporting events.\n\n"
        "Access my core functions below to begin."
    )

    await update.message.reply_html(
        welcome_message,
        reply_markup=main_menu_keyboard()
    )

def main_menu_keyboard():
    """Returns the InlineKeyboardMarkup for the main menu."""
    keyboard = [
        [InlineKeyboardButton("📈 Access Sport Markets", callback_data='list_sports')],
    ]
    return InlineKeyboardMarkup(keyboard)

def back_to_main_menu_button():
    return InlineKeyboardButton("⬅️ Main Menu", callback_data='main_menu')

# --- Central Callback Query Handler ---

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses all CallbackQuery updates from inline keyboards."""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == 'list_sports':
        await list_sports_handler(query, context)
    elif data.startswith('sport_'):
        sport_key = data.split('_', 1)[1]
        await list_events_handler(query, context, sport_key)
    elif data.startswith('match_'):
        parts = data.split('_', 2)
        sport_key, match_id = parts[1], parts[2]
        await show_match_options_handler(query, context, sport_key, match_id)
    elif data.startswith('analyze_'):
        parts = data.split('_', 2)
        sport_key, match_id = parts[1], parts[2]
        await analyze_match_handler(query, context, sport_key, match_id)
    elif data.startswith('arbitrage_'):
        parts = data.split('_', 2)
        sport_key, match_id = parts[1], parts[2]
        await check_market_inefficiency_handler(query, context, sport_key, match_id)
    elif data == 'main_menu':
        await query.edit_message_text(
            text="**Oracle Mainframe:**",
            reply_markup=main_menu_keyboard(),
            parse_mode='Markdown'
        )

# --- Handler Implementations ---

async def list_sports_handler(query, context):
    """Displays a list of available sports markets."""
    await query.edit_message_text("Accessing available sport markets...")
    sports = odds_api.get_sports()

    if not sports:
        await query.edit_message_text("Market data is currently unavailable. Please try again later.")
        return

    keyboard = []
    for sport in sports:
        keyboard.append([InlineKeyboardButton(sport['title'], callback_data=f"sport_{sport['key']}")])

    keyboard.append([back_to_main_menu_button()])

    await query.edit_message_text(
        "**Select a Market:**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def list_events_handler(query, context, sport_key):
    """Lists the upcoming events for a given sport."""
    market_name = sport_key.replace('_', ' ').title()
    await query.edit_message_text(f"Scanning for upcoming events in the {market_name} market...")

    events = odds_api.get_odds(sport_key)

    if not events:
        await query.edit_message_text(f"No significant events found for the {market_name} market at this time.")
        return

    keyboard = []
    for event in events[:10]:
        event_title = f"{event['home_team']} vs {event['away_team']}"
        callback_data = f"match_{sport_key}_{event['id']}"
        keyboard.append([InlineKeyboardButton(event_title, callback_data=callback_data)])

    keyboard.append([InlineKeyboardButton("⬅️ Back to Markets", callback_data='list_sports')])

    await query.edit_message_text(
        f"**Upcoming Events: {market_name}**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def show_match_options_handler(query, context, sport_key, match_id):
    """Shows analysis and market inefficiency options for a selected match."""
    events = odds_api.get_odds(sport_key)
    match = next((m for m in events if m['id'] == match_id), None)

    if not match:
        await query.edit_message_text("Error: Event data could not be retrieved.")
        return

    text = f"**Event:** {match['home_team']} vs {match['away_team']}\n\nSelect a strategic function:"

    keyboard = [
        [InlineKeyboardButton("🔮 Generate Outcome Projection", callback_data=f"analyze_{sport_key}_{match_id}")],
        [InlineKeyboardButton("💹 Scan for Market Inefficiencies", callback_data=f"arbitrage_{sport_key}_{match_id}")],
        [InlineKeyboardButton("⬅️ Back to Events", callback_data=f"sport_{sport_key}")]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def analyze_match_handler(query, context, sport_key, match_id):
    """Adds an AI analysis job to the queue and notifies the user."""
    await query.edit_message_text(
        "**Request Acknowledged.**\n\n"
        "Your request for an Outcome Projection has been queued. The Oracle is processing the data streams.\n\n"
        "Results will be delivered via a new transmission in approximately 2-3 minutes."
    )

    events = odds_api.get_odds(sport_key)
    match_details = next((m for m in events if m['id'] == match_id), None)

    if not match_details:
        await query.edit_message_text("Error: Could not retrieve full event details to queue the projection job.")
        return

    chat_id = query.effective_chat.id

    utils.add_analysis_job(chat_id, match_details)

    print(f"Successfully queued Outcome Projection job for chat_id: {chat_id} and match_id: {match_id}")

async def check_market_inefficiency_handler(query, context, sport_key, match_id):
    """Checks a specific match for market inefficiencies (arbitrage)."""
    await query.edit_message_text("Scanning for market inefficiencies...")

    events = odds_api.get_odds(sport_key)
    match = next((m for m in events if m['id'] == match_id), None)
    if not match:
        await query.edit_message_text("Error: Event data not found.")
        return

    opportunities = market_scanner.find_arbitrage_opportunities(match.get('bookmakers', []))

    home_team, away_team = match['home_team'], match['away_team']

    if not opportunities:
        message = f"**Market Scan Complete:** No significant pricing inefficiencies found for {home_team} vs {away_team}."
    else:
        opp = opportunities[0]
        message = (
            f"**Market Inefficiency Detected!**\n\n"
            f"**Potential Profit Margin:** {opp['profit_percentage']}%\n\n"
            "**Recommended Actions:**\n"
        )
        for outcome, details in opp['outcomes'].items():
            message += f"- **{outcome}**: Place wager with **{details['bookmaker']}** at odds of **{details['price']}**\n"

    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Event Options", callback_data=f"match_{sport_key}_{match_id}")]]),
        parse_mode='Markdown'
    )

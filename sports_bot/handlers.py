import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Import our custom modules
import odds_api
import wikipedia_data
import apify_scraper
import gemini_brain
import arbitrage_engine
import utils

# --- Main Menu and Start Command ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message and the main menu when the /start command is issued."""
    user = update.effective_user
    welcome_message = (
        f"Welcome, {user.first_name}! I'm your Sports Betting Assistant.\n\n"
        "I provide live odds, AI-powered predictions, and find arbitrage opportunities.\n\n"
        "Use the menu below to get started."
    )

    # Using reply_html to allow for simple formatting if needed later
    await update.message.reply_html(
        welcome_message,
        reply_markup=main_menu_keyboard()
    )

def main_menu_keyboard():
    """Returns the InlineKeyboardMarkup for the main menu."""
    keyboard = [
        [InlineKeyboardButton("⚽ View Sports", callback_data='list_sports')],
        # For simplicity, arbitrage and AI will be accessed after selecting a match.
    ]
    return InlineKeyboardMarkup(keyboard)

def back_to_main_menu_button():
    return InlineKeyboardButton("⬅️ Main Menu", callback_data='main_menu')

# --- Central Callback Query Handler ---

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses all CallbackQuery updates from inline keyboards."""
    query = update.callback_query
    await query.answer()  # Acknowledge the button press

    data = query.data

    # Simple router based on callback_data prefix
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
        await check_arbitrage_handler(query, context, sport_key, match_id)
    elif data == 'main_menu':
        await query.edit_message_text(
            text="Main Menu:",
            reply_markup=main_menu_keyboard()
        )

# --- Handler Implementations ---

async def list_sports_handler(query, context):
    """Displays a list of available sports."""
    await query.edit_message_text("Fetching available sports...")
    sports = odds_api.get_sports()

    if not sports:
        await query.edit_message_text("Could not fetch sports data. Please try again later.")
        return

    keyboard = []
    for sport in sports:
        # Callback data format: 'sport_soccer_epl'
        keyboard.append([InlineKeyboardButton(sport['title'], callback_data=f"sport_{sport['key']}")])

    keyboard.append([back_to_main_menu_button()])

    await query.edit_message_text(
        "Please select a sport:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def list_events_handler(query, context, sport_key):
    """Lists the upcoming events (matches) for a given sport."""
    await query.edit_message_text(f"Fetching matches for {sport_key.replace('_', ' ').title()}...")

    # Fetch odds which contain the list of events
    events = odds_api.get_odds(sport_key)

    if not events:
        await query.edit_message_text(f"No upcoming matches found for {sport_key.replace('_', ' ').title()}.")
        return

    keyboard = []
    for event in events[:10]:  # Limit to 10 events to avoid clutter
        event_title = f"{event['home_team']} vs {event['away_team']}"
        callback_data = f"match_{sport_key}_{event['id']}"
        keyboard.append([InlineKeyboardButton(event_title, callback_data=callback_data)])

    keyboard.append([InlineKeyboardButton("⬅️ Back to Sports", callback_data='list_sports')])

    await query.edit_message_text(
        f"Upcoming Matches for {sport_key.replace('_', ' ').title()}:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_match_options_handler(query, context, sport_key, match_id):
    """Shows analysis and arbitrage options for a selected match."""
    # We need to fetch the event details again to get the team names
    events = odds_api.get_odds(sport_key)
    match = next((m for m in events if m['id'] == match_id), None)

    if not match:
        await query.edit_message_text("Error: Could not retrieve match details.")
        return

    text = f"Selected Match: **{match['home_team']} vs {match['away_team']}**\n\nWhat would you like to do?"

    keyboard = [
        [InlineKeyboardButton("🤖 Get AI Prediction", callback_data=f"analyze_{sport_key}_{match_id}")],
        [InlineKeyboardButton("📊 Check for Arbitrage", callback_data=f"arbitrage_{sport_key}_{match_id}")],
        [InlineKeyboardButton("⬅️ Back to Matches", callback_data=f"sport_{sport_key}")]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def analyze_match_handler(query, context, sport_key, match_id):
    """
    Adds an AI analysis job to the queue and notifies the user.
    The actual analysis is performed by the scheduled worker script.
    """
    await query.edit_message_text("🤖 **Request Received!**\n\nYour AI analysis has been queued. I will send the results in a new message shortly (usually within 2-3 minutes).")

    # Fetch the full match data to store in the job
    events = odds_api.get_odds(sport_key)
    match_details = next((m for m in events if m['id'] == match_id), None)

    if not match_details:
        await query.edit_message_text("Error: Could not retrieve full match details to queue the job.")
        return

    chat_id = query.effective_chat.id

    # Add the job to the Supabase queue
    utils.add_analysis_job(chat_id, match_details)

    print(f"Successfully queued analysis job for chat_id: {chat_id} and match_id: {match_id}")

    # The user has been notified, and the job is queued.
    # The handler's work is done here. The worker script will handle the rest.

async def check_arbitrage_handler(query, context, sport_key, match_id):
    """Checks a specific match for arbitrage opportunities."""
    await query.edit_message_text("📊 Checking for arbitrage opportunities...")

    events = odds_api.get_odds(sport_key)
    match = next((m for m in events if m['id'] == match_id), None)
    if not match:
        await query.edit_message_text("Error: Match data not found.")
        return

    opportunities = arbitrage_engine.find_arbitrage_opportunities(match.get('bookmakers', []))

    home_team, away_team = match['home_team'], match['away_team']

    if not opportunities:
        message = f"**No arbitrage opportunities found for {home_team} vs {away_team}.**"
    else:
        opp = opportunities[0]
        message = f"**Arbitrage Opportunity Found!**\n\n**Profit:** {opp['profit_percentage']}%\n\n**Bets to Place:**\n"
        for outcome, details in opp['outcomes'].items():
            message += f"- Bet on **{outcome}** with **{details['bookmaker']}** at odds of **{details['price']}**\n"

    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Match Options", callback_data=f"match_{sport_key}_{match_id}")]]),
        parse_mode='Markdown'
    )

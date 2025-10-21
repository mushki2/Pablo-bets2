# /sports_bot/handlers.py

import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from utils import (
    is_admin,
    create_supabase_client,
    add_job_to_queue,
    format_prediction_results,
    format_historical_results,
    ADMIN_PASSWORD,
)
from odds_api import get_sports, get_odds
from market_scanner import find_arbitrage_opportunities
from prediction_core import get_prediction
from wikipedia_data import get_team_history

# --- Logging ---
logger = logging.getLogger(__name__)

# --- State definitions for ConversationHandler ---
API_KEY_SETUP = range(1)
ADMIN_LOGIN = range(1)


# --- Admin & Setup Handlers ---

async def setup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the admin verification process for bot setup."""
    user_id = update.effective_user.id
    if await is_admin(user_id):
        await update.message.reply_text("Admin verified. You can proceed with setup.")
        # Directly jump to the setup options if admin is already verified
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Please select the API key you wish to set:",
            reply_markup=setup_keyboard()
        )
        return API_KEY_SETUP
    else:
        await update.message.reply_text("This is a restricted command. Please enter the admin password:")
        return ADMIN_LOGIN

async def admin_password_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Asks for the admin password."""
    await update.message.reply_text("Please enter the admin password:")
    return ADMIN_LOGIN

async def handle_admin_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the admin password submission."""
    password = update.message.text
    # In a real bot, you would hash and compare this password
    if password == ADMIN_PASSWORD: # Replace with a secure check
        user_id = update.effective_user.id
        supabase = create_supabase_client()
        try:
            # Add user to the admin table
            await supabase.table("admins").insert({"user_id": user_id}).execute()
            await update.message.reply_text(
                "Password accepted. You are now an admin.\n"
                "Please select the API key you wish to set:",
                reply_markup=setup_keyboard()
            )
            return API_KEY_SETUP
        except Exception as e:
            logger.error(f"Error adding admin to Supabase: {e}")
            await update.message.reply_text("An error occurred. Please try again later.")
            return ConversationHandler.END
    else:
        await update.message.reply_text("Incorrect password. Access denied.")
        return ConversationHandler.END

def setup_keyboard():
    """Returns the keyboard for API key setup."""
    keyboard = [
        [InlineKeyboardButton("Set Odds API Key", callback_data='set_odds_api')],
        [InlineKeyboardButton("Set Apify API Key", callback_data='set_apify_api')],
        [InlineKeyboardButton("Set Gemini API Key", callback_data='set_gemini_api')],
        [InlineKeyboardButton("Cancel", callback_data='cancel_setup')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def set_api_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's API key input."""
    query = update.callback_query
    await query.answer()

    api_key_type = query.data.split('_')[1] # e.g., 'odds' from 'set_odds_api'
    context.user_data['api_key_type'] = api_key_type

    await query.edit_message_text(f"Please send the API key for: {api_key_type.upper()}")

    # This is a simplified approach. A more robust solution might use ConversationHandler states.
    # We will rely on the next text message from this user being the API key.
    return API_KEY_SETUP # Or a new state if using ConversationHandler for this part


async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles general text input, primarily for setting API keys after a prompt."""
    if 'api_key_type' in context.user_data:
        api_key_type = context.user_data.pop('api_key_type')
        api_key = update.message.text

        supabase = create_supabase_client()
        try:
            # Upsert the API key into the config table
            await supabase.table("config").upsert({
                "key": f"{api_key_type.upper()}_API_KEY",
                "value": api_key
            }).execute()

            await update.message.reply_text(f"{api_key_type.upper()} API key has been set successfully.")

            # Clean up the original message if possible
            if 'last_setup_message_id' in context.user_data:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data.pop('last_setup_message_id')
                )
        except Exception as e:
            logger.error(f"Error saving API key to Supabase: {e}")
            await update.message.reply_text("Failed to save the API key. Please try again.")
    else:
        # Default behavior for non-command, non-setup text
        await update.message.reply_text(
            "I'm not sure what you mean. Please use the menu or a command to interact with me."
        )


async def cancel_setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the setup process."""
    await update.message.reply_text("Setup process canceled.")
    return ConversationHandler.END


# --- Main Menu and Navigation ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the main menu."""
    keyboard = main_menu_keyboard()
    await update.message.reply_text(
        "Welcome to the Sports Oracle Bot! Please choose an option:",
        reply_markup=keyboard
    )

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles main menu button presses."""
    query = update.callback_query
    await query.answer()

    action = query.data.split('_')[1]

    if action == "sports":
        await list_sports(update, context)
    elif action == "arbitrage":
        await list_arbitrage(update, context)
    elif action == "history":
        await handle_history_request(update, context)
    elif action == "home":
        keyboard = main_menu_keyboard()
        await query.edit_message_text(
            "Welcome back to the main menu!",
            reply_markup=keyboard
        )

def main_menu_keyboard():
    """Returns the main menu keyboard."""
    keyboard = [
        [InlineKeyboardButton("⚽ View Sports & Leagues", callback_data="menu_sports")],
        [InlineKeyboardButton("📈 Market Inefficiencies (Arbitrage)", callback_data="menu_arbitrage")],
        [InlineKeyboardButton("📜 My Prediction History", callback_data="menu_history")],
    ]
    return InlineKeyboardMarkup(keyboard)


# --- Sports, Leagues, and Matches Flow ---

async def list_sports(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetches and displays a list of available sports."""
    query = update.callback_query
    sports = get_sports() # This should be cached

    if not sports:
        await query.edit_message_text("Could not retrieve sports data. Please try again later.")
        return

    keyboard = [
        [InlineKeyboardButton(sport['title'], callback_data=f"sport_{sport['key']}")]
        for sport in sports
    ]
    keyboard.append([InlineKeyboardButton("« Back to Main Menu", callback_data="menu_home")])

    await query.edit_message_text(
        "Please select a sport:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_sports_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the user's sport selection and lists leagues."""
    query = update.callback_query
    await query.answer()

    sport_key = query.data.split('_')[1]
    # For now, we assume all sports have the same leagues. This can be expanded.
    # In a real scenario, you'd fetch leagues for the specific sport.

    # Simplified league list
    leagues = {
        "NFL": "americanfootball_nfl",
        "NBA": "basketball_nba",
        "Premier League": "soccer_epl"
    }

    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"league_{key}")]
        for name, key in leagues.items()
    ]
    keyboard.append([InlineKeyboardButton("« Back to Sports", callback_data="menu_sports")])

    await query.edit_message_text(
        f"Selected sport: {sport_key.replace('_', ' ').title()}. Please choose a league:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_league_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles league selection and shows matches."""
    query = update.callback_query
    await query.answer()

    league_key = query.data.split('_', 1)[1]

    await query.edit_message_text("Fetching matches for the selected league... Please wait.")

    matches = get_odds(league_key)

    if not matches:
        await query.edit_message_text("No upcoming matches found for this league.")
        return

    keyboard = []
    for match in matches[:10]: # Limit to 10 matches to avoid oversized message
        match_id = match['id']
        home_team = match['home_team']
        away_team = match['away_team']
        keyboard.append([
            InlineKeyboardButton(f"{home_team} vs {away_team}", callback_data=f"match_{match_id}")
        ])

    keyboard.append([InlineKeyboardButton("« Back to Sports", callback_data="menu_sports")])

    await query.edit_message_text(
        "Select a match to get a strategic analysis:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_match_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays details for a selected match and analysis options."""
    query = update.callback_query
    await query.answer()

    match_id = query.data.split('_')[1]

    # Fetch all matches again to find the one with the selected ID
    # In a real app, you would cache this or fetch the single match by ID if the API supports it
    all_matches = get_odds(context.user_data.get('league_key', '')) # Requires saving league_key in context

    selected_match = next((m for m in all_matches if m['id'] == match_id), None)

    if not selected_match:
        await query.edit_message_text("Match details not found. It might have started or been removed.")
        return

    home_team = selected_match['home_team']
    away_team = selected_match['away_team']

    # Create a summary of the best odds
    summary_text = f"<b>{home_team} vs. {away_team}</b>\n\n"
    summary_text += "Best Available Odds:\n"
    # This part needs to be implemented: find best odds from bookmakers
    # For now, a placeholder:
    summary_text += "- <i>Odds data would be displayed here.</i>"

    keyboard = [
        [InlineKeyboardButton("🤖 Get AI-Powered Strategic Analysis", callback_data=f"analyze_{match_id}")],
        [InlineKeyboardButton("« Back to Matches", callback_data=f"league_{context.user_data.get('league_key', '')}")]
    ]

    await query.edit_message_text(
        summary_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


# --- Analysis and History ---

async def handle_analysis_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Adds a match analysis job to the queue."""
    query = update.callback_query
    await query.answer()

    match_id = query.data.split('_')[1]
    user_id = query.from_user.id

    try:
        job_id = add_job_to_queue(match_id, user_id)
        await query.edit_message_text(
            "Your request for a strategic analysis has been submitted.\n"
            f"The Oracle is processing... This may take a moment.\n"
            f"Job ID: `{job_id}`",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Failed to add job to queue: {e}")
        await query.edit_message_text(
            "There was an error submitting your request. Please try again later."
        )

async def handle_history_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetches and displays the user's prediction history."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    await query.edit_message_text("Fetching your prediction history...")

    supabase = create_supabase_client()
    try:
        response = await supabase.table("prediction_history").select("*").eq("user_id", user_id).execute()

        if not response.data:
            await query.edit_message_text("You have no prediction history yet.")
            return

        formatted_history = format_historical_results(response.data)

        keyboard = [[InlineKeyboardButton("« Back to Main Menu", callback_data="menu_home")]]

        await query.edit_message_text(
            formatted_history,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )

    except Exception as e:
        logger.error(f"Error fetching user history: {e}")
        await query.edit_message_text("Could not retrieve your history. Please try again.")


# --- Arbitrage ---

async def list_arbitrage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Finds and lists arbitrage opportunities."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text("Scanning markets for inefficiencies... This may take a moment.")

    # In a real app, you'd iterate through multiple sports/leagues
    all_odds = get_odds("upcoming") # A generic endpoint for all upcoming games
    opportunities = find_arbitrage_opportunities(all_odds)

    if not opportunities:
        await query.edit_message_text("No market inefficiencies found at the moment.")
        return

    message = "<b>Market Inefficiency Detected (Arbitrage)</b>\n\n"
    for opp in opportunities:
        message += (
            f"Match: {opp['home_team']} vs {opp['away_team']}\n"
            f"Profit Margin: {opp['profit_margin']:.2f}%\n"
            f"Bookmakers: {opp['bookmaker1']} & {opp['bookmaker2']}\n\n"
        )

    keyboard = [[InlineKeyboardButton("« Back to Main Menu", callback_data="menu_home")]]

    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

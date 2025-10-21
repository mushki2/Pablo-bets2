# /sports_bot/market_scanner.py

import logging
from itertools import combinations

logger = logging.getLogger(__name__)

def find_arbitrage_opportunities(matches: list) -> list:
    """
    Analyzes a list of matches to find arbitrage opportunities.

    An arbitrage opportunity exists if the sum of the inverse of the odds
    for all outcomes of an event is less than 1.
    Formula for a 2-way market (e.g., Team A vs. Team B):
        (1 / odds_team_A) + (1 / odds_team_B) < 1

    Args:
        matches: A list of match data, where each match includes a list of
                 bookmakers and their odds for different outcomes.

    Returns:
        A list of dictionaries, where each dictionary details a found
        arbitrage opportunity, including the match, involved bookmakers,
        and the potential profit margin.
    """
    opportunities = []

    if not matches:
        return opportunities

    for match in matches:
        home_team = match.get('home_team')
        away_team = match.get('away_team')
        bookmakers = match.get('bookmakers', [])

        # We need at least two bookmakers to find an arbitrage opportunity
        if len(bookmakers) < 2:
            continue

        # Structure to hold the best odds for each outcome across all bookies
        best_odds = {}  # E.g., {'home_team': {'price': 1.5, 'bookmaker': 'BookieA'}}

        for bookie in bookmakers:
            bookmaker_title = bookie.get('title', 'Unknown Bookmaker')
            h2h_market = next((m for m in bookie.get('markets', []) if m['key'] == 'h2h'), None)

            if not h2h_market:
                continue

            for outcome in h2h_market.get('outcomes', []):
                outcome_name = outcome.get('name')
                outcome_price = outcome.get('price')

                if not outcome_name or not outcome_price:
                    continue

                # If we haven't seen this outcome yet, or if the current price is better
                if outcome_name not in best_odds or outcome_price > best_odds[outcome_name]['price']:
                    best_odds[outcome_name] = {
                        'price': outcome_price,
                        'bookmaker': bookmaker_title
                    }

        # After checking all bookmakers, analyze the best odds for arbitrage
        if not best_odds:
            continue

        # We need odds for all possible outcomes to calculate arbitrage
        outcome_prices = [1 / data['price'] for data in best_odds.values()]

        if not outcome_prices or len(outcome_prices) < 2: # Need at least two outcomes
            continue

        arbitrage_value = sum(outcome_prices)

        if 0 < arbitrage_value < 1:
            profit_margin = (1 - arbitrage_value) * 100

            opportunity_details = {
                "match": f"{home_team} vs {away_team}",
                "profit_margin": profit_margin,
                "outcomes": best_odds,
                "arbitrage_value": arbitrage_value,
                "description": f"Bet on all outcomes across different bookmakers for a guaranteed profit of ~{profit_margin:.2f}%."
            }
            opportunities.append(opportunity_details)
            logger.info(f"Arbitrage opportunity found for {home_team} vs {away_team}! Profit: {profit_margin:.2f}%")

    return sorted(opportunities, key=lambda x: x['profit_margin'], reverse=True)

if __name__ == '__main__':
    # Example usage for direct testing with mock data
    mock_matches = [
        {
            'home_team': 'Team A',
            'away_team': 'Team B',
            'bookmakers': [
                {
                    'title': 'BookmakerX',
                    'markets': [{
                        'key': 'h2h',
                        'outcomes': [{'name': 'Team A', 'price': 2.15}, {'name': 'Team B', 'price': 1.8}]
                    }]
                },
                {
                    'title': 'BookmakerY',
                    'markets': [{
                        'key': 'h2h',
                        'outcomes': [{'name': 'Team A', 'price': 1.9}, {'name': 'Team B', 'price': 2.25}]
                    }]
                }
            ]
        },
        {
            'home_team': 'Team C',
            'away_team': 'Team D',
            'bookmakers': [
                {
                    'title': 'BookmakerZ',
                    'markets': [{
                        'key': 'h2h',
                        'outcomes': [{'name': 'Team C', 'price': 1.5}, {'name': 'Team D', 'price': 2.5}]
                    }]
                }
            ]
        }
    ]

    found_opportunities = find_arbitrage_opportunities(mock_matches)

    if found_opportunities:
        print("--- Market Inefficiencies Detected ---")
        for opp in found_opportunities:
            print(f"Match: {opp['match']}")
            print(f"  Profit Margin: {opp['profit_margin']:.2f}%")
            print(f"  Best Bets:")
            for outcome, details in opp['outcomes'].items():
                print(f"    - Bet on '{outcome}' at {details['bookmaker']} (Odds: {details['price']})")
            print("-" * 20)
    else:
        print("No arbitrage opportunities found in the mock data.")

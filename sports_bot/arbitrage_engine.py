from itertools import combinations

def find_arbitrage_opportunities(bookmaker_odds):
    """
    Analyzes odds from multiple bookmakers for a single event to find arbitrage opportunities.

    Args:
        bookmaker_odds (list): A list of dictionaries, where each dictionary represents
                               a bookmaker's odds for an event.
                               Example format:
                               [
                                   {
                                       "key": "draftkings",
                                       "title": "DraftKings",
                                       "markets": [
                                           {
                                               "key": "h2h",
                                               "outcomes": [
                                                   {"name": "Team A", "price": 1.5},
                                                   {"name": "Team B", "price": 2.8}
                                               ]
                                           }
                                       ]
                                   },
                                   ...
                               ]

    Returns:
        list: A list of dictionaries, each representing an arbitrage opportunity.
              Returns an empty list if no opportunities are found.
    """
    opportunities = []

    # We are interested in the 'h2h' (head-to-head) market for this simple example.
    h2h_odds = []
    for bookmaker in bookmaker_odds:
        for market in bookmaker.get("markets", []):
            if market.get("key") == "h2h":
                h2h_odds.append({
                    "bookmaker": bookmaker.get("title"),
                    "outcomes": market.get("outcomes", [])
                })

    if not h2h_odds:
        return opportunities

    # Find the best odds for each outcome across all bookmakers
    best_odds = {} # Key: outcome name, Value: {price: float, bookmaker: str}
    for bookmaker_data in h2h_odds:
        bookmaker_name = bookmaker_data["bookmaker"]
        for outcome in bookmaker_data["outcomes"]:
            outcome_name = outcome["name"]
            price = outcome["price"]

            if outcome_name not in best_odds or price > best_odds[outcome_name]["price"]:
                best_odds[outcome_name] = {"price": price, "bookmaker": bookmaker_name}

    # Check for arbitrage
    if len(best_odds) < 2: # Need at least two outcomes for an arbitrage bet
        return opportunities

    # The sum of reciprocals of the highest odds
    margin = sum(1 / data["price"] for data in best_odds.values())

    if margin < 1:
        profit_percentage = (1 - margin) * 100
        opportunity = {
            "outcomes": best_odds,
            "profit_percentage": round(profit_percentage, 2),
            "margin": margin
        }
        opportunities.append(opportunity)

    return opportunities

if __name__ == '__main__':
    # Example usage with sample data
    sample_odds_data = [
        {
            "key": "draftkings",
            "title": "DraftKings",
            "markets": [
                {"key": "h2h", "outcomes": [{"name": "Team A", "price": 2.1}, {"name": "Team B", "price": 1.8}]}
            ]
        },
        {
            "key": "fanduel",
            "title": "FanDuel",
            "markets": [
                {"key": "h2h", "outcomes": [{"name": "Team A", "price": 1.9}, {"name": "Team B", "price": 2.2}]}
            ]
        },
         {
            "key": "betmgm",
            "title": "BetMGM",
            "markets": [
                {"key": "h2h", "outcomes": [{"name": "Team A", "price": 2.15}, {"name": "Team B", "price": 1.95}]}
            ]
        }
    ]

    # In this example, best odds are:
    # Team A: 2.15 from BetMGM
    # Team B: 2.2 from FanDuel
    # Margin = (1/2.15) + (1/2.2) = 0.465 + 0.454 = 0.919 (< 1, so arbitrage exists)
    # Profit = (1 - 0.919) * 100 = 8.1%

    found_opportunities = find_arbitrage_opportunities(sample_odds_data)

    if found_opportunities:
        print("Arbitrage opportunities found!")
        for opp in found_opportunities:
            print(f"  Profit: {opp['profit_percentage']}%")
            print("  Bet on:")
            for outcome, details in opp['outcomes'].items():
                print(f"    - {outcome} at {details['price']} with {details['bookmaker']}")
    else:
        print("No arbitrage opportunities found in the sample data.")

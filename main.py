
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import requests
import random

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

ODDS_API_KEY = "6638784dcfb3dfa46904e848dc010af8"
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/baseball_ml/mlb/odds"
REGION = "us"
MARKETS = "h2h"

def fetch_odds():
    try:
        url = f"{ODDS_API_URL}?apiKey={ODDS_API_KEY}&regions={REGION}&markets={MARKETS}"
        res = requests.get(url, timeout=10)
        data = res.json()
        odds_dict = {}
        for game in data:
            if "bookmakers" not in game or not game["bookmakers"]:
                continue
            bookmaker = game["bookmakers"][0]
            for outcome in bookmaker["markets"][0]["outcomes"]:
                team = outcome["name"]
                odds = outcome.get("price", None)
                if odds is not None:
                    odds_dict.setdefault(f"{game['home_team']} vs {game['away_team']}", {})[team] = odds
        return odds_dict
    except Exception as e:
        print("Failed to fetch live odds:", e)
        return {}

def american_to_decimal(odds):
    if odds > 0:
        return 1 + odds / 100
    else:
        return 1 + 100 / abs(odds)

def generate_picks():
    games = [
        ("San Diego Padres", "Philadelphia Phillies"),
        ("St. Louis Cardinals", "Pittsburgh Pirates"),
        ("New York Yankees", "Toronto Blue Jays"),
        ("Cincinnati Reds", "Boston Red Sox"),
        ("Oakland Athletics", "Tampa Bay Rays"),
        ("Baltimore Orioles", "Texas Rangers"),
        ("Kansas City Royals", "Seattle Mariners"),
        ("San Francisco Giants", "Arizona Diamondbacks"),
    ]
    odds_data = fetch_odds()
    picks = []

    for away, home in games:
        matchup_key = f"{home} vs {away}"
        matchup = f"{away} at {home}"
        team_odds = odds_data.get(matchup_key, {})
        odds = team_odds.get(away, 110)
        try:
            odds = int(odds)
        except:
            odds = 110
        win_prob = round(random.uniform(0.35, 0.65), 3)
        payout = american_to_decimal(odds)
        ev = round((win_prob * payout) - 1, 3)

        picks.append({
            "matchup": matchup,
            "recommendation": f"{away} ML",
            "winProb": win_prob,
            "odds": odds,
            "ev": ev,
            "parlay": win_prob > 0.5,
            "away_pitcher": "TBD",
            "home_pitcher": "TBD"
        })

    return picks

@app.get("/api/mlb/picks")
def get_picks():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"Returning picks for {today}")
    picks = generate_picks()
    return picks

@app.get("/api/mlb/results")
def get_results():
    return {}


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import requests
import random
import re

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

def normalize(name):
    return re.sub(r'[^a-z]', '', name.lower())

def fetch_odds():
    try:
        url = f"{ODDS_API_URL}?apiKey={ODDS_API_KEY}&regions={REGION}&markets={MARKETS}"
        res = requests.get(url, timeout=10)
        data = res.json()
        odds_dict = {}
        for game in data:
            home = game["home_team"]
            away = game["away_team"]
            norm_key = f"{normalize(away)}_at_{normalize(home)}"
            if "bookmakers" in game and game["bookmakers"]:
                bm = game["bookmakers"][0]
                for outcome in bm["markets"][0]["outcomes"]:
                    odds_dict.setdefault(norm_key, {})[normalize(outcome["name"])] = outcome.get("price", 110)
        print("Fetched odds keys:", list(odds_dict.keys()))
        return odds_dict
    except Exception as e:
        print("Error fetching odds:", e)
        return {}

def american_to_decimal(odds):
    return 1 + odds / 100 if odds > 0 else 1 + 100 / abs(odds)

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
        norm_key = f"{normalize(away)}_at_{normalize(home)}"
        matchup = f"{away} at {home}"
        team_key = normalize(away)
        team_odds = odds_data.get(norm_key, {})
        odds = team_odds.get(team_key, 110)
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
    return generate_picks()

@app.get("/api/mlb/results")
def get_results():
    return {}

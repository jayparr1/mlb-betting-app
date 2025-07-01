
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import random

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Mock matchup generator
def generate_mock_picks():
    teams = [
        ("San Diego Padres", "Philadelphia Phillies"),
        ("St. Louis Cardinals", "Pittsburgh Pirates"),
        ("New York Yankees", "Toronto Blue Jays"),
        ("Cincinnati Reds", "Boston Red Sox"),
        ("Oakland Athletics", "Tampa Bay Rays"),
        ("Baltimore Orioles", "Texas Rangers"),
        ("Kansas City Royals", "Seattle Mariners"),
        ("San Francisco Giants", "Arizona Diamondbacks"),
    ]
    picks = []
    for away, home in teams:
        win_prob = round(random.uniform(0.35, 0.65), 3)
        ev = round((win_prob * (110 / 100)) - 1, 3)
        picks.append({
            "matchup": f"{away} at {home}",
            "recommendation": f"{away} ML",
            "winProb": win_prob,
            "odds": 110,
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
    picks = generate_mock_picks()
    return picks

@app.get("/api/mlb/results")
def get_results():
    return {}

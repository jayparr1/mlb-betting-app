
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

# DraftKings MLB event group URL
DK_URL = "https://sportsbook.draftkings.com/sites/US-SB/api/v5/eventgroups/84240?format=json"

def normalize_team(name):
    return re.sub(r"[^a-z]", "", name.lower())

def get_dk_odds():
    try:
        response = requests.get(DK_URL, timeout=10)
        data = response.json()
        games = data.get("eventGroup", {}).get("events", [])
        teams = {t["id"]: t["name"] for t in data.get("eventGroup", {}).get("teams", [])}
        odds_dict = {}

        print("DK Teams:", teams)

        for game in games:
            home_id = game.get("homeTeamId")
            away_id = game.get("awayTeamId")
            if home_id not in teams or away_id not in teams:
                continue
            home_name = teams[home_id]
            away_name = teams[away_id]
            matchup_key = (normalize_team(away_name), normalize_team(home_name))
            event_id = game.get("eventId")

            for offer_category in data.get("eventGroup", {}).get("offerCategories", []):
                for sub in offer_category.get("offerSubcategoryDescriptors", []):
                    for offer_obj in sub.get("offers", []):
                        for o in offer_obj:
                            if o.get("eventId") == event_id and o.get("label") in [home_name, away_name]:
                                label_key = normalize_team(o["label"])
                                odds = o["outcomes"][0].get("oddsAmerican")
                                if odds:
                                    odds_dict.setdefault(matchup_key, {})[label_key] = int(odds)
        print("Parsed DK odds:", odds_dict)
        return odds_dict
    except Exception as e:
        print("DraftKings fetch error:", e)
        return {}

def american_to_decimal(odds):
    if odds > 0:
        return 1 + odds / 100
    else:
        return 1 + 100 / abs(odds)

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
    dk_odds = get_dk_odds()
    picks = []

    for away, home in teams:
        matchup = f"{away} at {home}"
        matchup_key = (normalize_team(away), normalize_team(home))
        odds_entry = dk_odds.get(matchup_key, {})
        chosen_team = normalize_team(away)
        odds = odds_entry.get(chosen_team, 110)
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
    picks = generate_mock_picks()
    return picks

@app.get("/api/mlb/results")
def get_results():
    return {}

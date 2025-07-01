
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

API_KEY = "6638784dcfb3dfa46904e848dc010af8"
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/baseball_ml/mlb/odds"
BOOKMAKER = "draftkings"

def normalize_team(name):
    return name.lower().replace(" ", "").replace(".", "")

def fetch_pitchers():
    today = datetime.date.today().strftime('%Y-%m-%d')
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=probablePitcher"
    try:
        response = requests.get(url)
        data = response.json()
        matchups = {}
        for date in data.get("dates", []):
            for game in date.get("games", []):
                home = game["teams"]["home"]["team"]["name"]
                away = game["teams"]["away"]["team"]["name"]
                home_pitcher = game["teams"]["home"].get("probablePitcher", {}).get("fullName", "TBD")
                away_pitcher = game["teams"]["away"].get("probablePitcher", {}).get("fullName", "TBD")
                matchup_key = normalize_team(away) + "at" + normalize_team(home)
                matchups[matchup_key] = {
                    "home_pitcher": home_pitcher,
                    "away_pitcher": away_pitcher
                }
        return matchups
    except Exception as e:
        print(f"Error fetching pitchers: {e}")
        return {}

@app.get("/api/mlb/picks")
def get_mlb_picks():
    odds_data = []
    try:
        odds_response = requests.get(
            ODDS_API_URL,
            params={
                "apiKey": API_KEY,
                "bookmakers": BOOKMAKER,
                "markets": "h2h",
                "dateFormat": "iso"
            }
        )

        if odds_response.status_code != 200:
            return {
                "error": f"Odds API request failed",
                "status": odds_response.status_code,
                "response": odds_response.text
            }

        odds_data = odds_response.json()
    except Exception as e:
        return {
            "error": f"Could not decode odds API response: {str(e)}",
            "raw_response": odds_response.text if 'odds_response' in locals() else 'No response received.'
        }

    pitchers = fetch_pitchers()
    picks = []

    for game in odds_data:
        try:
            home_team = game["home_team"]
            away_team = [t for t in game["teams"] if t != home_team][0]
            matchup = f"{away_team} at {home_team}"
            key = normalize_team(away_team) + "at" + normalize_team(home_team)

            markets = game.get("bookmakers", [])[0].get("markets", [])
            if not markets:
                continue

            outcomes = markets[0].get("outcomes", [])
            away_odds = next((o["price"] for o in outcomes if o["name"] == away_team), None)
            home_odds = next((o["price"] for o in outcomes if o["name"] == home_team), None)

            if away_odds is None or home_odds is None:
                continue

            away_prob = 100 / (away_odds + 100) if away_odds > 0 else abs(away_odds) / (abs(away_odds) + 100)
            home_prob = 100 / (home_odds + 100) if home_odds > 0 else abs(home_odds) / (abs(home_odds) + 100)

            total = away_prob + home_prob
            away_prob /= total
            home_prob /= total

            recommendation = away_team if away_prob > home_prob else home_team
            win_prob = max(away_prob, home_prob)
            odds = away_odds if recommendation == away_team else home_odds
            ev = ((win_prob * (odds if odds > 0 else odds / 100 * 100)) - (1 - win_prob) * 100) / 100
            parlay = ev > 0.05

            picks.append({
                "matchup": matchup,
                "recommendation": recommendation,
                "winProb": round(win_prob, 3),
                "odds": odds,
                "ev": round(ev, 3),
                "parlay": parlay,
                "home_pitcher": pitchers.get(key, {}).get("home_pitcher", "TBD"),
                "away_pitcher": pitchers.get(key, {}).get("away_pitcher", "TBD")
            })
        except Exception as e:
            print(f"Error processing game: {e}")

    return picks

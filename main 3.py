
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

def fetch_pitchers():
    try:
        today = datetime.date.today().strftime('%Y-%m-%d')
        url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=probablePitcher(note,stats,leagueList,person)"
        response = requests.get(url)
        data = response.json()
        matchups = {}
        for date in data.get("dates", []):
            for game in date.get("games", []):
                home = game["teams"]["home"]["team"]["name"]
                away = game["teams"]["away"]["team"]["name"]
                home_pitcher = game["teams"]["home"].get("probablePitcher", {}).get("fullName", "TBD")
                away_pitcher = game["teams"]["away"].get("probablePitcher", {}).get("fullName", "TBD")
                key = f"{away} at {home}"
                matchups[key] = {
                    "home_pitcher": home_pitcher,
                    "away_pitcher": away_pitcher
                }
        return matchups
    except:
        return {}

@app.get("/api/mlb/picks")
def get_mlb_picks():
    odds_response = requests.get(
        ODDS_API_URL,
        params={"apiKey": API_KEY, "bookmakers": BOOKMAKER, "markets": "h2h", "dateFormat": "iso"}
    )

    try:
        odds_data = odds_response.json()
    except:
        return {"error": "Could not decode odds API response."}

    pitcher_data = fetch_pitchers()
    picks = []

    for game in odds_data:
        try:
            home_team = game["home_team"]
            away_team = [t for t in game["teams"] if t != home_team][0]
            matchup = f"{away_team} at {home_team}"

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

            pitchers = pitcher_data.get(matchup, {"home_pitcher": "TBD", "away_pitcher": "TBD"})

            picks.append({
                "matchup": matchup,
                "recommendation": recommendation,
                "winProb": round(win_prob, 3),
                "odds": odds,
                "ev": round(ev, 3),
                "parlay": parlay,
                "home_pitcher": pitchers["home_pitcher"],
                "away_pitcher": pitchers["away_pitcher"]
            })
        except Exception as e:
            print(f"Error processing game: {e}")

    return picks

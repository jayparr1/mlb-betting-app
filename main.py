from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import requests
from sklearn.linear_model import LogisticRegression

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DRAFTKINGS_API_KEY = "6638784dcfb3dfa46904e848dc010af8"

@app.get("/api/mlb/picks")
def get_mlb_picks():
    try:
        schedule_url = "https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1"
        schedule_data = requests.get(schedule_url).json()

        odds_url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
        odds_params = {
            "regions": "us",
            "markets": "h2h",
            "bookmakers": "draftkings",
            "apiKey": DRAFTKINGS_API_KEY
        }
        odds_data = requests.get(odds_url, params=odds_params).json()

        odds_map = {}
        for game in odds_data:
            teams = tuple(sorted([game["home_team"], game["away_team"]]))
            try:
                for outcome in game["bookmakers"][0]["markets"][0]["outcomes"]:
                    odds_map[(teams, outcome["name"])] = outcome["price"]
            except (IndexError, KeyError):
                continue

        matchups = []
        for date in schedule_data.get("dates", []):
            for game in date.get("games", []):
                home = game['teams']['home']['team']['name']
                away = game['teams']['away']['team']['name']
                matchup = f"{away} at {home}"
                teams_key = tuple(sorted([home, away]))

                home_odds = odds_map.get((teams_key, home), None)
                away_odds = odds_map.get((teams_key, away), None)

                matchups.append({
                    'matchup': matchup,
                    'home_team': home,
                    'away_team': away,
                    'home_pitcher': 'TBD',
                    'away_pitcher': 'TBD',
                    'home_win_pct': np.random.uniform(0.45, 0.65),
                    'away_win_pct': np.random.uniform(0.45, 0.65),
                    'home_recent_form': np.random.uniform(0.4, 0.6),
                    'away_recent_form': np.random.uniform(0.4, 0.6),
                    'stadium_hr_factor': np.random.uniform(0.9, 1.2),
                    'home_odds': home_odds,
                    'away_odds': away_odds,
                })

        if not matchups:
            return { "error": "No matchups found today" }

        df = pd.DataFrame(matchups)
        df['delta_win_pct'] = df['home_win_pct'] - df['away_win_pct']
        df['delta_form'] = df['home_recent_form'] - df['away_recent_form']
        X = df[['delta_win_pct', 'delta_form', 'stadium_hr_factor']]

        y_mock = (X['delta_win_pct'] > 0).astype(int)
        model = LogisticRegression().fit(X, y_mock)
        df['win_prob'] = model.predict_proba(X)[:, 1]

        picks = []
        for _, row in df.iterrows():
            recommendation = f"{row['home_team']} ML" if row['win_prob'] > 0.5 else f"{row['away_team']} ML"
            odds = row['home_odds'] if row['win_prob'] > 0.5 else row['away_odds']
            odds_display = odds if odds is not None else (-120 if row['win_prob'] > 0.5 else 110)
            ev = round((row['win_prob'] * (abs(odds_display) / 100)) - 1, 3) if odds_display else None

            picks.append({
                'matchup': row['matchup'],
                'home_pitcher': row['home_pitcher'],
                'away_pitcher': row['away_pitcher'],
                'recommendation': recommendation,
                'winProb': round(row['win_prob'], 3),
                'odds': int(odds_display) if odds_display else None,
                'ev': ev,
                'parlay': row['win_prob'] > 0.58
            })

        return picks

    except Exception as e:
        return { "error": str(e) }
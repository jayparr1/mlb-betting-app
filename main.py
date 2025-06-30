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

@app.get("/api/mlb/picks")
def get_mlb_picks():
    try:
        today_url = "https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1"
        game_data = requests.get(today_url).json()

        matchups = []
        for date in game_data.get("dates", []):
            for game in date.get("games", []):
                teams = f"{game['teams']['away']['team']['name']} at {game['teams']['home']['team']['name']}"
                home_team = game['teams']['home']['team']['name']
                away_team = game['teams']['away']['team']['name']

                matchups.append({
                    'matchup': teams,
                    'home_pitcher': 'TBD',
                    'away_pitcher': 'TBD',
                    'home_win_pct': np.random.uniform(0.45, 0.65),
                    'away_win_pct': np.random.uniform(0.45, 0.65),
                    'home_recent_form': np.random.uniform(0.4, 0.6),
                    'away_recent_form': np.random.uniform(0.4, 0.6),
                    'stadium_hr_factor': np.random.uniform(0.9, 1.2),
                })

        if not matchups:
            return {"error": "No matchups found today"}

        df = pd.DataFrame(matchups)
        df['delta_win_pct'] = df['home_win_pct'] - df['away_win_pct']
        df['delta_form'] = df['home_recent_form'] - df['away_recent_form']
        X = df[['delta_win_pct', 'delta_form', 'stadium_hr_factor']]

        y_mock = (X['delta_win_pct'] > 0).astype(int)
        model = LogisticRegression().fit(X, y_mock)
        df['win_prob'] = model.predict_proba(X)[:, 1]

        picks = []
        for _, row in df.iterrows():
            if ' at ' in row['matchup']:
                teams = row['matchup'].split(' at ')
            else:
                teams = row['matchup'].split('-')
            rec = f"{teams[1].strip()} ML" if row['win_prob'] > 0.5 else f"{teams[0].strip()} ML"
            picks.append({
                'matchup': row['matchup'],
                'recommendation': rec,
                'winProb': round(row['win_prob'], 3),
                'odds': -120 if row['win_prob'] > 0.5 else 110,
                'ev': round((row['win_prob'] * (110/100 if row['win_prob'] < 0.5 else 100/120)) - 1, 3),
                'parlay': row['win_prob'] > 0.58
            })

        return picks

    except Exception as e:
        return {"error": str(e)}



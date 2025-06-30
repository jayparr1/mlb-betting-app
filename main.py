
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
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
        url = 'https://www.espn.com/mlb/probablepitchers'
        res = requests.get(url)
        soup = BeautifulSoup(res.content, 'lxml')
        matchups = []
        for item in soup.select('.Table__TR')[1:]:
            cols = item.select('.Table__TD')
            if len(cols) >= 3:
                teams = cols[0].text.strip()
                pitchers = cols[1].text.strip(), cols[2].text.strip()
                matchups.append({
                    'matchup': teams,
                    'home_pitcher': pitchers[1],
                    'away_pitcher': pitchers[0],
                })

        for game in matchups:
            game['home_win_pct'] = np.random.uniform(0.45, 0.65)
            game['away_win_pct'] = np.random.uniform(0.45, 0.65)
            game['home_recent_form'] = np.random.uniform(0.4, 0.6)
            game['away_recent_form'] = np.random.uniform(0.4, 0.6)
            game['stadium_hr_factor'] = np.random.uniform(0.9, 1.2)

        df = pd.DataFrame(matchups)
        df['delta_win_pct'] = df['home_win_pct'] - df['away_win_pct']
        df['delta_form'] = df['home_recent_form'] - df['away_recent_form']
        X = df[['delta_win_pct', 'delta_form', 'stadium_hr_factor']]

        y_mock = (X['delta_win_pct'] > 0).astype(int)
        model = LogisticRegression().fit(X, y_mock)
        df['win_prob'] = model.predict_proba(X)[:, 1]

        picks = []
        for _, row in df.iterrows():
            team_names = row['matchup'].split(' at ')
            rec = f"{team_names[-1]} ML" if row['win_prob'] > 0.5 else f"{team_names[0]} ML"
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

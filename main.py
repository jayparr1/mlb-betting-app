# MLB Real-Time Betting Model (Google Colab Compatible)

# Step 1: Install dependencies
!pip install pandas numpy scikit-learn xgboost requests beautifulsoup4 lxml

# Step 2: Import libraries
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score
from datetime import datetime

# Step 3: Get today's matchups and probable pitchers (via ESPN)
espn_url = 'https://www.espn.com/mlb/probablepitchers'
res = requests.get(espn_url)
soup = BeautifulSoup(res.content, 'lxml')

matchups = []
for item in soup.select('.Table__TR')[1:]:
    cols = item.select('.Table__TD')
    if len(cols) >= 3:
        teams = cols[0].text.strip()
        pitchers = cols[1].text.strip(), cols[2].text.strip()
        matchup = {
            'matchup': teams,
            'home_pitcher': pitchers[1],
            'away_pitcher': pitchers[0],
            'home_win_pct': np.random.uniform(0.45, 0.65),
            'away_win_pct': np.random.uniform(0.45, 0.65),
            'home_recent_form': np.random.uniform(0.4, 0.6),
            'away_recent_form': np.random.uniform(0.4, 0.6),
            'stadium_hr_factor': np.random.uniform(0.9, 1.2)
        }
        matchups.append(matchup)

if not matchups:
    print(json.dumps({"error": "No matchups found today"}))
else:
    # Step 5: Prepare data for model input
    data = pd.DataFrame(matchups)
    data['delta_win_pct'] = data['home_win_pct'] - data['away_win_pct']
    data['delta_form'] = data['home_recent_form'] - data['away_recent_form']
    X = data[['delta_win_pct', 'delta_form', 'stadium_hr_factor']]

    # Step 6: Train model (using mock data for now)
    y_mock = (X['delta_win_pct'] > 0).astype(int)
    model = LogisticRegression()
    model.fit(X, y_mock)

    # Step 7: Predict win probabilities for each game
    data['win_prob'] = model.predict_proba(X)[:, 1]

    # Step 8: Output predictions in frontend-friendly format
    def format_for_api(df):
        picks = []
        for _, row in df.iterrows():
            if ' at ' in row['matchup']:
                teams = row['matchup'].split(' at ')
            elif ' vs ' in row['matchup']:
                teams = row['matchup'].split(' vs ')
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

    predictions = format_for_api(data)
    import json
    print(json.dumps(predictions, indent=2))

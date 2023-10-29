"""
Predict players for Dunkest.
Author: Matteo Courthoud
Date: 22/10/2022
"""

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from src.compute_stats import compute_gain, get_season_stats

SEASON = 2023
GAMES_FILE = f'data/nba_{SEASON}/games.csv'
CALENDAR_FILE = f'data/nba_{SEASON}/calendar.csv'
INJURIES_FILE = 'data/injuries.csv'
PREDICTED_GAIN_FILE = 'data/predicted_gain.csv'


def get_next_match():
    """Import dataframe with information on the next matches."""
    df_calendar = pd.read_csv(CALENDAR_FILE, index_col=0)
    df_calendar = df_calendar.rename(columns={'team_visitor': 'own_team', 'team_home': 'opponent_team'})
    df_calendar = pd.concat((df_calendar,
                             pd.read_csv('data/nba_2022/calendar.csv', index_col=0)\
                             .rename(columns={'team_visitor': 'opponent_team', 'team_home': 'own_team'})),
        ignore_index=True)
    df_calendar['date'] = pd.to_datetime(df_calendar['date'])
    df_calendar = df_calendar.sort_values('date')
    df_calendar = df_calendar[df_calendar.date >= pd.to_datetime('today')]
    return df_calendar.groupby('own_team', as_index=False)[['opponent_team']].first()


def get_data():
    """Import stats data and information on the next match."""
    df_stats = get_season_stats(season=SEASON)
    df_games = pd.read_csv(GAMES_FILE, index_col=0)[['date', 'winner', 'loser', 'url']]
    df_stats = pd.merge(df_stats, df_games, on='url', how='left')
    df_stats['date'] = pd.to_datetime((df_stats['date']))
    df_stats['own_team'] = np.where(df_stats.win == 1, df_stats.winner, df_stats.loser)
    df_stats['opponent_team'] = np.where(df_stats.win == 1, df_stats.loser, df_stats.winner)
    df_stats = pd.merge(df_stats, pd.read_csv(INJURIES_FILE, index_col=0), on='name', how='left')
    df_stats = df_stats.sort_values(['name', 'date'])
    df_next_match = df_stats.groupby('name', as_index=False)[['start', 'dunkest_value', 'own_team', 'status']].last()
    df_next_match = pd.merge(df_next_match, get_next_match(), on='own_team', how='left')
    return df_stats, df_next_match


def predict_gain(_df_train, _df_test):
    """Predict gain in test data using model fit on train data."""
    # Selecting train and test data
    df_train = _df_train.copy()
    df_train['last_date'] = df_train.groupby('name')['date'].transform('max')
    days_from_last_date = 1.0 + (df_train['last_date'] - df_train['date']).dt.days.astype(float)
    df_train['weights'] = days_from_last_date ** (-1)
    model = smf.wls('dunkest_score ~ -1 + C(name) + C(opponent_team) + start', df_train, weights=df_train.weights).fit()

    # Test data
    df_test = _df_test[pd.isna(_df_test.status)].copy()
    predictions = model.get_prediction(df_test)
    df_test['predicted_score'] = predictions.predicted_mean - 1*(predictions.se_mean - predictions.se_mean.mean())
    df_test['predicted_gain'] = [compute_gain(v, s) for (v, s) in zip(df_test.dunkest_value, df_test.predicted_score)]
    df_test.loc[~pd.isna(df_test.status), 'predicted_gain'] = -0.1
    df_test = df_test.sort_values('predicted_gain', ascending=False)
    return df_test


def test_model(df_stats: pd.DataFrame):
    dates = df_stats.sort_values('date').date.unique()[10:]
    scores = np.zeros(len(dates))
    for i, date in enumerate(dates):
        df_train = df_stats[(df_stats.date < date) & (pd.isna(df_stats.status))].copy()
        df_test = df_stats[(df_stats.date == date) & (df_stats.name.isin(df_train.name.unique()))].copy()

        # Evaluate model
        df_test = predict_gain(df_train, df_test)
        df_test = df_test[['name', 'dunkest_value', 'dunkest_gain', 'predicted_gain']]
        scores[i] = df_test.iloc[:20, 2].mean()
        print(f'{pd.to_datetime(date): %Y-%m-%d} score: {scores[i]: .4f}')
    print(f'      TOTAL score: {np.mean(scores): .4f}: ')


if __name__ == '__main__':
    #df_stats, _ = get_data()
    test_model(df_stats)





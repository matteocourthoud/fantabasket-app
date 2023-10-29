"""
Predict players for Dunkest.
Author: Matteo Courthoud
Date: 22/10/2022
"""
import os
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from model.compute_stats import compute_fantabasket_gain

CALENDAR_FILE = 'calendar.csv'
GAMES_FILE = 'games.csv'
INJURIES_FILE = 'injuries.csv'
CURRENT_STATS_FILE = 'current_stats.csv'
PREDICTED_GAIN_FILE = 'predicted_gain.csv'


class GainModel:

    def __init__(self,
                 data_dir: str,
                 season: int,
                 df_calendar: pd.DataFrame,
                 df_games: pd.DataFrame,
                 df_injuries: pd.DataFrame,
                 df_stats: pd.DataFrame):
        self._data_dir = data_dir
        self._season = season
        self._df_calendar = df_calendar
        self._df_games = df_games
        self._df_injuries = df_injuries
        self._df_stats = df_stats

    def _get_season_stats_with_match_info(self) -> pd.DataFrame:
        """Adds games information to df_stats"""
        df_stats = pd.merge(self._df_stats, self._df_games, on='game_id', how='left')
        df_stats['own_team'] = np.where(df_stats.win == 1, df_stats.winner, df_stats.loser)
        df_stats['opponent_team'] = np.where(df_stats.win == 1, df_stats.loser, df_stats.winner)
        return df_stats

    def _get_season_stats_with_injuries(self):
        """Import stats data and information on the next match."""
        df_stats = self._get_season_stats_with_match_info()
        df_stats['date'] = pd.to_datetime((df_stats['date']))
        df_stats = pd.merge(df_stats, self._df_injuries, on='name', how='left')
        df_stats = df_stats.sort_values(['name', 'date'])
        return df_stats

    def _get_next_match(self):
        """Imports dataframe with information on the next matches."""
        df_calendar = self._df_calendar.copy()
        df_calendar['date'] = pd.to_datetime(df_calendar['date'])
        temp1 = df_calendar.rename(columns={'team_visitor': 'own_team', 'team_home': 'opponent_team'})
        temp2 = df_calendar.rename(columns={'team_visitor': 'opponent_team', 'team_home': 'own_team'})
        df = pd.concat([temp1, temp2], ignore_index=True)
        # Get first matchup for each "own_team"
        df = df.sort_values('date')
        df = df[df.date >= pd.to_datetime('today')]
        df = df.groupby('own_team', as_index=False)[['opponent_team']].first()
        return df

    def _get_next_match_per_player(self, df_stats):
        """Check next match for each player"""
        df_player_next_match = df_stats.groupby('name', as_index=False)[['start', 'fanta_value', 'own_team', 'status']].last()
        df_player_next_match = pd.merge(df_player_next_match, self._get_next_match(), on='own_team', how='left')
        return df_player_next_match

    def _fit_model_gain(self, df: pd.DataFrame):
        """Predict gain in test data using model fit on train data."""
        # Selecting train and test data
        df_train = df.copy()
        df_train['last_date'] = df_train.groupby('name')['date'].transform('max')
        days_from_last_date = 1.0 + (df_train['last_date'] - df_train['date']).dt.days.astype(float)
        df_train['weights'] = days_from_last_date ** (-1)
        model = smf.wls('fanta_score ~ -1 + C(name) + C(opponent_team) + start', df_train, weights=df_train.weights).fit()
        return model

    def _predict_gain(self, df: pd.DataFrame, model):
        """Predict gain in test data using model fit on train data."""
        df_test = df[pd.isna(df.status)].copy()
        predictions = model.get_prediction(df_test)
        df_test['predicted_score'] = predictions.predicted_mean - 1*(predictions.se_mean - predictions.se_mean.mean())
        df_test['predicted_gain'] = [compute_fantabasket_gain(v, s) for (v, s) in zip(df_test.fanta_value, df_test.predicted_score)]
        df_test.loc[~pd.isna(df_test.status), 'predicted_gain'] = -0.1
        df_test = df_test.sort_values('predicted_gain', ascending=False)
        df_test = df_test[['name', 'predicted_gain', 'predicted_score', 'fanta_value', 'start', 'status']]
        return df_test

    def _compute_predicted_gain(self):
        df_stats = self._get_season_stats_with_injuries()
        df_next_match = self._get_next_match_per_player(df_stats)
        model = self._fit_model_gain(df_stats)
        df_predicted_gain = self._predict_gain(df_next_match, model)
        return df_predicted_gain

    def evaluate_model(self):
        # Get stats and test
        df_stats = self._get_season_stats_with_injuries()
        scores = np.zeros(10)
        dates = df_stats.sort_values('date').date.unique()
        for i, date in enumerate(dates[-10:]):
            df_train = df_stats[(df_stats.date < date) & (pd.isna(df_stats.status))].copy()
            df_test = df_stats[(df_stats.date == date) & (df_stats.name.isin(df_train.name.unique()))].copy()

            # Evaluate model
            model = self._fit_model_gain(df_train)
            df_test = self._predict_gain(df_test, model)
            df_test = df_test[['name', 'fanta_value', 'fanta_gain', 'predicted_gain']]
            scores[i] = df_test.iloc[:20, 2].mean()
            print(f'{pd.to_datetime(date): %Y-%m-%d} score: {scores[i]: .4f}')
        print(f'      TOTAL score: {np.sum(scores): .4f}: ')

    def update_get_predicted_gain(self) -> pd.DataFrame:
        """Predicts and saves the fantabasket gain for next match ."""
        file_path = os.path.join(self._data_dir, PREDICTED_GAIN_FILE)
        df_predicted_gain = self._compute_predicted_gain()
        df_predicted_gain.to_csv(file_path, index=False)
        return df_predicted_gain

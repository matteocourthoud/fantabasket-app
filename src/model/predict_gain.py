"""Predict fantabasket gain for the next match."""

import os
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from model.compute_fanta_stats import compute_fantabasket_gain

PLAYERS_FILE = 'players.csv'
GAMES_FILE = 'games.csv'
FANTABASKET_STATS_FILE = 'fantabasket_stats.csv'
PREDICTED_GAIN_FILE = 'predicted_gain.csv'
LINEUPS_FILE = "lineups.csv"
INJURIES_FILE = "injuries.csv"
CALENDAR_FILE = "calendar.csv"


def _get_season_stats_with_match_info(data_dir: str, season: int) -> pd.DataFrame:
    """Adds games information to df_stats"""
    df_fanta_stats = pd.read_csv(os.path.join(data_dir, FANTABASKET_STATS_FILE))
    df_games = pd.read_csv(os.path.join(data_dir, str(season), GAMES_FILE))

    df_stats = pd.merge(df_fanta_stats, df_games, on='game_id', how='left')
    df_stats['own_team'] = np.where(df_stats.win == 1, df_stats.winner, df_stats.loser)
    df_stats['opponent_team'] = np.where(df_stats.win == 1, df_stats.loser, df_stats.winner)
    return df_stats


def _get_season_stats_with_injuries(data_dir: str, season: int) -> pd.DataFrame:
    """Import stats data and information on the next match."""
    df_stats = _get_season_stats_with_match_info(data_dir=data_dir, season=season)
    df_stats['date'] = pd.to_datetime((df_stats['date']))
    df_injuries = pd.read_csv(os.path.join(data_dir, INJURIES_FILE))
    df_stats = pd.merge(df_stats, df_injuries, on='name', how='left')
    df_stats = df_stats.sort_values(['name', 'date'])
    return df_stats


def _get_next_match(data_dir: str, season: int) -> pd.DataFrame:
    """Imports dataframe with information on the next matches."""
    df_calendar = pd.read_csv(os.path.join(data_dir, str(season), CALENDAR_FILE))
    df_calendar['date'] = pd.to_datetime(df_calendar['date'])
    temp1 = df_calendar.rename(columns={'team_visitor': 'own_team', 'team_home': 'opponent_team'})
    temp2 = df_calendar.rename(columns={'team_visitor': 'opponent_team', 'team_home': 'own_team'})
    df = pd.concat([temp1, temp2], ignore_index=True)

    # Get first matchup for each "own_team"
    df = df.sort_values('date')
    df = df[df.date >= pd.to_datetime('today')]
    df = df.groupby('own_team', as_index=False)[['opponent_team']].first()
    return df


def _get_next_match_per_player(df_stats: pd.DataFrame, data_dir: str, season: int) -> pd.DataFrame:
    """Check next match for each player."""
    df_player_next_match = df_stats.groupby('name', as_index=False)[['start', 'fanta_value', 'own_team', 'status']].last()
    df_next_match = _get_next_match(data_dir=data_dir, season=season)
    df_player_next_match = pd.merge(df_player_next_match, df_next_match, on='own_team', how='left')
    return df_player_next_match


def _fit_model_gain(df: pd.DataFrame):
    """Predict gain in test data using model fit on train data."""
    # Selecting train and test data
    df_train = df.copy()
    df_train['last_date'] = df_train.groupby('name')['date'].transform('max')
    days_from_last_date = 1.0 + (df_train['last_date'] - df_train['date']).dt.days.astype(float)
    df_train['weights'] = days_from_last_date ** (-1)
    model = smf.wls('fanta_score ~ -1 + C(name) + C(opponent_team) + start', df_train, weights=df_train.weights).fit()
    return model


def _predict_gain(df: pd.DataFrame, model):
    """Predict gain in test data using model fit on train data."""
    df_test = df.copy()
    predictions = model.get_prediction(df_test)
    df_test['predicted_score'] = predictions.predicted_mean - 1*(predictions.se_mean - predictions.se_mean.mean())
    df_test['predicted_gain'] = [compute_fantabasket_gain(v, s) for (v, s) in zip(df_test.fanta_value, df_test.predicted_score)]
    df_test.loc[~pd.isna(df_test.status), 'predicted_gain'] = -0.1
    df_test = df_test.sort_values('predicted_gain', ascending=False)
    df_test = df_test[['name', 'predicted_gain', 'predicted_score', 'fanta_value', 'start', 'status']]
    return df_test


def _compute_predicted_gain(data_dir: str, season: int) -> pd.DataFrame:
    df_stats = _get_season_stats_with_injuries(data_dir=data_dir, season=season)
    df_next_match = _get_next_match_per_player(df_stats=df_stats, data_dir=data_dir, season=season)
    model = _fit_model_gain(df=df_stats)
    df_predicted_gain = _predict_gain(df_next_match, model)
    return df_predicted_gain


def update_get_predicted_gain(data_dir: str, season: int) -> pd.DataFrame:
    """Predicts and saves the fantabasket gain for next match ."""
    file_path = os.path.join(data_dir, PREDICTED_GAIN_FILE)
    df_predicted_gain = _compute_predicted_gain(data_dir=data_dir, season=season)
    df_predicted_gain.to_csv(file_path, index=False)
    return df_predicted_gain

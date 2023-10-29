"""
Predict players for Fantabasket.
Author: Matteo Courthoud
Date: 22/10/2022
"""
import os.path
import numpy as np
import pandas as pd

PLAYERS_FILE = 'players.csv'
GAMES_FILE = 'games.csv'
STATS_FILE = 'stats.csv'
CURRENT_STATS_FILE = 'current_stats.csv'


def compute_fantabasket_gain(old_value: float, score: float) -> float:
    """Function from backward_induct_gain_formula."""
    if np.isnan(score):
        return -0.1
    return 0.025 * score - 0.045 * old_value


def _compute_fantabasket_score(df: pd.DataFrame) -> pd.Series:
    fanta_score = (1 * df['pts'] + 1 * df['drb'] + 1.25 * df['orb'] + 1.5 * df['ast'] + 1.5 * df['stl'] + 1.5 * df['blk'] +
                   1 * df['start'] - 1 * (df['fga'] - df['fg']) - 1 * (df['fta'] - df['ft']) - 1.5 * df['tov'] +
                   5 * ((df['pts'] > 9) & (df['ast'] > 9)) + 5 * ((df['pts'] > 9) & (df['trb'] > 9)) - 5 * (df['pf'] > 5) +
                   3 * (df['3p'] > 2) + 1 * (df['3p'] > 3) + 1 * (df['3p'] > 4)) * (1 + 0.05 * df['win'])
    return fanta_score


class FantabasketStats:

    def __init__(self, data_dir: str, season: int, df_stats: pd.DataFrame):
        self._data_dir = data_dir
        self._season = season
        self._df_stats = df_stats

    def _init_fantabasket_values(self, past_season_stats_file: str) -> pd.DataFrame:
        df_past_season = pd.read_csv(past_season_stats_file)
        df_past_season['fanta_score'] = _compute_fantabasket_score(df_past_season)
        df_values = df_past_season.groupby('name', as_index=False).agg(fanta_value=('fanta_score', 'mean'))
        df_values['fanta_value'] = np.maximum(df_values['fanta_value'] / 2, 4).fillna(4)
        return df_values

    def _compute_player_value(self, df_player: pd.DataFrame):
        for i in range(len(df_player)):  # TODO: loop over dates increasing
            # If player has no initial value, replace it with half the first score
            fanta_score = df_player.iloc[i, 2]  # TODO: move to loc
            if np.isnan(df_player.iloc[i, 3]):
                if np.isnan(fanta_score):
                    df_player.iloc[i, 3] = 4
                else:
                    df_player.iloc[i, 3] = fanta_score / 2
            fanta_value = df_player.iloc[i, 3]
            df_player.iloc[i, 4] = compute_fantabasket_gain(fanta_value, fanta_score)
            df_player.iloc[i, 3] = max(fanta_value + df_player.iloc[i, 4], 4)
            if (i + 1) < len(df_player):
                df_player.iloc[i + 1, 3] = df_player.iloc[i, 3]
        return df_player

    def _compute_season_stats(self, past_season_stats_file: str) -> pd.DataFrame:
        # Get players values
        df_values = self._init_fantabasket_values(past_season_stats_file)
        df_current_stats = self._df_stats
        df_current_stats['fanta_score'] = _compute_fantabasket_score(df_current_stats)
        df_current_stats = pd.merge(df_current_stats, df_values, on='name', how='left').sort_values('game_id')

        # Compute value and gains
        df_current_stats['fanta_gain'] = 0.0
        cols = ['name', 'game_id', 'fanta_score', 'fanta_value', 'fanta_gain']
        for player in df_current_stats['name'].unique():
            df_current_stats.loc[df_current_stats['name'] == player, cols] = self._compute_player_value(
                df_current_stats.loc[df_current_stats['name'] == player, cols])
        return df_current_stats

    def update_get_fantabasket_stats(self) -> pd.DataFrame:
        """Computes and saves current season NBA statistics and fantabasket scores."""
        past_season_stats_file = os.path.join(self._data_dir, str(self._season - 1), STATS_FILE)
        df_stats = self._compute_season_stats(past_season_stats_file)
        df_stats.to_csv(os.path.join(self._data_dir, CURRENT_STATS_FILE), index=False)
        return df_stats

    def load_df(self, file_name):
        file_path = os.path.join(self._data_dir, str(self._season), file_name)
        df = pd.read_csv(file_path)
        return df

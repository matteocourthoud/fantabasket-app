"""Dashboard Utilities."""
import os
from datetime import datetime

import pandas as pd

PLAYERS_FILE = 'players.csv'
GAMES_FILE = 'games.csv'
FANTABASKET_STATS_FILE = 'fantabasket_stats.csv'
PREDICTED_GAIN_FILE = 'predicted_gain.csv'


def get_fantabasket_stats(data_dir: str, season: int) -> pd.DataFrame:
    """Gets dataset with fantabasket statistics, with game dates."""
    df_fanta_stats = pd.read_csv(os.path.join(data_dir, FANTABASKET_STATS_FILE))

    # Add game dates to df_fanta_stats
    games_path = os.path.join(data_dir, str(season), GAMES_FILE)
    df_dates = pd.read_csv(games_path)[['date', 'game_id']].drop_duplicates()
    df_dates['date'] = pd.to_datetime(df_dates['date'])
    df_fanta_stats = pd.merge(df_fanta_stats, df_dates, on='game_id', how='right')

    # Add time delta for filtering
    df_fanta_stats['time_delta'] = (datetime.today() - df_fanta_stats.date).dt.days

    # Add last price and gain
    df_fanta_stats['last_price'] = df_fanta_stats.groupby('name')['fanta_value'].transform('last')

    # Add predicted fantabasket gain
    df_gain = pd.read_csv(os.path.join(data_dir, PREDICTED_GAIN_FILE))[['name', 'predicted_gain', 'status']]
    df = pd.merge(df_fanta_stats, df_gain, on='name', how='left')
    df['status'] = df['status'].fillna('')
    return df_fanta_stats


def get_players_last_stats(data_dir: str, season: int) -> pd.DataFrame:
    """Gets player stats from the last game."""
    df_fanta_stats = get_fantabasket_stats(data_dir=data_dir, season=season)

    # Select the last game for each player
    df_last_dates = df_fanta_stats.groupby("name", as_index=False)["date"].max()
    df_last_stats = pd.merge(df_fanta_stats, df_last_dates, on=["name", "date"], how="inner")

    # Add players positions to df_fanta_stats
    players_path = os.path.join(data_dir, PLAYERS_FILE)
    df_last_stats = pd.merge(df_last_stats, pd.read_csv(players_path), on='name', how='left')
    return df_last_stats


def get_df_timeseries_plot(data_dir: str, season: int) -> pd.DataFrame:
    """Gets dataframe for time series plot in the dashboard."""
    df_ts_plot = get_fantabasket_stats(data_dir=data_dir, season=season)
    df_ts_plot['name'] = df_ts_plot['name'] + ' - ' + df_ts_plot['last_price'].apply(lambda x: '{0:.1f}'.format(x))
    return df_ts_plot


def get_df_stats_table(data_dir: str, season: int) -> pd.DataFrame:
    """Gets dataframe for statistics table in the dashboard."""
    df_stats_table = get_players_last_stats(data_dir=data_dir, season=season)
    df_stats_table['last_date'] = df_stats_table.groupby('name')['date'].transform('max')
    df_stats_table = df_stats_table[df_stats_table.date == df_stats_table.last_date]
    df_stats_table = df_stats_table[df_stats_table.date >= (pd.Timestamp.now().normalize() - pd.Timedelta(3, 'd'))]
    df_stats_table = df_stats_table[['name', 'position', 'fanta_value', 'fanta_score', 'fanta_gain',
                       'mp', 'pts', 'trb', 'ast', 'stl', 'blk', 'tov', 'pf']]
    df_stats_table.columns = ['Name', 'Role', 'Value', 'Score', 'Gain',
                       'min', 'pts', 'trb', 'ast', 'stl', 'blk', 'tov', 'pf']
    df_stats_table = df_stats_table.sort_values('Gain', ascending=False).reset_index(drop=True).round(1)
    return df_stats_table

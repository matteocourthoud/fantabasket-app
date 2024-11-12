"""Dashboard Utilities."""
import os
from datetime import datetime

import numpy as np
import pandas as pd

PLAYERS_FILE = 'players.csv'
GAMES_FILE = 'games.csv'
FANTABASKET_STATS_FILE = 'fantabasket_stats.csv'
PREDICTED_GAIN_FILE = 'predicted_gain.csv'
LINEUPS_FILE = "lineups.csv"


def add_game_dates_and_teams_to_stats(df_stats: pd.DataFrame, data_dir: str, season: int) -> pd.DataFrame:
    """Add game dates and teams to df_fanta_stats."""
    # Merge games file to stats file
    file_path = os.path.join(data_dir, str(season), GAMES_FILE)
    df_games = pd.read_csv(file_path).drop_duplicates()
    df_games['date'] = pd.to_datetime(df_games['date'])
    df_stats = pd.merge(df_stats, df_games, on='game_id', how='right')

    # Compute winner and loser
    df_stats['own_team'] = np.where(df_stats.win == 1, df_stats.winner, df_stats.loser)
    df_stats['opponent_team'] = np.where(df_stats.win == 1, df_stats.loser, df_stats.winner)
    df_stats = df_stats.drop(columns=["winner", "lower", "pts_winner", "pts_loser"])
    return df_stats


def add_teams_to_stats(df_stats: pd.DataFrame, data_dir: str, season: int) -> pd.DataFrame:
    """Add game dates to df_fanta_stats."""
    file_path = os.path.join(data_dir, str(season), GAMES_FILE)
    df_games = pd.read_csv(file_path).drop_duplicates()
    df_games['date'] = pd.to_datetime(df_games['date'])
    df_stats = pd.merge(df_stats, df_games, on='game_id', how='right')
    return df_stats


def get_fantabasket_stats(data_dir: str, season: int) -> pd.DataFrame:
    """Gets dataset with fantabasket statistics, with game dates."""
    df_fanta_stats = pd.read_csv(os.path.join(data_dir, FANTABASKET_STATS_FILE))

    # Add game dates to stats
    df_fanta_stats = add_game_dates_and_teams_to_stats(df_stats=df_fanta_stats, data_dir=data_dir, season=season)

    # Add time delta for filtering
    df_fanta_stats['time_delta'] = (datetime.today() - df_fanta_stats.date).dt.days

    # Add last price and gain
    df_fanta_stats['last_price'] = df_fanta_stats.groupby('name')['fanta_value'].transform('last')

    # Add predicted fantabasket gain
    df_gain = pd.read_csv(os.path.join(data_dir, PREDICTED_GAIN_FILE))[['name', 'predicted_gain', 'status']]
    df_fanta_stats = pd.merge(df_fanta_stats, df_gain, on='name', how='left')
    df_fanta_stats['status'] = df_fanta_stats['status'].fillna('')
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


def get_df_status_changes(data_dir: str, season: int) -> pd.DataFrame:
    """Get data on players whose status changes between the last match and the next."""
    # Get the last player status
    df_last_status = get_players_last_stats(data_dir=data_dir, season=season)
    df_last_status = df_last_status[df_last_status.time_delta < 4]
    df_last_status = df_last_status[["name", "start"]]
    df_last_status = df_last_status.rename(columns={"start": "start_last"})

    # Get the next player status
    df_next_status = pd.read_csv(os.path.join(data_dir, LINEUPS_FILE))[["name"]]
    df_next_status["start_next"] = 1

    # Get only players whose status has changes
    df_status_changes = pd.merge(df_last_status, df_next_status, on="name", how="left")
    df_status_changes["start_next"] = df_status_changes["start_next"].fillna(0).astype(int)
    df_status_changes = df_status_changes[df_status_changes.start_last != df_status_changes.start_next]

    # Add players positions to df_fanta_stats
    players_path = os.path.join(data_dir, PLAYERS_FILE)
    df_positions = pd.read_csv(players_path)[["name", "position"]]
    df_status_changes = pd.merge(df_status_changes, df_positions, on='name', how='left')
    return df_status_changes

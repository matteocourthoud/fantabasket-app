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
INJURIES_FILE = "injuries.csv"


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
    df_stats = df_stats.drop(columns=["winner", "loser", "pts_winner", "pts_loser"])
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
    df_players = pd.read_csv(os.path.join(data_dir, PLAYERS_FILE))[["name", "position"]]
    df_ts_plot = pd.merge(df_ts_plot, df_players, on='name', how='left')
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
    df_status_changes["status_change"] = df_status_changes["start_next"] - df_status_changes["start_last"]
    return df_status_changes


def get_substitute_players(df: pd.DataFrame) -> pd.DataFrame:
    """For each player, computes the player with highest and lowest minute correlation."""
    for col in ["name", "game_id", "mp", "own_team"]:
        assert col in df.columns, f"Column {col} not found!"

    df_players = pd.DataFrame()
    for team in df.own_team.unique():
        # Get table of minutes correlation within each team
        df_team = df[df.own_team == team].copy()
        df_team = df_team.pivot(index="game_id", columns="name", values="mp").fillna(0)
        df_team.columns = [''.join(col).strip() for col in df_team.columns]
        minute_correlations = df_team.corr().fillna(0).values
        minute_correlations[minute_correlations == 1] = 0

        # Extract players with highest and lowest minute correlation
        players = np.array(df_team.columns)
        temp = pd.DataFrame({
            "name": players,
            "first_substitute": players[minute_correlations.argmin(axis=1)],
            "first_complement": players[minute_correlations.argmax(axis=1)],
        })
        df_players = pd.concat([df_players, temp], ignore_index=True)
    return df_players


def compute_streak(df: pd.DataFrame) -> pd.DataFrame:
    """Computes fantabasket streak"""
    for col in ["name", "date", "fanta_gain"]:
        assert col in df.columns, f"Column {col} not found!"

    # Define streak function
    def compute_streak_by_group(group: pd.Series) -> pd.Series:
        group['streak'] = (group["fanta_gain"] > 0).astype(int)
        group['streak'] = group['streak'] * (
                    group['streak'].cumsum() - group['streak'].cumsum().where(group['streak'] == 0).ffill().fillna(
                0)).astype(int)
        return group

    # Compute streak for each customer
    df = df.sort_values(["name", "date"], ascending=True)
    df = df.groupby("name", group_keys=False).apply(compute_streak_by_group)
    return df


def add_starters(df: pd.DataFrame, data_dir: str) -> pd.DataFrame:
    """Adds the injury status to each player."""
    df_lineups = pd.read_csv(os.path.join(data_dir, LINEUPS_FILE)).rename(columns={"status": "inj_status"})
    df_lineups["start"] = 1
    df = pd.merge(df, df_lineups[["name", "inj_status", "start"]], on='name', how='left')
    df["start"] = df["start"].fillna(0)
    df.loc[df.status.isna(), "status"] = df.loc[df.status.isna(), "inj_status"]
    df = df.drop(columns=["inj_status"])
    return df


def get_df_table(data_dir: str, season: int) -> pd.DataFrame:
    """Gets data to show in table in dashboard."""
    df_fanta_stats = get_fantabasket_stats(data_dir=data_dir, season=season)

    # Compute streak
    df_fanta_stats = compute_streak(df_fanta_stats)

    # Select the last game for each player
    df_table = df_fanta_stats.groupby("name", as_index=False)["date"].max()
    df_table = pd.merge(df_fanta_stats, df_table, on=["name", "date"], how="inner")
    df_table = df_table[["name", "last_price", "predicted_gain", "streak", "opponent_team"]]

    # Add status changes
    df_status_changes = get_df_status_changes(data_dir=data_dir, season=season)
    df_table = pd.merge(df_table, df_status_changes[["name", "status_change"]], on='name', how='left')

    # Add injuries
    df_injuries = pd.read_csv(os.path.join(data_dir, INJURIES_FILE))
    df_table = pd.merge(df_table, df_injuries[["name", "status"]], on='name', how='left')

    # Add starters
    df_table = add_starters(df=df_table, data_dir=data_dir)

    # Add main substitute
    df_substitutes = get_substitute_players(df=df_fanta_stats)
    df_table = pd.merge(df_table, df_substitutes[["name", "first_substitute"]], on='name', how='left')

    # Add players positions to df_fanta_stats
    df_players = pd.read_csv(os.path.join(data_dir, "players.csv"))
    df_table = pd.merge(df_table, df_players[["name", "position"]], on='name', how='left')

    # Clean table
    df_table = df_table[["name", "position", "last_price", "predicted_gain", "streak", "status", "start", "status_change", "first_substitute", "opponent_team"]]
    df_table.columns = ["Name", "Role", "Value", "Gain", "Streak", "Injury", "Start", "Change", "Substitute", "Opponent"]
    df_table = df_table.sort_values("Gain", ascending=False).reset_index(drop=True)
    df_table["Value"] = df_table["Value"].round(1)
    df_table["Gain"] = df_table["Gain"].round(2)
    return df_table

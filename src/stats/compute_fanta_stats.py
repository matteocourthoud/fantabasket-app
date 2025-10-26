"""Compute Fantabasket statistics from NBA statistics."""

import os.path

import numpy as np
import pandas as pd

STATS_FILE = "stats.csv"
PLAYERS_FILE = "players.csv"
INITIAL_VALUES_FILE = "initial_ratings.csv"
FANTABASKET_STATS_FILE = "fantabasket_stats.csv"


def compute_fantabasket_gain(old_value: float, score: float) -> float:
    """Update player value, from previous value and current performance."""
    if np.isnan(score):
        return -0.1
    return 0.025 * score - 0.045 * old_value


def _compute_fantabasket_score(df: pd.DataFrame) -> pd.Series:
    """Source: https://docs.dunkest.com/v/rules-en/fantasy/player-scoring."""
    fanta_score = (
            (1 * df["pts"]
             + 1 * df["drb"]
             + 1.25 * df["orb"]
             + 1.5 * df["ast"]
             + 1.5 * df["stl"]
             - 1.5 * df["tov"]
             + 1.5 * df["blk"]
             + 5 * ((df["pts"] >= 10) & (df["ast"] >= 10))
             + 5 * ((df["pts"] >= 10) & (df["trb"] >= 10))
             + 1 * df["start"]
             + 3 * (df["3p"] >= 3)
             + 1 * (df["3p"] >= 4)
             + 1 * (df["3p"] >= 5)
             - 1 * (df["fga"] - df["fg"])
             - 1 * (df["fta"] - df["ft"])
             - 5 * (df["pf"] > 5)  # TODO: check if the fouled-out malus is still there
             )
            * (1 + 0.05 * df["win"]))
    return fanta_score


def _init_fantabasket_values(past_season_stats_file: str) -> pd.DataFrame:
    """Initializes the fantabasket values at the beginning of the season."""
    df_past_season = pd.read_csv(past_season_stats_file)
    df_past_season["fanta_score"] = _compute_fantabasket_score(df_past_season)
    df_values = df_past_season.groupby("name", as_index=False).agg(fanta_value=("fanta_score", "mean"))
    df_values["fanta_value"] = np.maximum(df_values["fanta_value"] / 2, 4).fillna(4)
    return df_values


def _load_initial_fantabasket_values(data_dir: str, season: int) -> pd.DataFrame:
    # Load initial values
    df_initial_values = pd.read_csv(os.path.join(data_dir, str(season), INITIAL_VALUES_FILE))
    assert not df_initial_values.duplicated().any(), f"Duplicated rows in {INITIAL_VALUES_FILE}."

    # Load players
    df_players = pd.read_csv(os.path.join(data_dir, PLAYERS_FILE))
    assert not df_players.duplicated().any(), f"Duplicated rows in {PLAYERS_FILE}."

    # Merge datasets
    df_initial_values = pd.merge(df_initial_values, df_players, on="name_short", how="inner")
    df_initial_values = df_initial_values.rename(columns={"initial_rating": "fanta_value"})
    return df_initial_values[["name", "fanta_value"]]


def _compute_player_value(df_player: pd.DataFrame) -> pd.DataFrame:
    """Computes players Fantabasket value given the initial values and players' performance."""
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


def _compute_fantabasket_stats(data_dir: str, season: int, df_stats: pd.DataFrame) -> pd.DataFrame:
    """Computes Fantabasket statistics in the current season: value, score and gain over games."""
    # Get players values
    df_values = _load_initial_fantabasket_values(data_dir=data_dir, season=season)
    df_fanta_stats = df_stats.copy()
    df_fanta_stats["fanta_score"] = _compute_fantabasket_score(df_fanta_stats)
    df_fanta_stats = pd.merge(df_fanta_stats, df_values, on="name", how="left").sort_values("game_id")

    # Compute value and gains
    df_fanta_stats["fanta_gain"] = 0.0
    cols = ["name", "game_id", "fanta_score", "fanta_value", "fanta_gain"]
    for player in df_fanta_stats["name"].unique():
        df_fanta_stats.loc[df_fanta_stats["name"] == player, cols] = _compute_player_value(
            df_fanta_stats.loc[df_fanta_stats["name"] == player, cols])
    return df_fanta_stats


def update_get_fantabasket_stats(data_dir: str, season: int, df_stats: pd.DataFrame, save: bool = True) -> pd.DataFrame:
    """Computes and saves current season NBA statistics and Fantabasket scores."""
    df_fanta_stats = _compute_fantabasket_stats(data_dir=data_dir, season=season, df_stats=df_stats)
    assert not df_fanta_stats.duplicated().any(), "Duplicated values in fantabasket stats final table."
    if save:
        df_fanta_stats.to_csv(os.path.join(data_dir, FANTABASKET_STATS_FILE), index=False)
    return df_fanta_stats

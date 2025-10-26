"""Compute Fantabasket statistics from NBA statistics."""

import os
import sys

import pandas as pd

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.scraping.utils import get_current_season
from src.supabase.table_names import (
    FANTA_STATS_TABLE,
    INITIAL_RATINGS_TABLE,
    PLAYERS_TABLE,
    STATS_TABLE,
)
from src.supabase.utils import load_dataframe_from_supabase, save_dataframe_to_supabase


def _compute_fanta_score(df: pd.DataFrame) -> pd.Series:
    """Computes the Dunkest score for each game."""
    # Convert boolean 'start' and 'win' columns to integer for calculations
    df["start"] = df["start"].astype(int)
    df["win"] = df["win"].astype(int)

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
         + 3 * (df["three_p"] >= 3)
         + 1 * (df["three_p"] >= 4)
         + 1 * (df["three_p"] >= 5)
         - 1 * (df["fga"] - df["fg"])
         - 1 * (df["fta"] - df["ft"])
         - 5 * (df["pf"] > 5)
         )
        * (1 + 0.05 * df["win"])
    )
    return fanta_score


def _compute_gain(value_before: float, score: float) -> float:
    """Computes the gain in value after a game."""
    if pd.isna(score):
        return -0.1
    return 0.025 * score - 0.045 * value_before


def _compute_player_fanta_stats(player_games: pd.DataFrame) -> pd.DataFrame:
    """Computes fanta stats for a single player's games, iterating chronologically."""
    player_games = player_games.sort_values("date")

    # Get the first valid initial rating for the player
    initial_rating = player_games["initial_rating"].first_valid_value()

    value_before = initial_rating
    # If no initial rating is found, use a default based on the first game's score
    if pd.isna(value_before):
        first_score = player_games["fanta_score"].iloc[0]
        value_before = first_score / 2 if not pd.isna(first_score) else 4.0

    fanta_stats_list = []
    for _, game in player_games.iterrows():
        score = game["fanta_score"]
        gain = _compute_gain(value_before, score)
        value_after = max(value_before + gain, 4.0)

        game_stats = game.to_dict()
        game_stats["value_before"] = value_before
        game_stats["gain"] = gain
        game_stats["value_after"] = value_after
        fanta_stats_list.append(game_stats)

        # The current game's 'value_after' becomes the next game's 'value_before'
        value_before = value_after

    return pd.DataFrame(fanta_stats_list)


def compute_fanta_stats(season: int = None) -> None:
    """Computes and saves fantabasket stats (value_before, value_after, gain) for a given season.
    The results are saved to the 'fanta_stats' table in Supabase.
    """
    if season is None:
        season = get_current_season()

    print(f"Computing fanta stats for season {season}...")

    # Load required data from Supabase
    stats_df = load_dataframe_from_supabase(STATS_TABLE, filters={"season": season})
    initial_ratings_df = load_dataframe_from_supabase(INITIAL_RATINGS_TABLE, filters={"season": season})
    players_df = load_dataframe_from_supabase(PLAYERS_TABLE)

    # Merge player names with initial ratings
    initial_ratings_df = pd.merge(
        initial_ratings_df,
        players_df[["name", "name_short"]],
        left_on="player_short",
        right_on="name_short",
        how="inner",
    )

    # Merge stats with initial ratings to get a starting value for each player
    df = pd.merge(
        stats_df,
        initial_ratings_df[["name", "initial_rating"]],
        left_on="player",
        right_on="name",
        how="left",
    )

    # Compute fanta_score for each game
    df["fanta_score"] = _compute_fanta_score(df)

    # Compute fanta stats for each player
    all_fanta_stats = df.groupby("player").apply(_compute_player_fanta_stats).reset_index(drop=True)

    # Clean up columns before saving
    all_fanta_stats = all_fanta_stats.drop(columns=["initial_rating", "name"])

    print(f"Computed fanta stats for {len(all_fanta_stats)} games.")

    # Save the computed stats to the new 'fanta_stats' table
    print(f"Saving fanta stats to Supabase table: {FANTA_STATS_TABLE}...")
    save_dataframe_to_supabase(
        df=all_fanta_stats,
        table_name=FANTA_STATS_TABLE,
        index_columns=["game_id", "player"],
        upsert=True,
    )
    print("Fanta stats computation and saving complete.")

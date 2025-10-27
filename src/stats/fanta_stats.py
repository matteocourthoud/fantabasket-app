"""Compute Fantabasket statistics from NBA statistics."""

import pandas as pd

from src.scraping.utils import get_current_season
from src.supabase.table_names import (
    FANTA_STATS_TABLE,
    GAMES_TABLE,
    INITIAL_VALUES_TABLE,
    PLAYERS_TABLE,
    STATS_TABLE,
)
from src.supabase.utils import load_dataframe_from_supabase, save_dataframe_to_supabase


def _compute_fanta_score(df: pd.DataFrame) -> pd.Series:
    """Computes the Dunkest score for each game.
    Source: https://docs.dunkest.com/v/rules-en/fantasy/player-scoring
    """
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
         + 3 * (df["tp"] >= 3)
         + 1 * (df["tp"] >= 4)
         + 1 * (df["tp"] >= 5)
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
    else:
        return 0.025 * score - 0.045 * value_before


def _compute_player_fanta_stats(player_games: pd.DataFrame, initial_value: float = None) -> pd.DataFrame:
    """Computes fanta stats for a single player's games, iterating chronologically.
    
    Args:
        player_games: DataFrame with all games for one player
        initial_value: Initial value for the player (from initial_values table)
        
    Returns:
        DataFrame with value_before, fanta_score, gain, and value_after for each game
    """
    player_games = player_games.sort_values("date")

    # Set initial value
    if pd.isna(initial_value):
        # If no initial value, use half of first score or default 4.0
        first_score = player_games["fanta_score"].iloc[0]
        value_before = first_score / 2 if not pd.isna(first_score) else 4.0
    else:
        value_before = initial_value

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
    
    For each player and each match in the stats table:
    - value_before: Player's value before the match
    - fanta_score: Score calculated from the match stats
    - gain: Change in value based on performance
    - value_after: Player's value after the match
    
    The initial value_before for the first match comes from the initial_values table.
    
    Args:
        season: Season to compute stats for (defaults to current season)
    """
    if season is None:
        season = get_current_season()

    print(f"Computing fanta stats for season {season}...")

    # Load required data from Supabase
    stats_df = load_dataframe_from_supabase(STATS_TABLE, {"season": season})
    games_df = load_dataframe_from_supabase(GAMES_TABLE, {"season": season})
    initial_values_df = load_dataframe_from_supabase(INITIAL_VALUES_TABLE, {"season": season})
    players_df = load_dataframe_from_supabase(PLAYERS_TABLE)

    # Merge stats with game dates
    stats_df = pd.merge(
        stats_df,
        games_df[["game_id", "date"]],
        on="game_id",
        how="left"
    )

    # Merge stats with players to get fanta_player_id
    stats_df = pd.merge(
        stats_df,
        players_df[["player", "fanta_player_id"]],
        on="player",
        how="left"
    )

    # Merge with initial values
    stats_df = pd.merge(
        stats_df,
        initial_values_df[["fanta_player_id", "initial_value"]],
        on="fanta_player_id",
        how="left"
    )

    # Compute fanta_score for each game
    print("  Computing fanta scores...")
    stats_df["fanta_score"] = _compute_fanta_score(stats_df)

    # Compute fanta stats for each player
    print("  Computing values and gains for each player...")
    all_fanta_stats = []
    
    for player in stats_df["player"].unique():
        player_games = stats_df[stats_df["player"] == player].copy()
        initial_value = player_games["initial_value"].iloc[0]
        player_fanta_stats = _compute_player_fanta_stats(player_games, initial_value)
        all_fanta_stats.append(player_fanta_stats)
    
    all_fanta_stats = pd.concat(all_fanta_stats, ignore_index=True)

    # Add season column
    all_fanta_stats["season"] = season

    # Select final columns
    final_cols = [
        "game_id", "player", "fanta_score", "value_before", "gain", "value_after", "season"
    ]
    all_fanta_stats = all_fanta_stats[final_cols]

    print(f"  ✓ Computed fanta stats for {len(all_fanta_stats)} games")

    # Save the computed stats to the fanta_stats table
    save_dataframe_to_supabase(
        df=all_fanta_stats,
        table_name=FANTA_STATS_TABLE,
        index_columns=["game_id", "player"],
        replace=True,
    )
    
    print(f"✓ Fanta stats saved for season {season}!")


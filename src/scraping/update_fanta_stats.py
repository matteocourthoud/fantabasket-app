"""Compute Fantabasket statistics from NBA statistics."""

import pandas as pd

from src.database.tables import (
    TABLE_FANTA_STATS,
    TABLE_GAME_RESULTS,
    TABLE_INITIAL_VALUES,
    TABLE_PLAYERS,
    TABLE_STATS,
    TABLE_TEAMS,
)
from src.database.utils import load_dataframe_from_supabase, save_dataframe_to_supabase
from src.scraping.utils import get_current_season


def _add_missing_player_games(stats_df: pd.DataFrame) -> pd.DataFrame:
    """Adds rows for players who didn't play a game (missing from stats_df)."""
    # Get the list of all players and their teams
    cols_player = ['player', 'team', 'player_id']
    df_players = stats_df[cols_player].drop_duplicates()

    # Get the list of all game_id and team combinations
    cols_games = ['game_id', 'team', 'team_winner', 'team_loser', 'win', 'date', 'season']
    df_games = stats_df[cols_games].drop_duplicates()

    # Merge players with games by team to get all player-game_id combinations
    all_combinations = pd.merge(df_players, df_games, on='team')

    # Identify missing player-game_id combinations
    existing_combinations = stats_df[['player', 'game_id']]
    missing_combinations = pd.merge(
        all_combinations,
        existing_combinations,
        on=['player', 'game_id'],
        how='left',
        indicator=True
    )
    missing_combinations = missing_combinations[missing_combinations['_merge'] == 'left_only']
    missing_combinations = missing_combinations.drop(columns=['_merge'])

    # Concatenate the missing rows with the original stats_df
    updated_stats_df = pd.concat([stats_df, missing_combinations], ignore_index=True)
    updated_stats_df = (
        updated_stats_df.
        sort_values(['player', 'game_id'])
        .reset_index(drop=True)
        .fillna(0)
    )
    
    # Convert column types to original types in stats_df
    for col in stats_df.columns:
        if col in updated_stats_df.columns:
            updated_stats_df[col] = updated_stats_df[col].astype(stats_df[col].dtype)

    return updated_stats_df


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
    if pd.isna(score) or (score == 0):
        return -0.1
    else:
        return 0.025 * score - 0.045 * value_before


def _compute_player_fanta_stats(
    player_games: pd.DataFrame,
    initial_value: float = None,
) -> pd.DataFrame:
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


def update_fanta_stats(season: int = None) -> None:
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
    stats_df = load_dataframe_from_supabase(TABLE_STATS.name, {"season": season})
    games_df = load_dataframe_from_supabase(TABLE_GAME_RESULTS.name, {"season": season})
    initial_values_df = load_dataframe_from_supabase(
        TABLE_INITIAL_VALUES.name, {"season": season}
    )
    players_df = load_dataframe_from_supabase(TABLE_PLAYERS.name)
    teams_df = load_dataframe_from_supabase(TABLE_TEAMS.name)
    
    # Add some extra stats
    stats_df["fg_pct"] = stats_df["fg"] / stats_df["fga"]
    stats_df["tp_pct"] = stats_df["tp"] / stats_df["tpa"]
    stats_df["ast_pct"] = stats_df["ast"] / (stats_df["ast"] + stats_df["tov"])

    # Merge stats with game info (date, team_winner, team_loser)
    stats_df = pd.merge(
        stats_df,
        games_df[["game_id", "date", "team_winner", "team_loser"]],
        on="game_id",
        how="left"
    )

    # Add team column: team = team_winner if win else team_loser
    stats_df["team"] = stats_df.apply(
        lambda row: row["team_winner"] if row["win"] else row["team_loser"],
        axis=1
    )
    
    # Add games for players who didn't play any game yet this season
    stats_df = _add_missing_player_games(stats_df)

    # Merge stats with players to get fanta_player_id
    stats_df = pd.merge(
        stats_df,
        players_df[["player", "fanta_player_id"]],
        on="player",
        how="left"
    )

    # Merge stats with teams to get fanta_team
    stats_df = pd.merge(
        stats_df,
        teams_df[["team", "fanta_team"]],
        on="team",
        how="left"
    )

    # Merge with initial values to get initial_value and position
    stats_df = pd.merge(
        stats_df,
        initial_values_df[["fanta_player_id", "initial_value", "position"]],
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
        
        # Ensure 'start' is boolean (already present from stats)
        player_fanta_stats = _compute_player_fanta_stats(player_games, initial_value)
        
        # Carry over 'start' and 'opponent_team' to the output
        all_fanta_stats.append(player_fanta_stats)
    
    all_fanta_stats = pd.concat(all_fanta_stats, ignore_index=True)

    # Add season column
    all_fanta_stats["season"] = season
    
    # Add opponent_team column
    all_fanta_stats["opponent_team"] = all_fanta_stats.apply(
        lambda row: (
            row["team_loser"] if row["team"] == row["team_winner"]
            else row["team_winner"]
        ),
        axis=1
    )

    # Drop players with missing position
    all_fanta_stats = all_fanta_stats.dropna(subset=["position"])

    # Select final columns
    final_cols = [
        "game_id", "player", "team", "fanta_team", "position", "fanta_score",
        "value_before", "gain", "value_after", "mp", "pts", "trb", "ast", "stl", "blk",
        "fg_pct", "tp_pct", "ast_pct", "start", "win", "opponent_team", "season",
    ]
    all_fanta_stats = all_fanta_stats[final_cols]

    print(f"  ✓ Computed fanta stats for {len(all_fanta_stats)} games")

    # Save the computed stats to the fanta_stats table
    save_dataframe_to_supabase(
        df=all_fanta_stats,
        table_name=TABLE_FANTA_STATS.name,
        index_columns=["game_id", "player"],
        replace=True,
    )
    
    print(f"✓ Fanta stats saved for season {season}!")


if __name__ == "__main__":
    update_fanta_stats()

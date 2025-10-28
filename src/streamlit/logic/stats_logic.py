"""Business logic for stats page - data loading and processing."""
import os
import sys

import pandas as pd


# Add the project root to the Python path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)

from src.supabase.tables import (  # noqa: E402
    TABLE_FANTA_STATS,
    TABLE_GAMES,
    TABLE_PLAYERS,
    TABLE_STATS,
    TABLE_TEAMS,
)
from src.supabase.utils import load_dataframe_from_supabase  # noqa: E402


def load_all_data(season: int) -> dict[str, pd.DataFrame]:
    """Load all required data for the stats page."""
    data = {
        "stats": load_dataframe_from_supabase(
            TABLE_STATS.name, filters={"season": season}
        ),
        "games": load_dataframe_from_supabase(
            TABLE_GAMES.name, filters={"season": season}
        ),
        "players": load_dataframe_from_supabase(TABLE_PLAYERS.name),
        "initial_values": load_dataframe_from_supabase(
            "initial_values", filters={"season": season}
        ),
        "fanta_stats": load_dataframe_from_supabase(TABLE_FANTA_STATS.name),
        "teams": load_dataframe_from_supabase(TABLE_TEAMS.name),
    }
    return data


def merge_player_data(
    stats_df: pd.DataFrame, players_df: pd.DataFrame, initial_values_df: pd.DataFrame
) -> pd.DataFrame:
    """Merge stats with player and position information."""
    # Merge stats with players to get fanta_player_id
    stats_df = pd.merge(
        stats_df, players_df[["player", "fanta_player_id"]], on="player", how="left"
    )

    # Merge with initial values to get position
    stats_df = pd.merge(
        stats_df,
        initial_values_df[["fanta_player_id", "position"]],
        on="fanta_player_id",
        how="left",
    )

    # Drop the temporary fanta_player_id column
    stats_df = stats_df.drop(columns=["fanta_player_id"])

    return stats_df


def get_team_list(games_df: pd.DataFrame) -> list[str]:
    """
    Extract sorted list of all teams from games dataframe.

    Args:
        games_df: Games dataframe

    Returns:
        Sorted list of team names
    """
    return sorted(
        set(games_df["winner"].unique().tolist() + games_df["loser"].unique().tolist())
    )


def calculate_player_averages(
    stats_df: pd.DataFrame,
    position_filter: str | None = None,
    aggregation_method: str = "mean",
) -> pd.DataFrame:
    """
    Calculate aggregate statistics per player.

    Args:
        stats_df: Player statistics dataframe
        position_filter: Optional position to filter by
        aggregation_method: Aggregation method ('mean', 'sum', or 'median')

    Returns:
        Dataframe with aggregated stats per player
    """
    # Filter by position if specified
    if position_filter and position_filter != "All":
        stats_df = stats_df[stats_df["position"] == position_filter]

    # Group by player and position, calculate the aggregation of numeric stats
    numeric_cols = stats_df.select_dtypes(include="number").columns
    cols_to_exclude = ["game_id", "player_id", "season"]
    cols_to_agg = [col for col in numeric_cols if col not in cols_to_exclude]

    # Map aggregation method to pandas function name
    agg_mapping = {
        "average": "mean",
        "sum": "sum",
        "median": "median",
    }
    agg_func = agg_mapping.get(aggregation_method.lower(), "mean")

    # Group by player and position - calculate aggregation and count games
    player_avg_stats = (
        stats_df.groupby(["player", "position"])
        .agg({**{col: agg_func for col in cols_to_agg}, "game_id": "count"})
        .reset_index()
    )

    # Rename game_id count to games and convert to integer
    player_avg_stats = player_avg_stats.rename(columns={"game_id": "games"})
    player_avg_stats["games"] = player_avg_stats["games"].astype(int)

    return player_avg_stats


def get_player_teams(
    stats_df: pd.DataFrame, games_df: pd.DataFrame, teams_df: pd.DataFrame
) -> pd.DataFrame:
    """Get the current team for each player based on most recent game."""

    # Merge stats with games to get team info
    stats_with_games = pd.merge(
        stats_df[["player", "game_id", "win"]],
        games_df[["game_id", "date", "winner", "loser"]],
        on="game_id",
        how="left",
    )

    # Determine team based on win/loss
    stats_with_games["team"] = stats_with_games.apply(
        lambda row: row["winner"] if row["win"] else row["loser"], axis=1
    )

    # Get the last team for each player (most recent game)
    player_teams = (
        stats_with_games.sort_values("date")
        .groupby("player")["team"]
        .last()
        .reset_index()
    )

    # Map team names to team codes
    team_mapping = teams_df.set_index("team_short")["fanta_team"].to_dict()
    player_teams["team"] = player_teams["team"].map(team_mapping)

    return player_teams


def add_player_valuations(
    player_stats: pd.DataFrame, fanta_stats_df: pd.DataFrame
) -> pd.DataFrame:
    """Add current valuation and average gain to player stats."""
    # Get the most recent value_after for each player (current valuation)
    player_current_value = (
        fanta_stats_df.groupby("player")
        .agg(value=("value_after", "last"), gain=("gain", "mean"))
        .reset_index()
    )

    # Merge with player_stats
    player_stats = pd.merge(player_stats, player_current_value, on="player", how="left")

    return player_stats


def reorder_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Reorder columns to show priority columns first."""
    cols = df.columns.tolist()
    priority_cols = ["player", "team", "position", "games", "value", "gain"]
    other_cols = [col for col in cols if col not in priority_cols]
    return df[priority_cols + other_cols]


def apply_filters(
    df: pd.DataFrame,
    team: str | None = None,
    value_range: tuple[float, float] | None = None,
) -> pd.DataFrame:
    """Apply team and value range filters to dataframe."""
    # Filter by team if specified
    if team and team != "All":
        df = df[df["team"] == team]

    # Filter by value range if specified
    if value_range:
        df = df[(df["value"] >= value_range[0]) & (df["value"] <= value_range[1])]

    return df


def process_player_stats(
    stats_df: pd.DataFrame,
    games_df: pd.DataFrame,
    fanta_stats_df: pd.DataFrame,
    teams_df: pd.DataFrame,
    position_filter: str | None = None,
    team_filter: str | None = None,
    value_range: tuple[float, float] | None = None,
    aggregation_method: str = "mean",
) -> pd.DataFrame:
    """
    Complete processing pipeline for player statistics.

    Args:
        stats_df: Merged stats dataframe (with positions)
        games_df: Games dataframe
        fanta_stats_df: Fantasy stats dataframe
        teams_df: Teams dataframe with team codes
        position_filter: Optional position filter
        team_filter: Optional team filter
        value_range: Optional value range filter
        aggregation_method: Aggregation method ('mean', 'sum', or 'median')

    Returns:
        Fully processed and filtered player statistics
    """
    # Calculate averages
    player_stats = calculate_player_averages(
        stats_df, position_filter, aggregation_method
    )

    # Add team information
    player_teams = get_player_teams(stats_df, games_df, teams_df)
    player_stats = pd.merge(player_stats, player_teams, on="player", how="left")

    # Add valuations
    player_stats = add_player_valuations(player_stats, fanta_stats_df)

    # Reorder columns
    player_stats = reorder_columns(player_stats)

    # Apply filters
    player_stats = apply_filters(player_stats, team_filter, value_range)

    # Sort by value (descending)
    player_stats = player_stats.sort_values("value", ascending=False)

    return player_stats

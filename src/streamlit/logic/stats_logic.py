"""Business logic for stats page - data loading and processing."""

import pandas as pd

from src.scraping.utils import get_current_season
from src.supabase.tables import TABLE_FANTA_STATS
from src.supabase.utils import load_dataframe_from_supabase


def load_fanta_stats_data() -> dict[str, pd.DataFrame]:
    """Load only fanta_stats for the stats page."""
    season = get_current_season()
    
    return {
        "fanta_stats": load_dataframe_from_supabase(TABLE_FANTA_STATS.name, filters={"season": season})
    }


def get_team_list(fanta_stats_df: pd.DataFrame) -> list[str]:
    """Extract sorted list of all teams from fanta_stats dataframe."""
    return sorted(fanta_stats_df["fanta_team"].dropna().unique().tolist())


def calculate_player_aggregates(
    fanta_stats_df: pd.DataFrame,
    position_filter: str | None = None,
    aggregation_method: str = "mean",
) -> pd.DataFrame:
    """Calculate aggregate statistics per player from fanta_stats."""
    df = fanta_stats_df.copy()
    if position_filter and position_filter != "All":
        df = df[df["position"] == position_filter]

    # Identify numeric columns to aggregate
    numeric_cols = df.select_dtypes(include="number").columns

    player_avg_stats = (
        df.groupby(["player", "fanta_team", "position"])
        .agg({**{col: aggregation_method for col in numeric_cols},
              "game_id": "count",
              #"value_after": "last",
        })
        .reset_index()
    )
    player_avg_stats = player_avg_stats.rename(columns={
        "game_id": "games",
        "value_after": "value",
        "fanta_team": "team",
        })
    player_avg_stats["games"] = player_avg_stats["games"].astype(int)
    return player_avg_stats


def apply_filters(
    df: pd.DataFrame,
    team: str | None = None,
    value_range: tuple[float, float] | None = None,
) -> pd.DataFrame:
    """Apply team and value range filters to dataframe."""
    
    # Filter by team if specified
    if team and team != "All":
        df = df[df["fanta_team"] == team]

    # Filter by value range if specified
    if value_range:
        df = df[(df["value"] >= value_range[0]) & (df["value"] <= value_range[1])]

    return df


def process_player_stats(
    fanta_stats_df: pd.DataFrame,
    position_filter: str | None = None,
    team_filter: str | None = None,
    value_range: tuple[float, float] | None = None,
    aggregation_method: str = "mean",
) -> pd.DataFrame:
    """Complete processing pipeline for player statistics using only fanta_stats."""
    
    # Calculate averages
    player_stats = calculate_player_aggregates(
        fanta_stats_df, position_filter, aggregation_method
    )

    # Apply filters
    player_stats = apply_filters(player_stats, team_filter, value_range)

    # Sort by value (descending)
    player_stats = player_stats.sort_values("value", ascending=False)

    return player_stats

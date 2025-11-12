"""Business logic for stats page - data loading and processing."""

import pandas as pd

from src.database.tables import TABLE_FANTA_STATS, TABLE_PREDICTIONS
from src.database.utils import load_dataframe_from_supabase
from src.scraping.update_fanta_stats import get_current_season


def get_team_list() -> list[str]:
    """Extract sorted list of all teams from fanta_stats dataframe."""
    fanta_stats_df = load_dataframe_from_supabase(TABLE_FANTA_STATS.name)
    return sorted(fanta_stats_df["fanta_team"].dropna().unique().tolist())


def calculate_player_aggregate_stats(
    df_fanta_stats: pd.DataFrame,
    position_filter: str | None = None,
) -> pd.DataFrame:
    """Calculate aggregate statistics per player from fanta_stats."""
    df = df_fanta_stats.copy()
    
    # Apply position filter if specified
    if position_filter and position_filter != "All":
        df = df[df["position"] == position_filter]

    # Aggregate statistics per player
    player_avg_stats = (
        df.groupby(["player", "fanta_team", "position"])
        .agg(
            games=("game_id", "count"),
            mp=("mp", "mean"),
            pts=("pts", "mean"),
            trb=("trb", "mean"),
            ast=("ast", "mean"),
            stl=("stl", "mean"),
            blk=("blk", "mean"),
            avg_gain=("gain", "mean"),
            med_gain=("gain", "median"),
            gain=("gain", "sum"),
            last_gain=("gain", "last"),
            value=("value_after", "last"),
            score=("fanta_score", "mean"),
        )
        .reset_index()
        .rename(columns={
            "fanta_team": "team",
            "position": "pos",
        })
    )
    
    return player_avg_stats


def apply_filters(
    df: pd.DataFrame,
    team: str | None = None,
    value_range: tuple[float, float] | None = None,
) -> pd.DataFrame:
    """Apply team and value range filters to dataframe."""
    
    # Filter by team if specified (expects fanta_team code like 'BOS', 'LAL')
    if team and team != "All":
        # Try both 'team' and 'fanta_team' columns
        if "team" in df.columns:
            df = df[df["team"] == team]
        elif "fanta_team" in df.columns:
            df = df[df["fanta_team"] == team]

    # Filter by value range if specified
    if value_range:
        df = df[(df["value"] >= value_range[0]) & (df["value"] <= value_range[1])]

    return df



def compute_bench_score(df_fanta_stats: pd.DataFrame) -> pd.DataFrame:
    """
    Compute the bench_score for each player based on recent bench transitions,
    including the next match predictions.

    Args:
        df_fanta_stats (pd.DataFrame): Historical fantasy stats DataFrame.
        lineups_df (pd.DataFrame): Lineups DataFrame for the next game.

    Returns:
        pd.DataFrame: DataFrame with players and their computed bench scores.
    """
    def calculate_bench_score(player_group):
        starts = player_group["start"].values
        if len(starts) < 2:
            return 0  # Not enough data to calculate bench_score

        # Identify spells of consecutive 0s or 1s
        spells = []
        current_spell = [starts[0]]

        for i in range(1, len(starts)):
            if starts[i] == current_spell[-1]:
                current_spell.append(starts[i])
            else:
                spells.append(current_spell)
                current_spell = [starts[i]]
        spells.append(current_spell)  # Add the last spell

        if len(spells) < 2:
            return 0  # Not enough spells to calculate bench_score

        # Calculate lengths of the most recent and previous spells
        most_recent_spell = spells[-1]
        previous_spell = spells[-2]
        most_recent_start_value = most_recent_spell[0]
        length_most_recent = len(most_recent_spell)
        length_previous = len(previous_spell)

        # Apply the formula
        bench_score = (
            (-1 + 2 * most_recent_start_value)
            / length_most_recent
            * length_previous
        )
        return bench_score

    # Group by player and calculate bench_score
    df_bench = df_fanta_stats.groupby("player", as_index=False).apply(
        lambda group: calculate_bench_score(group)
    )
    df_bench.columns = ["player", "bench"]

    return df_bench


def compute_player_stats(
    position_filter: str | None = None,
    team_filter: str | None = None,
    value_range: tuple[float, float] | None = None,
) -> pd.DataFrame:
    """Complete processing pipeline for player statistics."""
    
    # Load data
    filters = {"season": get_current_season()}
    df_fanta_stats = load_dataframe_from_supabase(TABLE_FANTA_STATS.name, filters=filters)
    df_predictions = load_dataframe_from_supabase(TABLE_PREDICTIONS.name)

    # Calculate averages
    df_players = calculate_player_aggregate_stats(
        df_fanta_stats, position_filter
    )

    # Merge with predictions to get predicted_gain
    df_players = pd.merge(
        df_players,
        df_predictions[["player", "predicted_gain"]],
        on="player",
        how="left",
    )
    # Rename predicted_gain to gain
    df_players = df_players.rename(columns={"predicted_gain": "gain_hat"})
    
    # Calculate med5 and med10
    df_median_5 = (
        df_fanta_stats.groupby("player").tail(5)
        .groupby("player", as_index=False).agg(gain5=("gain", "median"))
    )
    df_median_10 = (
        df_fanta_stats.groupby("player").tail(10)
        .groupby("player", as_index=False).agg(gain10=("gain", "median"))
    )

    # Merge med5 and med10 into df_players
    df_players = pd.merge(df_players, df_median_5, on="player", how="left")
    df_players = pd.merge(df_players, df_median_10, on="player", how="left")
    
    # Compute bench_score
    df_bench_score = compute_bench_score(df_fanta_stats)
    df_players = pd.merge(df_players, df_bench_score, on="player", how="left")

    # Apply filters
    df_players = apply_filters(df_players, team_filter, value_range)

    # Sort by gain (descending)
    df_players = df_players.sort_values("gain_hat", ascending=False)

    return df_players

"""Logic functions for Teams page."""

import pandas as pd

from src.database.tables import TABLE_FANTA_STATS, TABLE_TEAMS
from src.database.utils import load_dataframe_from_supabase
from src.scraping.update_fanta_stats import get_current_season


def get_teams_gain_table() -> pd.DataFrame:
    """Return DataFrame with team opponent gain stats for the Teams page."""
    # Load data
    filters = {"season": get_current_season()}
    df_fanta_stats = load_dataframe_from_supabase(TABLE_FANTA_STATS.name, filters=filters)
    df_teams = load_dataframe_from_supabase(TABLE_TEAMS.name)

    # Filter to only starting players
    starters = df_fanta_stats[df_fanta_stats["start"]].copy()

    # Group by opponent_team and compute average gain allowed
    df_team_gain = (
        starters.groupby("opponent_team")["gain"]
        .mean()
        .reset_index()
        .rename(columns={"opponent_team": "Team", "gain": "Avg Opponent Gain"})
    )

    # Average by position (C, F, G)
    for role in ["C", "F", "G"]:
        role_gain = (
            starters[starters["position"] == role]
            .groupby("opponent_team")["gain"]
            .mean()
            .reset_index()
            .rename(columns={"gain": f"Avg Gain ({role})"})
        )
        df_team_gain = pd.merge(df_team_gain, role_gain, left_on="Team", right_on="opponent_team", how="left")
        df_team_gain = df_team_gain.drop(columns=["opponent_team"], errors="ignore")


    # Merge Team with fanta_team
    df_team_gain = pd.merge(
        df_team_gain,
        df_teams[["team", "fanta_team"]],
        left_on="Team",
        right_on="team",
        how="left"
    )
    # Select columns
    columns = [
        "Team", "Avg Opponent Gain", "Avg Gain (C)",
        "Avg Gain (F)", "Avg Gain (G)", "fanta_team"
    ]
    df_team_gain = df_team_gain[[col for col in columns if col in df_team_gain.columns]]

    # Sort by average gain descending
    df_team_gain = df_team_gain.sort_values("Avg Opponent Gain", ascending=False)
    return df_team_gain

"""Logic functions for Teams page."""

import pandas as pd

from src.supabase.tables import TABLE_FANTA_STATS, TABLE_TEAMS
from src.supabase.utils import load_dataframe_from_supabase


def get_teams_gain_table(season: int = None) -> pd.DataFrame:
    """Return DataFrame with team opponent gain stats for the Teams page."""
    # Load data
    filters = {"season": season} if season is not None else None
    fanta_stats = load_dataframe_from_supabase(TABLE_FANTA_STATS.name, filters=filters)
    teams = load_dataframe_from_supabase(TABLE_TEAMS.name)

    # Filter to only starting players
    starters = fanta_stats[fanta_stats["start"]].copy()

    # Group by opponent_team and compute average gain allowed
    team_gain = (
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
        team_gain = pd.merge(team_gain, role_gain, left_on="Team", right_on="opponent_team", how="left")
        team_gain = team_gain.drop(columns=["opponent_team"], errors="ignore")


    # Merge Team with fanta_team
    team_gain = pd.merge(
        team_gain,
        teams[["team", "fanta_team"]],
        left_on="Team",
        right_on="team",
        how="left"
    )
    # Select columns
    columns = [
        "Team", "Avg Opponent Gain", "Avg Gain (C)",
        "Avg Gain (F)", "Avg Gain (G)", "fanta_team"
    ]
    team_gain = team_gain[[col for col in columns if col in team_gain.columns]]

    # Sort by average gain descending
    team_gain = team_gain.sort_values("Avg Opponent Gain", ascending=False)
    return team_gain

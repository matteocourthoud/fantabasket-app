
import pandas as pd

from src.supabase.tables import TABLE_FANTA_STATS, TABLE_TEAMS
from src.supabase.utils import load_dataframe_from_supabase


def get_teams_gain_table(season: int = None) -> pd.DataFrame:
    """Return DataFrame with team opponent gain stats for the Teams page, using only fanta_stats and teams tables."""
    # Load data
    fanta_stats = load_dataframe_from_supabase(TABLE_FANTA_STATS.name, filters={"season": season} if season else None)
    teams = load_dataframe_from_supabase(TABLE_TEAMS.name)

    # Filter to only starting players
    starters = fanta_stats[fanta_stats["start"] == True].copy()

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


    # Merge Team (full name) with team, then use team_short for logo
    team_gain = pd.merge(
        team_gain,
        teams[["team", "team_short", "fanta_team"]],
        left_on="Team",
        right_on="team_short",
        how="left"
    )
    # Select and order columns
    columns = ["Team", "Avg Opponent Gain", "Avg Gain (C)", "Avg Gain (F)", "Avg Gain (G)", "team_short", "fanta_team"]
    team_gain = team_gain[[col for col in columns if col in team_gain.columns]]

    # Sort by average gain descending
    team_gain = team_gain.sort_values("Avg Opponent Gain", ascending=False)
    return team_gain

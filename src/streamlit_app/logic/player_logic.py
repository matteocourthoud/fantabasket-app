"""Business logic for players page - individual player statistics."""

from datetime import datetime

import pandas as pd

from src.database.utils import load_dataframe_from_supabase
from src.scraping.update_fanta_stats import get_current_season


def get_player_next_game(
    player_name: str,
) -> dict:
    """Find the next scheduled game for the player's current team."""
    # Load data
    season = get_current_season()
    df_fanta_stats = load_dataframe_from_supabase("fanta_stats", {"season": season})
    df_calendar = load_dataframe_from_supabase("calendar", {"season": season})
    df_teams = load_dataframe_from_supabase("teams")
    
    # Find player's most recent team from stats/games
    team = df_fanta_stats[df_fanta_stats["player"] == player_name]["team"].iloc[-1]
    
    # Find next game for this team in calendar after today
    today = datetime.today().strftime('%Y-%m-%d')
    df_future_games = df_calendar[(df_calendar["date"] > today) &
                               ((df_calendar["team_home"] == team) |
                                (df_calendar["team_visitor"] == team))]
   
    next_game = df_future_games.sort_values("date").iloc[0]
    is_home = next_game["team_home"] == team
    if is_home:
        opponent = next_game["team_visitor"]
    else:
        opponent = next_game["team_home"]
    opponent = df_teams[df_teams["team"] == opponent]["fanta_team"].iloc[0]
    return {"date": next_game["date"], "opponent": opponent, "is_home": is_home}


def get_player_list(stats_df: pd.DataFrame) -> dict[str, str]:
    """Return a mapping of simplified_name -> original_name for players."""
    return sorted(stats_df["player"].unique().tolist())


def get_player_recent_games(player_name: str) -> pd.DataFrame:
    """Get recent game statistics for a specific player."""
    # Filter stats for the player
    df_fanta_stats = load_dataframe_from_supabase("fanta_stats", {"season": get_current_season()})
    df_player = df_fanta_stats[df_fanta_stats["player"] == player_name].copy()
    print(df_player.head())
    
    # Select and reorder relevant columns
    columns_to_show = [
        "opponent_team",
        "start",
        "win",
        "fanta_score",
        "gain",
        "pts",
        "trb",
        "ast",
        "stl",
        "blk",
        "fg_pct",
        "tp_pct",
        "ast_pct",
        "mp",
    ]

    # Only include columns that exist in the dataframe
    df_player = df_player[columns_to_show]
    
    # Rename columns for better display
    df_player = df_player.rename(columns={
        "opponent_team": "opponent",
        "fanta_score": "score",
        "fg_pct": "fg%",
        "tp_pct": "3p%",
        "ast_pct": "ast%",
    })

    return df_player


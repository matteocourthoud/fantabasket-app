"""Business logic for players page - individual player statistics."""

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
)
from src.supabase.utils import load_dataframe_from_supabase  # noqa: E402


def load_player_data(season: int) -> dict[str, pd.DataFrame]:
    """Load all required data for the players page."""
    from src.supabase.tables import TABLE_CALENDAR, TABLE_TEAMS
    data = {
        "stats": load_dataframe_from_supabase(TABLE_STATS.name, filters={"season": season}),
        "games": load_dataframe_from_supabase(TABLE_GAMES.name, filters={"season": season}),
        "players": load_dataframe_from_supabase(TABLE_PLAYERS.name),
        "fanta_stats": load_dataframe_from_supabase(TABLE_FANTA_STATS.name),
        "calendar": load_dataframe_from_supabase(TABLE_CALENDAR.name, filters={"season": season}),
        "teams": load_dataframe_from_supabase(TABLE_TEAMS.name),
    }
    return data


def get_player_next_game(
    player_name: str,
    stats_df: pd.DataFrame,
    games_df: pd.DataFrame,
    calendar_df: pd.DataFrame,
    today: str,
    st_debug=None,
    teams_df: pd.DataFrame = None,
) -> dict:
    """
    Find the next scheduled game for the player's current team. Prints debug info.

    Args:
        player_name: Name of the player
        stats_df: Player statistics dataframe
        games_df: Games dataframe
        calendar_df: Calendar dataframe
        today: Current date as string (YYYY-MM-DD)
        st_debug: Optional Streamlit module for debug printing

    Returns:
        Dict with 'date', 'opponent', and 'is_home' or None if not found
    """
    # Find player's most recent team from stats/games
    player_stats = stats_df[stats_df["player"] == player_name].copy()
    if player_stats.empty:
        return None
    
    # Merge with games to get winner/loser
    merged = pd.merge(
        player_stats,
        games_df[["game_id", "winner", "loser", "date"]],
        on="game_id",
        how="left",
    )
    merged = merged.sort_values("date", ascending=False)
    if merged.empty:
        return None
    
    # Guess team: if win, team = winner, else team = loser
    most_recent = merged.iloc[0]
    if most_recent.get("win", False):
        team = most_recent["winner"]
    else:
        team = most_recent["loser"]
        
    # Normalize team names (strip, upper)
    team = str(team).strip().upper()
    team_full = team
    if teams_df is not None:
        teams_df = teams_df.copy()
        teams_df["team_short"] = teams_df["team_short"].str.strip().str.upper()
        teams_df["team"] = teams_df["team"].str.strip().str.upper()
        match = teams_df[teams_df["team_short"] == team]
        if not match.empty:
            team_full = match.iloc[0]["team"]
    calendar_df = calendar_df.copy()
    calendar_df["team_home"] = calendar_df["team_home"].str.strip().str.upper()
    calendar_df["team_visitor"] = calendar_df["team_visitor"].str.strip().str.upper()
    team_full = team_full.strip().upper()
    
    # Find next game for this team in calendar after today
    future_games = calendar_df[(calendar_df["date"] > today) & ((calendar_df["team_home"] == team_full) | (calendar_df["team_visitor"] == team_full))]
    if future_games.empty:
        return None
    next_game = future_games.sort_values("date").iloc[0]
    is_home = next_game["team_home"] == team_full
    if is_home:
        opponent = next_game["team_visitor"]
    else:
        opponent = next_game["team_home"]
    return {"date": next_game["date"], "opponent": opponent, "is_home": is_home}


def get_player_list(stats_df: pd.DataFrame) -> dict[str, str]:
    """Return a mapping of simplified_name -> original_name for players."""
    return sorted(stats_df["player"].unique().tolist())


def get_player_recent_games(
    player_name: str, stats_df: pd.DataFrame, games_df: pd.DataFrame, fanta_stats_df: pd.DataFrame, n_games: int = 10
) -> pd.DataFrame:
    """
    Get recent game statistics for a specific player.

    Args:
        player_name: Name of the player
        stats_df: Player statistics dataframe
        games_df: Games dataframe
        n_games: Number of recent games to return

    Returns:
        Dataframe with player's recent game statistics
    """
    # Filter stats for the player
    player_stats = stats_df[stats_df["player"] == player_name].copy()

    # Merge with games to get date and opponent info
    player_stats = pd.merge(
        player_stats,
        games_df[["game_id", "date", "winner", "loser"]],
        on="game_id",
        how="left",
    )

    # Merge with fanta_stats to get gain (filter fanta_stats to this player to avoid duplicates)
    print(fanta_stats_df)
    player_fanta_stats = fanta_stats_df[fanta_stats_df["player"] == player_name][["game_id", "gain", "fanta_score"]]
    player_fanta_stats["score"] = player_fanta_stats["fanta_score"].astype(int)
    player_stats = pd.merge(
        player_stats,
        player_fanta_stats,
        on="game_id",
        how="left",
    )

    # Determine opponent
    player_stats["opponent"] = player_stats.apply(
        lambda row: row["loser"] if row["win"] else row["winner"], axis=1
    )

    # Sort by date descending and take most recent games
    player_stats = player_stats.sort_values("date", ascending=False).head(n_games)

    # Select and reorder relevant columns
    columns_to_show = [
        "date",
        "opponent",
        "win",
        "score",
        "gain",
        "mp",
        "pts",
        "trb",
        "ast",
        "stl",
        "blk",
        "fg",
        "fga",
        "tp",
        "tpa",
        "ft",
        "fta",
        "tov",
        "pf",
        "pm",
    ]

    # Only include columns that exist in the dataframe
    available_columns = [col for col in columns_to_show if col in player_stats.columns]
    player_stats = player_stats[available_columns]

    return player_stats


def get_player_performance_over_time(
    player_name: str, stats_df: pd.DataFrame, games_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Get player's performance statistics over time for plotting.

    Args:
        player_name: Name of the player
        stats_df: Player statistics dataframe
        games_df: Games dataframe

    Returns:
        Dataframe with player's performance over time (sorted by date)
    """
    # Filter stats for the player
    player_stats = stats_df[stats_df["player"] == player_name].copy()

    # Merge with games to get date
    player_stats = pd.merge(
        player_stats, games_df[["game_id", "date"]], on="game_id", how="left"
    )

    # Sort by date
    player_stats = player_stats.sort_values("date")

    return player_stats


def get_player_summary(
    player_name: str, stats_df: pd.DataFrame, fanta_stats_df: pd.DataFrame
) -> dict:
    """
    Get summary statistics for a player.

    Args:
        player_name: Name of the player
        stats_df: Player statistics dataframe
        fanta_stats_df: Fantasy stats dataframe

    Returns:
        Dictionary with summary statistics
    """
    player_stats = stats_df[stats_df["player"] == player_name]

    # Calculate averages
    numeric_cols = player_stats.select_dtypes(include="number").columns
    cols_to_exclude = ["id", "game_id", "player_id", "season"]
    cols_to_avg = [col for col in numeric_cols if col not in cols_to_exclude]

    avg_stats = player_stats[cols_to_avg].mean()

    # Get current fantasy value
    player_fanta = fanta_stats_df[fanta_stats_df["player"] == player_name]
    current_value = (
        player_fanta["value_after"].iloc[-1] if len(player_fanta) > 0 else None
    )
    avg_gain = player_fanta["gain"].mean() if len(player_fanta) > 0 else None

    summary = {
        "games_played": len(player_stats),
        "avg_points": avg_stats.get("pts", 0),
        "avg_rebounds": avg_stats.get("trb", 0),
        "avg_assists": avg_stats.get("ast", 0),
        "avg_minutes": avg_stats.get("mp", 0),
        "current_value": current_value,
        "avg_gain": avg_gain,
    }

    return summary

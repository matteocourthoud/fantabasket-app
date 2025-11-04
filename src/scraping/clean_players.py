"""Scrapes list of NBA players, with short names, positions and codes."""

import re

import pandas as pd
from unidecode import unidecode

from src.database.tables import TABLE_INITIAL_VALUES, TABLE_PLAYERS, TABLE_STATS
from src.database.utils import load_dataframe_from_supabase, save_dataframe_to_supabase


PLAYER_MAP = {
    "alex-sarr": "alexandre-sarr",
    "daron-holmes": "daron-holmes-ii",
    "walter-clayton": "walter-clayton-jr",
    "ron-holland": "ronald-holland-ii",
    "xavier-tillman-sr": "xavier-tillman",
    "yang-hansen": "hansen-yang",
    "yanic-konan-niederhauser": "yanic-niederhauser",
}


def _normalize_name(name: str) -> str:
    """Normalize player name for matching."""
    name = unidecode(str(name))  # Remove accents and special characters
    name = name.lower().strip() # Convert to lowercase and replace spaces with hyphens
    name = re.sub(r"['\.]", "", name)  # Remove apostrophes and periods
    name = re.sub(r"\s+", "-", name)  # Replace spaces with hyphens
    return name


def _extract_name_from_fanta_id(fanta_player_id: str) -> str:
    """Extract normalized name from fanta_player_id."""
    return str(fanta_player_id).split("/")[-1]


def _get_unique_players_from_stats() -> pd.DataFrame:
    """Get unique players from the STATS_TABLE."""
    df_stats = load_dataframe_from_supabase(TABLE_STATS.name)
    
    # Get unique players with their player_id
    df_players = df_stats[["player", "player_id"]].drop_duplicates()
    
    # Add normalized name for matching
    df_players["normalized_name"] = df_players["player"].apply(_normalize_name)
    df_players["normalized_name"] = df_players["normalized_name"].replace(PLAYER_MAP)
    
    print(f"  Found {len(df_players)} unique players in STATS_TABLE")
    return df_players


def _get_all_players_from_ratings() -> pd.DataFrame:
    """Get all players from the INITIAL_RATINGS_TABLE."""
    df_ratings = load_dataframe_from_supabase(TABLE_INITIAL_VALUES.name)
    
    # Get unique players with their fanta identifiers
    cols = ["fanta_player", "fanta_player_id"]
    df_players = df_ratings[cols].drop_duplicates(subset=["fanta_player_id"])
    
    # Add normalized name for matching
    df_players["normalized_name"] = df_players["fanta_player_id"].apply(_extract_name_from_fanta_id)
    
    print(f"  Found {len(df_players)} unique players in INITIAL_RATINGS_TABLE")
    return df_players


def _merge_dfs_players(df_stats: pd.DataFrame, df_ratings: pd.DataFrame) -> pd.DataFrame:
    """Merge player dataframes from stats and ratings tables.
    
    Merges on normalized names derived from:
    - STATS_TABLE: 'player' (e.g., 'Deandre Ayton')
    - INITIAL_RATINGS_TABLE: 'fanta_player_id' (e.g., '20/deandre-ayton')
    """
    print("  Merging player data...")
    
    # Perform outer merge to keep all players from both sources
    df_merged = pd.merge(
        df_stats,
        df_ratings,
        on="normalized_name",
        how="left",
        indicator=True,
    )
    
    # Report matching statistics
    both_count = (df_merged["_merge"] == "both").sum()
    stats_only_count = (df_merged["_merge"] == "left_only").sum()
    
    print("\n  Merge Results:")
    print(f"  ✓ Matched players: {both_count}")
    print(f"  ⚠ Only in STATS_TABLE: {stats_only_count}")
    
    # Print players not merged from STATS_TABLE
    if stats_only_count > 0:
        print("\n  Players in STATS_TABLE but not in INITIAL_RATINGS_TABLE:")
        stats_only = df_merged[df_merged["_merge"] == "left_only"]["player"].dropna().unique()
        for player in sorted(stats_only):  # Show all
            print(f"    - {player}")
    
    # Create final dataframe with selected columns
    df_players = df_merged[[
        "player",
        "player_id",
        "fanta_player",
        "fanta_player_id",
    ]].copy().dropna(subset=["player", "fanta_player"])
    
    print(f"\n  Final player count: {len(df_players)}")
    return df_players


def clean_players() -> None:
    """Cleans NBA players info, saves to Supabase."""
    print("Cleaning players info...")

    # Get players from stats table
    df_players_stats = _get_unique_players_from_stats()
    
    # Get players from the initial ratings table
    df_players_ratings = _get_all_players_from_ratings()

    # Merge the dataframes
    df_players = _merge_dfs_players(df_players_stats, df_players_ratings)

    # Save updated dataframe to Supabase
    save_dataframe_to_supabase(
        df=df_players,
        table_name=TABLE_PLAYERS.name,
        index_columns=["player"],
        replace=True,
    )
    
    print("\n✓ Players table updated successfully!")


if __name__ == "__main__":
    clean_players()

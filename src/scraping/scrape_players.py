"""Scrapes list of NBA players, with short names, positions and codes."""

import re
import time
from typing import Tuple
import requests
from unidecode import unidecode
import pandas as pd
from bs4 import BeautifulSoup
from supabase.utils import save_dataframe_to_supabase, load_dataframe_from_supabase
from src.supabase.table_names import PLAYERS_TABLE, STATS_TABLE

WEBSITE_URL = 'https://www.basketball-reference.com'


def _get_df_all_players() -> pd.DataFrame:
    """Get all unique players from stats table across all seasons."""
    df_stats = load_dataframe_from_supabase(STATS_TABLE)
    df_players = df_stats[["player", "game_id"]].drop_duplicates("player").reset_index(drop=True)
    return df_players


def _scrape_player_code_and_position(player_name: str, game_id: str) -> Tuple[str, str]:
    """Scrapes player code and position from basketball-reference.com."""
    time.sleep(4)
    game_url = f'{WEBSITE_URL}/boxscores/{game_id}.html'
    soup = BeautifulSoup(requests.get(game_url).content, "lxml")
    try:
        player_url = soup.find(lambda tag: tag.name == 'a' and tag.text == player_name)['href']
        player_code = re.findall(r"/([^/]+)\.html$", player_url)[0]
    except Exception as e:
        print(f"Error for {player_name} at {game_url}: {e}")
        return "", ""
    soup = BeautifulSoup(requests.get(WEBSITE_URL + player_url).content, "lxml")
    player_info = str(soup.find('div', id='meta'))
    for player_position in ['Center', 'Forward', 'Guard']:
        if player_position in player_info:
            return player_code, player_position[0]
    return player_code, ""


def _scrape_all_player_positions(df_players: pd.DataFrame, df_all_players: pd.DataFrame) -> pd.DataFrame:
    """Scrapes positions for all players not yet in the players table."""
    for i in range(len(df_all_players)):
        player_name = df_all_players.player[i]
        print(f'Progress: {i}/{len(df_all_players)}', end='\r')
        if player_name in df_players.player.values:
            continue
        game_id = df_all_players.game_id[i]
        player_code, player_position = _scrape_player_code_and_position(player_name=player_name, game_id=game_id)
        if player_position:
            df_player = pd.DataFrame({"player": [player_name], "player_code": [player_code], "position": [player_position]})
            df_players = pd.concat([df_players, df_player], ignore_index=True)
    return df_players


def _clean_player_name(name: str) -> str:
    """Cleans a player name to create a short version."""
    return f"{name.split()[0][0]}. {unidecode(name.split()[-1])}"


def _clean_player_name_with_suffix(name: str) -> str:
    """Cleans a player name with suffix (Jr., Sr., etc.) to create a short version."""
    return f"{name.split()[0][0]}. {unidecode(name.split()[-2])} {name.split()[-1]}"


def _add_name_short(df: pd.DataFrame) -> pd.DataFrame:
    """Adds a short name column to the players dataframe."""
    df["name_short"] = df['player'].apply(_clean_player_name)

    # Clean suffixes
    for suffix in ["Jr.", "Sr.", "II", "III", "IV"]:
        rows = df["name_short"].str.endswith(suffix)
        df.loc[rows, "name_short"] = df.loc[rows, 'player'].apply(_clean_player_name_with_suffix)

    # Custom cleaning
    df.loc[df.player == "Xavier Tillman Sr.", "name_short"] = "X. Tillman"
    df.loc[df.player == "Ron Holland", "name_short"] = "R. Holland II"
    df.loc[df.player == "Tristan Da Silva", "name_short"] = "T. da Silva"
    df.loc[df.player == "Yongxi Cui", "name_short"] = "C. Yongxi"
    return df


def scrape_players() -> None:
    """Scrapes NBA players with codes and positions, saves to Supabase."""
    print("Scraping players from all seasons...")
    
    # Get all players from stats table
    df_all_players = _get_df_all_players()
    
    # Load existing players from Supabase
    df_players = load_dataframe_from_supabase(PLAYERS_TABLE)
    if df_players.empty:
        df_players = pd.DataFrame(columns=["player", "name_short", "player_code", "position"])

    # Scrape missing players
    df_players = _scrape_all_player_positions(df_players=df_players, df_all_players=df_all_players)
    print("\n✓ Players database is up to date!")

    # Update name_short column
    df_players = _add_name_short(df=df_players)
    
    # Save updated dataframe to Supabase
    save_dataframe_to_supabase(
        df=df_players,
        table_name=PLAYERS_TABLE,
        index_columns=['player'],
        replace=True,
    )

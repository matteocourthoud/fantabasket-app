"""Scrapes list of NBA players, with short names, positions and codes."""

import os
import re
import time
from typing import Tuple
import requests
from unidecode import unidecode
import pandas as pd
from bs4 import BeautifulSoup

PLAYERS_FILE = 'players.csv'
STATS_FILE = 'stats.csv'
WEBSITE_URL = 'https://www.basketball-reference.com'


def _get_df_all_players(data_dir: str, season: int):
    seasons = range(season, 2021, -1)
    dfs_stats = [pd.read_csv(os.path.join(data_dir, str(s), STATS_FILE))[["name", "game_id"]] for s in seasons]
    df_players = pd.concat(dfs_stats).drop_duplicates("name").reset_index(drop=True)
    return df_players


def _scrape_player_code_and_position(player_name: str, game_id: str) -> Tuple[str, str]:
    time.sleep(4)
    game_url = f'{WEBSITE_URL}/boxscores/{game_id}.html'
    soup = BeautifulSoup(requests.get(game_url).content, "lxml")
    try:
        player_url = soup.find(lambda tag: tag.name == 'a' and tag.text == player_name)['href']
        player_code = re.findall(r"/([^/]+)\.html$", player_url)[0]
    except:
        print(player_name, game_url)
        return "", ""
    soup = BeautifulSoup(requests.get(WEBSITE_URL + player_url).content, "lxml")
    player_info = str(soup.find('div', id='meta'))
    for player_position in ['Center', 'Forward', 'Guard']:
        if player_position in player_info:
            return player_code, player_position[0]
    return player_code, ""


def _scrape_all_player_positions(df_players: pd.DataFrame, df_all_players: pd.DataFrame, file_path: str) -> pd.DataFrame:
    for i in range(len(df_all_players)):
        player_name = df_all_players.name[i]
        print(f'Progress: {i}/{len(df_all_players)}', end='\r')
        if player_name in df_players.name.values:
            continue
        game_id = df_all_players.game_id[i]
        player_code, player_position = _scrape_player_code_and_position(player_name=player_name, game_id=game_id)
        if player_position is not None:
            df_player = pd.DataFrame({"name": [player_name], "code": [player_code], "position": [player_position]})
            df_players = pd.concat([df_players, df_player])
            df_players.to_csv(file_path, index=False)
    return df_players


def _add_name_sort(df: pd.DataFrame) -> pd.DataFrame:
    f_clean_names = lambda x: f"{x.split()[0][0]}. {unidecode(x.split()[-1])}"
    df["name_short"] = df['name'].apply(f_clean_names)

    # Clean suffixes
    for suffix in ["Jr.", "Sr.", "II", "III", "IV"]:
        rows = df["name_short"].str.endswith(suffix)
        f_clean_names_with_suffix = lambda x: f"{x.split()[0][0]}. {unidecode(x.split()[-2])} {x.split()[-1]}"
        df.loc[rows, "name_short"] = df.loc[rows, 'name'].apply(f_clean_names_with_suffix)

    # Custom cleaning
    df.loc[df.name == "Xavier Tillman Sr.", "name_short"] = "X. Tillman"
    df.loc[df.name == "Ron Holland", "name_short"] = "R. Holland II"
    df.loc[df.name == "Tristan Da Silva", "name_short"] = "T. da Silva"
    df.loc[df.name == "Yongxi Cui", "name_short"] = "C. Yongxi"
    return df


def get_players(data_dir: str, season: int) -> pd.DataFrame():
    df_all_players = _get_df_all_players(data_dir=data_dir, season=season)
    file_path = os.path.join(data_dir, PLAYERS_FILE)
    if not os.path.exists(file_path):
        df_players = pd.read_csv(file_path)
    else:
        df_players = pd.DataFrame(columns=["name", "name_short", "code", "position"])

    # Scrape players
    df_players = _scrape_all_player_positions(df_players=df_players, df_all_players=df_all_players,
                                              file_path=file_path)
    print("Players database is up to date!")

    # Update name short
    df_players = _add_name_sort(df=df_players)
    return df_players


def update_get_players(data_dir: str, season: int, update: bool = False) -> pd.DataFrame():
    # Import / initialize dataframes
    file_path = os.path.join(data_dir, PLAYERS_FILE)
    if update or not os.path.exists(file_path):
        df_players = get_players(data_dir=data_dir, season=season)
        df_players.to_csv(file_path, index=False)
    df_players = pd.read_csv(file_path)
    assert not df_players.duplicated(subset=["name"]).any(), f"Duplicated 'name' in {file_path}."
    return df_players

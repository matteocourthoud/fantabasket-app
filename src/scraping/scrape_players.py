"""Scrapes list of NBA players, with short names, positions and codes."""

import os
import re
import time
from typing import Tuple
import requests
import pandas as pd
from bs4 import BeautifulSoup

PLAYERS_FILE = 'players.csv'
STATS_FILE = 'stats.csv'
WEBSITE_URL = 'https://www.basketball-reference.com'


def _get_df_all_players(data_dir: str, season: int):
    # Import data
    players_file_path = os.path.join(data_dir, PLAYERS_FILE)
    if os.path.exists(players_file_path):
        df_players = pd.read_csv(players_file_path, index_col=0)
    else:
        seasons = range(season, 2021, -1)
        dfs_stats = [pd.read_csv(os.path.join(data_dir, str(s), STATS_FILE))[["name", "game_id"]] for s in seasons]
        df_players = pd.concat(dfs_stats).drop_duplicates("name").reset_index(drop=True)
    return df_players


def _scrape_player_code_and_position(player_name: str, game_id: str) -> Tuple[str, str]:
    time.sleep(4)
    game_url = f'{WEBSITE_URL}/boxscores/{game_id}.html'
    soup = BeautifulSoup(requests.get(game_url).content, "lxml")
    player_url = soup.find(lambda tag: tag.name == 'a' and tag.text == player_name)['href']
    player_code = re.findall(r"/([^/]+)\.html$", player_url)[0]
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
            df_player = pd.DataFrame({"name": [player_name], "code": [player_code], "position": [player_position[0]]})
            df_players = pd.concat([df_players, df_player])
            df_players.to_csv(file_path, index=False)
    return df_players


def _add_name_sort(df: pd.DataFrame) -> pd.DataFrame:
    df["name_short"] = df['name'].apply(lambda x: f"{x.split()[0][0]}. {x.split()[-1]}")
    return df


def update_get_players(data_dir: str, season: int) -> pd.DataFrame():
    # Import / initialize dataframes
    df_all_players = _get_df_all_players(data_dir=data_dir, season=season)
    file_path = os.path.join(data_dir, str(season), PLAYERS_FILE)
    if os.path.exists(file_path):
        df_players = pd.read_csv(file_path)
    else:
        df_players = pd.DataFrame(columns=["name", "name_short", "code", "position"])

    # Scrape players
    df_players = _scrape_all_player_positions(df_players=df_players, df_all_players=df_all_players, file_path=file_path)
    print("Players database is up to date!")

    # Update name short
    df_players = _add_name_sort(df=df_players)
    df_players.to_csv(file_path, index=False)

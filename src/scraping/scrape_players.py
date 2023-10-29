"""
Scrape NBA games stats.
Author: Matteo Courthoud
Date: 22/10/2022
"""

import os
import requests
import pandas as pd
from bs4 import BeautifulSoup
from scrape_games import save_data


PLAYERS_FILE = 'data/players.csv'
WEBSITE_URL = 'https://www.basketball-reference.com'

# Import data
if os.path.exists(PLAYERS_FILE):
    df_players = pd.read_csv(PLAYERS_FILE, index_col=0)
else:
    df_players = pd.DataFrame(columns=['name', 'position'])
df_urls = pd.concat([pd.read_csv('data_2021/stats.csv', index_col=0)[['name', 'url']],
                     pd.read_csv('data_2022/stats.csv', index_col=0)[['name', 'url']]]
                    ).drop_duplicates('name').reset_index(drop=True)


# Add position
for i in range(len(df_urls)):
    print(f'Progress: {i}/{len(df_urls)}', end='\r')
    if df_urls.name[i] in df_players.name.values:
        pass
    game_url = f'{WEBSITE_URL}/boxscores/{df_urls.url[i]}.html'
    soup = BeautifulSoup(requests.get(game_url).content, "lxml")
    player_url = soup.find(lambda tag: tag.name == 'a' and tag.text == df_urls.name[i])['href']
    soup = BeautifulSoup(requests.get(WEBSITE_URL + player_url).content, "lxml")
    player_info = str(soup.find('div', id='meta'))
    for pos in ['Center', 'Forward', 'Guard']:
        if pos in player_info:
            df_player = pd.DataFrame({'name': [df_urls.name[i]], 'position': [pos[0]]})
    save_data(df_player, PLAYERS_FILE, 'name')

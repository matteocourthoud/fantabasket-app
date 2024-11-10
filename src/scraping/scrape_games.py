"""Scrape NBA games stats."""

import datetime
import os
import re
import requests
import time
import pandas as pd
from typing import List
from io import StringIO
from bs4 import BeautifulSoup

CALENDAR_FILE = 'calendar.csv'
DATES_FILE = 'dates.csv'
GAMES_FILE = 'games.csv'
STATS_FILE = 'stats.csv'
PLAYERS_FILE = 'old_players.csv'
WEBSITE_URL = 'https://www.basketball-reference.com'


def _load_data(data_dir: str, season: int, file_name: str) -> pd.DataFrame:
    """Loads data from file."""
    file_path = os.path.join(data_dir, str(season), file_name)
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    return pd.DataFrame()


def _save_data(data_dir: str, season: int, df: pd.DataFrame, file_name: str, index_col: str):
    """Saves/appends data to file."""
    file_path = os.path.join(data_dir, str(season), file_name)
    df = df.sort_values(by=index_col, ignore_index=True)
    df.to_csv(file_path, index=False)


def _get_unscraped_dates(df_calendar: pd.DataFrame, df_dates: pd.DataFrame) -> List[str]:
    """Generates a list of unscraped dates."""
    all_dates = df_calendar.date.values
    latest_date = datetime.date.today()
    all_dates = set([d for d in all_dates if datetime.datetime.strptime(d, "%Y-%m-%d").date() < latest_date])
    if df_dates.empty:
        return sorted(list(all_dates))
    scraped_dates = set(df_dates.date.values)
    unscraped_dates = sorted(list(all_dates - scraped_dates))
    return unscraped_dates


def _get_game_id(game):
    """Gets game id from game object."""
    game_url = game.find("td", class_='right gamelink').find('a', href=True)['href']
    game_id = re.findall('/boxscores/(\w+).html', game_url)[0]
    return game_id


def _get_unscraped_games(games, df_games: pd.DataFrame) -> List[str]:
    """Generates a list of unscraped dates."""
    if df_games.empty:
        return games
    scraped_games_id = df_games.game_id.values
    unscraped_games = [game for game in games if _get_game_id(game) not in scraped_games_id]
    return unscraped_games


def _scrape_game(game, date: str) -> pd.DataFrame:
    """Scrapes game."""
    df_game = pd.DataFrame({
        'game_id': _get_game_id(game),
        'date': date,
        'winner': [game.find('tr', class_='winner').find('a', href=True).text],
        'loser': [game.find('tr', class_='loser').find('a', href=True).text],
        'pts_winner': [game.find('tr', class_='winner').find(class_='right').text],
        'pts_loser': [game.find('tr', class_='loser').find(class_='right').text],
    })
    return df_game


def _get_df_stats(dfs: List[pd.DataFrame], scores: List[int]) -> pd.DataFrame:
    """Combines the two team tables into a single one with players' stats."""
    df_stats = pd.DataFrame()
    for df, score in zip(dfs, scores):
        df.columns = [col[1].lower() for col in df.columns]
        df['start'] = (df.index < 5).astype(int)
        df['win'] = int(score > min(scores))
        df = df.rename(columns={'starters': 'name'})
        df = df.loc[~df['name'].isin(['Reserves', 'Team Totals']), :]
        df['mp'] = df['mp'].str.extract('^(\d+)')
        for col in df.columns[1:]:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df_stats = pd.concat([df_stats, df]).reset_index(drop=True)
    return df_stats


def _scrape_game_stats(game) -> pd.DataFrame:
    """Scrapes NBA stats from game url."""
    game_url = game.find("td", class_='right gamelink').find('a', href=True)['href']
    soup = BeautifulSoup(requests.get(WEBSITE_URL + game_url).content, "lxml")
    scores = [int(s.text) for s in soup.find('div', class_='scorebox').find_all('div', class_='score')]
    tables = soup.find_all(lambda tag: tag.name == 'table' and tag.has_attr('id') and "game-basic" in tag['id'])
    dfs = [pd.read_html(StringIO(str(table)))[0] for table in tables]
    df_stats = _get_df_stats(dfs, scores)
    df_stats["game_id"] = _get_game_id(game)
    return df_stats


def _scrape_games_from_date(date: str) -> List:
    """Scrape all the game html elements from a date."""
    year, month, day = date.split("-")
    results_url = f'{WEBSITE_URL}/boxscores/?month={month}&day={day}&year={year}'
    soup = BeautifulSoup(requests.get(results_url).content, "lxml")
    games = soup.find_all(lambda tag: tag.name == 'div' and tag.has_attr('class') and "game_summary" in tag['class'])
    return games


def _scrape_nba_season(data_dir: str, season: int):
    """Scrapes nba data for a full season (year)."""
    df_stats = _load_data(data_dir=data_dir, season=season, file_name=STATS_FILE)
    df_games = _load_data(data_dir=data_dir, season=season, file_name=GAMES_FILE)
    df_dates = _load_data(data_dir=data_dir, season=season, file_name=DATES_FILE)
    df_calendar = _load_data(data_dir=data_dir, season=season, file_name=CALENDAR_FILE)

    unscraped_dates = _get_unscraped_dates(df_calendar=df_calendar, df_dates=df_dates)
    for date in unscraped_dates:
        time.sleep(4)
        games = _scrape_games_from_date(date=date)
        if not len(games):
            print(f"\033[93mWarning: No games found on {date}.\033[0m")
            continue
        unscraped_games = _get_unscraped_games(games=games, df_games=df_games)
        print(f"Scraping {date}: {len(games)} games.")
        for game in unscraped_games:
            time.sleep(4)
            # Scrape and save game information
            df_game = _scrape_game(game, date)
            df_games = pd.concat([df_games, df_game], ignore_index=True)
            _save_data(data_dir=data_dir, season=season, df=df_games, file_name=GAMES_FILE, index_col="game_id")
            # Scrape and save game stats
            df_stat = _scrape_game_stats(game)
            df_stats = pd.concat([df_stats, df_stat], ignore_index=True)
            _save_data(data_dir=data_dir, season=season, df=df_stats, file_name=STATS_FILE, index_col="game_id")
        # Save date information
        df_date = pd.DataFrame({'date': [date]})
        df_dates = pd.concat([df_dates, df_date], ignore_index=True)
        _save_data(data_dir=data_dir, season=season, df=df_dates, file_name=DATES_FILE, index_col="date")


def update_get_nba_stats(data_dir: str, season: int):
    """Scrapes, saves and loads NBA statistics."""
    _scrape_nba_season(data_dir=data_dir, season=season)
    print("Game stats up to date!")
    file_path = os.path.join(data_dir, str(season), STATS_FILE)
    df_stats = pd.read_csv(file_path)
    assert not df_stats.duplicated(subset=["game_id", "name"]).any(), f"Duplicated 'name'-'game_id' in {file_path}."
    return df_stats

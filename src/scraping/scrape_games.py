"""Scrape NBA games stats."""

import datetime
import re
import requests
import time
import pandas as pd
import numpy as np

from io import StringIO
from bs4 import BeautifulSoup
from src.database.supabase_utils import save_dataframe_to_supabase, load_dataframe_from_supabase
from src.database.table_names import CALENDAR_TABLE, GAMES_TABLE, STATS_TABLE
from src.scraping.utils import get_current_season

WEBSITE_URL = 'https://www.basketball-reference.com'


def _get_unscraped_dates(df_calendar: pd.DataFrame, df_games: pd.DataFrame) -> list[str]:
    """Generates a list of unscraped dates based on calendar and games tables."""
    all_dates = df_calendar['date'].values
    latest_date = datetime.date.today()
    all_dates = set([d for d in all_dates if datetime.datetime.strptime(d, "%Y-%m-%d").date() < latest_date])
    
    if df_games.empty:
        return sorted(list(all_dates))
    
    # Get dates that already have games scraped
    scraped_dates = set(df_games['date'].values)
    unscraped_dates = sorted(list(all_dates - scraped_dates))
    return unscraped_dates


def _get_game_id(game_element) -> str:
    """Gets game id from game HTML element."""
    game_url = game_element.find("td", class_='right gamelink').find('a', href=True)['href']
    game_id = re.findall('/boxscores/(\w+).html', game_url)[0]
    return game_id


def _get_unscraped_games(game_elements, df_games: pd.DataFrame) -> list:
    """Generates a list of unscraped game HTML elements."""
    if df_games.empty:
        return game_elements
    scraped_games_id = df_games.game_id.values
    unscraped_games = [game_element for game_element in game_elements if _get_game_id(game_element) not in scraped_games_id]
    return unscraped_games


def _scrape_game(game_element, date: str, season: int) -> pd.DataFrame:
    """Scrapes game information from HTML element."""
    df_game = pd.DataFrame({
        'game_id': _get_game_id(game_element),
        'date': date,
        'winner': [game_element.find('tr', class_='winner').find('a', href=True).text],
        'loser': [game_element.find('tr', class_='loser').find('a', href=True).text],
        'pts_winner': [game_element.find('tr', class_='winner').find(class_='right').text],
        'pts_loser': [game_element.find('tr', class_='loser').find(class_='right').text],
    })
    df_game['season'] = season
    return df_game


def _get_df_stats(dfs: list[pd.DataFrame], scores: list[int]) -> pd.DataFrame:
    """Combines the two team tables into a single one with players' stats."""
    df_stats = pd.DataFrame()
    for df, score in zip(dfs, scores):
        df.columns = [col[1].lower() for col in df.columns]
        df['start'] = (df.index < 5).astype(int)
        df['win'] = int(score > min(scores))
        df = df.rename(columns={'starters': 'player'})
        df = df.loc[~df['player'].isin(['Reserves', 'Team Totals']), :]
        df['mp'] = df['mp'].str.extract('^(\d+)')
        for col in df.columns[1:]:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df_stats = pd.concat([df_stats, df]).reset_index(drop=True)
    return df_stats


def _fetch_game_page_data(game_element) -> tuple[list[pd.DataFrame], list[int]]:
    """Fetches and parses the game page HTML to extract tables and scores."""
    game_url = game_element.find("td", class_='right gamelink').find('a', href=True)['href']
    soup = BeautifulSoup(requests.get(WEBSITE_URL + game_url).content, "lxml")
    scores = [int(s.text) for s in soup.find('div', class_='scorebox').find_all('div', class_='score')]
    tables = soup.find_all(lambda tag: tag.name == 'table' and tag.has_attr('id') and "game-basic" in tag['id'])
    dfs = [pd.read_html(StringIO(str(table)))[0] for table in tables]
    return dfs, scores


def _scrape_games_from_date(date: str) -> list:
    """Scrape all the game HTML elements from a date."""
    year, month, day = date.split("-")
    results_url = f'{WEBSITE_URL}/boxscores/?month={month}&day={day}&year={year}'
    soup = BeautifulSoup(requests.get(results_url).content, "lxml")
    game_elements = soup.find_all(lambda tag: tag.name == 'div' and tag.has_attr('class') and "game_summary" in tag['class'])
    return game_elements


def _clean_stats_dataframe(df_stats: pd.DataFrame) -> pd.DataFrame:
    """Clean and prepare stats dataframe for Supabase."""
    # Rename columns to match schema
    df_stats = df_stats.rename(columns={
        'fg%': 'fg_pct',
        '3p': 'three_p',
        '3pa': 'three_pa',
        '3p%': 'three_p_pct',
        'ft%': 'ft_pct',
        '+/-': 'plus_minus'
    })

    # Convert integer columns
    int_cols = ['fg', 'fga', 'three_p', 'three_pa', 'ft', 'fta', 'orb', 'drb', 'trb', 'ast', 'stl', 'blk', 'tov', 'pf', 'pts']
    for col in int_cols:
        df_stats[col] = pd.to_numeric(df_stats[col], errors='coerce').fillna(0).astype(int)

    # Convert boolean columns
    for col in ['start', 'win']:
        df_stats[col] = df_stats[col].astype(bool)
    
    # Replace NaN with None for JSON serialization
    df_stats = df_stats.replace([np.nan, np.inf, -np.inf], None)
    df_stats = df_stats.where(pd.notna(df_stats), None)
    
    return df_stats


def _scrape_game_stats(game_element, season) -> pd.DataFrame:
    """Scrapes NBA stats from game HTML element."""
    dfs, scores = _fetch_game_page_data(game_element)
    df_stats = _get_df_stats(dfs, scores)
    df_stats["game_id"] = _get_game_id(game_element)
    df_stats["season"] = season
    df_stats = _clean_stats_dataframe(df_stats)
    return df_stats


def scrape_games(season: int = None) -> None:
    """Scrapes NBA games and stats for a season and saves to Supabase."""
    if season is None:
        season = get_current_season()
    
    print(f"Scraping games for season {season}...")
    
    # Load calendar data from Supabase
    df_calendar = load_dataframe_from_supabase(CALENDAR_TABLE)
    df_calendar = df_calendar[df_calendar['season'] == season]
    
    # Load games data from Supabase
    df_games = load_dataframe_from_supabase(GAMES_TABLE)
    df_games = df_games[df_games['season'] == season] if not df_games.empty else pd.DataFrame()

    # Get unscraped dates
    unscraped_dates = _get_unscraped_dates(df_calendar=df_calendar, df_games=df_games)
    
    # Scrape games and stats for each unscraped date
    for date in unscraped_dates:
        time.sleep(4)
        game_elements = _scrape_games_from_date(date=date)
        if not len(game_elements):
            print(f"\033[93mWarning: No games found on {date}.\033[0m")
            continue
        print(f"  Scraping {date}: {len(game_elements)} games.")
        
        # Scrape each game
        for game_element in game_elements:
            time.sleep(4)
            
            # Scrape game information
            df_game = _scrape_game(game_element, date, season)
            
            # Save game to Supabase
            save_dataframe_to_supabase(
                df=df_game,
                table_name=GAMES_TABLE,
                index_columns=['game_id'],
                upsert=True,
            )
            
            # Update local df_games for checking unscraped games
            df_games = pd.concat([df_games, df_game], ignore_index=True)
            
            # Scrape game stats
            df_stat = _scrape_game_stats(game_element, season)
            
            # Save stats to Supabase
            save_dataframe_to_supabase(
                df=df_stat,
                table_name=STATS_TABLE,
                index_columns=['game_id', 'player'],
                upsert=True,
            )
    
    print(f"✓ Game stats up to date for season {season}!")

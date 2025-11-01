"""Scrape NBA games stats."""

import datetime
import re
import time
from io import StringIO

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.scraping.utils import clean_player_name, get_current_season
from src.supabase.tables import (
    TABLE_CALENDAR,
    TABLE_GAME_RESULTS,
    TABLE_STATS,
    TABLE_TEAMS,
)
from src.supabase.utils import load_dataframe_from_supabase, save_dataframe_to_supabase


WEBSITE_URL = "https://www.basketball-reference.com"


def _get_unscraped_dates(df_calendar: pd.DataFrame, df_games: pd.DataFrame) -> list[str]:
    """Generates a list of unscraped dates based on calendar and games tables."""
    
    # Get all dates from calendar before today
    df_all_dates = df_calendar.groupby("date").size().reset_index(name="games")
    df_all_dates = df_all_dates[df_all_dates["date"] < str(datetime.date.today())]
    
    # If no dates have already been scraped, scrape all dates until today
    if df_games.empty:
        return df_all_dates["date"].values

    # Get dates that already have games scraped
    df_scraped_dates = (
        df_games.groupby("date")
        .agg(scraped_games=("game_id", "nunique"))
        .reset_index()
    )

    # Join all dates with scraped dates
    df_joined = pd.merge(
        df_all_dates,
        df_scraped_dates,
        on="date",
        how="left",
    ).fillna(0)

    # Identify unscraped dates
    df_unscraped = df_joined[df_joined["games"] > df_joined["scraped_games"]]
    return df_unscraped["date"].values


def _get_game_id(game_element) -> str:
    """Gets game id from game HTML element."""
    game_url = game_element.find("td", class_="right gamelink").find("a", href=True)["href"]
    game_id = re.findall(r"/boxscores/(\w+).html", game_url)[0]
    return game_id


def _scrape_game(
    game_element, date: str, season: int, team_mapping: dict
) -> pd.DataFrame:
    """Scrapes game information from HTML element and converts team names."""
    winner_short = game_element.find("tr", class_="winner").find("a", href=True).text
    loser_short = game_element.find("tr", class_="loser").find("a", href=True).text
    
    df_game = pd.DataFrame({
        "game_id": _get_game_id(game_element),
        "date": date,
        "team_winner": [team_mapping.get(winner_short, winner_short)],
        "team_loser": [team_mapping.get(loser_short, loser_short)],
        "pts_winner": [
            game_element.find("tr", class_="winner").find(class_="right").text
        ],
        "pts_loser": [
            game_element.find("tr", class_="loser").find(class_="right").text
        ],
    })
    df_game["season"] = season
    return df_game


def _scrape_player_ids(table) -> list[str]:
    """Extracts player IDs from table rows."""
    player_ids = []
    for row in table.find("tbody").find_all("tr"):
        th = row.find("th", {"data-stat": "player"})
        if th and th.find("a", href=True):
            player_url = th.find("a", href=True)["href"]
            player_id = re.findall(r"/players/\w/(\w+)\.html", player_url)
            player_ids.append(player_id[0] if player_id else None)
    return player_ids


def _get_df_stats(tables: list, scores: list[int]) -> pd.DataFrame:
    """Combines the two team tables into a single one with players' stats."""
    df_stats = pd.DataFrame()
    for table, score in zip(tables, scores):
        # Parse table data
        df = pd.read_html(StringIO(str(table)))[0]
        df.columns = [col[1].lower() for col in df.columns]
        df["start"] = (df.index < 5).astype(int)
        df["win"] = int(score > min(scores))
        df = df.rename(columns={"starters": "player"})
        
        # Filter out rows without valid player data
        df = df.loc[~df["player"].isin(["Reserves", "Team Totals"]), :]
        df["mp"] = df["mp"].str.extract(r"^(\d+)")
        df["player_id"] = _scrape_player_ids(table)
        for col in df.columns[1:]:
            if col not in ["player", "player_id"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df_stats = pd.concat([df_stats, df]).reset_index(drop=True)
    return df_stats


def _fetch_game_page_data(game_element) -> tuple[list, list[int]]:
    """Fetches and parses the game page HTML to extract tables and scores."""
    time.sleep(4) # Basketball Reference rate is 20 requests per minute
    game_url = game_element.find("td", class_="right gamelink").find("a", href=True)["href"]
    soup = BeautifulSoup(requests.get(WEBSITE_URL + game_url).content, "lxml")
    scores = [int(s.text) for s in soup.find("div", class_="scorebox").find_all("div", class_="score")]
    tables = soup.find_all(lambda tag: tag.name == "table" and tag.has_attr("id") and "game-basic" in tag["id"])
    return tables, scores


def _scrape_games_from_date(date: str) -> list:
    """Scrape all the game HTML elements from a date."""
    time.sleep(4) # Basketball Reference rate is 20 requests per minute
    year, month, day = date.split("-")
    results_url = f"{WEBSITE_URL}/boxscores/?month={month}&day={day}&year={year}"
    soup = BeautifulSoup(requests.get(results_url).content, "lxml")
    game_elements = soup.find_all(lambda tag: tag.name == "div" and tag.has_attr("class") and "game_summary" in tag["class"])
    return game_elements


def _clean_stats_dataframe(df_stats: pd.DataFrame) -> pd.DataFrame:
    """Clean and prepare stats dataframe for Supabase."""
    
    # Rename columns to match schema
    df_stats = df_stats.rename(columns={
        "3p": "tp",
        "3pa": "tpa",
        "+/-": "pm",
    })

    # Clean player names: remove accents and punctuation
    df_stats["player"] = df_stats["player"].apply(clean_player_name)

    # Drop percentage columns (can be calculated from made/attempted)
    pct_cols = ["fg%", "3p%", "ft%"]
    df_stats = df_stats.drop(columns=[col for col in pct_cols if col in df_stats.columns], errors="ignore")

    # Convert integer columns
    int_cols = ["mp", "fg", "fga", "tp", "tpa", "ft", "fta", "orb", "drb", "trb",
                "ast", "stl", "blk", "tov", "pf", "pts", "pm"]
    for col in int_cols:
        df_stats[col] = pd.to_numeric(df_stats[col], errors="coerce").fillna(0).astype(int)
    
    # Convert float columns
    float_cols = ["gmsc"]
    for col in float_cols:
        df_stats[col] = pd.to_numeric(df_stats[col], errors="coerce").fillna(0.0).astype(float)

    # Convert boolean columns
    for col in ["start", "win"]:
        df_stats[col] = df_stats[col].astype(bool)

    # Replace NaN with None for JSON serialization
    df_stats = df_stats.replace([np.nan, np.inf, -np.inf], None)
    df_stats = df_stats.where(pd.notna(df_stats), None)

    return df_stats


def _scrape_game_stats(game_element, season) -> pd.DataFrame:
    """Scrapes NBA stats from game HTML element."""
    tables, scores = _fetch_game_page_data(game_element)
    df_stats = _get_df_stats(tables, scores)
    df_stats["game_id"] = _get_game_id(game_element)
    df_stats["season"] = season
    df_stats = _clean_stats_dataframe(df_stats)
    return df_stats


def scrape_games(season: int = None) -> int:
    """Scrapes NBA games and stats for a season and saves to Supabase."""
    if season is None:
        season = get_current_season()

    print(f"Scraping games for season {season}...")

    # Load calendar data from Supabase
    df_calendar = load_dataframe_from_supabase(TABLE_CALENDAR.name, {"season": season})

    # Load games data from Supabase
    df_games = load_dataframe_from_supabase(
        TABLE_GAME_RESULTS.name, {"season": season}
    )

    # Load teams table for team_short to team mapping
    df_teams = load_dataframe_from_supabase(TABLE_TEAMS.name)
    team_mapping = dict(zip(df_teams["team_short"], df_teams["team"]))

    # Get unscraped dates
    unscraped_dates = _get_unscraped_dates(df_calendar=df_calendar, df_games=df_games)

    # Initialize counter for new games
    new_games_count = 0

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

            # Scrape game information with team name conversion
            df_game = _scrape_game(game_element, date, season, team_mapping)

            # Scrape game stats
            df_stats = _scrape_game_stats(game_element, season)

            # Save stats to Supabase
            save_dataframe_to_supabase(
                df=df_stats,
                table_name=TABLE_STATS.name,
                index_columns=["game_id", "player_id"],
                upsert=True,
            )
            
            # Save game to Supabase
            save_dataframe_to_supabase(
                df=df_game,
                table_name=TABLE_GAME_RESULTS.name,
                index_columns=["game_id"],
                upsert=True,
            )
            
        # Increment new games count by number of games scraped
        new_games_count += len(game_elements)

    print(f"✓ Game stats up to date for season {season}!")
    return new_games_count

if __name__ == "__main__":
    n = scrape_games()
    print(f"Scraped {n} new games.")

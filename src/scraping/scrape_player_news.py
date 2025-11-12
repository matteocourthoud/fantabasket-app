"""Scrape player-related news headlines and save to Supabase."""

import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.database.tables import TABLE_PLAYER_NEWS
from src.database.utils import load_dataframe_from_supabase, save_dataframe_to_supabase


ROTOWIRE_SEARCH = "https://www.rotowire.com/search.php?sport=NBA&term={player}"


def _load_player_news(player: str) -> pd.DataFrame:
    """Load existing news for a specific player from Supabase."""
    return load_dataframe_from_supabase(
        table_name=TABLE_PLAYER_NEWS.name,
        filters={"player": player},
    )


def _get_df_player_news(player: str) -> pd.DataFrame:
    """Scrape Rotowire news for a player using requests and return a DataFrame."""
    url = ROTOWIRE_SEARCH.format(player=player)
    print(url)
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        text_news = soup.select("div.news-update__news")[0].get_text().strip()
        text_analysis = soup.select("div.news-update__analysis")[0].get_text().strip()
        text = text_news + "\n\n" + text_analysis.replace("ANALYSIS", "")
        now = datetime.datetime.now(datetime.UTC).isoformat()
        return pd.DataFrame([{"player": player, "news": text, "scraped_at": now}])
    except Exception as e:
        print(f"Error scraping news for {player} at {url}: {e}")
        return pd.DataFrame()


def scrape_player_news(player: str) -> pd.DataFrame:
    """Scrape Rotowire news for a specific player and return a DataFrame."""
    # Check if we already have news for this player, from today
    existing_news = _load_player_news(player)
    if (not existing_news.empty):
        if pd.to_datetime(
            existing_news.iloc[0]["scraped_at"], utc=True
        ).date() == pd.Timestamp.now(tz="UTC").date():
            return existing_news

    # Scrape page content
    df = _get_df_player_news(player)

    # Save news to Supabase
    save_dataframe_to_supabase(
        df=df[["player", "news", "scraped_at"]],
        table_name=TABLE_PLAYER_NEWS.name,
        index_columns=["player"],
        upsert=True,
    )

    return df

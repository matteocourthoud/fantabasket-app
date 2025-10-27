"""Scrape player-related news headlines and save to Supabase."""

import datetime

import pandas as pd
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.scraping.utils import get_chrome_driver
from src.supabase.tables import TABLE_PLAYER_NEWS
from src.supabase.utils import load_dataframe_from_supabase, save_dataframe_to_supabase


ROTOWIRE_SEARCH = "https://www.rotowire.com/search.php?sport=NBA&term={player}"


def _load_player_news(player: str) -> pd.DataFrame:
    """Load existing news for a specific player from Supabase."""
    return load_dataframe_from_supabase(
        table_name=TABLE_PLAYER_NEWS.name,
        filters={"player": player},
    )

def _scrape_player_news(player: str) -> pd.DataFrame:
    """Scrape Rotowire news for a specific player and return a DataFrame."""
    
    # Check if we already have news for this player, from today
    existing_news = _load_player_news(player)
    if (not existing_news.empty):
        if pd.to_datetime(
            existing_news.iloc[0]["scraped_at"], utc=True
        ).date() == pd.Timestamp.now(tz="UTC").date():
            return existing_news
    
    # Scrape page content
    url = ROTOWIRE_SEARCH.format(player=player)
    driver = get_chrome_driver()
    driver.get(url)
    
    # Parse news content
    try:
        WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.news-update"))
        )
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        div = soup.select("div.news-update__news")[0]
        text = div.get_text(separator=" ", strip=True)
        now = datetime.datetime.now(datetime.UTC).isoformat()
        df = pd.DataFrame([{"player": player, "news": text, "scraped_at": now}])
    except Exception as e:
        print(f"Error scraping news for {player} at {url}: {e}")
        return pd.DataFrame()
    
    # Save news to Supabase
    save_dataframe_to_supabase(
        df=df[["player", "news", "scraped_at"]],
        table_name=TABLE_PLAYER_NEWS.name,
        index_columns=["player"],
        upsert=True,
    )
    
    return df

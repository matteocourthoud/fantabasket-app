"""Utility functions for scraping."""

import re
import unicodedata
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def get_current_season() -> int:
    """Get the current NBA season year (month of last September)."""
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    if current_month < 9:
        return current_year - 1
    return current_year


def get_chrome_driver() -> webdriver.Chrome:
    """Initialize and return a headless Chrome WebDriver for Selenium scraping."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)
    return driver


def clean_player_name(name: str) -> str:
    """Remove accents and non-letter characters from a player name."""
    s = str(name)
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^A-Za-z\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

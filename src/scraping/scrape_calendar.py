"""Scrape NBA games stats."""

import time

import pandas as pd
from src.database.table_names import TABLE_CALENDAR

from src.scraping.utils import get_current_season
from src.database.utils import save_dataframe_to_supabase


MONTHS = ["october", "november", "december", "january", "february", "march", "april"]


def scrape_calendar(season: int = None) -> None:
    """Scrapes NBA calendar for a season and saves to Supabase."""
    if season is None:
        season = get_current_season()

    # Scrape calendar data
    print(f"Scraping calendar for season {season}...")
    df_calendar = pd.DataFrame()
    for month in MONTHS:
        print(f"  Scraping {month.capitalize()}...")
        time.sleep(4) # Basketball Reference rate is 20 requests per minute
        url = f"https://www.basketball-reference.com/leagues/NBA_{season+1}_games-{month}.html"
        df = pd.read_html(url)[0]
        df = df[["Date", "Visitor/Neutral", "Home/Neutral"]]
        df.columns = ["date", "team_visitor", "team_home"]
        df["date"] = pd.to_datetime(df["date"])
        df_calendar = pd.concat([df_calendar, df]).reset_index(drop=True)

    # Add season column
    df_calendar["season"] = season

    # Sort by date
    df_calendar = df_calendar.sort_values(by="date", ignore_index=True)

    # Convert date to string for JSON serialization
    df_calendar["date"] = df_calendar["date"].dt.strftime("%Y-%m-%d")

    # Save to Supabase
    save_dataframe_to_supabase(
        df=df_calendar,
        table_name=TABLE_CALENDAR.name,
        index_columns=["season", "date", "team_home"],
        upsert=True,
    )


if __name__ == "__main__":
    scrape_calendar()

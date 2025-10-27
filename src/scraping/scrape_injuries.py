"""Scrapes NBA players' injuries from www.cbssports.com/nba/injuries/."""

from datetime import datetime

import pandas as pd

from src.supabase.tables import TABLE_INJURIES
from src.supabase.utils import save_dataframe_to_supabase


WEBSITE_URL = "https://www.cbssports.com/nba/injuries/"


def _combine_dfs_injuries(dfs: list[pd.DataFrame]) -> pd.DataFrame:
    """Combines single dataframes from www.cbssports.com into one."""
    df_injuries = pd.DataFrame()
    for df in dfs:
        if ("Player" not in df.columns) | ("Injury Status" not in df.columns):
            pass
        df = df[["Player", "Injury Status"]]
        df.columns = ["player", "status"]
        df_injuries = pd.concat([df_injuries, df]).reset_index(drop=True)
    return df_injuries


def _clean_df_injuries(df_injuries: pd.DataFrame) -> pd.DataFrame:
    """Cleans dataframe with injuries information."""
    df_injuries = df_injuries.reset_index(drop=True)
    names = df_injuries["player"].values
    for i in range(len(names)):
        first_name = names[i].split(" ")[-1]
        name_index = names[i].find(first_name) + len(first_name)
        names[i] = names[i][name_index:]
    df_injuries["player"] = names
    return df_injuries


def scrape_injuries() -> None:
    """Scrapes NBA injured players and saves to Supabase."""
    print("Scraping injuries...")

    # Scrape and clean dataframe with injuries
    dfs = pd.read_html(WEBSITE_URL)
    df_injuries = _combine_dfs_injuries(dfs)
    df_injuries = _clean_df_injuries(df_injuries)
    df_injuries = df_injuries.sort_values(by="player", ignore_index=True)
    df_injuries["scraped_at"] = pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M")

    # Save to Supabase (upsert will update all existing records with fresh data)
    save_dataframe_to_supabase(
        df=df_injuries,
        table_name=TABLE_INJURIES.name,
        index_columns=["player"],
        upsert=True,
        replace=True,
    )

    print(f"✓ Scraped {len(df_injuries)} injuries and saved to Supabase")


if __name__ == "__main__":
    scrape_injuries()

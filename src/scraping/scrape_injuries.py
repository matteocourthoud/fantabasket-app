"""Scrapes NBA players' injuries from www.cbssports.com/nba/injuries/."""

from datetime import datetime
import pandas as pd
from src.database.supabase_utils import save_dataframe_to_supabase
from src.database.table_names import INJURIES_TABLE

WEBSITE_URL = 'https://www.cbssports.com/nba/injuries/'


def _combine_dfs_injuries(dfs: list[pd.DataFrame]) -> pd.DataFrame:
    """Combines single dataframes from www.cbssports.com into one."""
    df_injuries = pd.DataFrame()
    for df in dfs:
        if ('Player' not in df.columns) | ('Injury Status' not in df.columns):
            pass
        df = df[['Player', 'Injury Status']]
        df.columns = ['name', 'status']
        df_injuries = pd.concat([df_injuries, df]).reset_index(drop=True)
    return df_injuries


def _clean_df_injuries(df_injuries: pd.DataFrame) -> pd.DataFrame:
    """Cleans dataframe with injuries information."""
    df_injuries = df_injuries.reset_index(drop=True)
    names = df_injuries['name'].values
    for i in range(len(names)):
        first_name = names[i].split(" ")[-1]
        name_index = names[i].find(first_name) + len(first_name)
        names[i] = names[i][name_index:]
    df_injuries['name'] = names
    df_injuries['status'] = df_injuries['status'].str.replace('Expected to be out until at least ', '')
    df_injuries['status'] = df_injuries['status'].str.replace('Game Time Decision', 'gtd')
    return df_injuries


def scrape_injuries(table_name: str = INJURIES_TABLE) -> None:
    """Scrapes NBA injured players and saves to Supabase."""
    print("Scraping injuries...")
    
    # Scrape and clean dataframe with injuries
    dfs = pd.read_html(WEBSITE_URL)
    df_injuries = _combine_dfs_injuries(dfs)
    df_injuries = _clean_df_injuries(df_injuries)
    df_injuries = df_injuries.sort_values(by="name", ignore_index=True)
    df_injuries['scraped_at'] = datetime.now().isoformat()
    
    # Save to Supabase (upsert will update all existing records with fresh data)
    save_dataframe_to_supabase(
        df=df_injuries,
        table_name=table_name,
        index_columns=["name"],
        upsert=True,
        replace=True,
    )

"""
Scrape NBA games stats.
Author: Matteo Courthoud
Date: 22/10/2022
"""
import os
import pandas as pd

INJURIES_FILE = 'injuries.csv'
WEBSITE_URL = 'https://www.cbssports.com/nba/injuries/'


def _combine_dfs_injuries(dfs):
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
    for i in range(len(df_injuries)):
        first_name = df_injuries['name'][i].split(" ")[-1]
        name_index = df_injuries['name'][i].find(first_name) + len(first_name)
        df_injuries['name'][i] = df_injuries['name'][i][name_index:]
    df_injuries['status'] = df_injuries['status'].str.replace('Expected to be out until at least ', '')
    df_injuries['status'] = df_injuries['status'].str.replace('Game Time Decision', 'gtd')
    return df_injuries


def _scrape_injuries() -> pd.DataFrame:
    """Scrapes data on NBA injured players"""
    dfs = pd.read_html(WEBSITE_URL)
    df_injuries = _combine_dfs_injuries(dfs)
    df_injuries = _clean_df_injuries(df_injuries)
    return df_injuries


def update_get_nba_injuries(data_dir: str, update: bool = False):
    """Updates and returns dataframe with injured NBA players."""
    file_path = os.path.join(data_dir, INJURIES_FILE)
    if update:
        try:
            df_injuries = _scrape_injuries()
            df_injuries.to_csv(file_path, index=False)
        except Exception as e:
            print(e)
    df_injuries = pd.read_csv(file_path)
    return df_injuries

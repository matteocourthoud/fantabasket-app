"""Scrape NBA lineups for the next game for each team using BeautifulSoup and requests."""

from io import StringIO

import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.database.tables import TABLE_LINEUPS, TABLE_TEAMS
from src.database.utils import load_dataframe_from_supabase, save_dataframe_to_supabase
from src.scraping.utils import clean_player_name


WEBSITE_URL = "https://basketballmonster.com/nbalineups.aspx"


def _remove_suffixes(strings: list[str]) -> tuple[list[str], list[str]]:
    suffixes = {
        "Q": "questionable",
        "P": "probable",
        "IN": "injured",
        "Off Inj": "off injury",
    }
    cleaned_strings = []
    statuses = []
    for s in strings:
        status = ""
        for suffix in suffixes:
            if s.endswith(suffix):
                s = s[:-len(suffix)]  # Remove the suffix
                status = suffixes[suffix]
                break  # Exit the loop once a suffix is removed
        statuses.append(status)
        cleaned_strings.append(s.strip())
    return cleaned_strings, statuses


def _parse_lineups_from_page(page_source: str, df_teams: pd.DataFrame) -> pd.DataFrame:
    """Parses lineups from the current page HTML.

    Args:
        page_source (str): HTML content of the page.
        df_teams (pd.DataFrame): DataFrame containing team mappings.

    Returns:
        pd.DataFrame: DataFrame with complete lineups.
    """
    df_lineups = pd.DataFrame()
    dfs = pd.read_html(StringIO(page_source))

    for df in dfs:
        for col in [1, 2]:
            # Extract team code from column header
            team_code = df.columns[col][1].replace("@ ", "")
            team_code = team_code if team_code != "NOR" else "NOP"

            # Check if lineup has null values (incomplete lineup)
            if df.iloc[:, col].isnull().any():
                continue

            team_name = df_teams.loc[
                df_teams["fanta_team"] == team_code, "team"
            ].values[0]
            players, statuses = _remove_suffixes(df.iloc[:, col].to_list())
            temp = pd.DataFrame(
                {
                    "team": [team_name] * 5,
                    "player": players,
                    "status": statuses,
                }
            )
            df_lineups = pd.concat([df_lineups, temp], ignore_index=True)

    return df_lineups


def _get_df_lineups() -> pd.DataFrame:
    """Fetches and parses the lineups page to get the lineups DataFrame."""
    
    # Load team mappings
    df_teams = load_dataframe_from_supabase(TABLE_TEAMS.name)
    
    # Fetch the page content
    response = requests.get(
        WEBSITE_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=10
    )
    response.raise_for_status()  # Raise an error for bad status codes

    # Parse the page content
    soup = BeautifulSoup(response.content, "html.parser")
    page_source = soup.prettify()

    # Parse lineups from the page
    df_lineups = _parse_lineups_from_page(page_source, df_teams)

    # Clean player names
    df_lineups["player"] = df_lineups["player"].apply(clean_player_name)

    # Validate no duplicates
    assert not df_lineups.duplicated(subset=["player"]).any(), \
        f"Duplicated found:\n{df_lineups[df_lineups.duplicated(subset=['player'])]}"
        
    return df_lineups


def scrape_lineups() -> int:
    """Scrapes NBA lineups from https://basketballmonster.com/nbalineups."""
    print("Scraping lineups...")

    # Get lineups DataFrame
    df_lineups = _get_df_lineups()

    # Save to Supabase
    save_dataframe_to_supabase(
        df=df_lineups,
        table_name=TABLE_LINEUPS.name,
        index_columns=["player"],
        replace=True,
    )

    # Compute number of teams with complete lineups
    teams_with_lineups = df_lineups["team"].nunique() if not df_lineups.empty else 0

    print("✓ Lineups updated.")
    return teams_with_lineups


if __name__ == "__main__":
    scrape_lineups()

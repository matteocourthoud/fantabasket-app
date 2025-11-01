"""Scrape NBA lineups for the next game for each team."""

import time
from io import StringIO

import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.scraping.utils import clean_player_name, get_chrome_driver
from src.supabase.tables import TABLE_LINEUPS, TABLE_TEAMS
from src.supabase.utils import load_dataframe_from_supabase, save_dataframe_to_supabase


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


def _parse_lineups_from_page(
    page_source: str,
    df_teams: pd.DataFrame,
    teams_found: set,
    teams_with_lineups: set,
) -> tuple[pd.DataFrame, set, set]:
    """Parses lineups from the current page HTML.
    
    Returns:
        df_lineups: DataFrame with complete lineups
        teams_found: Set of all team codes found (even without lineups)
        teams_with_lineups: Set of team codes with complete lineups

    """
    df_lineups = pd.DataFrame()
    dfs = pd.read_html(StringIO(page_source))

    for df in dfs:
        for col in [1, 2]:
            # Extract team code from column header
            team_code = df.columns[col][1].replace("@ ", "")
            team_code = team_code if team_code != "NOR" else "NOP"

            # Track that we found this team (even if lineup is incomplete)
            teams_found.add(team_code)

            # Check if lineup has null values (incomplete lineup)
            if df.iloc[:, col].isnull().any():
                continue

            # Check if we already have this team's lineup
            if team_code in teams_with_lineups:
                continue

            team_name = df_teams.loc[df_teams["fanta_team"] == team_code, "team"].values[0]
            players, statuses = _remove_suffixes(df.iloc[:, col].to_list())
            temp = pd.DataFrame({"team": [team_name]*5, "player": players, "status": statuses})
            df_lineups = pd.concat([df_lineups, temp], ignore_index=True)
            teams_with_lineups.add(team_code)

    return df_lineups, teams_found, teams_with_lineups


def _scrape_lineups() -> pd.DataFrame:
    """Scrapes next game lineups from basketballmonster.com using Selenium."""
    df_teams = load_dataframe_from_supabase(TABLE_TEAMS.name)

    # Initialize empty dataframe and sets
    df_lineups = pd.DataFrame()
    teams_found = set()  # All teams found (even without lineups)
    teams_with_lineups = set()  # Teams with complete lineups

    # Initialize Chrome driver
    driver = get_chrome_driver()

    # Load initial page
    driver.get(WEBSITE_URL)

    for day in range(10): # Limit to 10 iterations
        time.sleep(2)  # Wait for initial page load

        # Parse lineups from current page
        page_source = driver.page_source
        new_lineups, teams_found, teams_with_lineups = _parse_lineups_from_page(page_source, df_teams, teams_found, teams_with_lineups)
        df_lineups = pd.concat([df_lineups, new_lineups], ignore_index=True)

        print(f"Day {day + 1}: Found {len(teams_found)} teams ({len(teams_with_lineups)} with lineups)")

        # If we have all teams, break
        if len(teams_found) >= 30:
            break

        # Try to click "next" button to load next day
        try:
            next_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.NAME, "DateNextButton")),
            )
            next_button.click()
        except Exception as e:
            print(f"Could not find next button after day {day + 1}: {e}")
            break
        
    # Clean player names
    df_lineups["player"] = df_lineups["player"].apply(clean_player_name)

    # Report teams without lineups
    if len(teams_with_lineups) < len(teams_found):
        teams_without_lineups = teams_found - teams_with_lineups
        print(f"Note: {len(teams_without_lineups)} team(s) found without lineups: {teams_without_lineups}")

    # Report completely missing teams
    if len(teams_found) < 30:
        all_teams = set(df_teams["fanta_team"].values)
        missing_teams = all_teams - teams_found
        print(f"Warning: Only found {len(teams_found)} teams. Missing: {missing_teams}")

    driver.quit()
    return df_lineups


def scrape_lineups() -> int:
    """Scrapes NBA lineups from https://basketballmonster.com/nbalineups."""
    print("Scraping lineups...")

    # Scrape upcoming lineups
    df_lineups = _scrape_lineups()

    # Validate no duplicates
    assert not df_lineups.duplicated(subset=["player"]).any(), \
       f"Duplicated found:\n{df_lineups[df_lineups.duplicated(subset=['player'])]}"

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

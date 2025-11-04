"""Scrape player values."""

import pandas as pd
from selenium.webdriver.common.by import By

from src.scraping.utils import get_chrome_driver, get_current_season
from src.database.tables import TABLE_INITIAL_VALUES
from src.database.utils import save_dataframe_to_supabase


SEASON_ID_MAP = {
    2025: 25,
    2024: 19,
    2023: 13,
    2022: 9,
}


def _extract_dunkest_table(driver) -> pd.DataFrame:
    """Extracts the dunkest table from the current page of the webdriver."""
    rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
    data = []
    for row in rows:
        cols = row.find_elements(By.TAG_NAME, "td")
        
        # Extract player link from first column to get fanta_code and fanta_name
        player_link_element = cols[0].find_element(By.TAG_NAME, "a")
        player_link = player_link_element.get_attribute("href")
        
        # Parse fanta_code and fanta_name from link
        link_parts = player_link.rstrip("/").split("/")
        fanta_id = link_parts[-2] + "/" +  link_parts[-1]
        
        # Append all text data plus the extracted fanta_code and fanta_name
        row_data = [col.text for col in cols] + [fanta_id]
        data.append(row_data)

    df = pd.DataFrame(data).iloc[:, [-1, 0, 1, 4, 5, ]]
    df.columns = ["fanta_player_id", "fanta_player", "position", "value", "gain"]
    return df


def _scrape_values(url: str) -> pd.DataFrame:
    """Scrapes player values from dunkest.com using Selenium."""
    # Initialize chrome driver
    driver = get_chrome_driver()

    # Extract player data
    driver.get(url)
    driver.implicitly_wait(1)

    # Verify we're on the correct URL
    print(url)
    assert driver.current_url == url, \
        f"Expected URL:\n{url}\nGot URL:\n{driver.current_url}"

    # Try to dismiss cookie consent banner if present
    try:
        # Look for common cookie consent button selectors
        selector = ".iubenda-cs-accept-btn, button[class*='accept'], button[class*='cookie']"
        cookie_button = driver.find_element(By.CSS_SELECTOR, selector)
        cookie_button.click()
        driver.implicitly_wait(0.5)
    except Exception as e:
        print(f"Could not click cookie button: {e}")
        pass  # No cookie banner or already dismissed

    df_current_values = pd.DataFrame()
    page_num = 1
    while True:
        new_data = _extract_dunkest_table(driver)
        df_current_values = pd.concat([df_current_values, new_data])
        print(f"Scraped page {page_num}: total {len(df_current_values)} players.")

        driver.implicitly_wait(0.1)
        try:
            link = driver.find_element(By.LINK_TEXT, "»")
        except Exception:
            break

        # Use JavaScript click to bypass any overlay issues
        try:
            driver.execute_script("arguments[0].click();", link)
            page_num += 1
        except Exception as e:
            print(f"Could not click next page button: {e}")
            break

    driver.quit()
    return df_current_values


def _scrape_initial_values(season: int) -> pd.DataFrame:
    """Scrapes initial player values for a season from dunkest.com."""
    # Calculate season_id
    season_id = SEASON_ID_MAP.get(season)

    # Build URL for the first few weeks of the season
    url = f"https://www.dunkest.com/en/nba/stats/players/table/regular-season/{season}-{season+1}?"
    url += f"season_id={season_id}&mode=dunkest&stats_type=tot"
    url += "".join([f"&weeks[]={i}" for i in range(1, 3)])
    url += "".join([f"&teams[]={i}" for i in range(1, 31)])
    url += "&positions[]=1&positions[]=2&positions[]=3"
    url += "&player_search=&min_cr=4&max_cr=35&sort_by=pdk&sort_order=desc"

    # Scrape values
    df_values = _scrape_values(url)

    # Clean and format values DataFrame
    df_values["initial_rating"] = pd.to_numeric(df_values["value"]) - pd.to_numeric(
        df_values["gain"].str.replace("+", "").str.replace("−", "-"))
    df_values = df_values[["fanta_player_id", "fanta_player", "position", "initial_rating"]]
    df_values["season"] = season
    
    # Check for duplicates
    assert not df_values.duplicated(subset=["fanta_player_id"]).any(), \
        "Duplicated fanta_player_id in initial values."
    return df_values


def scrape_initial_values(season: int = None) -> None:
    """Scrapes initial player values for a season and saves to Supabase."""
    if season is None:
        season = get_current_season()

    # Scrape initial values
    print(f"Scraping initial values for season {season}...")
    df_initial_values = _scrape_initial_values(season)

    # Save to Supabase
    save_dataframe_to_supabase(
        df=df_initial_values,
        table_name=TABLE_INITIAL_VALUES.name,
        index_columns=["fanta_player_id", "season"],
        upsert=True,
    )
    
    print(f"✓ Initial values updated for season {season}.")


if __name__ == "__main__":
    scrape_initial_values()

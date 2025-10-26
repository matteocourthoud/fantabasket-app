"""Scrape player ratings."""

import pandas as pd
from selenium.webdriver.common.by import By
from supabase.utils import save_dataframe_to_supabase
from src.supabase.table_names import INITIAL_RATINGS_TABLE
from src.scraping.utils import get_current_season, get_chrome_driver

WEBSITE_URL = 'https://basketballmonster.com/nbalineups.aspx'


def _extract_dunkest_table(driver) -> pd.DataFrame:
    """Extracts the dunkest table from the current page of the webdriver."""
    rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
    data = []
    for row in rows:
        cols = row.find_elements(By.TAG_NAME, "td")
        data.append([col.text for col in cols])
        
    print(pd.DataFrame(data).iloc[:, :7])
    
    df = pd.DataFrame(data).iloc[:, [0, 2, 4, 5]]
    df.columns = ["name_short", "team_code", "dunkest_value", "plus"]
    return df


def _scrape_ratings(url: str) -> pd.DataFrame:
    """Scrapes player ratings from dunkest.com using Selenium."""
    # Initialize chrome driver
    driver = get_chrome_driver()

    # Extract player data
    driver.get(url)
    driver.implicitly_wait(1)
    
    # Verify we're on the correct URL
    assert driver.current_url == url, \
        f"""Could not load the page correctly. Expected URL:\n{url}\nGot URL:\n{driver.current_url}"""
    
    # Try to dismiss cookie consent banner if present
    try:
        # Look for common cookie consent button selectors
        cookie_button = driver.find_element(By.CSS_SELECTOR, ".iubenda-cs-accept-btn, button[class*='accept'], button[class*='cookie']")
        cookie_button.click()
        driver.implicitly_wait(0.5)
    except Exception:
        pass  # No cookie banner or already dismissed
    
    df_current_ratings = pd.DataFrame()
    page_num = 1
    while True:
        new_data = _extract_dunkest_table(driver)
        df_current_ratings = pd.concat([df_current_ratings, new_data])
        print(f"Scraped page {page_num}: {len(new_data)} players (total: {len(df_current_ratings)})")
        
        driver.implicitly_wait(0.1)
        try:
            link = driver.find_element(By.LINK_TEXT, '»')
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
    return df_current_ratings


def _scrape_initial_ratings(season: int) -> pd.DataFrame:
    """Scrapes initial player ratings for a season from dunkest.com."""
    # Calculate season_id
    season_id = season - 2000
    
    # Build URL for the first few weeks of the season
    url = f"https://www.dunkest.com/en/nba/stats/players/table?season_id={season_id}&mode=dunkest&stats_type=tot"
    url += "".join([f"&weeks[]={i}" for i in range(1, 3)])
    url += "".join([f"&teams[]={i}" for i in range(1, 31)])
    url += "&positions[]=1&positions[]=2&positions[]=3&player_search=&min_cr=4&max_cr=35&sort_by=pdk&sort_order=desc"
    
    # Scrape ratings
    df_ratings = _scrape_ratings(url)

    # Clean and format ratings DataFrame
    df_ratings["initial_rating"] = pd.to_numeric(df_ratings["dunkest_value"]) - pd.to_numeric(
        df_ratings["plus"].str.replace("+", "").str.replace("−", "-"))
    df_ratings = df_ratings[["name_short", "team_code", "initial_rating"]]
    df_ratings.rename(columns={"name_short": "player_short"}, inplace=True)
    df_ratings["season"] = season
    return df_ratings


def _remove_duplicates(df: pd.DataFrame, subset_columns: list[str]) -> pd.DataFrame:
    """Removes duplicate players and prints information about them."""
    initial_count = len(df)
    
    # Find and print duplicates before removing them
    duplicates_mask = df.duplicated(subset=subset_columns, keep=False)
    if duplicates_mask.any():
        duplicate_players = df[duplicates_mask].sort_values(by=subset_columns)
        print(f"\nFound {duplicates_mask.sum()} duplicate entries for {len(duplicate_players.groupby(subset_columns))} players:")
        for group_keys, group_df in duplicate_players.groupby(subset_columns):
            print(f"  {group_keys}: {list(group_df['initial_rating'].values)}")
    
    df = df.drop_duplicates(subset=subset_columns, keep="first")
    
    if len(df) < initial_count:
        print(f"\nNote: Removed {initial_count - len(df)} duplicate entries")
    
    return df


def scrape_initial_ratings(season: int = None) -> None:
    """Scrapes initial player ratings for a season and saves to Supabase."""
    if season is None:
        season = get_current_season()
    
    print(f"Scraping initial ratings for season {season}...")
    df_initial_ratings = _scrape_initial_ratings(season)
    df_initial_ratings = df_initial_ratings.round({"initial_rating": 1})
    
    # Remove duplicates (keep first occurrence)
    df_initial_ratings = _remove_duplicates(df_initial_ratings, ["player_short", "team_code"])
    
    # Save to Supabase
    save_dataframe_to_supabase(
        df=df_initial_ratings,
        table_name=INITIAL_RATINGS_TABLE,
        index_columns=['player_short', 'team_code', 'season'],
        upsert=True,
    )
    
    print(f"✓ Initial ratings updated for season {season}. Saved {len(df_initial_ratings)} player ratings.")

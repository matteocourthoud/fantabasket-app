"""Scrape player ratings."""

import os
from datetime import datetime

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

SEASON = 2024
INITIAL_RATINGS_FILE = "%initial_ratings.csv"
RATINGS_FILE = "%ratings.csv"
WEBSITE_URL = 'https://basketballmonster.com/nbalineups.aspx'


def _extract_dunkest_table(driver) -> pd.DataFrame:
    # Locate the table rows
    rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
    data = []
    for row in rows:
        cols = row.find_elements(By.TAG_NAME, "td")
        data.append([col.text for col in cols])
        df = pd.DataFrame(data).iloc[:, [0, 4, 5]]
    df.columns = ["name_short", "dunkest_value", "plus"]
    return df


def _scrape_ratings(url: str) -> pd.DataFrame:
    # Initialize chrome driver
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    driver = webdriver.Chrome(options=chrome_options)

    # Extract player data
    driver.get(url)
    driver.implicitly_wait(1)
    df_current_ratings = pd.DataFrame()
    while True:
        df_current_ratings = pd.concat([df_current_ratings, _extract_dunkest_table(driver)])
        driver.implicitly_wait(0.1)
        try:
            link = driver.find_element(By.LINK_TEXT, '»')
        except:
            break
        link.click()
    driver.quit()
    return df_current_ratings


def _update_ratings(data_dir: str, season: int) -> pd.DataFrame:
    file_path = os.path.join(data_dir, RATINGS_FILE % season)
    date_today = datetime.now().date()

    if os.path.exists(file_path):
        df_ratings = pd.read_csv(file_path)
        if date_today in df_ratings.date.unique():
            return df_ratings
    else:
        df_ratings = pd.DataFrame()

    print("Scraping ratings...")
    url = f"https://www.dunkest.com/en/nba/stats/players/table?season_id={season - 2005}&mode=dunkest"
    df_current_ratings = _scrape_ratings(url=url)[["name_short", "rating"]]
    df_current_ratings["date"] = date_today
    df_ratings = pd.concat([df_ratings, df_current_ratings])
    df_ratings.to_csv(file_path, index=False)
    return df_ratings


def _scrape_initial_ratings() -> pd.DataFrame:
    # Extract player data
    url = "https://www.dunkest.com/en/nba/stats/players/table?season_id=19&mode=dunkest&stats_type=tot"
    url += "".join([f"&weeks[]={i}" for i in range(1, 6)])
    url += "".join([f"&teams[]={i}" for i in range(1, 31)])
    url += "&positions[]=1&positions[]=2&positions[]=3&player_search=&min_cr=4&max_cr=35&sort_by=pdk&sort_order=desc"
    print("Verify that url works: \n", url)

    df_ratings = _scrape_ratings(url)
    df_ratings["initial_rating"] = pd.to_numeric(df_ratings["dunkest_value"]) - pd.to_numeric(
        df_ratings["plus"].str.replace("+", "").str.replace("−", "-"))
    df_ratings = df_ratings[["name_short", "initial_rating"]]
    return df_ratings


def update_get_initial_ratings(data_dir: str, season: int) -> pd.DataFrame:
    file_path = os.path.join(data_dir, str(season), INITIAL_RATINGS_FILE)
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    else:
        print("Scraping initial ratings")
        df_ratings = _scrape_initial_ratings()
        df_ratings.round(1).to_csv(file_path, index=False)
        return df_ratings

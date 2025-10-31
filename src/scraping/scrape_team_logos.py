"""Scrape NBA team logos from Basketball Reference and save locally."""

import os
import time

import requests
from bs4 import BeautifulSoup

from src.supabase.tables import TABLE_TEAMS
from src.supabase.utils import load_dataframe_from_supabase


DATA_DIR = os.path.join(os.path.dirname(__file__), "../../data/teams/")
os.makedirs(DATA_DIR, exist_ok=True)

BASE_URL = "https://www.basketball-reference.com/teams/{}.html"


def get_team_logos():
    teams_df = load_dataframe_from_supabase(TABLE_TEAMS.name)
    for _, row in teams_df.iterrows():
        fanta_team = row["fanta_team"]
        if not fanta_team:
            continue
        # Use 'NOL' instead of 'NOP' for scraping and saving
        team_code = "NOP/2026" if fanta_team == "NOP" else fanta_team
        url = BASE_URL.format(team_code)
       
        # Check if logo file already exists (any extension)
        existing = [fn for fn in os.listdir(DATA_DIR) if fn.startswith(fanta_team + ".")]
        if existing:
            print(f"Logo already exists for {fanta_team}, skipping.")
            continue
        try:
            time.sleep(4)
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            img = soup.find("img", class_="teamlogo")
            if not img or not img.get("src"):
                print(f"No logo found for {fanta_team} at {url}")
                continue
            img_url = img["src"]
            ext = os.path.splitext(img_url)[-1].split("?")[0] or ".png"
            img_data = requests.get(img_url, timeout=10).content
            out_path = os.path.join(DATA_DIR, f"{fanta_team}{ext}")
            with open(out_path, "wb") as f:
                f.write(img_data)
            print(f"Saved logo for {fanta_team} -> {out_path}")
        except Exception as e:
            print(f"Error fetching logo for {fanta_team}: {e}")

if __name__ == "__main__":
    get_team_logos()

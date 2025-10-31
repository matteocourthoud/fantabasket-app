"""Scrape NBA player images from Basketball Reference and save locally."""

import os
import time

import requests
from bs4 import BeautifulSoup

from src.supabase.tables import TABLE_PLAYERS
from src.supabase.utils import load_dataframe_from_supabase


DATA_DIR = os.path.join(os.path.dirname(__file__), "../../data/players/")
os.makedirs(DATA_DIR, exist_ok=True)

BASE_URL = "https://www.basketball-reference.com/players/{}/{}.html"


def get_player_images():
    players_df = load_dataframe_from_supabase(TABLE_PLAYERS.name)
    for _, row in players_df.iterrows():
        player_id = row.get("player_id")
        if not player_id or not isinstance(player_id, str) or len(player_id) < 2:
            continue
        url = BASE_URL.format(player_id[0], player_id)
        out_path = os.path.join(DATA_DIR, f"{player_id}.jpg")
        if os.path.exists(out_path):
            print(f"Image already exists for {player_id}, skipping.")
            continue
        try:
            print(f"Fetching {url}")
            time.sleep(4)
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            # Find the tag with itemscope="image"
            itemscope_tag = soup.find(attrs={"itemscope": "image"})
            img = None
            if itemscope_tag:
                img = itemscope_tag.find("img")
            if not img or not img.get("src"):
                print(f"No image found for {player_id} at {url}")
                continue
            img_url = img["src"]
            img_data = requests.get(img_url, timeout=10).content
            with open(out_path, "wb") as f:
                f.write(img_data)
            print(f"Saved image for {player_id} -> {out_path}")
        except Exception as e:
            print(f"Error fetching image for {player_id}: {e}")

if __name__ == "__main__":
    get_player_images()

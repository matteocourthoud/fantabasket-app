"""Main file to prepare data for the fantabasket dashboard."""

import os
import pandas as pd

from scraping.scrape_calendar import update_get_nba_calendar
from scraping.scrape_injuries import update_get_nba_injuries
from scraping.scrape_next_lineups import update_get_next_lineups
from scraping.scrape_games import update_get_nba_stats
from model.compute_fanta_stats import update_get_fantabasket_stats
from model.predict_gain import GainModel

DATA_DIR = "../data"
SEASON = 2024

if __name__ == '__main__':
    # Load game data
    df_games = pd.read_csv(os.path.join(DATA_DIR, str(SEASON), "games.csv"))

    # Scrape calendar
    df_calendar = update_get_nba_calendar(data_dir=DATA_DIR, season=SEASON)

    # Scrape injuries
    df_injuries = update_get_nba_injuries(data_dir=DATA_DIR, update=True)

    # Scrape lineups
    df_lineups = update_get_next_lineups(data_dir=DATA_DIR, season=SEASON)

    # Scrape stats
    df_stats = update_get_nba_stats(data_dir=DATA_DIR, season=SEASON)

    # Compute fantabasket stats
    df_fanta_stats = update_get_fantabasket_stats(data_dir=DATA_DIR, season=SEASON, df_stats=df_stats)

    # Compute predicted gain
    gm = GainModel(data_dir=DATA_DIR, season=SEASON, df_calendar=df_calendar, df_injuries=df_injuries,
                   df_games=df_games, df_fanta_stats=df_fanta_stats)
    df_predicted_gain = gm.update_get_predicted_gain()

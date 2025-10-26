"""Predict players for Dunkest.
Author: Matteo Courthoud
Date: 22/10/2022
"""
import os

import numpy as np
import pandas as pd
from model.compute_stats import FantabasketStats
from model.predict_gain import GainModel

from src.scraping.scrape_games import Scraper

CALENDAR_FILE = "calendar.csv"
GAMES_FILE = "games.csv"
INJURIES_FILE = "injuries.csv"
CURRENT_STATS_FILE = "current_stats.csv"


def test_model(model: GainModel):
    # Get stats and test
    df_stats = model._get_season_stats_with_injuries()
    scores = np.zeros(10)
    dates = df_stats.sort_values("date").date.unique()
    for i, date in enumerate(dates[-10:]):
        df_train = df_stats[(df_stats.date < date) & (pd.isna(df_stats.status))].copy()
        df_test = df_stats[(df_stats.date == date) & (df_stats.name.isin(df_train.name.unique()))].copy()

        # Evaluate model
        model = model._fit_model_gain(df_train)
        df_test = model._predict_gain(df_test, model)
        df_test = df_test[["name", "fanta_value", "fanta_gain", "predicted_gain"]]
        scores[i] = df_test.iloc[:20, 2].mean()
        print(f"{pd.to_datetime(date): %Y-%m-%d} score: {scores[i]: .4f}")
    print(f"      TOTAL score: {np.sum(scores): .4f}: ")


if __name__ == "__main__":
    data_dir = "../../data"
    season = 2022
    # Import data
    df_calendar = pd.read_csv(os.path.join(data_dir, str(season), CALENDAR_FILE))
    df_games = pd.read_csv(os.path.join(data_dir, str(season), GAMES_FILE))
    df_injuries = pd.read_csv(os.path.join(data_dir, INJURIES_FILE))
    scraper = Scraper(data_dir=data_dir, season=season, df_calendar=df_calendar)
    df_nba_stats = scraper.update_get_nba_stats()
    fs = FantabasketStats(data_dir=data_dir, season=season, df_stats=df_nba_stats)
    df_current_stats = fs.update_get_fantabasket_stats(save=False)
    # Test model
    gm = GainModel(data_dir=data_dir, season=season,
                   df_calendar=df_calendar, df_injuries=df_injuries, df_games=df_games, df_stats=df_current_stats)
    test_model(gm)





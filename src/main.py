from scraping.scrape_calendar import update_get_nba_calendar
from scraping.scrape_injuries import update_get_nba_injuries
from scraping.scrape_games import Scraper
from model.compute_stats import FantabasketStats
from model.predict_gain import GainModel

DATA_DIR = "../data"
SEASON = 2023

if __name__ == '__main__':
    # Scrape calendar
    df_calendar = update_get_nba_calendar(data_dir=DATA_DIR, season=SEASON)

    # Scrape injuries
    df_injuries = update_get_nba_injuries(data_dir=DATA_DIR, update=True)

    # Scrape stats
    scraper = Scraper(data_dir=DATA_DIR, season=SEASON, df_calendar=df_calendar)
    df_stats = scraper.update_get_nba_stats()

    # Compute fantabasket stats
    ds = FantabasketStats(data_dir=DATA_DIR, season=SEASON, df_stats=df_stats)
    df_stats = ds.update_get_fantabasket_stats()
    df_games = ds.load_df("games.csv")

    # Compute predicted gain
    gm = GainModel(data_dir=DATA_DIR, season=SEASON, df_calendar=df_calendar, df_injuries=df_injuries,
                   df_games=df_games, df_stats=df_stats)
    df_predicted_gain = gm.update_get_predicted_gain()

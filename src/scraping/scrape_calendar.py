"""Scrape NBA games stats."""

import pandas as pd
from supabase.utils import save_dataframe_to_supabase, load_dataframe_from_supabase
from src.supabase.table_names import CALENDAR_TABLE, TEAMS_TABLE
from src.scraping.utils import get_current_season

WEBSITE_URL = 'https://www.basketball-reference.com'
MONTHS = ['october', 'november', 'december', 'january', 'february', 'march', 'april']


def scrape_calendar(season: int = None) -> None:
    """Scrapes NBA calendar for a season and saves to Supabase."""
    if season is None:
        season = get_current_season()
    
    print(f"Scraping calendar for season {season}...")
    
    # Load teams mapping from Supabase
    df_teams = load_dataframe_from_supabase(TEAMS_TABLE)
    team_names_map = dict(zip(df_teams['team_long'], df_teams['team']))
    
    df_calendar = pd.DataFrame()
    for month in MONTHS:
        print(f"  Scraping {month.capitalize()}...")
        df = pd.read_html(WEBSITE_URL + f'/leagues/NBA_{season+1}_games-{month}.html')[0]
        df = df[['Date', 'Visitor/Neutral', 'Home/Neutral']]
        df.columns = ['date', 'team_visitor', 'team_home']
        df['date'] = pd.to_datetime((df['date']))
        df_calendar = pd.concat([df_calendar, df]).reset_index(drop=True)
    
    # Clean team names using teams table
    for team in ['team_visitor', 'team_home']:
        df_calendar[team] = df_calendar[team].replace(team_names_map)
    
    # Add season column
    df_calendar['season'] = season
    
    # Sort by date
    df_calendar = df_calendar.sort_values(by="date", ignore_index=True)
    
    # Convert date to string for JSON serialization
    df_calendar['date'] = df_calendar['date'].dt.strftime('%Y-%m-%d')
    
    # Save to Supabase
    save_dataframe_to_supabase(
        df=df_calendar,
        table_name=CALENDAR_TABLE,
        index_columns=['season', 'date', 'team_home'],
        upsert=True
    )

"""
Scrape NBA games stats.
Author: Matteo Courthoud
Date: 22/10/2022
"""
import os.path
import pandas as pd

CALENDAR_FILE = 'calendar.csv'
WEBSITE_URL = 'https://www.basketball-reference.com'
MONTHS = ['october', 'november', 'december', 'january', 'february', 'march', 'april']
TEAM_NAMES_MAP = {
    'Brooklyn Nets': 'Brooklyn',
    'Golden State Warriors': 'Golden State',
    'Indiana Pacers': 'Indiana',
    'Chicago Bulls': 'Chicago',
    'Boston Celtics': 'Boston',
    'Washington Wizards': 'Washington',
    'Cleveland Cavaliers': 'Cleveland',
    'Houston Rockets': 'Houston',
    'Philadelphia 76ers': 'Philadelphia',
    'Orlando Magic': 'Orlando',
    'Oklahoma City Thunder': 'Oklahoma City',
    'Sacramento Kings': 'Sacramento',
    'Denver Nuggets': 'Denver',
    'Dallas Mavericks': 'Dallas',
    'Milwaukee Bucks': 'Milwaukee',
    'Los Angeles Clippers': 'LA Clippers',
    'New York Knicks': 'New York',
    'Charlotte Hornets': 'Charlotte',
    'Toronto Raptors': 'Toronto',
    'New Orleans Pelicans': 'New Orleans',
    'San Antonio Spurs': 'San Antonio',
    'Phoenix Suns': 'Phoenix',
    'Utah Jazz': 'Utah',
    'Atlanta Hawks': 'Atlanta',
    'Miami Heat': 'Miami',
    'Detroit Pistons': 'Detroit',
    'Memphis Grizzlies': 'Memphis',
    'Portland Trail Blazers': 'Portland',
    'Los Angeles Lakers': 'LA Lakers',
    'Minnesota Timberwolves': 'Minnesota',
}


def scrape_nba_calendar(season: int):
    """Scrapes calendar of all NBA games for a season."""
    df_calendar = pd.DataFrame()
    for month in MONTHS:
        df = pd.read_html(WEBSITE_URL + f'/leagues/NBA_{season+1}_games-{month}.html')[0]
        df = df[['Date', 'Visitor/Neutral', 'Home/Neutral']]
        df.columns = ['date', 'team_visitor', 'team_home']
        df['date'] = pd.to_datetime((df['date']))
        df_calendar = pd.concat([df_calendar, df]).reset_index(drop=True)
    # Clean team names
    for team in ['team_visitor', 'team_home']:
        df_calendar[team] = df_calendar[team].replace(TEAM_NAMES_MAP)
    return df_calendar


def update_get_nba_calendar(data_dir: str, season: int):
    """Loads NBA calendar."""
    file_path = os.path.join(data_dir, str(season), CALENDAR_FILE)
    if not os.path.exists(file_path):
        df_calendar = scrape_nba_calendar(season=season)
        df_calendar = df_calendar.sort_values(by="date", ignore_index=True)
        df_calendar.to_csv(file_path, index=False)
    df_calendar = pd.read_csv(file_path)
    return df_calendar

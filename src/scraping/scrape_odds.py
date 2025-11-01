"""Scrape NBA game odds from The Odds API."""

import os
from datetime import datetime

import pandas as pd
import requests
from dotenv import load_dotenv

from src.scraping.utils import get_current_season
from src.supabase.tables import TABLE_CALENDAR, TABLE_GAME_ODDS
from src.supabase.utils import load_dataframe_from_supabase, save_dataframe_to_supabase


# Load environment variables
load_dotenv()

ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
ODDS_API_KEY = os.getenv("ODDS_API_KEY")


def american_odds_to_probability(odds: int) -> float:
    """Convert American odds to implied probability."""
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)


def fetch_nba_odds() -> list[dict]:
    """Fetch NBA odds from The Odds API."""
    if not ODDS_API_KEY:
        raise ValueError("ODDS_API_KEY environment variable not set")
    
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
    }
    
    print("Fetching NBA odds from The Odds API...")
    
    try:
        response = requests.get(ODDS_API_URL, params=params, timeout=10)
        response.raise_for_status()
        
        # Check remaining requests
        remaining = response.headers.get("x-requests-remaining")
        used = response.headers.get("x-requests-used")
        if remaining and used:
            print(f"API usage: {used} used, {remaining} remaining")
        
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching odds: {e}")
        return []


def parse_odds_data(odds_data: list[dict]) -> pd.DataFrame:
    """Parse odds data into a structured dataframe, averaging across all bookmakers."""
    games = []
    
    for game in odds_data:
        home_team = game["home_team"]
        away_team = game["away_team"]
        commence_time = game["commence_time"]
        
        # Parse datetime
        game_date = datetime.fromisoformat(
            commence_time.replace("Z", "+00:00")
        ).date().isoformat()
        
        if not game.get("bookmakers"):
            continue
        
        # Collect odds from all bookmakers
        home_probs = []
        away_probs = []
        total_points_list = []
        
        for bookmaker in game["bookmakers"]:
            # Extract h2h (moneyline) odds
            h2h_market = next(
                (m for m in bookmaker["markets"] if m["key"] == "h2h"), None
            )
            if h2h_market:
                home_ml = None
                away_ml = None
                for outcome in h2h_market["outcomes"]:
                    if outcome["name"] == home_team:
                        home_ml = outcome["price"]
                    elif outcome["name"] == away_team:
                        away_ml = outcome["price"]
                
                if home_ml is not None and away_ml is not None:
                    home_probs.append(american_odds_to_probability(home_ml))
                    away_probs.append(american_odds_to_probability(away_ml))
            
            # Extract totals (over/under)
            totals_market = next(
                (m for m in bookmaker["markets"] if m["key"] == "totals"), None
            )
            if totals_market and totals_market["outcomes"]:
                point = totals_market["outcomes"][0].get("point")
                if point is not None:
                    total_points_list.append(point)
        
        # Calculate averages
        avg_home_prob = sum(home_probs) / len(home_probs) if home_probs else None
        avg_total_points = (
            sum(total_points_list) / len(total_points_list)
            if total_points_list
            else None
        )
        
        games.append({
            "date": game_date,
            "home_team": home_team,
            "away_team": away_team,
            "team_home_win_probability": avg_home_prob,
            "total_points": avg_total_points,
        })
    
    return pd.DataFrame(games)


def match_odds_to_calendar() -> pd.DataFrame:
    """Match scraped odds to games in the calendar table."""
    season = get_current_season()
    
    # Load calendar for upcoming games
    calendar_df = load_dataframe_from_supabase(
        TABLE_CALENDAR.name,
        filters={"season": season}
    )
    
    # Filter to future games only
    today = datetime.now().date().isoformat()
    calendar_df = calendar_df[calendar_df["date"] >= today].copy()
    
    # Fetch odds from API
    odds_data = fetch_nba_odds()
    
    if not odds_data:
        print("No odds data received from API.")
        return pd.DataFrame()
    
    print(f"Received odds for {len(odds_data)} games")
    
    # Parse odds
    odds_df = parse_odds_data(odds_data)
    
    if odds_df.empty:
        print("No odds data to process.")
        return pd.DataFrame()
    
    # Normalize team names for matching
    def normalize_team(name: str) -> str:
        return name.strip().upper()
    
    odds_df["home_team_norm"] = odds_df["home_team"].apply(normalize_team)
    odds_df["away_team_norm"] = odds_df["away_team"].apply(normalize_team)
    calendar_df["team_home_norm"] = calendar_df["team_home"].apply(normalize_team)
    calendar_df["team_visitor_norm"] = (
        calendar_df["team_visitor"].apply(normalize_team)
    )
    
    # Match odds to calendar games
    matched_data = []
    for _, cal_row in calendar_df.iterrows():
        # Try to find matching odds
        match = odds_df[
            (odds_df["home_team_norm"] == cal_row["team_home_norm"]) &
            (odds_df["away_team_norm"] == cal_row["team_visitor_norm"])
        ]
        
        if not match.empty:
            odds_row = match.iloc[0]
            matched_data.append({
                "date": cal_row["date"],
                "team_home": cal_row["team_home"],
                "team_visitor": cal_row["team_visitor"],
                "team_home_win_probability": odds_row["team_home_win_probability"],
                "total_points": odds_row["total_points"],
            })
    
    if not matched_data:
        print("No matches found between odds and calendar.")
        print(f"Calendar has {len(calendar_df)} games")
        print(f"Odds has {len(odds_df)} games")
        if not odds_df.empty:
            print("\nSample odds teams:")
            print(odds_df[["home_team", "away_team"]].head())
        if not calendar_df.empty:
            print("\nSample calendar teams:")
            print(calendar_df[["team_home", "team_visitor"]].head())
        return pd.DataFrame()
    
    df_matched = pd.DataFrame(matched_data)
    print(f"✓ Matched odds for {len(df_matched)} games")
    return df_matched


def save_odds_to_database() -> int:
    """Scrape odds and save to database."""
    df_odds = match_odds_to_calendar()
    
    if df_odds.empty:
        print("No odds data to save.")
        return 0
    
    # Save news to Supabase
    save_dataframe_to_supabase(
        df=df_odds,
        table_name=TABLE_GAME_ODDS.name,
        index_columns=["date", "team_home"],
        upsert=True,
    )
    
    print(f"✓ Saved odds for {len(df_odds)} games to database")
    return len(df_odds)


if __name__ == "__main__":
    save_odds_to_database()

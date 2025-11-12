"""Business logic for injuries page - injured players information."""

import datetime

import pandas as pd

from src.database.tables import TABLE_CALENDAR, TABLE_INJURIES
from src.database.utils import load_dataframe_from_supabase


def get_injury_summary(injuries_df: pd.DataFrame) -> dict:
    """Get summary statistics about injuries."""
    summary = {
        "total_injuries": len(injuries_df),
        "unique_players": injuries_df["player"].nunique()
        if len(injuries_df) > 0
        else 0,
    }

    return summary


def parse_status(status: str, calendar_df: pd.DataFrame) -> pd.Timestamp | None:
    """Parse injury status to extract expected return date."""
    
    if "Expected to be out until at least" in status:
        # Get day month in the form Nov 18
        mm_dd = status.split("at least")[-1].strip()
        
        # Use the current year for the return date
        current_year = datetime.datetime.now().year
        
        # Construct full date
        date_string = f"{mm_dd} {current_year}"
        date = datetime.datetime.strptime(date_string, "%b %d %Y")
        
        # If the date has already passed this year, assume it's next year
        if date < datetime.datetime.today() - datetime.timedelta(days=1):
            date = date.replace(year=current_year + 1)
        return pd.Timestamp(date)
    
    elif "Out for the season" in status:
        # Use the last date of the season
        return pd.to_datetime(calendar_df["date"].max(), errors="coerce")
    
    return None


def load_injuries_data() -> pd.DataFrame:
    """Load all injuries data from the database."""
    
    # Load injuries data
    df_injuries = load_dataframe_from_supabase(TABLE_INJURIES.name)
    df_injuries = df_injuries.sort_values(by="player", ignore_index=True)
    
    # Add return date
    df_calendar = load_dataframe_from_supabase(table_name=TABLE_CALENDAR.name)
    df_injuries["return_date"] = df_injuries["status"].apply(
        parse_status, calendar_df=df_calendar
    )
    
    # Add days until return
    today = pd.Timestamp(datetime.date.today())
    df_injuries["days_until_return"] = df_injuries["return_date"].apply(
        lambda return_date: (
            (return_date - today).days
            if pd.notnull(return_date)
            else None
        )
    )
    
    return df_injuries

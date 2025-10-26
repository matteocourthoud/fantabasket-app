import os
import sys

import streamlit as st

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.scraping.utils import get_current_season
from src.supabase.table_names import STATS_TABLE
from src.supabase.utils import load_dataframe_from_supabase


def stats_tab():
    """This function creates the 'Stats' tab in the Streamlit app.
    It loads and displays player stats for the current season from Supabase.
    """
    st.title("Player Stats")

    season = get_current_season()
    st.header(f"Season {season}")

    # Load stats for the current season
    stats_df = load_dataframe_from_supabase(STATS_TABLE, filters={"season": season})

    # Group by player and calculate the mean of numeric stats
    numeric_cols = stats_df.select_dtypes(include="number").columns
    cols_to_exclude = ["id", "game_id", "player_id", "season"]
    cols_to_avg = [col for col in numeric_cols if col not in cols_to_exclude]

    # Assuming 'player_name' is the column to group by
    player_avg_stats = stats_df.groupby("player")[cols_to_avg].mean().reset_index()

    st.dataframe(player_avg_stats)

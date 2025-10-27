"""Injuries page UI - displays injured players information."""

import os
import sys

import streamlit as st


# Add the project root to the Python path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)

from logic import injuries_logic

from src.supabase.utils import get_table_last_updated


def main():
    # Page title
    st.title("Player Injuries")
    
    # Show last update time from the updates table (UTC)
    last_updated = get_table_last_updated("injuries")
    text = f"Table last updated: {last_updated.strftime('%Y-%m-%d %H:%M')} UTC"
    st.markdown(f'<p style="font-size:12px;">{text}</p>', unsafe_allow_html=True)

    # Load injuries data
    df_injuries = injuries_logic.load_injuries_data()
    df_injuries = df_injuries.drop(columns=["scraped_at", "status"], errors="ignore")
    st.dataframe(df_injuries, width="stretch", hide_index=True)


if __name__ == "__main__":
    main()

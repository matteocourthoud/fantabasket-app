"""Injuries page UI - displays injured players information."""

import streamlit as st

from src.database.utils import get_table_last_updated
from src.streamlit_app.logic import injuries_logic


def main():
    # Page title
    st.title("Player Injuries")

    # Load injuries data
    df_injuries = injuries_logic.load_injuries_data()
    df_injuries = df_injuries.drop(columns=["scraped_at", "status"], errors="ignore")
    df_injuries = df_injuries.sort_values(by="return_date", ascending=True)
    st.dataframe(df_injuries, width="stretch", hide_index=True)
    
    # Show last update time from the updates table (UTC)
    last_updated = get_table_last_updated("injuries")
    text = f"Table last updated: {last_updated.strftime('%Y-%m-%d %H:%M')} UTC"
    st.markdown(f'<p style="font-size:12px;">{text}</p>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()

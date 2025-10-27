"""Injuries page UI - displays injured players information."""

import os
import sys

import pandas as pd

import streamlit as st


# Add the project root to the Python path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)

from logic import injuries_logic

from src.scraping.scrape_injuries import scrape_injuries


def main():
    """Injuries page of the Streamlit application."""
    # Page title
    st.title("Player Injuries")

    # Load injuries data
    injuries_df = injuries_logic.load_injuries_data()

    # Show last scraped_at if available
    scraped_at = pd.to_datetime(injuries_df["scraped_at"], errors="coerce").max()
    scraped_at = scraped_at.strftime("%Y-%m-%d %H:%M")
    
    # Disable button if scraping in the last 10 minutes
    disable_button = False
    if pd.notnull(scraped_at):
        last_scraped_time = pd.to_datetime(scraped_at)
        time_diff = pd.Timestamp.now() - last_scraped_time
        if time_diff.total_seconds() < 600:  # 10 minutes
            disable_button = True
            st.warning("Injuries were scraped less than 10 minutes ago. Please wait before scraping again.")
        else:
            st.info(f"Last scraped at: {scraped_at}")

    # Button to scrape latest injuries
    if st.button("🔄 Scrape Latest Injuries", type="secondary", disabled=disable_button):
        with st.spinner("Scraping injuries data..."):
            try:
                scrape_injuries()
                st.success("✅ Injuries data updated successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error scraping injuries: {str(e)}")
                return

    # Load injuries data
    df_injuries = injuries_logic.load_injuries_data()

    if len(df_injuries) == 0:
        st.success("🎉 No injuries reported! All players are healthy.")
        return

    # Remove 'scraped_at' column if present
    if "scraped_at" in df_injuries.columns:
        df_injuries = df_injuries.drop(columns=["scraped_at"])

    st.dataframe(df_injuries, width="stretch", hide_index=True)


if __name__ == "__main__":
    main()

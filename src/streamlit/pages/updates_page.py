"""Updates page UI - shows last update times and allows manual updates."""

import pandas as pd

import streamlit as st
from src.scraping.scrape_injuries import scrape_injuries
from src.scraping.scrape_lineups import scrape_lineups
from src.supabase.utils import load_dataframe_from_supabase


TABLES_TO_UPDATE = ["injuries", "lineups", "fanta_stats"]


def main():
    """Updates page of the Streamlit application."""
    st.title("Data Updates")

    st.markdown("Monitor and manually update data tables.")

    # Load updates data
    df_updates = load_dataframe_from_supabase("updates")

    # Filter for tables we want to show
    df_updates = df_updates[df_updates["table_name"].isin(TABLES_TO_UPDATE)]

    if df_updates.empty:
        st.info(
            "No update data available yet. "
            "Tables will appear here after their first update."
        )
        return

    for table_name in TABLES_TO_UPDATE:
        table_updates = df_updates[df_updates["table_name"] == table_name]

        if table_updates.empty:
            st.warning(f"No update data found for {table_name}. It may not have been scraped yet.")
            continue

        last_updated = pd.to_datetime(table_updates["last_updated"].iloc[0])
        time_diff = pd.Timestamp.now(tz="UTC") - last_updated
        time_since_update = time_diff.total_seconds() / 60  # minutes

        with st.container():
            st.markdown('<div class="update-card">', unsafe_allow_html=True)
            cols = st.columns([3, 1])
            with cols[0]:
                st.markdown(f"### {table_name.capitalize().replace('_', ' ')}")
                st.write(f"Last updated: {last_updated.strftime('%Y-%m-%d %H:%M')} UTC")
            with cols[1]:
                disabled = time_since_update < 10
                if st.button("Update", key=f"update_{table_name}", disabled=disabled):
                    with st.spinner(f"Updating {table_name}..."):
                        try:
                            if table_name == "injuries":
                                scrape_injuries()
                            elif table_name == "lineups":
                                scrape_lineups()
                            st.success(f"{table_name.capitalize()} updated")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating {table_name}: {e}")
            st.markdown('</div>', unsafe_allow_html=True)

    # Additional information
    st.markdown("---")
    st.markdown("""
    **Rate Limiting**: Updates are limited to once every 10 minutes
    to avoid overloading data sources.

    **Automatic Updates**: Tables are automatically updated when data
    is scraped through the application.
    """)


if __name__ == "__main__":
    main()

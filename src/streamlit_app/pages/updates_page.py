"""Updates page UI - shows last update times and allows manual updates."""

import pandas as pd
import streamlit as st

from src.database.utils import load_dataframe_from_supabase
from src.scraping.scrape_games import scrape_games
from src.scraping.scrape_injuries import scrape_injuries
from src.scraping.scrape_lineups import scrape_lineups
from src.scraping.scrape_odds import save_odds_to_database
from src.scraping.update_fanta_stats import update_fanta_stats


TABLES_TO_UPDATE = ["injuries", "lineups", "stats", "fanta_stats", "game_odds"]


def main():
    """Updates page of the Streamlit application."""
    st.title("Data Updates")

    st.markdown("Monitor and manually update data tables.")

    # Load updates data
    df_updates = load_dataframe_from_supabase("updates")

    # Filter for tables we want to show
    df_updates = df_updates[df_updates["table_name"].isin(TABLES_TO_UPDATE)]

    for table_name in TABLES_TO_UPDATE:
        table_updates = df_updates[df_updates["table_name"] == table_name]
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
                            result_msg = None
                            if table_name == "injuries":
                                n = scrape_injuries()
                                result_msg = f"Found {n} injured players."
                            elif table_name == "lineups":
                                n_teams = scrape_lineups()
                                result_msg = f"Found lineups for {n_teams} teams."
                            elif table_name == "stats":
                                n_games = scrape_games()
                                result_msg = f"Scraped {n_games} new games."
                            elif table_name == "fanta_stats":
                                update_fanta_stats()
                                result_msg = "Fanta stats updated."
                            elif table_name == "game_odds":
                                n_games = save_odds_to_database()
                                result_msg = f"Scraped odds for {n_games} games."

                            # Persist a success message in session state so it stays
                            st.session_state[f"update_msg_{table_name}"] = result_msg
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating {table_name}: {e}")
            st.markdown('</div>', unsafe_allow_html=True)

            # Show persisted success message for this table (if any)
            msg_key = f"update_msg_{table_name}"
            if msg_key in st.session_state and st.session_state[msg_key]:
                st.success(st.session_state[msg_key])

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

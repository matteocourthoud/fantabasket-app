"""Players page UI - individual player statistics and performance."""

import os
import sys

import pandas as pd

import streamlit as st


# Add the project root to the Python path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)

from src.scraping.utils import get_current_season
from src.streamlit.logic import players_logic


def main():
    """Players page of the Streamlit application."""
    season = get_current_season()

    # Load all data
    data = players_logic.load_player_data(season)

    # Get player list
    player_list = players_logic.get_player_list(data["stats"])

    # Page title
    st.title("Player Performance")

    # Player selection with search
    st.markdown("**Search and select a player:**")
    selected_player = st.selectbox(
        "Player:",
        player_list,
        index=0 if player_list else None,
        label_visibility="collapsed",
        help="Start typing to search for a player",
    )

    if not selected_player:
        st.warning("No players available.")
        return
    
    # Player news box (auto-fetched, read-only)
    st.subheader("Latest News")
    
    # Lazy import to avoid circular imports at module import time
    from src.scraping.scrape_player_news import _scrape_player_news  # noqa: E402

    with st.spinner("Fetching latest news..."):
        news_df = _scrape_player_news(selected_player)

    if news_df.empty:
        st.info("No news found for this player.")
    else:
        news_text = news_df.iloc[0]["news"]
        st.markdown(news_text.replace("\n", "  \n"))

    # Get player summary
    summary = players_logic.get_player_summary(
        selected_player, data["stats"], data["fanta_stats"]
    )

    # Display summary metrics
    st.subheader(f"Season Summary")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Games Played", summary["games_played"])
    with col2:
        st.metric("Avg Points", f"{summary['avg_points']:.1f}")
    with col3:
        st.metric("Avg Rebounds", f"{summary['avg_rebounds']:.1f}")
    with col4:
        st.metric("Avg Assists", f"{summary['avg_assists']:.1f}")
    with col5:
        if summary["current_value"]:
            st.metric("Current Value", f"{summary['current_value']:.1f}")
        else:
            st.metric("Current Value", "N/A")

    # Recent games section
    st.subheader("Recent Games")
    n_games = st.slider("Number of games to show:", min_value=5, max_value=20, value=10)

    recent_games = players_logic.get_player_recent_games(
        selected_player, data["stats"], data["games"], n_games=n_games
    )

    if len(recent_games) > 0:
        # Format the date column
        recent_games["date"] = pd.to_datetime(recent_games["date"]).dt.strftime(
            "%Y-%m-%d"
        )

        # Display the table
        st.dataframe(recent_games, width="stretch", hide_index=True)
    else:
        st.info("No game data available for this player.")


if __name__ == "__main__":
    import pandas as pd

    main()

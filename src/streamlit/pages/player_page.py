"""Players page UI - individual player statistics and performance."""

import datetime
import os
import sys

import streamlit as st
from src.scraping.utils import get_current_season


# Add the project root to the Python path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)

from logic import player_logic


def main():
    """Players page of the Streamlit application."""
    # Add CSS to prevent metrics from stacking on mobile
    st.markdown("""
        <style>
        [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) .stColumn {
            min-width: 0 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    season = get_current_season()

    # Load all data
    data = player_logic.load_player_data(season)

    # Get player name from query params
    query_params = st.query_params
    selected_player = query_params.get("name")
    if not selected_player:
        st.error("No player specified in URL.")
        return

    # Display player image if available
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )
    player_code = data["players"].loc[
        data["players"]["player"] == selected_player, "player_id"
    ].values[0]
    image_path = os.path.join(project_root, "data", "players", f"{player_code}.jpg")
        
    # Title and image
    title_col, image_col = st.columns([8, 1], width="stretch")
    with title_col:
        st.title(selected_player)
    with image_col:
        st.image(image_path, width=80)
    
    # Get next game info
    next_game = player_logic.get_player_next_game(
        selected_player,
        data["stats"],
        data["games"],
        data["calendar"],
        today = datetime.date.today().isoformat(),
        teams_df=data["teams"],
    )
    
    # Get player summary (current value, total gain)
    summary = player_logic.get_player_summary(
        selected_player,
        data["stats"],
        data["fanta_stats"],
    )
    
    # Get next opponent fanta_team
    next_fanta_team = None
    if next_game is not None:
        opp_nba = next_game["opponent"]
        teams_df = data["teams"]
        teams_df["team"] = teams_df["team"].str.strip().str.upper()
        teams_df["fanta_team"] = teams_df["fanta_team"].astype(str)
        match = teams_df[teams_df["team"] == str(opp_nba).strip().upper()]
        if not match.empty:
            next_fanta_team = match.iloc[0]["fanta_team"]
        else:
            next_fanta_team = opp_nba
    
    # Compute latest gain and median gain
    latest_gain = None
    median_gain = None
    fanta_stats = data["fanta_stats"]
    player_fanta = fanta_stats[fanta_stats["player"] == selected_player]
    if not player_fanta.empty:
        latest_gain = player_fanta.iloc[-1]["gain"]
        median_gain = player_fanta["gain"].median()
    
    # Metrics display
    col1, col2, col3 = st.columns(3, width="stretch")
    col1.metric(
        "Current Value",
        f"{summary['current_value']:.1f}" if summary['current_value'] is not None else "-",
        delta=round(latest_gain, 1) if latest_gain is not None else 0.0,
        label_visibility="visible",
    )
    col2.metric(
        "Total Gain",
        f"{summary['avg_gain']:.1f}" if summary['avg_gain'] is not None else "-",
        delta=round(median_gain, 1) if median_gain is not None else 0.0,
        label_visibility="visible",
    )
    if next_fanta_team:
        col3.metric("Next Opponent", next_fanta_team)
    else:
        col3.metric("Next Opponent", "-")

    # Recent games section
    st.subheader("Recent Games")
    recent_games = player_logic.get_player_recent_games(
        selected_player, data["stats"], data["games"], data["fanta_stats"], n_games=100,
    )
    
    # Style the gain column as in stats_page
    def _gain_style(v):
        import pandas as pd
        try:
            if pd.isna(v):
                return ""
            if v > 0:
                return "color: #28a745; font-weight: 600"
            if v < 0:
                return "color: #dc3545; font-weight: 600"
            return "font-weight: 600"
        except Exception:
            return ""

    styler = recent_games.style.format({"gain": "{:.1f}"})
    styler = styler.map(_gain_style, subset=["gain"])
    st.dataframe(styler, width="stretch", hide_index=True)

    # Player news box (auto-fetched, read-only)
    st.subheader("Latest News")
    from src.scraping.scrape_player_news import _scrape_player_news  # noqa: E402
    with st.spinner("Fetching latest news..."):
        news_df = _scrape_player_news(selected_player)
    if news_df.empty:
        st.info("No news found for this player.")
    else:
        news_text = news_df.iloc[0]["news"]
        st.markdown(news_text.replace("\n", "  \n"))


if __name__ == "__main__":
    main()

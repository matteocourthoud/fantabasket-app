"""Players page UI - individual player statistics and performance."""

import os

import pandas as pd
import streamlit as st

from src.database.utils import load_dataframe_from_supabase
from src.scraping.scrape_player_news import scrape_player_news
from src.scraping.utils import get_current_season
from src.streamlit_app.logic import player_logic


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

    # Get player name from query params
    query_params = st.query_params
    selected_player = query_params.get("name")
    if not selected_player:
        st.error("No player specified in URL.")
        return
    
    # Load all data
    season = get_current_season()
    df_player = load_dataframe_from_supabase("players")
    df_fanta_stats = load_dataframe_from_supabase("fanta_stats", {"season": season})

    # Display player image if available
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )
    player_code = df_player.loc[
        df_player["player"] == selected_player, "player_id"
    ].values[0]
    image_path = os.path.join(project_root, "data", "players", f"{player_code}.jpg")
        
    # Title and image
    title_col, image_col = st.columns([8, 1], width="stretch")
    with title_col:
        st.title(selected_player)
    with image_col:
        st.image(image_path, width=80)
    
    # Get next game info
    next_game = player_logic.get_player_next_game(selected_player)
    
    # Compute latest gain and median gain
    player_fanta = df_fanta_stats[df_fanta_stats["player"] == selected_player]
    current_value = player_fanta["value_after"].iloc[-1]
    latest_gain = player_fanta.iloc[-1]["gain"]
    avg_score = player_fanta["fanta_score"].mean()
    median_score = player_fanta["fanta_score"].median()
    
    # Metrics display
    col1, col2, col3, col4 = st.columns(4, width="stretch")

    col1.metric(
        "Current Value",
        round(current_value, 1),
        delta=round(latest_gain, 1),
    )
    col2.metric(
        "Avg Score",
        round(avg_score, 1),
    )
    col3.metric(
        "Median Score",
        round(median_score, 1),
    )
    col4.metric("Next Opponent", next_game["opponent"])

    # Recent games section
    st.subheader("Recent Games")
    df_recent_games = player_logic.get_player_recent_games(selected_player)
    
    # Style the gain column as in stats_page and color the opponent cell by win/loss
    def _gain_style(v):
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

    def _opponent_row_style(row: pd.Series) -> pd.Series:
        """Return a Series of CSS styles for a row where only the 'opponent'
        column is colored depending on the value of the 'win' column.
        """
        styles = pd.Series("", index=row.index)
        if "opponent" in row.index and "win" in row.index:
            if pd.isna(row["win"]):
                return styles
            if row["win"]:
                styles["opponent"] = "color: #6aa994"
            else:
                styles["opponent"] = "color: #b06f6f"
        return styles

    # Ensure 'start' column visible (move near opponent if present)
    display_df = df_recent_games.copy()

    # Prepare Streamlit column_config for percent columns (fg%, 3p%, ast%)
    col_config = {}
    percent_cols = [col for col in display_df.columns if "%" in col]
    for col in percent_cols:
        display_df[col] *= 100
        col_config[col] = st.column_config.NumberColumn(format="%.0f%%")

    # Precompute opponent styles (so we can reapply them even if we must
    precomputed_opponent_styles = display_df.apply(_opponent_row_style, axis=1)

    # Fallback for older pandas: drop 'win' and reapply precomputed styles
    disp = display_df.drop(columns=["win"])
    styler = disp.style.format({"gain": "{:.1f}", "score": "{:.1f}"})

    # If we computed opponent styles earlier, apply them to the display
    if precomputed_opponent_styles is not None:
        def _apply_precomputed(row: pd.Series) -> pd.Series:
            styles_row = precomputed_opponent_styles.loc[row.name]
            return styles_row.reindex(disp.columns)
        styler = styler.apply(_apply_precomputed, axis=1)

    # Reapply gain mapping on the fallback display
    styler = styler.map(_gain_style, subset=["gain"])
    
    st.dataframe(
        styler,
        hide_index=True,
        column_config=col_config,
    )

    # Player news box (auto-fetched, read-only)
    st.subheader("Latest News")
    with st.spinner("Fetching latest news..."):
        news_df = scrape_player_news(selected_player)
    if news_df.empty:
        st.info("No news found for this player.")
    else:
        news_text = news_df.iloc[0]["news"]
        st.markdown(news_text.replace("\n", "  \n"))


if __name__ == "__main__":
    main()

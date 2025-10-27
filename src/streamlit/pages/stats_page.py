"""Stats page UI - displays player statistics with filters."""

import streamlit as st
import pandas as pd
from src.scraping.utils import get_current_season
from src.streamlit.logic import stats_logic
from src.supabase.utils import get_table_last_updated


def main():
    """Stats page of the Streamlit application."""
    season = get_current_season()

    # Load all data
    data = stats_logic.load_all_data(season)

    # Merge player data
    stats_df = stats_logic.merge_player_data(
        data["stats"], data["players"], data["initial_values"]
    )

    # Get team list for filter
    all_teams = stats_logic.get_team_list(data["games"])

    # Page title
    st.title("Player Stats")

    # Filters
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        aggregation_method = st.selectbox(
            "Aggregation:",
            ["Average", "Sum", "Median"],
            index=0,
        )

    with col2:
        all_positions = sorted(stats_df["position"].dropna().unique())
        position_options = ["All"] + list(all_positions)
        selected_position = st.selectbox("Select Position:", position_options)

    with col3:
        team_options = ["All"] + all_teams
        selected_team = st.selectbox("Select Team:", team_options)

    with col4:
        # Get min and max values
        min_value = 4.0
        max_value = 35.0

        value_range = st.slider(
            "Value Range:",
            min_value=min_value,
            max_value=max_value,
            value=(min_value, max_value),
            step=0.5,
        )

    # Process and filter player stats
    player_avg_stats = stats_logic.process_player_stats(
        stats_df=stats_df,
        games_df=data["games"],
        fanta_stats_df=data["fanta_stats"],
        teams_df=data["teams"],
        position_filter=selected_position,
        team_filter=selected_team,
        value_range=value_range,
        aggregation_method=aggregation_method.lower(),
    )

    # We'll build numeric recent-trend lists (see below) and render them

    # compute per-player recent scores from fanta_stats table
    try:
        from src.supabase.utils import load_dataframe_from_supabase

        df_fanta = load_dataframe_from_supabase("fanta_stats")
        if not df_fanta.empty:
            # group gains by player (sorted by game_id so lists are chronological)
            score_map = (
                df_fanta.sort_values("game_id")
                .groupby("player")
                ["gain"]
                .apply(lambda s: s.dropna().tolist())
                .to_dict()
            )
        else:
            score_map = {}
    except Exception:
        score_map = {}

    # trend string column removed; we'll compute numeric 'trend' lists later

    # Reduce to only the requested columns (include player) and prepare formatting
    # keep `gain` instead of `games` per request and show the gain histogram
    display_cols = ["player", "team", "position", "value", "gain", "trend"]

    # If some columns are missing, keep existing ones
    display_cols = [c for c in display_cols if c in player_avg_stats.columns]

    player_display = player_avg_stats[display_cols].copy()

    # Add some spacing before the table
    st.markdown("")
    
    # Show last update time from the updates table (UTC)
    last_updated = get_table_last_updated("fanta_stats")
    text = f"Table last updated: {last_updated.strftime('%Y-%m-%d %H:%M')} UTC"
    st.markdown(f'<p style="font-size:12px;">{text}</p>', unsafe_allow_html=True)

    # Removed SVG sparkline code; we'll use Streamlit's BarChartColumn with
    # numeric 'trend' lists below.

    # Use Streamlit's native dataframe with a BarChartColumn for recent gains.
    display_df = player_display.copy()

    # Build a numeric list of recent gains (most recent 12) per player
    def _recent_n_padded(scores: list[float], n: int = 5) -> list[float]:
        """Return the most recent n scores, right-padded with zeros if needed."""
        if not scores:
            return [0.0] * n
        recent = scores[-n:]
        pad = [0.0] * (n - len(recent))
        return recent + pad

    display_df["trend"] = display_df["player"].apply(
        lambda p: _recent_n_padded(score_map.get(p, []), n=5)
    )

    # Keep only the columns we want and limit rows for display
    cols_order = [
        c
        for c in ["player", "team", "position", "value", "gain", "trend"]
        if c in display_df.columns
    ]
    display_df = display_df[cols_order].head(500)

    # Create a pandas Styler to format numbers and color the gain column
    # Format value and gain to 1 decimal
    styler = display_df.style.format({"value": "{:.1f}", "gain": "{:.1f}"})

    # Color gain: green if positive, red if negative, muted otherwise
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

    if "gain" in display_df.columns:
        styler = styler.applymap(_gain_style, subset=["gain"])

    # Configure columns: pin player and render gain_hist as bar chart
    col_config = {"player": st.column_config.Column(pinned=True)}
    if "trend" in display_df.columns:
        col_config["trend"] = st.column_config.BarChartColumn(
            width="small", color="grey",
        )

    # Display the styled dataframe with Streamlit native renderer
    st.dataframe(
        styler,
        width="stretch",
        hide_index=True,
        column_config=col_config,
    )


if __name__ == "__main__":
    main()

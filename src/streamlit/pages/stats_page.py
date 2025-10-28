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
    st.set_page_config(layout="wide")
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
        max_value = 30.0

        value_range = st.slider(
            "Value Range:",
            min_value=min_value,
            max_value=max_value,
            value=(min_value, max_value),
            step=0.5,
        )

    # Process and filter player stats
    df_stats = stats_logic.process_player_stats(
        stats_df=stats_df,
        games_df=data["games"],
        fanta_stats_df=data["fanta_stats"],
        teams_df=data["teams"],
        position_filter=selected_position,
        team_filter=selected_team,
        value_range=value_range,
        aggregation_method=aggregation_method.lower(),
    )

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

    # Add some spacing before the table
    st.markdown("")
    
    # Show last update time from the updates table (UTC)
    last_updated = get_table_last_updated("fanta_stats")
    text = f"Table last updated: {last_updated.strftime('%Y-%m-%d %H:%M')} UTC"
    st.markdown(f'<p style="font-size:12px;">{text}</p>', unsafe_allow_html=True)


    # Build a numeric list of recent gains (most recent 5) per player
    def _recent_n_padded(scores: list[float], n: int = 5) -> list[float]:
        """Return the most recent n scores, right-padded with zeros if needed."""
        if not scores:
            return [0.0] * n
        recent = scores[-n:]
        pad = [0.0] * (n - len(recent))
        return recent + pad

    df_stats["trend"] = df_stats["player"].apply(
        lambda p: _recent_n_padded(score_map.get(p, []), n=5)
    )

     # Reduce to only the requested columns (include player) and prepare formatting
    display_cols = ["player", "value", "gain", "trend", "mp", "pts", "trb", "ast", "stl", "blk", "team", "position"]
    df_stats = df_stats[display_cols]

    # Create a pandas Styler to format numbers and color the gain column
    styler = df_stats.style.format({
        "value": "{:.1f}",
        "gain": "{:.1f}",
        "mp": "{:.1f}",
        "pts": "{:.1f}",
        "trb": "{:.1f}",
        "ast": "{:.1f}",
        "stl": "{:.1f}",
        "blk": "{:.1f}",
    })

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

    styler = styler.applymap(_gain_style, subset=["gain"])

    # Configure columns: pin player and render gain_hist as bar chart
    col_config = {"player": st.column_config.Column(pinned=True)}
    col_config["trend"] = st.column_config.BarChartColumn(width="small", color="grey")

    # Display the styled dataframe with Streamlit native renderer
    st.dataframe(
        styler,
        width="stretch",
        hide_index=True,
        column_config=col_config,
    )


if __name__ == "__main__":
    main()

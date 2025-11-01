"""Stats page UI - displays player statistics with filters."""

import streamlit as st
from src.streamlit.logic import stats_logic
from src.streamlit.utils import color_gain
from src.supabase.utils import get_table_last_updated


def main():
    """Stats page of the Streamlit application."""

    # Load all data
    data = stats_logic.load_fanta_stats_data()
    fanta_stats = data["fanta_stats"]
    predictions = data["predictions"]

    # Get team list for filter
    all_teams = stats_logic.get_team_list(fanta_stats)

    # Page title
    st.set_page_config(layout="wide")
    st.title("Player Stats")


    # Filters inside an expander
    with st.expander("Filters", expanded=False):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            aggregation_method = st.selectbox(
                "Aggregation:",
                ["mean", "sum", "median"],
                index=0,
            )

        with col2:
            all_positions = sorted(fanta_stats["position"].dropna().unique())
            position_options = ["All"] + list(all_positions)
            selected_position = st.selectbox("Select Position:", position_options)

        with col3:
            team_options = ["All"] + all_teams
            selected_team = st.selectbox("Select Team:", team_options)

        with col4:
            value_range = st.slider(
                "Value Range:",
                min_value=4.0,
                max_value=30.0,
                value=(4.0, 30.0),
                step=1.0,
            )

    # Process and filter player stats
    df_stats = stats_logic.process_player_stats(
        fanta_stats_df=fanta_stats,
        predictions_df=predictions,
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

    # Add a clickable link for each player using LinkColumn
    from urllib.parse import quote

    df_stats["player"] = df_stats["player"].apply(
        lambda name: f"/player?name={quote(name)}"
    )

    # Reduce to only the requested columns (player, ...)
    display_cols = [
        "player",
        "value",
        "score",
        "gain_hat",
        "trend",
        "mp",
        "pts",
        "trb",
        "ast",
        "stl",
        "blk",
        "team",
        "position",
    ]
    df_stats = df_stats[display_cols]

    # Create a pandas Styler to format numbers and color gain column
    styler = df_stats.style.format(
        {
            "value": "{:.1f}",
            "score": "{:.1f}",
            "gain_hat": "{:.2f}",
            "mp": "{:.1f}",
            "pts": "{:.1f}",
            "trb": "{:.1f}",
            "ast": "{:.1f}",
            "stl": "{:.1f}",
            "blk": "{:.1f}",
        }
    )

    # Apply color styling to gain column using shared utility function
    styler = styler.map(color_gain, subset=["gain_hat"])

    # Configure columns: LinkColumn for player, BarChart for trend
    col_config = {
        "player": st.column_config.LinkColumn(display_text=r"name=(.*?)$"),
        "trend": st.column_config.BarChartColumn(width="small", color="grey"),
    }

    # Display the dataframe with clickable player links
    st.dataframe(
        styler,
        hide_index=True,
        column_config=col_config,
        width="stretch",
    )


if __name__ == "__main__":
    main()

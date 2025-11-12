"""Stats page UI - displays player statistics with filters."""

from urllib.parse import quote

import streamlit as st

from src.database.tables import TABLE_PLAYERS
from src.database.utils import get_table_last_updated, load_dataframe_from_supabase
from src.streamlit_app.logic import players_logic
from src.streamlit_app.utils import color_gain, image_to_data_uri


def main():
    """Stats page of the Streamlit application."""

    # Get team list for filter
    all_teams = players_logic.get_team_list()

    # Page title
    st.set_page_config(layout="wide")
    st.title("Player Stats")


    # Filters inside an expander
    with st.expander("Filters", expanded=False):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            player_search = st.text_input("Search player:", value="")

        with col2:
            position_options = ["All", "G", "F", "C"]
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
    df_stats = players_logic.compute_player_stats(
        position_filter=selected_position,
        team_filter=selected_team,
        value_range=value_range,
    )
    
    # If the user entered a player search string, filter results by player name
    if player_search and "player" in df_stats.columns:
        df_stats = df_stats[
            df_stats["player"].str.contains(
                player_search, case=False, na=False
            )
        ]
        if df_stats.empty:
            st.error("No players match your search.")

    # Compute per-player recent scores from fanta_stats table
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

    # Add some spacing before the table
    st.markdown("")

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
    players_df = load_dataframe_from_supabase(TABLE_PLAYERS.name)
    if not players_df.empty:
        df_stats = df_stats.merge(
            players_df[["player", "player_id"]], on="player", how="left"
        )
        df_stats["image"] = df_stats["player_id"].apply(image_to_data_uri)

    df_stats["player"] = df_stats["player"].apply(
        lambda name: f"/player?name={quote(name)}"
    )

    # Reduce to only the requested columns (player, ...)
    display_cols = [
        "image",
        "player",
        "pos",
        "value",
        "score",
        "gain",
        "trend",
        "gain_hat",
        "gain5",
        "gain10",
        "bench",
        "team",
    ]
    df_stats = df_stats[display_cols]

    # Create a pandas Styler to format numbers and color gain column
    styler = df_stats.style.format(
        {
            "value": "{:.1f}",
            "score": "{:.1f}",
            "gain": "{:.2f}",
            "gain_hat": "{:.2f}",
            "gain5": "{:.2f}",
            "gain10": "{:.2f}",
            "bench": "{:.1f}",
        }
    )

    # Apply color styling to gain column using shared utility function
    styler = styler.map(color_gain, subset=["gain_hat"])

    # Configure columns: LinkColumn for player, BarChart for trend
    col_config = {
        "image": st.column_config.ImageColumn(label="", width="small"),
        "player": st.column_config.LinkColumn(display_text=r"name=(.*?)$"),
        "trend": st.column_config.BarChartColumn(width="small", color="grey"),
    }

    # Display the dataframe with clickable player links
    st.dataframe(
        styler,
        hide_index=True,
        column_config=col_config,
    )
    
    # Show last update time from the updates table (UTC)
    last_updated = get_table_last_updated("fanta_stats")
    text = f"Table last updated: {last_updated.strftime('%Y-%m-%d %H:%M')} UTC"
    st.markdown(f'<p style="font-size:12px;">{text}</p>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()

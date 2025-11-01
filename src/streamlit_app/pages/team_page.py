"""Team page UI - shows average opponent gain and average gain allowed by role for each team."""

from urllib.parse import quote

import streamlit as st

from src.streamlit_app.logic import stats_logic, teams_logic
from src.streamlit_app.utils import color_gain


def main():

    # Get team from query params
    query_params = st.query_params
    selected_team = query_params.get("team")
    if not selected_team:
        st.error("No team specified in URL.")
        return

    # Load team data
    teams_df = teams_logic.get_teams_gain_table()
    teams_df = teams_df[teams_df["Team"] == selected_team]

    # Display team logo smaller and inline with title
    fanta_team = teams_df.iloc[0]["fanta_team"]
    logo_path = f"data/teams/{fanta_team}.png"
    title_col, logo_col = st.columns([8, 1])
    with title_col:
        st.title(selected_team)
    with logo_col:
        st.image(logo_path, width=72)

    # Metrics display
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Avg Gain",
        f"{teams_df.iloc[0]['Avg Opponent Gain']:.1f}",
        label_visibility="visible",
    )
    col2.metric(
        "Avg Gain (C)",
        f"{teams_df.iloc[0]['Avg Gain (C)']:.1f}",
        label_visibility="visible",
    )
    col3.metric(
        "Avg Gain (F)",
        f"{teams_df.iloc[0]['Avg Gain (F)']:.1f}",
        label_visibility="visible",
    )
    col4.metric(
        "Avg Gain (G)",
        f"{teams_df.iloc[0]['Avg Gain (G)']:.1f}",
        label_visibility="visible",
    )

    # Add spacing
    st.markdown("---")
    st.subheader("Team Roster")

    # Load player stats data
    data = stats_logic.load_fanta_stats_data()
    fanta_stats = data["fanta_stats"]
    predictions = data["predictions"]

    # Get fanta_team code for filtering
    # The stats are stored with fanta_team codes, not full team names
    team_filter = fanta_team

    # Process player stats filtered by team
    df_stats = stats_logic.process_player_stats(
        fanta_stats_df=fanta_stats,
        predictions_df=predictions,
        team_filter=team_filter,
        aggregation_method="mean",
    )

    # Compute per-player recent scores from fanta_stats table
    try:
        from src.supabase.utils import load_dataframe_from_supabase

        df_fanta = load_dataframe_from_supabase("fanta_stats")
        if not df_fanta.empty:
            # Group gains by player (sorted by game_id so lists are chronological)
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

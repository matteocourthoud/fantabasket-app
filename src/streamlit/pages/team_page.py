"""Team page UI - shows average opponent gain and average gain allowed by role for each team."""

import streamlit as st
from src.streamlit.logic import teams_logic


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
    logo_col, title_col = st.columns([1, 8])
    with logo_col:
        st.image(logo_path, width=72)
    with title_col:
        st.title(selected_team)

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


if __name__ == "__main__":
    main()

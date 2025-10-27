"""Stats page UI - displays player statistics with filters."""

import streamlit as st
from src.scraping.utils import get_current_season
from src.streamlit.logic import stats_logic


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

    # Format numeric columns to 1 decimal place and highlight the value column
    numeric_cols_to_format = player_avg_stats.select_dtypes(include="number").columns

    # Function to color avg_gain based on positive/negative values
    def color_avg_gain(val):
        """Color avg_gain green if positive, red if negative."""
        try:
            if val > 0:
                return "color: #28a745; font-weight: bold"  # Softer green
            elif val < 0:
                return "color: #dc3545; font-weight: bold"  # Softer red
            else:
                return "font-weight: bold"
        except (TypeError, ValueError):
            return ""

    # Apply styling with thinner font and bold value column
    styled_df = (
        player_avg_stats.style.format("{:.1f}", subset=numeric_cols_to_format)
        .set_properties(**{"font-weight": "100"})
        .set_properties(subset=["player", "value"], **{"font-weight": "bold"})
        .map(color_avg_gain, subset=["gain"])
    )

    # Add some spacing before the table
    st.markdown("")

    # Display the styled dataframe
    st.dataframe(styled_df, width="stretch", hide_index=True)


if __name__ == "__main__":
    main()

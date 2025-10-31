"""Games page - shows all upcoming games for the next day, with player lists and current values."""

from datetime import datetime

import streamlit as st
from src.supabase.tables import TABLE_CALENDAR, TABLE_FANTA_STATS
from src.supabase.utils import load_dataframe_from_supabase


def main():
    st.set_page_config(layout="wide")
    st.title("Upcoming Games")


    # Get today's date (UTC)
    today = datetime.utcnow().date()

    # Load all future games from calendar table
    calendar_df = load_dataframe_from_supabase(TABLE_CALENDAR.name)
    future_games = calendar_df[calendar_df["date"] >= today.isoformat()]
    # Get up to 5 unique dates with games, sorted
    next_dates = sorted(future_games["date"].unique())[:5]
    if not next_dates:
        st.info("No upcoming games found.")
        return


    # Load latest fanta_stats for player values
    fanta_stats = load_dataframe_from_supabase(TABLE_FANTA_STATS.name)
    player_latest_value = (
        fanta_stats.sort_values(["player", "game_id"])
        .groupby("player")
        .agg({"value_after": "last", "team": "last"})
        .reset_index()
    )

    # Create a tab for each of the next 5 dates with games
    tabs = st.tabs([date for date in next_dates])
    for i, date in enumerate(next_dates):
        with tabs[i]:
            games_df = calendar_df[calendar_df["date"] == date]

            # Expanders for each game to show player lists/values
            for _, game in games_df.iterrows():
                expander_label = f"{game['team_home']} -- {game['team_visitor']}"
                with st.expander(expander_label):
                    col1, col2 = st.columns(2)
                    for j, team in enumerate([game["team_home"], game["team_visitor"]]):
                        with (col1 if j == 0 else col2):
                            st.markdown(f"**{team}**")
                            team_players = player_latest_value[player_latest_value["team"] == team]
                            if team_players.empty:
                                st.write("No player data available.")
                            else:
                                st.dataframe(
                                    team_players[["player", "value_after"]].rename(
                                        columns={"player": "Player", "value_after": "Current Value"}
                                    ),
                                    hide_index=True,
                                    width="stretch",
                                )

if __name__ == "__main__":
    main()

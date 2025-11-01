"""Games page - shows upcoming games with player lists and values."""

from datetime import datetime

import streamlit as st
from src.streamlit.utils import color_gain
from src.supabase.tables import (
    TABLE_CALENDAR,
    TABLE_FANTA_STATS,
    TABLE_GAME_ODDS,
    TABLE_LINEUPS,
    TABLE_PREDICTIONS,
)
from src.supabase.utils import load_dataframe_from_supabase


def main():
    from urllib.parse import quote
    
    # Page title
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
    
    # Load lineups to check starter status
    lineups_df = load_dataframe_from_supabase(TABLE_LINEUPS.name)
    starters = set(lineups_df["player"].unique()) if not lineups_df.empty else set()
    
    # Load predictions for predicted gain
    predictions_df = load_dataframe_from_supabase(TABLE_PREDICTIONS.name)
    if not predictions_df.empty:
        player_latest_value = player_latest_value.merge(
            predictions_df[["player", "predicted_gain"]],
            on="player",
            how="left"
        )
    
    # Load game odds
    odds_df = load_dataframe_from_supabase(TABLE_GAME_ODDS.name)

    # Create a tab for each of the next 5 dates with games
    tabs = st.tabs([date for date in next_dates])
    for i, date in enumerate(next_dates):
        with tabs[i]:
            games_df = calendar_df[calendar_df["date"] == date]

            # Expanders for each game to show player lists/values
            for _, game in games_df.iterrows():
                # Get odds for this game
                game_odds = odds_df[
                    (odds_df["date"] == game["date"]) &
                    (odds_df["team_home"] == game["team_home"]) &
                    (odds_df["team_visitor"] == game["team_visitor"])
                ]
                
                # Build expander label with odds if available
                if not game_odds.empty:
                    odds = game_odds.iloc[0]
                    home_prob = odds["team_home_win_probability"]
                    away_prob = 1 - home_prob
                    total = odds["total_points"]
                    expander_label = (
                        f"{game['team_home']} ({home_prob:.0%}) -- "
                        f"{game['team_visitor']} ({away_prob:.0%}) "
                        f"[Points: {total:.0f}]"
                    )
                else:
                    expander_label = (
                        f"{game['team_home']} -- {game['team_visitor']}"
                    )
                
                with st.expander(expander_label):
                    col1, col2 = st.columns(2)
                    for j, team in enumerate([game["team_home"], game["team_visitor"]]):
                        with (col1 if j == 0 else col2):
                            team_url = f"/team?team={quote(team)}"
                            st.markdown(f"**[{team}]({team_url})**")
                            team_players = player_latest_value[
                                player_latest_value["team"] == team
                            ].copy()
                            if team_players.empty:
                                st.write("No player data available.")
                            else:
                                # Store original player name for sorting
                                team_players["player_name"] = team_players["player"]
                                
                                # Add starter status (check original name)
                                team_players["starter"] = team_players["player"].apply(
                                    lambda name: name in starters
                                )
                                
                                # Sort by starter (True first), then by name
                                team_players = team_players.sort_values(
                                    by=["starter", "player_name"],
                                    ascending=[False, True]
                                )
                                
                                # Convert player names to URLs
                                team_players["player"] = team_players["player"].apply(
                                    lambda name: f"/player?name={quote(name)}"
                                )
                                
                                # Select columns to display
                                columns = ["player", "starter", "value_after"]
                                if "predicted_gain" in team_players.columns:
                                    columns.append("predicted_gain")
                                
                                display_df = team_players[columns].rename(
                                    columns={
                                        "player": "Player",
                                        "starter": "Starter",
                                        "value_after": "Value",
                                        "predicted_gain": "Gain"
                                    }
                                )
                                
                                # Apply color styling to Gain column
                                if "Gain" in display_df.columns:
                                    styled_df = display_df.style.map(
                                        color_gain, subset=["Gain"]
                                    )
                                else:
                                    styled_df = display_df
                                
                                col_config = {
                                    "Player": st.column_config.LinkColumn(
                                        display_text=r"name=(.*?)$",
                                        width=150,
                                    ),
                                    "Value": st.column_config.NumberColumn(
                                        format="%.1f"
                                    ),
                                    "Starter": st.column_config.CheckboxColumn(),
                                }
                                if "Gain" in display_df.columns:
                                    col_config["Gain"] = st.column_config.NumberColumn(
                                        format="%.2f"
                                    )
                                
                                st.dataframe(
                                    styled_df,
                                    hide_index=True,
                                    width="stretch",
                                    column_config=col_config,
                                )

if __name__ == "__main__":
    main()

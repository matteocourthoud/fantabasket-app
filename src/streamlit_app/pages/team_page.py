"""Team page UI - shows team stats and recent opponent starter performance."""

from urllib.parse import quote

import streamlit as st

from src.scraping.utils import get_current_season
from src.streamlit_app.logic import teams_logic
from src.streamlit_app.utils import color_gain, image_to_data_uri
from src.database.tables import (
    TABLE_FANTA_STATS,
    TABLE_GAME_RESULTS,
    TABLE_PLAYERS,
    TABLE_STATS,
)
from src.database.utils import load_dataframe_from_supabase


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
    
    # Recent games section: show opponent starter stats for the 5 most recent games
    st.subheader("Recent Games - Opponent Starters")
    
    # Load game results, stats (for starters), fanta_stats, and players data
    season = get_current_season()
    games_df = load_dataframe_from_supabase(
        TABLE_GAME_RESULTS.name, filters={"season": season}
    )
    stats_df = load_dataframe_from_supabase(
        TABLE_STATS.name, filters={"season": season}
    )
    fanta_stats_df = load_dataframe_from_supabase(TABLE_FANTA_STATS.name)
    players_df = load_dataframe_from_supabase(TABLE_PLAYERS.name)
    
    # Find games where selected_team was winner or loser
    team_games = games_df[
        (games_df["team_winner"] == selected_team) |
        (games_df["team_loser"] == selected_team)
    ].copy()
    
    # Sort by date descending and take the 5 most recent
    team_games = team_games.sort_values("date", ascending=False).head(5)
    
    if team_games.empty:
        st.info("No recent games found for this team.")
    else:
        # For each game, show opponent starter stats from fanta_stats
        for _, game in team_games.iterrows():
            # Determine opponent team
            if game["team_winner"] == selected_team:
                opponent = game["team_loser"]
                result = "W"
                score = f"{game['pts_winner']}-{game['pts_loser']}"
            else:
                opponent = game["team_winner"]
                result = "L"
                score = f"{game['pts_loser']}-{game['pts_winner']}"
            
            # Get starters for this game from stats table
            game_starters = stats_df[
                (stats_df["game_id"] == game["game_id"]) &
                (stats_df["start"])
            ].copy()
            
            # Filter to opponent team's players (use win column to identify team)
            opponent_won = (game["team_winner"] == opponent)
            game_starters = game_starters[game_starters["win"] == opponent_won]
            
            # Calculate percentage stats for starters
            game_starters["fg%"] = game_starters["fg"] / game_starters["fga"]
            game_starters["3p%"] = game_starters["tp"] / game_starters["tpa"]
            game_starters["ast%"] = (
                game_starters["ast"] / (game_starters["ast"] + game_starters["tov"])
            )
            
            # Get game_id and player list to merge with fanta_stats
            starter_players = game_starters["player"].tolist()
            
            # Get fanta_stats for this game and these players
            game_fanta_stats = fanta_stats_df[
                (fanta_stats_df["game_id"] == game["game_id"]) &
                (fanta_stats_df["player"].isin(starter_players))
            ].copy()
            
            # Merge with game_starters to get percentage stats
            game_fanta_stats = game_fanta_stats.merge(
                game_starters[["player", "fg%", "3p%", "ast%"]],
                on="player",
                how="left",
            )
            
            # Merge with players to get player_id for images
            game_fanta_stats = game_fanta_stats.merge(
                players_df[["player", "player_id"]],
                on="player",
                how="left",
            )
            
            # Add image column
            game_fanta_stats["image"] = game_fanta_stats["player_id"].apply(
                image_to_data_uri
            )
            
            # Display game header
            st.markdown(f"**{game['date']} - vs {opponent} ({result} {score})**")
            
            if game_fanta_stats.empty:
                st.info("No starter stats available for this game.")
            else:
                # Select relevant columns for display
                display_cols = [
                    "image",
                    "player",
                    "value_after",
                    "gain",
                    "pts",
                    "trb",
                    "ast",
                    "stl",
                    "blk",
                    "fg%",
                    "3p%",
                    "ast%",
                ]
                available_cols = [
                    col for col in display_cols if col in game_fanta_stats.columns
                ]
                display_df = game_fanta_stats[available_cols].copy()
                
                # Rename value_after to value for display
                if "value_after" in display_df.columns:
                    display_df = display_df.rename(columns={"value_after": "value"})
                
                # Convert percentage columns to 0-100 scale for display
                for pct_col in ["fg%", "3p%", "ast%"]:
                    if pct_col in display_df.columns:
                        display_df[pct_col] *= 100
                
                # Add clickable links to player names
                display_df["player"] = display_df["player"].apply(
                    lambda name: f"/player?name={quote(name)}"
                )
                
                # Create a styler to format and color-code gain
                format_dict = {
                    "value": "{:.1f}",
                    "gain": "{:.1f}",
                    "pts": "{:.0f}",
                    "trb": "{:.0f}",
                    "ast": "{:.0f}",
                    "stl": "{:.0f}",
                    "blk": "{:.0f}",
                }
                styler = display_df.style.format(format_dict)
                
                # Apply color styling to gain column
                if "gain" in display_df.columns:
                    styler = styler.map(color_gain, subset=["gain"])
                
                # Prepare column config for image and percentages
                col_config = {
                    "image": st.column_config.ImageColumn(label="", width="small"),
                    "player": st.column_config.LinkColumn(
                        display_text=r"name=(.*?)$"
                    ),
                }
                for pct_col in ["fg%", "3p%", "ast%"]:
                    if pct_col in display_df.columns:
                        col_config[pct_col] = st.column_config.NumberColumn(
                            format="%.0f%%"
                        )
                
                # Display the table
                st.dataframe(
                    styler,
                    hide_index=True,
                    column_config=col_config,
                    width="stretch",
                )
            
            # Add spacing between games
            st.markdown("")


if __name__ == "__main__":
    main()

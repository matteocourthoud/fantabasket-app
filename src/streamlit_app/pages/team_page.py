"""Team page UI - shows team stats and recent opponent starter performance."""

from urllib.parse import quote

import streamlit as st

from src.database.tables import TABLE_FANTA_STATS, TABLE_PLAYERS
from src.database.utils import load_dataframe_from_supabase
from src.scraping.utils import get_current_season
from src.streamlit_app.logic import teams_logic
from src.streamlit_app.utils import color_gain, image_to_data_uri


def main():
    st.markdown("""
        <style>
        [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) .stColumn {
            min-width: 0 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Get team from query params
    query_params = st.query_params
    selected_team = query_params.get("team")
    if not selected_team:
        st.error("No team specified in URL.")
        return

    # Load team data
    df_teams = teams_logic.get_teams_gain_table()
    df_teams = df_teams[df_teams["Team"] == selected_team]

    # Display team logo smaller and inline with title
    fanta_team = df_teams.iloc[0]["fanta_team"]
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
        f"{df_teams.iloc[0]['Avg Opponent Gain']:.1f}",
        label_visibility="visible",
    )
    col2.metric(
        "Avg Gain (C)",
        f"{df_teams.iloc[0]['Avg Gain (C)']:.1f}",
        label_visibility="visible",
    )
    col3.metric(
        "Avg Gain (F)",
        f"{df_teams.iloc[0]['Avg Gain (F)']:.1f}",
        label_visibility="visible",
    )
    col4.metric(
        "Avg Gain (G)",
        f"{df_teams.iloc[0]['Avg Gain (G)']:.1f}",
        label_visibility="visible",
    )

    # Add spacing
    st.markdown("---")
    
    # Recent games section: show opponent starter stats for the 5 most recent games
    st.subheader("Recent Games - Opponent Starters")
    
    # Load game results, stats (for starters), fanta_stats, and players data
    season = get_current_season()
    df_fanta_stats = load_dataframe_from_supabase(TABLE_FANTA_STATS.name, {"season": season})
    
    # Add player id to fanta_stats
    df_players = load_dataframe_from_supabase(TABLE_PLAYERS.name)
    df_fanta_stats = df_fanta_stats.merge(
        df_players[["player", "player_id"]],
        on="player",
        how="left"
    )
    
    # Add game information
    df_games = load_dataframe_from_supabase("game_results", {"season": season})
    df_fanta_stats = df_fanta_stats.merge(
        df_games[["game_id", "date", "pts_winner", "pts_loser"]],
        on="game_id",
        how="left"
    )
    
    # Find games where selected_team was winner or loser
    cols = ["game_id", "team", "opponent_team", "win", "date", "pts_winner", "pts_loser"]
    df_games = df_fanta_stats[cols].drop_duplicates()
    df_games = df_games[df_games["team"] == selected_team]
    df_games = df_games.sort_values("game_id", ascending=False).head(5)
    
    if df_games.empty:
        st.info("No recent games found for this team.")
    else:
        # For each game, show opponent starter stats from fanta_stats
        for _, game in df_games.iterrows():
            
            # Get starters for this game from stats table
            df_starters_stats = df_fanta_stats[
                (df_fanta_stats["game_id"] == game["game_id"]) &
                (df_fanta_stats["team"] != selected_team) &
                (df_fanta_stats["start"])
            ].copy()
            
            print(selected_team)
            print(df_starters_stats["team"])
            
            # Add image column
            df_starters_stats["image"] = df_starters_stats["player_id"].apply(
                image_to_data_uri
            )
            
            # Display game header
            opponent = game["opponent_team"]
            result = "W" if game["win"] else "L"
            score = f"{game['pts_winner']}-{game['pts_loser']}"
            st.markdown(f"**{game['date']} - vs {opponent} ({result} {score})**")
            
            if df_starters_stats.empty:
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
                    "fg_pct",
                    "tp_pct",
                    "ast_pct",
                ]
                display_df = df_starters_stats[display_cols].copy()
                
                # Rename columns for display
                display_df = display_df.rename(columns={
                    "value_after": "value",
                    "fg_pct": "fg%",
                    "tp_pct": "3p%",
                    "ast_pct": "ast%",
                })
                
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
                )
            
            # Add spacing between games
            st.markdown("")


if __name__ == "__main__":
    main()

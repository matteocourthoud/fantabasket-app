"""Home page of the Streamlit application."""

from urllib.parse import quote

import streamlit as st

from src.database.tables import TABLE_PLAYERS
from src.database.utils import (
    get_time_since_last_table_update,
    load_dataframe_from_supabase,
)
from src.scraping import scrape_injuries, scrape_lineups
from src.streamlit_app.logic import injuries_logic, players_logic
from src.streamlit_app.utils import image_to_data_uri


def main():
    """Home page of the Streamlit application."""
    
    # Hero section with centered styling
    st.title("Fantabasket Stats")
    st.write("Your NBA Fantasy Basketball Analytics Hub")
    
    # Scrape latest injuries on app start
    with st.spinner("Checking for latest injuries..."):
        time_since_update_injuries = get_time_since_last_table_update("injuries")
        if time_since_update_injuries > 60:
            print("Time since last injuries update:", time_since_update_injuries)
            scrape_injuries.scrape_injuries()
            
    # Scrape lineups data on app start
    with st.spinner("Checking for latest lineups..."):
        time_since_update_lineups = get_time_since_last_table_update("lineups")
        if time_since_update_lineups > 60:
            print("Time since last lineups update:", time_since_update_lineups)
            scrape_lineups.scrape_lineups()
            
    # Create two columns for hottest players and latest injuries
    col1, col2 = st.columns(2)

    # Left column: Hottest Players
    with col1:
        st.markdown("### 🔥 Hottest Players")
        
        # Load players table for player_id mapping
        players_df = load_dataframe_from_supabase(TABLE_PLAYERS.name)

        # Process player stats to get aggregated data with predictions
        df_hot = players_logic.compute_player_stats()
        
        # Merge with players table to get player_id
        df_hot = df_hot.merge(
            players_df[["player", "player_id"]],
            on="player",
            how="left"
        )
        
        # Add image column with base64 data URIs
        df_hot["image"] = df_hot["player_id"].apply(
            image_to_data_uri
        )

        # Prepare display dataframe
        df_display = df_hot[
            ["image", "player", "value", "gain_hat"]
        ].copy()
        df_display = df_display.rename(
            columns={
                "image": "Image",
                "player": "Player",
                "value": "Value",
                "gain_hat": "Gain",
            }
        )

        # Add clickable links to player names
        df_display["Player"] = df_display["Player"].apply(
            lambda name: f"/player?name={quote(name)}"
        )

        # Format Value and Gain columns
        df_display["Value"] = df_display["Value"].apply(
            lambda x: f"{x:.1f}"
        )
        df_display["Gain"] = df_display["Gain"].apply(
            lambda x: f"{x:.3f}"
        )

        # Display table with column config (no styling for images)
        st.dataframe(
            df_display,
            hide_index=True,
            column_config={
                "Image": st.column_config.ImageColumn(
                    label="",
                    width="small",
                ),
                "Player": st.column_config.LinkColumn(
                    display_text=r"name=(.*?)$"
                ),
            },
        )
        
        # Link to full players page
        st.markdown("[View all players →](/players)")

    # Right column: Latest Injuries
    with col2:
        st.markdown("### 🏥 Latest Injuries")

        # Load injuries data using injuries_logic
        df_injuries = injuries_logic.load_injuries_data()
        
        # Load players table for player_id mapping
        players_df = load_dataframe_from_supabase(TABLE_PLAYERS.name)

        # Filter out injuries without return dates and sort
        df_injuries_sorted = (
            df_injuries[df_injuries["return_date"].notna()]
            .copy()
        )
        df_injuries_sorted = df_injuries_sorted.sort_values(
            by="return_date", ascending=True
        )
        
        # Merge with players table to get player_id
        df_injuries_sorted = df_injuries_sorted.merge(
            players_df[["player", "player_id"]],
            on="player",
            how="left"
        )
        
        # Add image column with base64 data URIs
        df_injuries_sorted["image"] = df_injuries_sorted["player_id"].apply(
            image_to_data_uri
        )

        # Prepare display dataframe
        df_inj_display = df_injuries_sorted[
            ["image", "player", "return_date", "days_until_return"]
        ].copy()
        df_inj_display = df_inj_display.rename(
            columns={
                "image": "Image",
                "player": "Player",
                "return_date": "Return Date",
                "days_until_return": "Days",
            }
        )

        # Add clickable links to player names
        df_inj_display["Player"] = df_inj_display["Player"].apply(
            lambda name: f"/player?name={quote(name)}"
        )

        # Format Return Date and Days columns
        df_inj_display["Return Date"] = df_inj_display["Return Date"].apply(
            lambda x: x.strftime("%b %d") if x else "N/A"
        )
        df_inj_display["Days"] = df_inj_display["Days"].apply(
            lambda x: f"{x:.0f}" if x else "N/A"
        )

        # Display table (no styling for images to work)
        st.dataframe(
            df_inj_display,
            hide_index=True,
            column_config={
                "Image": st.column_config.ImageColumn(
                    label="",
                    width="small",
                ),
                "Player": st.column_config.LinkColumn(
                    display_text=r"name=(.*?)$"
                )
            },
        )
        
        # Link to full injuries page
        st.markdown("[View all injuries →](/injuries)")

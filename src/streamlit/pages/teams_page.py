"""Teams page UI - displays average gain of opponents for each team."""

from urllib.parse import quote

import streamlit as st
from src.streamlit.logic.teams_logic import get_teams_gain_table


def main():
    """Teams page of the Streamlit application."""
    st.set_page_config(layout="wide")
    st.title("Teams")
    st.write(
        "This table shows, for each team, the average gain of starting players who played against them."
    )

    # For display, make a copy and modify only for the table
    display_df = get_teams_gain_table()
    display_df["Logo"] = display_df["fanta_team"].apply(
        lambda code: f"data/teams/{code}.png")
   
    # Move Logo to first column
    cols = ["Logo"] + [c for c in display_df.columns if c != "Logo"]
    display_df = display_df[cols]
    print(display_df)

    # Update Team column to be a link
    display_df["Team"] = display_df["Team"].apply(lambda t: f"/team?team={quote(str(t))}")
    col_config = {
        "Logo": st.column_config.ImageColumn("Logo", width="sm"),
        "Team": st.column_config.LinkColumn(display_text=r"team=(.*?)$"),
    }
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config=col_config,
    )

if __name__ == "__main__":
    main()

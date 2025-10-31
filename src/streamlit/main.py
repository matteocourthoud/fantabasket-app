"""Main entry point for the Streamlit application."""


from pages import (
    injuries_page,
    player_page,
    stats_page,
    team_page,
    teams_page,
    updates_page,
    games_page,
)

import streamlit as st


# Configure the page
st.set_page_config(
    page_title="Fantabasket",
    layout="centered",  # Better for mobile
    page_icon="icon.png",
    initial_sidebar_state="auto",  # Start with sidebar closed on mobile
)

# Get other pages
stats_page_obj = st.Page(
    stats_page.main,
    title="Stats",
    icon=":material/bar_chart:",
    url_path="stats",
)
player_page_obj = st.Page(
    player_page.main,
    title="Player",
    icon=":material/person:",
    url_path="player",
)
teams_page_obj = st.Page(
    teams_page.main,
    title="Teams",
    icon=":material/people:",
    url_path="teams",
)
injuries_page_obj = st.Page(
    injuries_page.main,
    title="Injuries",
    icon=":material/healing:",
    url_path="injuries",
)
updates_page_obj = st.Page(
    updates_page.main,
    title="Updates",
    icon=":material/refresh:",
    url_path="updates",
)
team_page_obj = st.Page(
    team_page.main,
    title="Team",
    icon=":material/shield:",
    url_path="team",
)
games_page_obj = st.Page(
    games_page.main,
    title="Games",
    icon=":material/sports_basketball:",
    url_path="games",
)



def home():
    """Home page of the Streamlit application."""
    st.logo("icon.png")
    st.title("Fantabasket Dashboard")

    # Welcome message
    st.markdown("Welcome to the Fantabasket Dashboard!")

    # Navigation buttons
    if st.button("Stats", icon=":material/bar_chart:", width=300):
        st.switch_page(stats_page_obj)
    if st.button("Players", icon=":material/person:", width=300):
        st.switch_page(player_page_obj)
    if st.button("Games", icon=":material/sports_basketball:", width=300):
        st.switch_page(games_page_obj)
    if st.button("Teams", icon=":material/people:", width=300):
        st.switch_page(teams_page_obj)
    if st.button("Injuries", icon=":material/healing:", width=300):
        st.switch_page(injuries_page_obj)
    if st.button("Updates", icon=":material/refresh:", width=300):
        st.switch_page(updates_page_obj)


# Define pages with icons

pg = st.navigation(
    [
        st.Page(home, title="Home", icon=":material/home:", url_path="home"),
        stats_page_obj,
        player_page_obj,
        games_page_obj,
        team_page_obj,  # Registered for routing, not shown in nav
        teams_page_obj,
        injuries_page_obj,
        updates_page_obj,
    ]
)


# Run the selected page
pg.run()

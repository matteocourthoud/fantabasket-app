"""Main entry point for the Streamlit application."""

import streamlit as st

from src.streamlit_app.pages import (
    games_page,
    home_page,
    injuries_page,
    player_page,
    stats_page,
    team_page,
    teams_page,
    updates_page,
)


# Configure the page
st.set_page_config(
    page_title="Fantabasket",
    layout="centered",  # Better for mobile
    page_icon="icon.png",
    initial_sidebar_state="auto",  # Start with sidebar closed on mobile
)

# Get other pages
home_page_obj = st.Page(
    home_page.main,
    title="Home",
    icon=":material/home:",
    url_path="home"
)
stats_page_obj = st.Page(
    stats_page.main,
    title="Players",
    icon=":material/bar_chart:",
    url_path="players",
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


# Sidebar
st.logo("icon.png")
st.sidebar.page_link(home_page_obj, label='Home')
st.sidebar.page_link(games_page_obj, label='Games')
st.sidebar.page_link(stats_page_obj, label='Players')
st.sidebar.page_link(teams_page_obj, label='Teams')
st.sidebar.page_link(injuries_page_obj, label='Injuries')
st.sidebar.page_link(updates_page_obj, label='Updates')


# Define pages with icons
pg = st.navigation(
    [
        home_page_obj,
        stats_page_obj,
        player_page_obj,
        games_page_obj,
        team_page_obj,
        teams_page_obj,
        injuries_page_obj,
        updates_page_obj,
    ],
    position="hidden",
)


# Run the selected page
pg.run()

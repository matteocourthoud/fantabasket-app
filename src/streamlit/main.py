"""Main entry point for the Streamlit application."""

from pages import injuries_page, players_page, stats_page, updates_page

import streamlit as st


# Configure the page
st.set_page_config(
    page_title="Fantabasket",
    layout="centered",  # Better for mobile
    page_icon="icon.png",
    initial_sidebar_state="auto",  # Start with sidebar closed on mobile
)

# Get other pages
stats_page = st.Page(
    stats_page.main,
    title="Stats",
    icon=":material/bar_chart:",
    url_path="stats",
)
players_page = st.Page(
    players_page.main,
    title="Players",
    icon=":material/person:",
    url_path="players",
)
injuries_page = st.Page(
    injuries_page.main,
    title="Injuries",
    icon=":material/healing:",
    url_path="injuries",
)
updates_page = st.Page(
    updates_page.main,
    title="Updates",
    icon=":material/refresh:",
    url_path="updates",
)


def home():
    """Home page of the Streamlit application."""
    st.logo("icon.png")
    st.title("Fantabasket Dashboard")

    # Welcome message
    st.markdown("Welcome to the Fantabasket Dashboard!")

    # Navigation buttons
    if st.button("Stats", icon=":material/bar_chart:", width=300):
        st.switch_page(stats_page)
    if st.button("Players", icon=":material/person:", width=300):
        st.switch_page(players_page)
    if st.button("Injuries", icon=":material/healing:", width=300):
        st.switch_page(injuries_page)
    if st.button("Updates", icon=":material/refresh:", width=300):
        st.switch_page(updates_page)


# Define pages with icons
pg = st.navigation(
    [
        st.Page(home, title="Home", icon=":material/home:", url_path="home"),
        stats_page,
        players_page,
        injuries_page,
        updates_page,
    ]
)


# Run the selected page
pg.run()

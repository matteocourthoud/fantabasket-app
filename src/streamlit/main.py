"""Main entry point for the Streamlit application."""

from pages import injuries_page, players_page, stats_page

import streamlit as st


# Must be called first, before any other Streamlit commands
st.set_page_config(layout="wide", page_title="Fantabasket")

# Custom CSS to make sidebar font bigger
st.markdown(
    """
    <style>
    /* Increase sidebar navigation icon size */
    [data-testid="stSidebarNav"] li a span {
        font-size: 1.1rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def home():
    """Home page of the Streamlit application."""
    st.title("Fantabasket Dashboard")
    st.markdown("## Welcome to the Fantabasket Analytics Platform")

    st.info("Use the sidebar to navigate between different pages.")

    st.markdown(
        """
    ### Available Pages:
    - **Stats**: View player statistics and performance metrics
    - **Players**: Individual player performance and trends
    - **Injuries**: Current injury reports
    - More features coming soon!
    """
    )


# Define pages with icons
pg = st.navigation(
    [
        st.Page(home, title="Home", icon=":material/home:", url_path="home"),
        st.Page(
            stats_page.main,
            title="Stats",
            icon=":material/bar_chart:",
            url_path="stats",
        ),
        st.Page(
            players_page.main,
            title="Players",
            icon=":material/person:",
            url_path="players",
        ),
        st.Page(
            injuries_page.main,
            title="Injuries",
            icon=":material/healing:",
            url_path="injuries",
        ),
    ]
)

# Run the selected page
pg.run()

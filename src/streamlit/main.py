import os
import sys

import streamlit as st

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.streamlit.stats import stats_tab


def main():
    """Main function to run the Streamlit application. Sets up the page configuration and tabs."""
    st.set_page_config(layout="wide", page_title="Fantabasket Dashboard")

    # --- TABS ---
    tab_stats, tab_placeholder = st.tabs(["Stats", "Coming Soon"])

    with tab_stats:
        stats_tab()

    with tab_placeholder:
        st.info("More features coming soon!")

if __name__ == "__main__":
    main()

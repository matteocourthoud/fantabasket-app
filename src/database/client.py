"""Supabase client configuration."""

import os

from dotenv import load_dotenv
from supabase import Client, create_client


def _get_supabase_credentials() -> tuple[str, str]:
    """Get Supabase credentials from either .env or Streamlit secrets."""
    # First try environment variables
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    # If not found, try Streamlit secrets
    if not url or not key:
        try:
            import streamlit as st
            url = st.secrets.connections.supabase.SUPABASE_URL
            key = st.secrets.connections.supabase.SUPABASE_KEY
        except (AttributeError, KeyError):
            raise ValueError(
                "Supabase credentials not found. Please set either:\n"
                "1. SUPABASE_URL and SUPABASE_KEY in .env file, or\n"
                "2. connections.supabase credentials in .streamlit/secrets.toml"
            )
    
    return url, key


_client: Client | None = None


def get_supabase_client() -> Client:
    """Get or create Supabase client singleton."""
    global _client
    if _client is None:
        url, key = _get_supabase_credentials()
        _client = create_client(url, key)
    return _client

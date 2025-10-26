"""Supabase client configuration."""

import os

from dotenv import load_dotenv

from supabase import Client, create_client

# Load environment variables from .env file
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

_client: Client | None = None


def get_supabase_client() -> Client:
    """Get or create Supabase client singleton."""
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY must be set in environment variables. "
                "Please create a .env file with these values.",
            )
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client

"""Utility functions for Streamlit pages."""

import base64
from pathlib import Path

import pandas as pd


def get_image_data_uri(
    image_id: str | None, subfolder: str = "players", extension: str = "jpg"
) -> str | None:
    """Convert an image to a base64 data URI for use in Streamlit ImageColumn.
    
    Args:
        image_id: The identifier for the image file (without extension)
        subfolder: The subfolder within 'data/' (default: 'players')
        extension: The file extension (default: 'jpg')
    
    Returns:
        Base64 data URI string or None if image not found
    """
    if not image_id or pd.isna(image_id):
        return None
    image_path = Path(f"data/{subfolder}/{image_id}.{extension}")
    if not image_path.exists():
        return None
    
    # Determine MIME type based on extension
    mime_type = f"image/{extension}" if extension != "jpg" else "image/jpeg"
    
    try:
        with open(image_path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode()
        return f"data:{mime_type};base64,{img_data}"
    except Exception:
        return None


def image_to_data_uri(player_id: str | None) -> str | None:
    """Convert a player image to a base64 data URI for use in Streamlit ImageColumn.
    
    Deprecated: Use get_image_data_uri(player_id, 'players') instead.
    """
    return get_image_data_uri(player_id, "players")


def color_gain(val: float | None, threshold: float = 0.1) -> str:
    """Apply color styling to gain values for Streamlit dataframes."""
    if val is None or pd.isna(val):
        return ""
    if -threshold <= val <= threshold:
        color = "gray"
    elif val > 0:
        color = "green"
    else:
        color = "red"
    return f"color: {color}"

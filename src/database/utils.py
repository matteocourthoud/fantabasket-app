"""Utility functions for Supabase database operations."""

import datetime

import pandas as pd

from src.database.client import get_supabase_client
from src.database.tables import TABLE_UPDATES


def save_dataframe_to_supabase(
    df: pd.DataFrame,
    table_name: str,
    index_columns: list[str],
    upsert: bool = True,
    replace: bool = False,
    batch_size: int = None,
) -> None:
    """Save a pandas DataFrame to a Supabase table.
    
    Args:
        df: DataFrame to save
        table_name: Name of the Supabase table
        index_columns: List of column names that uniquely identify rows (used for conflict detection)
        upsert: If True, update existing rows on conflict; if False, insert only
        replace: If True, delete all existing records before inserting new ones (full table replacement)
        batch_size: Number of records to insert per batch (default: insert all at once)
    
    Returns:
        dict: Response from Supabase with information about the operation

    """
    client = get_supabase_client()

    # Convert DataFrame to list of dictionaries
    records = df.where(pd.notna(df), None).to_dict("records")
    assert records, f"No records to save to {table_name}"

    # If replace mode, delete all existing records first
    if replace:
        client.table(table_name).delete().neq(index_columns[0], "").execute()
        print(f"✓ Cleared all existing records from '{table_name}' table")

    # Process in batches if batch_size is specified
    if batch_size and len(records) > batch_size:
        total_batches = (len(records) + batch_size - 1) // batch_size
        print(f"  Processing {len(records)} records in {total_batches} batches of {batch_size}...")

        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            batch_num = (i // batch_size) + 1

            if upsert and not replace:
                client.table(table_name).upsert(
                    batch,
                    on_conflict=",".join(index_columns),
                ).execute()
            else:
                client.table(table_name).insert(batch).execute()

            print(f"  ✓ Batch {batch_num}/{total_batches}: Saved {len(batch)} records")

        print(f"✓ Saved total of {len(records)} records to '{table_name}' table in Supabase")
    else:
        # Insert all at once
        if upsert and not replace:
            # Upsert: insert new records or update existing ones
            client.table(table_name).upsert(
                records,
                on_conflict=",".join(index_columns),
            ).execute()
        else:
            # Insert only: will fail if records already exist (unless we just cleared in replace mode)
            client.table(table_name).insert(records).execute()

        print(f"✓ Saved {len(records)} records to '{table_name}' table in Supabase")

    # Update the updates table with the current timestamp
    now_utc = datetime.datetime.now(datetime.UTC).isoformat()
    client.table(TABLE_UPDATES.name).upsert(
        {"table_name": table_name, "last_updated": now_utc},
        on_conflict="table_name",
    ).execute()



def load_dataframe_from_supabase(
        table_name: str,
        filters: dict = None,
    ) -> pd.DataFrame:
    """Load data from a Supabase table into a pandas DataFrame.
    
    Args:
        table_name: Name of the Supabase table
        filters: A dictionary of filters to apply (e.g., {'season': 2025})

    """
    client = get_supabase_client()
    query = client.table(table_name).select("*")

    if filters:
        for column, value in filters.items():
            query = query.eq(column, value)

    response = query.execute()
    df = pd.DataFrame(response.data)
    print(f"✓ Loaded {len(df)} records from '{table_name}' table in Supabase")
    return df



def get_table_last_updated(table_name: str) -> pd.Timestamp | None:
    """Return the last_updated timestamp for a table from the updates table."""
    df_updates = load_dataframe_from_supabase(TABLE_UPDATES.name)
    matching = df_updates[df_updates.get("table_name") == table_name]
    ts = pd.to_datetime(matching["last_updated"].iloc[0], errors="coerce")
    return ts


def get_time_since_last_table_update(table_name: str) -> float:
    """Get time in minutes since last update of a given table in the database."""
    print("Getting time since last update for table:", table_name)
    df_updates = load_dataframe_from_supabase(TABLE_UPDATES.name)
    matching = df_updates[df_updates.get("table_name") == table_name]
    last_updated = pd.to_datetime(matching["last_updated"].iloc[0])
    time_diff = pd.Timestamp.now(tz="UTC") - last_updated
    time_since_update = time_diff.total_seconds() / 60  # minutes
    return time_since_update

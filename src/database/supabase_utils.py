"""Utility functions for Supabase database operations."""

import pandas as pd
from typing import List
from .supabase_client import get_supabase_client


def save_dataframe_to_supabase(
    df: pd.DataFrame,
    table_name: str,
    index_columns: List[str],
    upsert: bool = True,
    replace: bool = False,
    batch_size: int = None
) -> None:
    """
    Save a pandas DataFrame to a Supabase table.
    
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
        client.table(table_name).delete().neq(index_columns[0], '').execute()
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
                    on_conflict=','.join(index_columns)
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
                on_conflict=','.join(index_columns)
            ).execute()
        else:
            # Insert only: will fail if records already exist (unless we just cleared in replace mode)
            client.table(table_name).insert(records).execute()
        
        print(f"✓ Saved {len(records)} records to '{table_name}' table in Supabase")



def load_dataframe_from_supabase(table_name: str) -> pd.DataFrame:
    """Load all data from a Supabase table into a pandas DataFrame."""
    client = get_supabase_client()
    response = client.table(table_name).select('*').execute()    
    df = pd.DataFrame(response.data)
    print(f"✓ Loaded {len(df)} records from '{table_name}' table in Supabase")
    return df

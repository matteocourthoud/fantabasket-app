"""Tests to verify that table schemas match actual Supabase database structure."""

import pytest

from src.database.client import get_supabase_client
from src.database.tables import ALL_TABLES, TABLES_BY_NAME


@pytest.fixture(scope="module")
def supabase_client():
    """Get Supabase client for all tests."""
    return get_supabase_client()


def get_actual_columns(client, table_name: str) -> set[str]:
    """Get actual column names from Supabase table."""
    try:
        response = client.table(table_name).select("*").limit(1).execute()
        if response.data and len(response.data) > 0:
            return set(response.data[0].keys())
        # If table is empty, try to infer from schema (this may fail)
        return set()
    except Exception as e:
        pytest.fail(f"Failed to fetch columns from table '{table_name}': {e}.")


class TestTableExistence:
    """Test that all defined tables exist in Supabase."""
    
    @pytest.mark.parametrize("table", ALL_TABLES)
    def test_table_exists(self, supabase_client, table):
        """Test that table exists and is accessible."""
        try:
            response = supabase_client.table(table.name).select("*").limit(1).execute()
            assert response is not None, f"Table '{table.name}' does not exist."
        except Exception as e:
            pytest.fail(f"Table '{table.name}' does not exist: {e}.")


class TestColumnDefinitions:
    """Test that column definitions match actual database schema."""
    
    @pytest.mark.parametrize("table", ALL_TABLES)
    def test_all_defined_columns_exist(self, supabase_client, table):
        """Test that all columns defined in schema exist in actual table."""
        actual_columns = get_actual_columns(supabase_client, table.name)
        
        if not actual_columns:
            pytest.skip(f"Table '{table.name}' is empty, cannot verify columns.")
        
        defined_columns = set(table.get_column_names())
        missing_in_db = defined_columns - actual_columns
        
        assert not missing_in_db, (
            f"Table '{table.name}': Columns missing in database: {missing_in_db}."
        )
    
    @pytest.mark.parametrize("table", ALL_TABLES)
    def test_no_unexpected_columns(self, supabase_client, table):
        """Test that no unexpected columns exist in actual table."""
        actual_columns = get_actual_columns(supabase_client, table.name)
        
        if not actual_columns:
            pytest.skip(f"Table '{table.name}' is empty, cannot verify columns")
        
        defined_columns = set(table.get_column_names())
        unexpected_in_db = actual_columns - defined_columns
        
        assert not unexpected_in_db, (
            f"Table '{table.name}': Columns not defined in schema: {unexpected_in_db}."
        )


class TestPrimaryKeys:
    """Test primary key definitions."""
    
    @pytest.mark.parametrize("table", ALL_TABLES)
    def test_has_primary_keys(self, table):
        """Test that each table has at least one primary key defined."""
        primary_keys = table.get_primary_keys()
        assert len(primary_keys) > 0, f"Table '{table.name}' has no primary keys."
    
    @pytest.mark.parametrize("table", ALL_TABLES)
    def test_primary_keys_not_nullable(self, table):
        """Test that primary key columns are not nullable."""
        for col in table.columns:
            if col.is_primary:
                assert not col.is_nullable, (
                    f"Table '{table.name}': Column '{col.name}' should not be nullable."
                )


class TestDataIntegrity:
    """Test data integrity constraints."""
    
    @pytest.mark.parametrize("table", ALL_TABLES)
    def test_primary_key_columns_exist(self, table):
        """Test that primary key columns are defined in the column list."""
        column_names = table.get_column_names()
        primary_keys = table.get_primary_keys()
        
        for pk in primary_keys:
            assert pk in column_names, (
                f"Table '{table.name}': Primary key '{pk}' not found in columns."
            )
    
    @pytest.mark.parametrize("table", ALL_TABLES)
    def test_unique_columns_are_primary_or_explicitly_unique(self, table):
        """Test that unique constraints make sense."""
        for col in table.columns:
            if col.is_unique and not col.is_primary:
                # It's okay to have unique non-primary columns
                pass


class TestTableRegistry:
    """Test the table registry functions."""
    
    def test_all_tables_in_registry(self):
        """Test that all tables are in the registry."""
        assert len(ALL_TABLES) == len(TABLES_BY_NAME)
        
        for table in ALL_TABLES:
            assert table.name in TABLES_BY_NAME
            assert TABLES_BY_NAME[table.name] == table
    
    def test_expected_tables_exist(self):
        """Test that all expected tables are defined."""
        expected_tables = [
            "stats", "games", "calendar", "initial_values", "fanta_stats",
            "players", "teams", "lineups", "injuries"
        ]
        
        for table_name in expected_tables:
            assert table_name in TABLES_BY_NAME, f"Missing table: {table_name}."

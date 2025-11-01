"""Supabase table schema definitions."""

from dataclasses import dataclass


@dataclass
class Column:
    """Represents a database column with its properties."""
    
    name: str
    type: str
    is_primary: bool = False
    is_nullable: bool = False
    is_unique: bool = False


@dataclass
class Table:
    """Represents a database table with its columns."""
    
    name: str
    columns: list[Column]
    
    def get_column(self, name: str) -> Column | None:
        """Get a column by name."""
        for col in self.columns:
            if col.name == name:
                return col
        return None
    
    def get_primary_keys(self) -> list[str]:
        """Get list of primary key column names."""
        return [col.name for col in self.columns if col.is_primary]
    
    def get_column_names(self) -> list[str]:
        """Get list of all column names."""
        return [col.name for col in self.columns]



# ============================================================================
# TABLE DEFINITIONS
# ============================================================================

TABLE_STATS = Table(
    name="stats",
    columns=[
        Column("game_id", "text", is_primary=True),
        Column("player_id", "text", is_primary=True),
        Column("season", "integer"),
        Column("player", "text"),
        Column("mp", "integer"),
        Column("fg", "integer"),
        Column("fga", "integer"),
        Column("tp", "integer"),
        Column("tpa", "integer"),
        Column("ft", "integer"),
        Column("fta", "integer"),
        Column("orb", "integer"),
        Column("drb", "integer"),
        Column("trb", "integer"),
        Column("ast", "integer"),
        Column("stl", "integer"),
        Column("blk", "integer"),
        Column("tov", "integer"),
        Column("pf", "integer"),
        Column("pts", "integer"),
        Column("pm", "integer"),
        Column("start", "boolean"),
        Column("win", "boolean"),
        Column("gmsc", "float"),
    ],
)

TABLE_GAME_RESULTS = Table(
    name="game_results",
    columns=[
        Column("game_id", "text", is_primary=True, is_unique=True),
        Column("season", "integer"),
        Column("date", "text"),
        Column("team_winner", "text"),
        Column("team_loser", "text"),
        Column("pts_winner", "integer"),
        Column("pts_loser", "integer"),
    ],
)

TABLE_CALENDAR = Table(
    name="calendar",
    columns=[
        Column("date", "text", is_primary=True),
        Column("team_home", "text", is_primary=True),
        Column("team_visitor", "text"),
        Column("season", "integer"),
    ],
)

TABLE_INITIAL_VALUES = Table(
    name="initial_values",
    columns=[
        Column("fanta_player_id", "text", is_primary=True),
        Column("season", "integer", is_primary=True),
        Column("fanta_player", "text"),
        Column("position", "text"),
        Column("initial_value", "float"),
    ],
)

TABLE_FANTA_STATS = Table(
    name="fanta_stats",
    columns=[
        Column("game_id", "text", is_primary=True, is_unique=True),
        Column("player", "text"),
        Column("team", "text"),
        Column("fanta_team", "text"),
        Column("position", "text"),
        Column("fanta_score", "float"),
        Column("value_before", "float"),
        Column("gain", "float"),
        Column("value_after", "float"),
        Column("mp", "float"),
        Column("pts", "float"),
        Column("trb", "float"),
        Column("ast", "float"),
        Column("stl", "float"),
        Column("blk", "float"),
        Column("start", "boolean"),
        Column("opponent_team", "text"),
        Column("season", "integer"),
    ],
)

TABLE_PLAYERS = Table(
    name="players",
    columns=[
        Column("player_id", "text", is_primary=True, is_unique=True),
        Column("player", "text"),
        Column("fanta_player_id", "text"),
        Column("fanta_player", "text"),
    ],
)

TABLE_TEAMS = Table(
    name="teams",
    columns=[
        Column("team", "text", is_primary=True, is_unique=True),
        Column("team_short", "text"),
        Column("fanta_team", "text"),
    ],
)

TABLE_LINEUPS = Table(
    name="lineups",
    columns=[
        Column("team", "text", is_primary=True),
        Column("player", "text", is_primary=True),
        Column("status", "text", is_nullable=True),
    ],
)

TABLE_INJURIES = Table(
    name="injuries",
    columns=[
        Column("player", "text", is_primary=True, is_unique=True),
        Column("status", "text"),
    ],
)

TABLE_PLAYER_NEWS = Table(
    name="player_news",
    columns=[
        Column("player", "text", is_primary=True),
        Column("news", "text"),
        Column("scraped_at", "timestamptz"),
    ],
)

TABLE_UPDATES = Table(
    name="updates",
    columns=[
        Column("table_name", "text", is_primary=True, is_unique=True),
        Column("last_updated", "timestamptz"),
    ],
)

TABLE_PREDICTIONS = Table(
    name="predictions",
    columns=[
        Column("player", "text", is_primary=True, is_unique=True),
        Column("predicted_score", "float"),
        Column("predicted_gain", "float"),
    ],
)

TABLE_GAME_ODDS = Table(
    name="game_odds",
    columns=[
        Column("date", "text", is_primary=True),
        Column("team_home", "text", is_primary=True),
        Column("team_visitor", "text"),
        Column("team_home_win_probability", "float"),
        Column("total_points", "float"),
    ],
)


# ============================================================================
# TABLE REGISTRY
# ============================================================================

ALL_TABLES = [
    TABLE_STATS,
    TABLE_GAME_RESULTS,
    TABLE_CALENDAR,
    TABLE_INITIAL_VALUES,
    TABLE_FANTA_STATS,
    TABLE_PLAYERS,
    TABLE_TEAMS,
    TABLE_LINEUPS,
    TABLE_INJURIES,
    TABLE_PLAYER_NEWS,
    TABLE_UPDATES,
    TABLE_PREDICTIONS,
    TABLE_GAME_ODDS,
]

TABLES_BY_NAME = {table.name: table for table in ALL_TABLES}

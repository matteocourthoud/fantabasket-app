"""Predict fantabasket gain for the next match."""


import pandas as pd
import statsmodels.formula.api as smf

from src.scraping.update_fanta_stats import _compute_gain
from src.scraping.utils import get_current_season
from src.supabase.tables import (
    TABLE_CALENDAR,
    TABLE_FANTA_STATS,
    TABLE_GAME_RESULTS,
    TABLE_INJURIES,
    TABLE_LINEUPS,
    TABLE_PREDICTIONS,
)
from src.supabase.utils import load_dataframe_from_supabase, save_dataframe_to_supabase


def _get_season_stats_with_match_info(season: int) -> pd.DataFrame:
    """Adds games information to fanta_stats."""
    # Load data from Supabase
    df_fanta_stats = load_dataframe_from_supabase(TABLE_FANTA_STATS.name)
    df_games = load_dataframe_from_supabase(TABLE_GAME_RESULTS.name)

    # Filter by season
    df_fanta_stats = df_fanta_stats[df_fanta_stats["season"] == season]
    df_games = df_games[df_games["season"] == season]

    # Merge fanta_stats with games
    df_stats = pd.merge(df_fanta_stats, df_games, on="game_id", how="left")

    return df_stats


def _get_season_stats_with_injuries(season: int) -> pd.DataFrame:
    """Import stats data and information on the next match."""
    df_stats = _get_season_stats_with_match_info(season=season)
    df_stats["date"] = pd.to_datetime(df_stats["date"])

    # Load injuries from Supabase
    df_injuries = load_dataframe_from_supabase(TABLE_INJURIES.name)

    # Merge stats with injuries
    df_stats = pd.merge(df_stats, df_injuries, on="player", how="left")
    df_stats = df_stats.sort_values(["player", "date"])
    return df_stats


def _get_next_opponent(season: int) -> pd.DataFrame:
    """Imports dataframe with information on the next matches."""
    df_calendar = load_dataframe_from_supabase(TABLE_CALENDAR.name)
    df_calendar = df_calendar[df_calendar["season"] == season]
    df_calendar["date"] = pd.to_datetime(df_calendar["date"])

    # Create two versions: one for home teams, one for visitors
    temp1 = df_calendar.rename(
        columns={
            "team_visitor": "own_team",
            "team_home": "opponent_team",
        }
    )
    temp2 = df_calendar.rename(
        columns={
            "team_visitor": "opponent_team",
            "team_home": "own_team",
        }
    )
    df = pd.concat([temp1, temp2], ignore_index=True)

    # Get first matchup for each "own_team"
    df = df.sort_values("date")
    df = df[df.date >= pd.to_datetime("today")]
    df = df.groupby("own_team", as_index=False)[["opponent_team"]].first()
    return df


def _get_next_match_per_player(df_stats: pd.DataFrame, season: int) -> pd.DataFrame:
    """Check next match for each player."""
    # Get latest value and team for each player
    # Note: Using 'value_after' as the current fanta value
    df_player_next_match = df_stats.groupby("player", as_index=False)[
        ["value_after", "team", "status"]
    ].last()
    df_player_next_match = df_player_next_match.rename(
        columns={"value_after": "fanta_value"}
    )

    # Use team name directly (already in full format)
    df_player_next_match["own_team"] = df_player_next_match["team"]

    # Add next opponent
    df_next_match = _get_next_opponent(season=season)
    df_player_next_match = pd.merge(
        df_player_next_match, df_next_match, on="own_team", how="left"
    )

    # Add lineup status (starter or not)
    df_lineups = load_dataframe_from_supabase(TABLE_LINEUPS.name)
    # Lineups table has 'player' and 'status' columns
    # We need to check if player is in starting lineup
    df_lineups_starters = df_lineups[
        df_lineups["status"].str.lower().str.contains("starter", na=False)
    ].copy()
    df_lineups_starters["start"] = 1

    df_player_next_match = pd.merge(
        df_player_next_match,
        df_lineups_starters[["player", "start"]],
        on="player",
        how="left",
    )
    df_player_next_match["start"] = df_player_next_match["start"].fillna(0)
    return df_player_next_match


def _fit_model_gain(df: pd.DataFrame):
    """Fit weighted least squares model to predict fantasy scores."""
    df_train = df.copy()
    df_train["last_date"] = df_train.groupby("player")["date"].transform("max")
    days_from_last_date = 1.0 + (
        df_train["last_date"] - df_train["date"]
    ).dt.days.astype(float)
    df_train["weights"] = days_from_last_date ** (-1)

    model = smf.wls(
        "fanta_score ~ -1 + C(player) + C(opponent_team) + start",
        df_train,
        weights=df_train.weights,
    ).fit()
    return model


def _predict_gain(df: pd.DataFrame, model) -> pd.DataFrame:
    """Predict gain in test data using fitted model."""
    df_test = df.copy()
    predictions = model.get_prediction(df_test)

    # Calculate predicted score with conservative adjustment
    df_test["predicted_score"] = predictions.predicted_mean - 1 * (
        predictions.se_mean - predictions.se_mean.mean()
    )

    # Calculate gain using the official Dunkest formula
    df_test["predicted_gain"] = df_test.apply(
        lambda row: _compute_gain(row["fanta_value"], row["predicted_score"]),
        axis=1,
    )

    # Penalize injured players (excluding "game time decision")
    df_test.loc[
        (~pd.isna(df_test.status)) & (df_test.status != "gtd"),
        "predicted_gain",
    ] = -0.1

    df_test = df_test.sort_values("predicted_gain", ascending=False)
    df_test = df_test[
        [
            "player",
            "predicted_gain",
            "predicted_score",
            "fanta_value",
            "start",
            "status",
            "opponent_team",
        ]
    ]
    return df_test


def _compute_predicted_gain(season: int) -> pd.DataFrame:
    """Compute predicted gains for all players."""
    df_stats = _get_season_stats_with_injuries(season=season)
    df_next_match = _get_next_match_per_player(df_stats=df_stats, season=season)
    model = _fit_model_gain(df=df_stats)
    df_predicted_gain = _predict_gain(df_next_match, model)
    return df_predicted_gain


def update_predicted_gain(season: int | None = None) -> pd.DataFrame:
    """Predicts the fantabasket gain for next match and saves to database."""

    if season is None:
        season = get_current_season()


    # Compute predictions
    df_predicted_gain = _compute_predicted_gain(season=season)
    
    # Select only the columns we want to save
    df_to_save = df_predicted_gain[
        ["player", "predicted_score", "predicted_gain"]
    ].copy()
    
    # Save to database
    save_dataframe_to_supabase(
        df=df_to_save,
        table_name=TABLE_PREDICTIONS.name,
        index_columns=["player"],
        upsert=True,
    )
    
    return df_predicted_gain


if __name__ == "__main__":
    update_predicted_gain()

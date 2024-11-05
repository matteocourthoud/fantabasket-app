"""Scrape NBA lineups for the next game for each team."""

import os
import numpy as np
import pandas as pd

LINEUPS_FILE = 'lineups.csv'
TEAMS_FILE = 'teams.csv'
STATS_FILE = '%i/stats.csv'
GAMES_FILE = '%i/games.csv'
WEBSITE_URL = 'https://basketballmonster.com/nbalineups.aspx'


def _get_df_last_lineups(data_dir: str, season: int) -> pd.DataFrame:
    df_stats = pd.read_csv(os.path.join(data_dir, str(season), STATS_FILE))
    df_games = pd.read_csv(os.path.join(data_dir, GAMES_FILE % season))
    df_teams = pd.read_csv(os.path.join(data_dir, TEAMS_FILE))

    df_stats = pd.merge(df_stats, df_games, on="game_id", how="left")
    df_stats["team"] = np.where(df_stats.win == 1, df_stats.winner, df_stats.loser)

    df_lineups = pd.DataFrame()
    for team in df_teams.team.to_list():
        df_team = df_stats[df_stats.team == team]
        df_team = df_team[(df_team.date == df_team.date.max()) & (df_team.start == 1)]
        df_lineups = pd.concat([df_lineups, df_team[["team", "name", "date"]]])

    assert len(df_lineups) == 150
    return df_lineups


def _remove_suffixes(strings: list[str]) -> list[str]:
    suffixes = ["Q", "P", "IN", "Off Inj"]
    cleaned_strings = []
    for s in strings:
        # Check each suffix and remove if found at the end of the string
        for suffix in suffixes:
            if s.endswith(suffix):
                s = s[:-len(suffix)]  # Remove the suffix
                break  # Exit the loop once a suffix is removed
        cleaned_strings.append(s.strip())
    return cleaned_strings


def _scrape_next_lineups(data_dir: str) -> pd.DataFrame:
    df_teams = pd.read_csv(os.path.join(data_dir, TEAMS_FILE))
    dfs = pd.read_html(WEBSITE_URL)
    df_next_lineups = pd.DataFrame()
    for df in dfs:
        for col in [1, 2]:
            team_short = df.columns[col][1].replace("@ ", "")
            team_short = team_short if team_short != "NOR" else "NOP"
            team_name = df_teams.loc[df_teams.team_short == team_short, "team"].values[0]
            players = _remove_suffixes(df.iloc[:, col].to_list())
            temp = pd.DataFrame({"team": [team_name]*5, "name": players})
            df_next_lineups = pd.concat([df_next_lineups, temp])
    return df_next_lineups


def update_get_next_lineups(data_dir: str, season: int) -> pd.DataFrame:
    """Scrape NBA lineups from https://basketballmonster.com/nbalineups."""
    print("Scraping lineups...")

    df_last_lineups = _get_df_last_lineups(data_dir=data_dir, season=season)
    df_next_lineups = _scrape_next_lineups(data_dir=data_dir)
    df_last_lineups_not_updated = df_last_lineups[~df_last_lineups.team.isin(df_next_lineups.team.unique())]
    df_lineups = pd.concat([df_last_lineups_not_updated, df_next_lineups]).sort_values("team").reset_index(drop=True)
    df_lineups.to_csv(os.path.join(data_dir, LINEUPS_FILE), index=False)
    return df_lineups

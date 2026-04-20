#!/usr/bin/env python3

import argparse
import csv
from datetime import date
from pathlib import Path


FEATURE_COLUMNS = [
    "Home_PPG_Last5",
    "Away_PPG_Last5",
    "Home_GoalsScored_Last5",
    "Away_GoalsScored_Last5",
    "Home_GoalsConceded_Last5",
    "Away_GoalsConceded_Last5",
    "Home_Shots_Last5",
    "Away_Shots_Last5",
    "Home_ShotsAllowed_Last5",
    "Away_ShotsAllowed_Last5",
    "Home_SOT_Last5",
    "Away_SOT_Last5",
    "Home_SOTAllowed_Last5",
    "Away_SOTAllowed_Last5",
    "Home_OppAvgElo_Last5",
    "Away_OppAvgElo_Last5",
    "PPG_Last5_Diff",
    "Goals_Last5_Diff",
    "GoalsConceded_Last5_Diff",
    "Shots_Last5_Diff",
    "SOT_Last5_Diff",
    "ShotDiff_Last5_Diff",
    "HomeRestDays",
    "AwayRestDays",
    "RestDiff",
]


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    default_input = script_dir.parent / "data" / "epl_2020_onward_with_elo.csv"
    default_output = script_dir.parent / "data" / "epl_model_features.csv"

    parser = argparse.ArgumentParser(
        description="Build rolling Last5 and rest-day model features for EPL matches."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=default_input,
        help=f"Annotated match CSV path. Defaults to {default_input}.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help=f"Destination feature CSV path. Defaults to {default_output}.",
    )
    parser.add_argument(
        "--window-size",
        type=int,
        default=5,
        help="Number of prior matches to use for rolling features.",
    )
    parser.add_argument(
        "--rest-cap",
        type=int,
        default=20,
        help="Maximum rest days to record for either team.",
    )
    return parser.parse_args()


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def format_float(value: float | None) -> str:
    if value is None:
        return "NaN"
    return f"{value:.2f}"


def format_int(value: int | None) -> str:
    if value is None:
        return "NaN"
    return str(value)


def parse_match_date(value: str) -> date:
    return date.fromisoformat(value)


def team_points(result: str, is_home_team: bool) -> float:
    if result == "D":
        return 1.0
    if result == "H":
        return 3.0 if is_home_team else 0.0
    if result == "A":
        return 0.0 if is_home_team else 3.0
    raise ValueError(f"Unsupported FullTimeResult value: {result!r}")


def build_team_match_stats(
    row: dict[str, str], is_home_team: bool
) -> dict[str, float]:
    if is_home_team:
        goals_scored = float(row["FullTimeHomeGoals"])
        goals_conceded = float(row["FullTimeAwayGoals"])
        shots = float(row["HomeShots"])
        shots_allowed = float(row["AwayShots"])
        sot = float(row["HomeShotsOnTarget"])
        sot_allowed = float(row["AwayShotsOnTarget"])
        opponent_elo = float(row["AwayElo"])
    else:
        goals_scored = float(row["FullTimeAwayGoals"])
        goals_conceded = float(row["FullTimeHomeGoals"])
        shots = float(row["AwayShots"])
        shots_allowed = float(row["HomeShots"])
        sot = float(row["AwayShotsOnTarget"])
        sot_allowed = float(row["HomeShotsOnTarget"])
        opponent_elo = float(row["HomeElo"])

    return {
        "points": team_points(row["FullTimeResult"], is_home_team),
        "goals_scored": goals_scored,
        "goals_conceded": goals_conceded,
        "shots": shots,
        "shots_allowed": shots_allowed,
        "sot": sot,
        "sot_allowed": sot_allowed,
        "opp_elo": opponent_elo,
    }


def summarize_history(history: list[dict[str, float]]) -> dict[str, float | None]:
    return {
        "ppg": mean([match["points"] for match in history]),
        "goals_scored": mean([match["goals_scored"] for match in history]),
        "goals_conceded": mean([match["goals_conceded"] for match in history]),
        "shots": mean([match["shots"] for match in history]),
        "shots_allowed": mean([match["shots_allowed"] for match in history]),
        "sot": mean([match["sot"] for match in history]),
        "sot_allowed": mean([match["sot_allowed"] for match in history]),
        "opp_elo": mean([match["opp_elo"] for match in history]),
    }


def diff_or_none(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return left - right


def rest_days_or_none(
    current_date: date, previous_date: date | None, rest_cap: int
) -> int | None:
    if previous_date is None:
        return None
    return min((current_date - previous_date).days, rest_cap)


def trim_history(history: list[dict[str, float]], window_size: int) -> None:
    if len(history) > window_size:
        del history[:-window_size]


def main() -> None:
    args = parse_args()
    team_history: dict[str, list[dict[str, float]]] = {}
    last_match_dates: dict[str, date] = {}

    with args.input.open(newline="", encoding="utf-8-sig") as infile:
        reader = csv.DictReader(infile)
        output_columns = list(reader.fieldnames or []) + FEATURE_COLUMNS

        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", newline="", encoding="utf-8") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=output_columns)
            writer.writeheader()

            for row in reader:
                match_date = parse_match_date(row["MatchDate"])
                home_team = row["HomeTeam"]
                away_team = row["AwayTeam"]

                home_history = team_history.get(home_team, [])
                away_history = team_history.get(away_team, [])
                home_summary = summarize_history(home_history)
                away_summary = summarize_history(away_history)

                home_rest = rest_days_or_none(
                    match_date, last_match_dates.get(home_team), args.rest_cap
                )
                away_rest = rest_days_or_none(
                    match_date, last_match_dates.get(away_team), args.rest_cap
                )

                row["Home_PPG_Last5"] = format_float(home_summary["ppg"])
                row["Away_PPG_Last5"] = format_float(away_summary["ppg"])
                row["Home_GoalsScored_Last5"] = format_float(
                    home_summary["goals_scored"]
                )
                row["Away_GoalsScored_Last5"] = format_float(
                    away_summary["goals_scored"]
                )
                row["Home_GoalsConceded_Last5"] = format_float(
                    home_summary["goals_conceded"]
                )
                row["Away_GoalsConceded_Last5"] = format_float(
                    away_summary["goals_conceded"]
                )
                row["Home_Shots_Last5"] = format_float(home_summary["shots"])
                row["Away_Shots_Last5"] = format_float(away_summary["shots"])
                row["Home_ShotsAllowed_Last5"] = format_float(
                    home_summary["shots_allowed"]
                )
                row["Away_ShotsAllowed_Last5"] = format_float(
                    away_summary["shots_allowed"]
                )
                row["Home_SOT_Last5"] = format_float(home_summary["sot"])
                row["Away_SOT_Last5"] = format_float(away_summary["sot"])
                row["Home_SOTAllowed_Last5"] = format_float(
                    home_summary["sot_allowed"]
                )
                row["Away_SOTAllowed_Last5"] = format_float(
                    away_summary["sot_allowed"]
                )
                row["Home_OppAvgElo_Last5"] = format_float(home_summary["opp_elo"])
                row["Away_OppAvgElo_Last5"] = format_float(away_summary["opp_elo"])
                row["PPG_Last5_Diff"] = format_float(
                    diff_or_none(home_summary["ppg"], away_summary["ppg"])
                )
                row["Goals_Last5_Diff"] = format_float(
                    diff_or_none(
                        home_summary["goals_scored"], away_summary["goals_scored"]
                    )
                )
                row["GoalsConceded_Last5_Diff"] = format_float(
                    diff_or_none(
                        home_summary["goals_conceded"], away_summary["goals_conceded"]
                    )
                )
                row["Shots_Last5_Diff"] = format_float(
                    diff_or_none(home_summary["shots"], away_summary["shots"])
                )
                row["SOT_Last5_Diff"] = format_float(
                    diff_or_none(home_summary["sot"], away_summary["sot"])
                )
                row["ShotDiff_Last5_Diff"] = format_float(
                    diff_or_none(
                        diff_or_none(
                            home_summary["shots"], home_summary["shots_allowed"]
                        ),
                        diff_or_none(
                            away_summary["shots"], away_summary["shots_allowed"]
                        ),
                    )
                )
                row["HomeRestDays"] = format_int(home_rest)
                row["AwayRestDays"] = format_int(away_rest)
                row["RestDiff"] = format_int(
                    None if home_rest is None or away_rest is None else home_rest - away_rest
                )
                writer.writerow(row)

                home_history = team_history.setdefault(home_team, [])
                away_history = team_history.setdefault(away_team, [])
                home_history.append(build_team_match_stats(row, is_home_team=True))
                away_history.append(build_team_match_stats(row, is_home_team=False))
                trim_history(home_history, args.window_size)
                trim_history(away_history, args.window_size)
                last_match_dates[home_team] = match_date
                last_match_dates[away_team] = match_date


if __name__ == "__main__":
    main()

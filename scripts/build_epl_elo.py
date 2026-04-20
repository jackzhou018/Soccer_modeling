#!/usr/bin/env python3

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    default_input = script_dir.parent / "data" / "epl_2020_onward.csv"
    default_output = script_dir.parent / "data" / "epl_elo.csv"

    parser = argparse.ArgumentParser(
        description="Build final EPL Elo ratings from a match-by-match CSV."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=default_input,
        help=f"Source match CSV path. Defaults to {default_input}.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help=f"Destination ratings CSV path. Defaults to {default_output}.",
    )
    parser.add_argument(
        "--initial-rating",
        type=float,
        default=1500.0,
        help="Starting Elo rating for every team.",
    )
    parser.add_argument(
        "--k-factor",
        type=float,
        default=20.0,
        help="K-factor used in the Elo update formula.",
    )
    return parser.parse_args()


def expected_score(team_rating: float, opponent_rating: float) -> float:
    return 1.0 / (1.0 + 10 ** ((opponent_rating - team_rating) / 400.0))


def actual_scores(result: str) -> tuple[float, float]:
    if result == "H":
        return 1.0, 0.0
    if result == "A":
        return 0.0, 1.0
    if result == "D":
        return 0.5, 0.5
    raise ValueError(f"Unsupported FullTimeResult value: {result!r}")


def main() -> None:
    args = parse_args()
    ratings: dict[str, float] = {}

    with args.input.open(newline="", encoding="utf-8-sig") as infile:
        reader = csv.DictReader(infile)

        for row in reader:
            home_team = row["HomeTeam"]
            away_team = row["AwayTeam"]
            home_rating = ratings.setdefault(home_team, args.initial_rating)
            away_rating = ratings.setdefault(away_team, args.initial_rating)

            home_expected = expected_score(home_rating, away_rating)
            away_expected = expected_score(away_rating, home_rating)
            home_actual, away_actual = actual_scores(row["FullTimeResult"])

            ratings[home_team] = home_rating + args.k_factor * (
                home_actual - home_expected
            )
            ratings[away_team] = away_rating + args.k_factor * (
                away_actual - away_expected
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    ordered_ratings = sorted(ratings.items(), key=lambda item: (-item[1], item[0]))

    with args.output.open("w", newline="", encoding="utf-8") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(["Team", "Elo"])
        for team, rating in ordered_ratings:
            writer.writerow([team, f"{rating:.2f}"])


if __name__ == "__main__":
    main()

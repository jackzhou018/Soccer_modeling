#!/usr/bin/env python3

import argparse
import csv
from pathlib import Path

from build_epl_elo import actual_scores, expected_score


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    default_input = script_dir.parent / "data" / "epl_2020_onward.csv"
    default_output = script_dir.parent / "data" / "epl_2020_onward_with_elo.csv"

    parser = argparse.ArgumentParser(
        description="Append pre-match Elo ratings to each EPL match row."
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
        help=f"Destination annotated CSV path. Defaults to {default_output}.",
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


def main() -> None:
    args = parse_args()
    ratings: dict[str, float] = {}

    with args.input.open(newline="", encoding="utf-8-sig") as infile:
        reader = csv.DictReader(infile)
        output_columns = list(reader.fieldnames or []) + [
            "HomeElo",
            "AwayElo",
            "EloDiff",
        ]

        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", newline="", encoding="utf-8") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=output_columns)
            writer.writeheader()

            for row in reader:
                home_team = row["HomeTeam"]
                away_team = row["AwayTeam"]
                home_rating = ratings.setdefault(home_team, args.initial_rating)
                away_rating = ratings.setdefault(away_team, args.initial_rating)

                row["HomeElo"] = f"{home_rating:.2f}"
                row["AwayElo"] = f"{away_rating:.2f}"
                row["EloDiff"] = f"{home_rating - away_rating:.2f}"
                writer.writerow(row)

                home_expected = expected_score(home_rating, away_rating)
                away_expected = expected_score(away_rating, home_rating)
                home_actual, away_actual = actual_scores(row["FullTimeResult"])

                ratings[home_team] = home_rating + args.k_factor * (
                    home_actual - home_expected
                )
                ratings[away_team] = away_rating + args.k_factor * (
                    away_actual - away_expected
                )


if __name__ == "__main__":
    main()

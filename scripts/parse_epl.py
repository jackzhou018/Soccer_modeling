#!/usr/bin/env python3

import argparse
import csv
from pathlib import Path


OUTPUT_COLUMNS = [
    "Season",
    "MatchDate",
    "HomeTeam",
    "AwayTeam",
    "FullTimeHomeGoals",
    "FullTimeAwayGoals",
    "FullTimeResult",
    "HomeShots",
    "AwayShots",
    "HomeShotsOnTarget",
    "AwayShotsOnTarget",
]


def season_start_year(season: str) -> int:
    return int(season.split("/", 1)[0])


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    default_input = script_dir.parent / "data" / "archive" / "epl_final.csv"
    default_output = script_dir.parent / "data" / "epl_2020_onward.csv"

    parser = argparse.ArgumentParser(
        description="Filter EPL results from the 2020/21 season onward."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=default_input,
        help=f"Source CSV path. Defaults to {default_input}.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help=f"Destination CSV path. Defaults to {default_output}.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with args.input.open(newline="", encoding="utf-8-sig") as infile:
        reader = csv.DictReader(infile)
        with args.output.open("w", newline="", encoding="utf-8") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=OUTPUT_COLUMNS)
            writer.writeheader()

            for row in reader:
                if season_start_year(row["Season"]) < 2020:
                    continue

                writer.writerow({column: row[column] for column in OUTPUT_COLUMNS})


if __name__ == "__main__":
    main()

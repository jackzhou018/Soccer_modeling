#!/usr/bin/env python3

import argparse
import csv
import io
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


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

SOURCE_TO_OUTPUT_COLUMNS = {
    "HomeTeam": "HomeTeam",
    "AwayTeam": "AwayTeam",
    "FTHG": "FullTimeHomeGoals",
    "FTAG": "FullTimeAwayGoals",
    "FTR": "FullTimeResult",
    "HS": "HomeShots",
    "AS": "AwayShots",
    "HST": "HomeShotsOnTarget",
    "AST": "AwayShotsOnTarget",
}

REQUIRED_SOURCE_COLUMNS = ["Date", *SOURCE_TO_OUTPUT_COLUMNS]


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    default_end_year = 2026
    default_output = (
        script_dir.parent / "data" / f"epl_{default_end_year - 1}_{default_end_year}.csv"
    )

    parser = argparse.ArgumentParser(
        description=(
            "Download and normalize football-data.co.uk Premier League results "
            "into the local EPL CSV schema."
        )
    )
    parser.add_argument(
        "--season-end-year",
        type=int,
        default=default_end_year,
        help="Calendar year the season ends in. Defaults to 2026 for the 2025/26 season.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help=f"Destination CSV path. Defaults to {default_output}.",
    )
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="Optional override for the football-data.co.uk CSV URL.",
    )
    return parser.parse_args()


def season_label(end_year: int) -> str:
    return f"{end_year - 1}/{end_year % 100:02d}"


def season_code(end_year: int) -> str:
    start_suffix = (end_year - 1) % 100
    end_suffix = end_year % 100
    return f"{start_suffix:02d}{end_suffix:02d}"


def default_url(end_year: int) -> str:
    return f"https://www.football-data.co.uk/mmz4281/{season_code(end_year)}/E0.csv"


def download_csv_text(url: str) -> str:
    try:
        with urlopen(url) as response:
            return response.read().decode("utf-8-sig")
    except HTTPError as exc:
        raise SystemExit(f"Failed to download {url}: HTTP {exc.code}") from exc
    except URLError as exc:
        raise SystemExit(f"Failed to download {url}: {exc.reason}") from exc


def parse_match_date(value: str) -> str:
    stripped = value.strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(stripped, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"Unsupported date format: {value!r}")


def validate_columns(fieldnames: list[str] | None) -> None:
    available = set(fieldnames or [])
    missing = [column for column in REQUIRED_SOURCE_COLUMNS if column not in available]
    if missing:
        raise SystemExit(f"Source CSV is missing required columns: {', '.join(missing)}")


def is_completed_match(row: dict[str, str]) -> bool:
    required_values = [row[column].strip() for column in REQUIRED_SOURCE_COLUMNS]
    return all(required_values) and row["FTR"].strip() in {"H", "D", "A"}


def normalize_rows(csv_text: str, season: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(csv_text))
    validate_columns(reader.fieldnames)

    normalized_rows: list[dict[str, str]] = []
    for row in reader:
        if not is_completed_match(row):
            continue

        normalized_row = {column: "" for column in OUTPUT_COLUMNS}
        normalized_row["Season"] = season
        normalized_row["MatchDate"] = parse_match_date(row["Date"])

        for source_column, output_column in SOURCE_TO_OUTPUT_COLUMNS.items():
            normalized_row[output_column] = row[source_column].strip()

        normalized_rows.append(normalized_row)

    normalized_rows.sort(
        key=lambda row: (
            row["MatchDate"],
            row["HomeTeam"],
            row["AwayTeam"],
        )
    )
    return normalized_rows


def write_rows(output_path: Path, rows: list[dict[str, str]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    season = season_label(args.season_end_year)
    url = args.url or default_url(args.season_end_year)

    csv_text = download_csv_text(url)
    rows = normalize_rows(csv_text, season)
    write_rows(args.output, rows)

    print(f"Downloaded season: {season}")
    print(f"Source URL: {url}")
    print(f"Completed matches written: {len(rows)}")
    print(f"Output file: {args.output}")


if __name__ == "__main__":
    main()

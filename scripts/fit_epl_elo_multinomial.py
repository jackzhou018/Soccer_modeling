#!/usr/bin/env python3

import argparse
import csv
import math
from pathlib import Path


RESULTS = ["H", "D", "A"]
MODELLED_RESULTS = ["H", "D"]
RESULT_LABELS = {"H": "Home Win", "D": "Draw", "A": "Away Win"}
RESULT_COLORS = {"H": "#1f9d55", "D": "#d97706", "A": "#2563eb"}


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    default_input = script_dir.parent / "data" / "epl_2020_onward_with_elo.csv"
    default_graph = script_dir.parent / "data" / "elo_diff_multinomial.svg"
    default_table = script_dir.parent / "data" / "elo_diff_multinomial_table.csv"

    parser = argparse.ArgumentParser(
        description="Fit multinomial logistic regression on EloDiff vs FullTimeResult."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=default_input,
        help=f"Annotated match CSV path. Defaults to {default_input}.",
    )
    parser.add_argument(
        "--graph-output",
        type=Path,
        default=default_graph,
        help=f"SVG probability chart path. Defaults to {default_graph}.",
    )
    parser.add_argument(
        "--table-output",
        type=Path,
        default=default_table,
        help=f"CSV summary table path. Defaults to {default_table}.",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=6000,
        help="Number of gradient descent iterations.",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=0.1,
        help="Gradient descent learning rate.",
    )
    parser.add_argument(
        "--l2",
        type=float,
        default=0.001,
        help="L2 regularization strength.",
    )
    return parser.parse_args()


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def stddev(values: list[float], value_mean: float) -> float:
    variance = sum((value - value_mean) ** 2 for value in values) / len(values)
    return math.sqrt(variance) or 1.0


def softmax_probabilities(
    x_scaled: float, params: dict[str, list[float]]
) -> dict[str, float]:
    logits = {
        "H": params["H"][0] + params["H"][1] * x_scaled,
        "D": params["D"][0] + params["D"][1] * x_scaled,
        "A": 0.0,
    }
    max_logit = max(logits.values())
    exp_logits = {
        result: math.exp(logit - max_logit) for result, logit in logits.items()
    }
    denominator = sum(exp_logits.values())
    return {
        result: exp_logit / denominator for result, exp_logit in exp_logits.items()
    }


def fit_model(
    x_values: list[float],
    y_values: list[str],
    iterations: int,
    learning_rate: float,
    l2: float,
) -> tuple[dict[str, list[float]], float, float]:
    x_mean = mean(x_values)
    x_std = stddev(x_values, x_mean)
    x_scaled_values = [(x - x_mean) / x_std for x in x_values]
    params = {result: [0.0, 0.0] for result in MODELLED_RESULTS}
    sample_count = len(x_scaled_values)

    for _ in range(iterations):
        gradients = {result: [0.0, 0.0] for result in MODELLED_RESULTS}

        for x_scaled, actual_result in zip(x_scaled_values, y_values):
            probabilities = softmax_probabilities(x_scaled, params)
            for result in MODELLED_RESULTS:
                error = probabilities[result] - float(actual_result == result)
                gradients[result][0] += error
                gradients[result][1] += error * x_scaled

        for result in MODELLED_RESULTS:
            for index in range(2):
                gradient = gradients[result][index] / sample_count
                gradient += l2 * params[result][index]
                params[result][index] -= learning_rate * gradient

    return params, x_mean, x_std


def predict_probabilities(
    elo_diff: float, params: dict[str, list[float]], x_mean: float, x_std: float
) -> dict[str, float]:
    x_scaled = (elo_diff - x_mean) / x_std
    return softmax_probabilities(x_scaled, params)


def rounded_bounds(values: list[float], step: int = 50) -> tuple[int, int]:
    lower = step * math.floor(min(values) / step)
    upper = step * math.ceil(max(values) / step)
    if lower == upper:
        upper = lower + step
    return lower, upper


def build_table_rows(
    x_values: list[float], params: dict[str, list[float]], x_mean: float, x_std: float
) -> list[dict[str, str]]:
    lower, upper = rounded_bounds(x_values)
    max_abs = max(abs(lower), abs(upper), 200)
    diffs = list(range(-max_abs, max_abs + 1, 50))

    rows = []
    for diff in diffs:
        probabilities = predict_probabilities(diff, params, x_mean, x_std)
        most_likely = max(RESULTS, key=lambda result: probabilities[result])
        rows.append(
            {
                "EloDiff": str(diff),
                "HomeWinProb": f"{probabilities['H']:.3f}",
                "DrawProb": f"{probabilities['D']:.3f}",
                "AwayWinProb": f"{probabilities['A']:.3f}",
                "MostLikelyResult": RESULT_LABELS[most_likely],
            }
        )
    return rows


def write_table(table_output: Path, rows: list[dict[str, str]]) -> None:
    table_output.parent.mkdir(parents=True, exist_ok=True)
    with table_output.open("w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(
            outfile,
            fieldnames=[
                "EloDiff",
                "HomeWinProb",
                "DrawProb",
                "AwayWinProb",
                "MostLikelyResult",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def render_probability_chart(
    graph_output: Path,
    x_values: list[float],
    params: dict[str, list[float]],
    x_mean: float,
    x_std: float,
) -> None:
    width = 920
    height = 560
    margin_left = 80
    margin_right = 30
    margin_top = 50
    margin_bottom = 70
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom

    lower, upper = rounded_bounds(x_values)
    points = []
    step_count = 300
    for index in range(step_count + 1):
        elo_diff = lower + (upper - lower) * index / step_count
        probabilities = predict_probabilities(elo_diff, params, x_mean, x_std)
        points.append((elo_diff, probabilities))

    def x_to_svg(x_value: float) -> float:
        return margin_left + ((x_value - lower) / (upper - lower)) * plot_width

    def y_to_svg(y_value: float) -> float:
        return margin_top + (1.0 - y_value) * plot_height

    lines = []
    lines.append(
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="white" />'
    )

    for tick in range(0, 11):
        probability = tick / 10
        y = y_to_svg(probability)
        lines.append(
            f'<line x1="{margin_left}" y1="{y:.2f}" x2="{width - margin_right}" y2="{y:.2f}" '
            'stroke="#e5e7eb" stroke-width="1" />'
        )
        lines.append(
            f'<text x="{margin_left - 12}" y="{y + 4:.2f}" text-anchor="end" '
            'font-size="12" fill="#374151">'
            f"{probability:.1f}</text>"
        )

    tick_step = 50
    for tick_value in range(lower, upper + 1, tick_step):
        x = x_to_svg(tick_value)
        lines.append(
            f'<line x1="{x:.2f}" y1="{margin_top}" x2="{x:.2f}" y2="{height - margin_bottom}" '
            'stroke="#f3f4f6" stroke-width="1" />'
        )
        lines.append(
            f'<text x="{x:.2f}" y="{height - margin_bottom + 24}" text-anchor="middle" '
            'font-size="12" fill="#374151">'
            f"{tick_value}</text>"
        )

    lines.append(
        f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{height - margin_bottom}" '
        'stroke="#111827" stroke-width="1.5" />'
    )
    lines.append(
        f'<line x1="{margin_left}" y1="{height - margin_bottom}" x2="{width - margin_right}" y2="{height - margin_bottom}" '
        'stroke="#111827" stroke-width="1.5" />'
    )

    for result in RESULTS:
        path_points = " ".join(
            f"{x_to_svg(elo_diff):.2f},{y_to_svg(probabilities[result]):.2f}"
            for elo_diff, probabilities in points
        )
        lines.append(
            f'<polyline fill="none" stroke="{RESULT_COLORS[result]}" stroke-width="3" '
            f'points="{path_points}" />'
        )

    title_x = width / 2
    lines.append(
        f'<text x="{title_x:.2f}" y="26" text-anchor="middle" font-size="22" '
        'font-family="Arial, sans-serif" fill="#111827">'
        "Match Outcome Probabilities From EloDiff</text>"
    )
    lines.append(
        f'<text x="{title_x:.2f}" y="{height - 18}" text-anchor="middle" font-size="14" '
        'font-family="Arial, sans-serif" fill="#111827">'
        "EloDiff (HomeElo - AwayElo)</text>"
    )
    lines.append(
        f'<text x="20" y="{height / 2:.2f}" text-anchor="middle" font-size="14" '
        'font-family="Arial, sans-serif" fill="#111827" '
        f'transform="rotate(-90 20 {height / 2:.2f})">'
        "Predicted Probability</text>"
    )

    legend_x = width - 200
    legend_y = 54
    for index, result in enumerate(RESULTS):
        y = legend_y + index * 24
        lines.append(
            f'<line x1="{legend_x}" y1="{y}" x2="{legend_x + 24}" y2="{y}" '
            f'stroke="{RESULT_COLORS[result]}" stroke-width="3" />'
        )
        lines.append(
            f'<text x="{legend_x + 34}" y="{y + 4}" font-size="13" fill="#111827">'
            f"{RESULT_LABELS[result]}</text>"
        )

    graph_output.parent.mkdir(parents=True, exist_ok=True)
    svg = "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            *lines,
            "</svg>",
        ]
    )
    graph_output.write_text(svg, encoding="utf-8")


def load_training_data(input_path: Path) -> tuple[list[float], list[str]]:
    x_values: list[float] = []
    y_values: list[str] = []

    with input_path.open(newline="", encoding="utf-8-sig") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            x_values.append(float(row["EloDiff"]))
            y_values.append(row["FullTimeResult"])

    if not x_values:
        raise ValueError("Input CSV does not contain any match rows.")

    return x_values, y_values


def print_table(rows: list[dict[str, str]]) -> None:
    headers = [
        ("EloDiff", "EloDiff"),
        ("Home Win", "HomeWinProb"),
        ("Draw", "DrawProb"),
        ("Away Win", "AwayWinProb"),
        ("Most Likely", "MostLikelyResult"),
    ]
    widths = []
    for label, key in headers:
        content_width = max(len(label), max(len(row[key]) for row in rows))
        widths.append(content_width)

    header_line = "  ".join(
        label.ljust(width) for (label, _), width in zip(headers, widths)
    )
    divider = "  ".join("-" * width for width in widths)
    print(header_line)
    print(divider)
    for row in rows:
        print(
            "  ".join(
                row[key].ljust(width) for (_, key), width in zip(headers, widths)
            )
        )


def main() -> None:
    args = parse_args()
    x_values, y_values = load_training_data(args.input)
    params, x_mean, x_std = fit_model(
        x_values,
        y_values,
        iterations=args.iterations,
        learning_rate=args.learning_rate,
        l2=args.l2,
    )

    table_rows = build_table_rows(x_values, params, x_mean, x_std)
    write_table(args.table_output, table_rows)
    render_probability_chart(args.graph_output, x_values, params, x_mean, x_std)
    print_table(table_rows)
    print()
    print(f"Graph written to: {args.graph_output}")
    print(f"Table written to: {args.table_output}")


if __name__ == "__main__":
    main()

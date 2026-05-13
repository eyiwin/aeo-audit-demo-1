"""Compare the two latest file-based monitoring runs."""

from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def find_latest_run_dirs(runs_root: Path) -> list[Path]:
    """Return the two latest run folders by folder name."""
    if not runs_root.exists():
        return []
    run_dirs = [path for path in runs_root.iterdir() if path.is_dir()]
    return sorted(run_dirs, key=lambda path: path.name)[-2:]


def load_findings(run_dir: Path) -> list[dict]:
    findings_path = run_dir / "page_findings.json"
    if not findings_path.exists():
        raise FileNotFoundError(f"Missing page_findings.json in {run_dir}")
    data = json.loads(findings_path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return [data]
    return data


def compare_runs(output_dir: Path) -> Path:
    """Compare latest two runs and write monitoring_comparison.md."""
    latest_runs = find_latest_run_dirs(output_dir / "runs")
    comparison_path = output_dir / "monitoring_comparison.md"
    if len(latest_runs) < 2:
        comparison_path.write_text(
            "# Monitoring Run Comparison\n\nAt least two run folders are needed before comparison is available.\n",
            encoding="utf-8",
        )
        return comparison_path

    previous_dir, current_dir = latest_runs
    previous = {item["url"]: item for item in load_findings(previous_dir)}
    current = {item["url"]: item for item in load_findings(current_dir)}

    improved = []
    declined = []
    unchanged_weaknesses = []
    for url, current_page in current.items():
        previous_page = previous.get(url)
        if not previous_page:
            continue
        delta = round(current_page["overall_score"] - previous_page["overall_score"], 2)
        label = current_page["page_title"] or url
        if delta > 0:
            improved.append((label, delta, previous_page["overall_score"], current_page["overall_score"]))
        elif delta < 0:
            declined.append((label, delta, previous_page["overall_score"], current_page["overall_score"]))

        previous_weak = set(previous_page.get("top_weaknesses", []))
        current_weak = set(current_page.get("top_weaknesses", []))
        for weakness in sorted(previous_weak.intersection(current_weak)):
            unchanged_weaknesses.append((label, weakness))

    lines = [
        "# Monitoring Run Comparison",
        "",
        f"Previous run: {previous_dir.name}",
        f"Current run: {current_dir.name}",
        "",
        "## Improved Pages",
        "",
    ]
    lines.extend(_page_delta_lines(improved, "No improved pages detected."))
    lines.extend(["", "## Declined Pages", ""])
    lines.extend(_page_delta_lines(declined, "No declined pages detected."))
    lines.extend(["", "## Unchanged Weaknesses", ""])
    if unchanged_weaknesses:
        lines.extend([f"- {label}: {weakness}" for label, weakness in unchanged_weaknesses])
    else:
        lines.append("- No unchanged weaknesses detected.")
    lines.append("")

    comparison_path.write_text("\n".join(lines), encoding="utf-8")
    return comparison_path


def _page_delta_lines(items: list[tuple[str, float, float, float]], fallback: str) -> list[str]:
    if not items:
        return [f"- {fallback}"]
    return [f"- {label}: {previous_score}/100 -> {current_score}/100 ({delta:+})" for label, delta, previous_score, current_score in items]


def main() -> None:
    comparison_path = compare_runs(PROJECT_ROOT / "outputs")
    print(f"Generated comparison: {comparison_path}")


if __name__ == "__main__":
    main()

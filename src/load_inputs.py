"""Load and validate JSON and CSV inputs for the audit."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


CLIENT_BRIEF_FIELDS = [
    "client_name",
    "brand_name",
    "website_url",
    "target_market",
    "target_audience",
    "business_goal",
    "primary_conversion",
    "main_service",
    "primary_topic",
    "secondary_topics",
    "competitors",
    "notes",
]

URL_COLUMNS = ["url", "page_type", "target_topic", "priority"]
QUESTION_COLUMNS = ["question", "intent_type", "priority", "expected_page_type", "target_topic"]
ENTITY_COLUMNS = ["entity", "entity_type", "priority", "related_topic"]
RUBRIC_DIMENSION_FIELDS = [
    "id",
    "name",
    "weight",
    "description",
    "what_good_looks_like",
    "what_bad_looks_like",
    "scoring_guidance",
    "evidence_to_collect",
    "recommended_fix_logic",
]


def _require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Required input file not found: {path}")
    if not path.is_file():
        raise ValueError(f"Expected a file but found something else: {path}")


def _load_json(path: Path) -> dict[str, Any]:
    _require_file(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {path}: {error}") from error
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}.")
    return data


def _missing_fields(data: dict[str, Any], required_fields: list[str]) -> list[str]:
    return [field for field in required_fields if field not in data]


def _clean_row(row: dict[str, str | None]) -> dict[str, str]:
    return {key: (value or "").strip() for key, value in row.items() if key is not None}


def _load_csv(path: Path, required_columns: list[str]) -> list[dict[str, str]]:
    _require_file(path)
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise ValueError(f"CSV file has no header row: {path}")

        missing = [column for column in required_columns if column not in reader.fieldnames]
        if missing:
            raise ValueError(f"Missing required columns in {path}: {', '.join(missing)}")

        rows = [_clean_row(row) for row in reader]

    rows = [row for row in rows if any(row.values()) and not row.get(required_columns[0], "").startswith("#")]
    return rows


def load_client_brief(path: Path) -> dict[str, Any]:
    """Load client context from client_brief.json."""
    data = _load_json(path)
    missing = _missing_fields(data, CLIENT_BRIEF_FIELDS)
    if missing:
        raise ValueError(f"Missing required fields in {path}: {', '.join(missing)}")
    return data


def load_urls(path: Path) -> list[dict[str, str]]:
    """Load URL/page context rows from urls.csv."""
    rows = _load_csv(path, URL_COLUMNS)
    if not rows:
        raise ValueError(f"No URL rows found in {path}.")
    return rows


def load_target_questions(path: Path) -> list[dict[str, str]]:
    """Load target questions from target_questions.csv."""
    rows = _load_csv(path, QUESTION_COLUMNS)
    if not rows:
        raise ValueError(f"No target question rows found in {path}.")
    return rows


def load_required_entities(path: Path) -> list[dict[str, str]]:
    """Load required entity rows from required_entities.csv."""
    rows = _load_csv(path, ENTITY_COLUMNS)
    if not rows:
        raise ValueError(f"No required entity rows found in {path}.")
    return rows


def load_scoring_rubric(path: Path) -> dict[str, Any]:
    """Load and validate the AEO scoring rubric JSON."""
    data = _load_json(path)
    missing = _missing_fields(data, ["rubric_name", "total_points", "dimensions"])
    if missing:
        raise ValueError(f"Missing required fields in {path}: {', '.join(missing)}")

    dimensions = data["dimensions"]
    if not isinstance(dimensions, list) or not dimensions:
        raise ValueError(f"Rubric must include a non-empty dimensions list: {path}")

    total_weight = 0
    for index, dimension in enumerate(dimensions, start=1):
        if not isinstance(dimension, dict):
            raise ValueError(f"Rubric dimension {index} must be an object in {path}.")
        missing_dimension_fields = _missing_fields(dimension, RUBRIC_DIMENSION_FIELDS)
        if missing_dimension_fields:
            raise ValueError(
                f"Missing fields in rubric dimension {index} ({path}): {', '.join(missing_dimension_fields)}"
            )
        total_weight += int(dimension["weight"])

    if total_weight != int(data["total_points"]):
        raise ValueError(
            f"Rubric weights total {total_weight}, but total_points is {data['total_points']} in {path}."
        )

    return data

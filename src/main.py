"""Entry point for the local AEO Retrieval Readiness Audit MVP."""

from __future__ import annotations

from pathlib import Path

from audit_engine import audit_page
from export_results import export_audit_results
from load_inputs import (
    load_client_brief,
    load_required_entities,
    load_scoring_rubric,
    load_target_questions,
    load_urls,
)
from scrape_page import scrape_page


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _resolve_url(url: str) -> str:
    """Allow the first test page to be a local file path."""
    local_path = PROJECT_ROOT / url
    if local_path.exists():
        return str(local_path)
    return url


def main() -> None:
    """Run the full one-page AEO audit."""
    client_brief = load_client_brief(PROJECT_ROOT / "inputs" / "client_brief.json")
    urls = load_urls(PROJECT_ROOT / "inputs" / "urls.csv")
    target_questions = load_target_questions(PROJECT_ROOT / "inputs" / "target_questions.csv")
    required_entities = load_required_entities(PROJECT_ROOT / "inputs" / "required_entities.csv")
    scoring_rubric = load_scoring_rubric(PROJECT_ROOT / "config" / "aeo_scoring_rubric.json")

    page_context = urls[0]
    scrape_target = _resolve_url(page_context["url"])

    print("AEO Retrieval Readiness Audit MVP")
    print(f"Client name: {client_brief['client_name']}")
    print(f"Brand name: {client_brief['brand_name']}")
    print(f"Auditing first URL: {page_context['url']}")

    page = scrape_page(scrape_target)
    audit_result = audit_page(
        scraped_page=page,
        client_brief=client_brief,
        page_context=page_context,
        target_questions=target_questions,
        required_entities=required_entities,
        scoring_rubric=scoring_rubric,
    )
    output_paths = export_audit_results(
        audit_result=audit_result,
        client_brief=client_brief,
        page_context=page_context,
        target_questions=target_questions,
        required_entities=required_entities,
        scraped_page=page,
        output_dir=PROJECT_ROOT / "outputs",
        prompt_template_path=PROJECT_ROOT / "prompts" / "llm_review_prompt_template.md",
    )

    print(f"Overall score: {audit_result['overall_score']}/100")
    print(f"Grade: {audit_result['grade']}")
    print("Dimension scores:")
    for dimension in audit_result["dimension_results"]:
        print(
            f"- {dimension['dimension_name']}: "
            f"{dimension['score_raw']}/10 "
            f"({dimension['weighted_score']}/{dimension['weight']} weighted)"
        )

    print("")
    print("Generated files:")
    for path in output_paths.values():
        print(f"- {path}")


if __name__ == "__main__":
    main()

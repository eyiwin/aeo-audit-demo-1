"""Entry point for the local AEO Retrieval Readiness Audit MVP."""

from __future__ import annotations

from pathlib import Path

from audit_engine import audit_page
from export_results import export_site_audit_results
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
    """Allow test pages to be repo-relative local file paths."""
    local_path = PROJECT_ROOT / url
    if local_path.exists():
        return str(local_path)
    return url


def main() -> None:
    """Run the full multi-page AEO audit."""
    client_brief = load_client_brief(PROJECT_ROOT / "inputs" / "client_brief.json")
    urls = load_urls(PROJECT_ROOT / "inputs" / "urls.csv")
    target_questions = load_target_questions(PROJECT_ROOT / "inputs" / "target_questions.csv")
    required_entities = load_required_entities(PROJECT_ROOT / "inputs" / "required_entities.csv")
    scoring_rubric = load_scoring_rubric(PROJECT_ROOT / "config" / "aeo_scoring_rubric.json")

    print("AEO Retrieval Readiness Audit MVP")
    print(f"Client name: {client_brief['client_name']}")
    print(f"Brand name: {client_brief['brand_name']}")
    print(f"Pages to audit: {len(urls)}")
    print("")

    audit_results = []
    audited_contexts = []
    for index, page_context in enumerate(urls, start=1):
        print(f"[{index}/{len(urls)}] Auditing: {page_context['url']}")
        scrape_target = _resolve_url(page_context["url"])
        try:
            page = scrape_page(scrape_target)
        except RuntimeError as error:
            print(f"  Skipped: {error}")
            continue

        page["url"] = page_context["url"]
        audit_result = audit_page(
            scraped_page=page,
            client_brief=client_brief,
            page_context=page_context,
            target_questions=target_questions,
            required_entities=required_entities,
            scoring_rubric=scoring_rubric,
        )
        audit_results.append(audit_result)
        audited_contexts.append(page_context)
        print(f"  Score: {audit_result['overall_score']}/100 ({audit_result['grade']})")

    if not audit_results:
        raise RuntimeError("No pages were successfully audited.")

    output_paths = export_site_audit_results(
        audit_results=audit_results,
        client_brief=client_brief,
        page_contexts=audited_contexts,
        output_dir=PROJECT_ROOT / "outputs",
    )

    average_score = round(sum(result["overall_score"] for result in audit_results) / len(audit_results), 2)
    print("")
    print(f"Audited pages: {len(audit_results)}")
    print(f"Average score: {average_score}/100")
    print("")
    print("Generated files:")
    for path in output_paths["page_reports"]:
        print(f"- {path}")
    print(f"- {output_paths['site_summary']}")
    print(f"- {output_paths['all_scores']}")
    print(f"- {output_paths['all_findings']}")
    print(f"- {output_paths['run_dir']}")


if __name__ == "__main__":
    main()

"""Export audit results to Markdown, CSV, JSON, and review prompts."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import re
import shutil
from datetime import date

from generate_report import generate_markdown_report


def export_audit_results(
    audit_result: dict,
    client_brief: dict,
    page_context: dict,
    target_questions: list[dict],
    required_entities: list[dict],
    scraped_page: dict,
    output_dir: Path,
    prompt_template_path: Path,
) -> dict[str, Path]:
    """Write the one-page audit outputs and return their paths."""
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / "audit_report.md"
    scores_path = output_dir / "audit_scores.csv"
    findings_path = output_dir / "page_findings.json"
    prompt_path = output_dir / "llm_review_prompt.md"

    report_path.write_text(generate_markdown_report(audit_result, client_brief, page_context), encoding="utf-8")
    _write_scores_csv(audit_result, scores_path)
    findings_path.write_text(json.dumps(audit_result, indent=2), encoding="utf-8")
    prompt_path.write_text(
        generate_llm_review_prompt(
            template_path=prompt_template_path,
            audit_result=audit_result,
            client_brief=client_brief,
            page_context=page_context,
            target_questions=target_questions,
            required_entities=required_entities,
            scraped_page=scraped_page,
        ),
        encoding="utf-8",
    )

    return {
        "audit_report": report_path,
        "audit_scores": scores_path,
        "page_findings": findings_path,
        "llm_review_prompt": prompt_path,
    }


def _write_scores_csv(audit_result: dict, output_path: Path) -> None:
    fieldnames = [
        "url",
        "page_title",
        "overall_score",
        "grade",
        "dimension_id",
        "dimension_name",
        "weight",
        "score_raw",
        "weighted_score",
        "why_this_score",
        "what_would_improve_the_score",
        "confidence_level",
        "evidence_found",
        "evidence_missing",
        "aeo_impact",
        "recommended_fix",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for dimension in audit_result["dimension_results"]:
            writer.writerow(
                {
                    "url": audit_result["url"],
                    "page_title": audit_result["page_title"],
                    "overall_score": audit_result["overall_score"],
                    "grade": audit_result["grade"],
                    "dimension_id": dimension["dimension_id"],
                    "dimension_name": dimension["dimension_name"],
                    "weight": dimension["weight"],
                    "score_raw": dimension["score_raw"],
                    "weighted_score": dimension["weighted_score"],
                    "why_this_score": dimension["why_this_score"],
                    "what_would_improve_the_score": dimension["what_would_improve_the_score"],
                    "confidence_level": dimension["confidence_level"],
                    "evidence_found": " | ".join(dimension["evidence_found"]),
                    "evidence_missing": " | ".join(dimension["evidence_missing"]),
                    "aeo_impact": dimension["aeo_impact"],
                    "recommended_fix": dimension["recommended_fix"],
                }
            )


def export_site_audit_results(
    audit_results: list[dict],
    client_brief: dict,
    page_contexts: list[dict],
    output_dir: Path,
) -> dict[str, Path | list[Path]]:
    """Write multi-page audit outputs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    page_audits_dir = output_dir / "page_audits"
    page_audits_dir.mkdir(parents=True, exist_ok=True)

    page_report_paths = []
    for index, audit_result in enumerate(audit_results, start=1):
        page_context = page_contexts[index - 1]
        report_path = page_audits_dir / f"{index:02d}-{_slugify(page_context['page_type'])}-{_slugify(page_context['target_topic'])}.md"
        report_path.write_text(generate_markdown_report(audit_result, client_brief, page_context), encoding="utf-8")
        page_report_paths.append(report_path)

    site_summary_path = output_dir / "site_summary.md"
    all_scores_path = output_dir / "all_scores.csv"
    all_findings_path = output_dir / "all_findings.json"

    site_summary_path.write_text(generate_site_summary(audit_results, client_brief), encoding="utf-8")
    _write_all_scores_csv(audit_results, all_scores_path)
    all_findings_path.write_text(json.dumps(audit_results, indent=2), encoding="utf-8")
    run_dir = archive_site_run(
        output_dir=output_dir,
        page_report_paths=page_report_paths,
        site_summary_path=site_summary_path,
        all_scores_path=all_scores_path,
        all_findings_path=all_findings_path,
    )

    return {
        "page_reports": page_report_paths,
        "site_summary": site_summary_path,
        "all_scores": all_scores_path,
        "all_findings": all_findings_path,
        "run_dir": run_dir,
    }


def archive_site_run(
    output_dir: Path,
    page_report_paths: list[Path],
    site_summary_path: Path,
    all_scores_path: Path,
    all_findings_path: Path,
) -> Path:
    """Copy latest multi-page outputs into a dated run-history folder."""
    run_dir = _next_run_dir(output_dir / "runs", date.today().isoformat())
    page_audits_dir = run_dir / "page_audits"
    page_audits_dir.mkdir(parents=True, exist_ok=True)

    if page_report_paths:
        shutil.copy2(page_report_paths[0], run_dir / "audit_report.md")
    shutil.copy2(all_scores_path, run_dir / "audit_scores.csv")
    shutil.copy2(all_findings_path, run_dir / "page_findings.json")
    shutil.copy2(site_summary_path, run_dir / "site_summary.md")

    prompt_path = output_dir / "llm_review_prompt.md"
    if prompt_path.exists():
        shutil.copy2(prompt_path, run_dir / "llm_review_prompt.md")
    else:
        (run_dir / "llm_review_prompt.md").write_text(
            "# LLM Review Prompt\n\nNo single-page LLM review prompt was generated for this multi-page run.\n",
            encoding="utf-8",
        )

    for path in page_report_paths:
        shutil.copy2(path, page_audits_dir / path.name)

    return run_dir


def _next_run_dir(runs_root: Path, date_label: str) -> Path:
    runs_root.mkdir(parents=True, exist_ok=True)
    candidate = runs_root / date_label
    if not candidate.exists():
        candidate.mkdir()
        return candidate

    index = 2
    while True:
        candidate = runs_root / f"{date_label}-{index:02d}"
        if not candidate.exists():
            candidate.mkdir()
            return candidate
        index += 1


def generate_site_summary(audit_results: list[dict], client_brief: dict) -> str:
    """Return a simple site-level Markdown summary."""
    average_score = round(sum(result["overall_score"] for result in audit_results) / max(len(audit_results), 1), 2)
    sorted_pages = sorted(audit_results, key=lambda result: result["overall_score"], reverse=True)
    missing_questions = _repeated_missing_items(audit_results, "query_answer_coverage")
    missing_entities = _repeated_missing_items(audit_results, "entity_clarity")
    faq_opportunities = _dimension_gaps(audit_results, "faq_readiness")
    schema_opportunities = _dimension_gaps(audit_results, "schema_readiness")
    recommendations = _site_recommendations(audit_results)

    lines = [
        "# Site-Level AEO Retrieval Readiness Summary",
        "",
        f"Client: {client_brief['client_name']}",
        f"Brand: {client_brief['brand_name']}",
        f"Overall average score: {average_score}/100",
        "",
        "## Best-Performing Pages",
        "",
    ]
    lines.extend([f"- {result['page_title'] or result['url']}: {result['overall_score']}/100" for result in sorted_pages[:3]])

    lines.extend(["", "## Weakest Pages", ""])
    lines.extend([f"- {result['page_title'] or result['url']}: {result['overall_score']}/100" for result in sorted_pages[-3:]])

    lines.extend(["", "## Repeated Missing Questions", ""])
    lines.extend(_count_lines(missing_questions, "No repeated missing target question patterns detected."))

    lines.extend(["", "## Repeated Missing Entities", ""])
    lines.extend(_count_lines(missing_entities, "No repeated missing entity patterns detected."))

    lines.extend(["", "## Common FAQ Opportunities", ""])
    lines.extend(_count_lines(faq_opportunities, "No common FAQ opportunity detected."))

    lines.extend(["", "## Common Schema Opportunities", ""])
    lines.extend(_count_lines(schema_opportunities, "No common schema opportunity detected."))

    lines.extend(["", "## Top 10 Prioritized Site-Wide Recommendations", ""])
    if recommendations:
        lines.extend([f"{index}. {recommendation}" for index, recommendation in enumerate(recommendations[:10], start=1)])
    else:
        lines.append("No high-priority site-wide recommendations detected.")

    lines.append("")
    return "\n".join(lines)


def _write_all_scores_csv(audit_results: list[dict], output_path: Path) -> None:
    fieldnames = [
        "url",
        "page_title",
        "overall_score",
        "grade",
        "dimension_id",
        "dimension_name",
        "weight",
        "score_raw",
        "weighted_score",
        "why_this_score",
        "what_would_improve_the_score",
        "confidence_level",
        "evidence_found",
        "evidence_missing",
        "aeo_impact",
        "recommended_fix",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for audit_result in audit_results:
            for dimension in audit_result["dimension_results"]:
                writer.writerow(
                    {
                        "url": audit_result["url"],
                        "page_title": audit_result["page_title"],
                        "overall_score": audit_result["overall_score"],
                        "grade": audit_result["grade"],
                        "dimension_id": dimension["dimension_id"],
                        "dimension_name": dimension["dimension_name"],
                        "weight": dimension["weight"],
                        "score_raw": dimension["score_raw"],
                        "weighted_score": dimension["weighted_score"],
                        "why_this_score": dimension["why_this_score"],
                        "what_would_improve_the_score": dimension["what_would_improve_the_score"],
                        "confidence_level": dimension["confidence_level"],
                        "evidence_found": " | ".join(dimension["evidence_found"]),
                        "evidence_missing": " | ".join(dimension["evidence_missing"]),
                        "aeo_impact": dimension["aeo_impact"],
                        "recommended_fix": dimension["recommended_fix"],
                    }
                )


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:80] or "page"


def _dimension(result: dict, dimension_id: str) -> dict:
    return next(item for item in result["dimension_results"] if item["dimension_id"] == dimension_id)


def _repeated_missing_items(audit_results: list[dict], dimension_id: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in audit_results:
        for item in _dimension(result, dimension_id)["evidence_missing"]:
            if item != "No major deterministic gap detected.":
                counts[item] = counts.get(item, 0) + 1
    return {item: count for item, count in sorted(counts.items(), key=lambda pair: pair[1], reverse=True)}


def _dimension_gaps(audit_results: list[dict], dimension_id: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in audit_results:
        dimension = _dimension(result, dimension_id)
        if dimension["score_raw"] < 8:
            for item in dimension["evidence_missing"]:
                if item != "No major deterministic gap detected.":
                    counts[item] = counts.get(item, 0) + 1
    return {item: count for item, count in sorted(counts.items(), key=lambda pair: pair[1], reverse=True)}


def _site_recommendations(audit_results: list[dict]) -> list[str]:
    counts: dict[str, int] = {}
    for result in audit_results:
        weak_dimensions = sorted(result["dimension_results"], key=lambda item: item["score_raw"])
        for dimension in weak_dimensions[:4]:
            if dimension["score_raw"] < 8:
                fix = dimension["recommended_fix"]
                counts[fix] = counts.get(fix, 0) + 1
    return [item for item, _ in sorted(counts.items(), key=lambda pair: pair[1], reverse=True)]


def _count_lines(counts: dict[str, int], fallback: str) -> list[str]:
    if not counts:
        return [f"- {fallback}"]
    return [f"- {item} ({count} page{'s' if count != 1 else ''})" for item, count in counts.items()]


def generate_llm_review_prompt(
    template_path: Path,
    audit_result: dict,
    client_brief: dict,
    page_context: dict,
    target_questions: list[dict],
    required_entities: list[dict],
    scraped_page: dict,
) -> str:
    """Fill the manual LLM review prompt template."""
    template = template_path.read_text(encoding="utf-8")
    replacements = {
        "client_brief": _format_json(client_brief),
        "page_context": _format_json(page_context),
        "target_topic": page_context.get("target_topic", ""),
        "target_audience": client_brief.get("target_audience", ""),
        "business_goal": client_brief.get("business_goal", ""),
        "target_questions": _format_questions(target_questions),
        "required_entities": _format_entities(required_entities),
        "page_summary": _format_page_summary(scraped_page),
        "audit_scores": _format_scores(audit_result),
        "key_weaknesses": _format_weaknesses(audit_result),
    }

    prompt = template
    for key, value in replacements.items():
        prompt = prompt.replace("{{" + key + "}}", value)
    return prompt


def _format_json(data: dict) -> str:
    return "```json\n" + json.dumps(data, indent=2) + "\n```"


def _format_questions(target_questions: list[dict]) -> str:
    lines = []
    for question in target_questions:
        lines.append(
            f"- {question['question']} "
            f"(intent: {question['intent_type']}, priority: {question['priority']}, topic: {question['target_topic']})"
        )
    return "\n".join(lines)


def _format_entities(required_entities: list[dict]) -> str:
    lines = []
    for entity in required_entities:
        lines.append(
            f"- {entity['entity']} "
            f"(type: {entity['entity_type']}, priority: {entity['priority']}, topic: {entity['related_topic']})"
        )
    return "\n".join(lines)


def _format_page_summary(scraped_page: dict) -> str:
    headings = [f"- {heading['level'].upper()}: {heading['text']}" for heading in scraped_page["headings"][:12]]
    return "\n".join(
        [
            f"- Page title: {scraped_page['title']}",
            f"- Meta description: {scraped_page['meta_description']}",
            f"- Text length: {scraped_page['text_length']}",
            f"- Number of headings: {len(scraped_page['headings'])}",
            f"- Number of links: {len(scraped_page['links'])}",
            f"- FAQ-like headings detected: {scraped_page['has_faq_like_headings']}",
            "",
            "Top headings:",
            *headings,
            "",
            "Sample extracted text:",
            scraped_page["text"][:1200],
        ]
    )


def _format_scores(audit_result: dict) -> str:
    lines = [
        f"- Overall score: {audit_result['overall_score']}/100",
        f"- Grade: {audit_result['grade']}",
        "",
    ]
    for dimension in audit_result["dimension_results"]:
        lines.append(
            f"- {dimension['dimension_name']}: {dimension['score_raw']}/10 "
            f"({dimension['weighted_score']}/{dimension['weight']} weighted)"
        )
    return "\n".join(lines)


def _format_weaknesses(audit_result: dict) -> str:
    lines = []
    for weakness in audit_result["top_weaknesses"]:
        lines.append(f"- {weakness}")
    if audit_result["priority_recommendations"]:
        lines.append("")
        lines.append("Priority recommendations:")
        for recommendation in audit_result["priority_recommendations"]:
            lines.append(f"- {recommendation}")
    return "\n".join(lines)

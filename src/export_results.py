"""Export audit results to Markdown, CSV, JSON, and review prompts."""

from __future__ import annotations

import csv
import json
from pathlib import Path

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
                    "evidence_found": " | ".join(dimension["evidence_found"]),
                    "evidence_missing": " | ".join(dimension["evidence_missing"]),
                    "aeo_impact": dimension["aeo_impact"],
                    "recommended_fix": dimension["recommended_fix"],
                }
            )


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

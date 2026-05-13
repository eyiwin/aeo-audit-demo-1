"""Generate Markdown audit reports."""

from __future__ import annotations


def _join_items(items: list[str]) -> str:
    return " ".join(items) if items else "None found."


def _interpret(score_raw: int) -> str:
    if score_raw >= 8:
        return "Strong retrieval-readiness signal"
    if score_raw >= 6:
        return "Moderate retrieval-readiness signal"
    if score_raw >= 4:
        return "Weak retrieval-readiness signal"
    return "High-priority gap"


def _finding_block(dimension: dict) -> list[str]:
    return [
        f"### {dimension['dimension_name']}",
        "",
        f"- Finding: {_interpret(dimension['score_raw'])}",
        f"- Why this score: {dimension['why_this_score']}",
        f"- What would improve the score: {dimension['what_would_improve_the_score']}",
        f"- Confidence level: {dimension['confidence_level']}",
        f"- Evidence: {_join_items(dimension['evidence_found'])}",
        f"- AEO impact: {dimension['aeo_impact']}",
        f"- Recommended fix: {dimension['recommended_fix']}",
        "",
    ]


def generate_markdown_report(audit_result: dict, client_brief: dict, page_context: dict) -> str:
    """Return a Markdown report for one audited page."""
    dimensions = audit_result["dimension_results"]
    url = audit_result["url"]
    target_topic = page_context["target_topic"]

    summary = (
        f"{client_brief['brand_name']} scored {audit_result['overall_score']}/100 "
        f"for retrieval-readiness on {target_topic}. This is a deterministic AEO review of whether "
        "the page is structured for AI systems to retrieve, understand, summarize, and potentially cite. "
        "It does not guarantee citation by any AI system."
    )

    lines = [
        "# AEO Retrieval Readiness Audit",
        "",
        "## 1. Executive Summary",
        "",
        f"- Client: {client_brief['client_name']}",
        f"- Brand: {client_brief['brand_name']}",
        f"- URL: {url}",
        f"- Target topic: {target_topic}",
        f"- Target market: {client_brief['target_market']}",
        f"- Overall score: {audit_result['overall_score']}/100",
        f"- Grade: {audit_result['grade']}",
        "",
        summary,
        "",
        "## Scoring Caveats",
        "",
        "This MVP uses rule-based proxy signals, such as keyword coverage, headings, entities, links, and CTA language. Scores should be combined with strategist review and optional LLM review before making final content decisions. The recommendations remain practical priorities, but the score is not a definitive measure of AI citation, ranking, or visibility.",
        "",
        "## 2. Score Breakdown",
        "",
        "| Dimension | Weight | Raw score | Weighted score | Short interpretation |",
        "| --- | ---: | ---: | ---: | --- |",
    ]

    for dimension in dimensions:
        lines.append(
            f"| {dimension['dimension_name']} | {dimension['weight']} | "
            f"{dimension['score_raw']}/10 | {dimension['weighted_score']} | "
            f"{_interpret(dimension['score_raw'])} |"
        )

    lines.extend(["", "## 3. Key Strengths", ""])
    for strength in audit_result["top_strengths"]:
        lines.append(f"- {strength}")

    lines.extend(["", "## 4. Key Weaknesses", ""])
    for weakness in audit_result["top_weaknesses"]:
        lines.append(f"- {weakness}")

    query_dimension = _by_id(dimensions, "query_answer_coverage")
    entity_dimension = _by_id(dimensions, "entity_clarity")
    semantic_dimension = _by_id(dimensions, "semantic_relationship_clarity")
    faq_dimension = _by_id(dimensions, "faq_readiness")
    schema_dimension = _by_id(dimensions, "schema_readiness")
    evidence_dimension = _by_id(dimensions, "evidence_source_support")
    conversion_dimension = _by_id(dimensions, "conversion_alignment")

    lines.extend(["", "## 5. Missing or Weak Target Questions", ""])
    lines.extend(_finding_block(query_dimension))

    lines.extend(["## 6. Entity and Semantic Clarity Review", ""])
    lines.extend(_finding_block(entity_dimension))
    lines.extend(_finding_block(semantic_dimension))

    lines.extend(["## 7. FAQ and Schema Opportunities", ""])
    lines.extend(_finding_block(faq_dimension))
    lines.extend(_finding_block(schema_dimension))

    lines.extend(["## 8. Evidence and Source Support Review", ""])
    lines.extend(_finding_block(evidence_dimension))

    lines.extend(["## 9. Conversion Alignment Review", ""])
    lines.extend(_finding_block(conversion_dimension))

    lines.extend(["## 10. Prioritized Recommendations", ""])
    recommendations = audit_result["priority_recommendations"]
    if not recommendations:
        lines.append("- No high-priority deterministic recommendation detected.")
    for recommendation in recommendations:
        lines.append(f"- {recommendation}")

    lines.append("")
    return "\n".join(lines)


def _by_id(dimensions: list[dict], dimension_id: str) -> dict:
    for dimension in dimensions:
        if dimension["dimension_id"] == dimension_id:
            return dimension
    raise KeyError(f"Dimension not found in audit result: {dimension_id}")

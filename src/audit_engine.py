"""Deterministic AEO retrieval-readiness audit engine."""

from __future__ import annotations

import re


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "can",
    "do",
    "for",
    "how",
    "in",
    "is",
    "of",
    "or",
    "the",
    "to",
    "what",
    "when",
    "where",
    "why",
    "with",
}


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 2 and token not in STOPWORDS
    }


def _contains_any(text: str, terms: list[str]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def _score_from_ratio(ratio: float) -> int:
    if ratio >= 0.9:
        return 10
    if ratio >= 0.75:
        return 8
    if ratio >= 0.55:
        return 6
    if ratio >= 0.35:
        return 4
    if ratio > 0:
        return 2
    return 0


def _grade(score: float) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def _near_each_other(text: str, first: str, second: str, window: int = 160) -> bool:
    lowered = text.lower()
    first_positions = [match.start() for match in re.finditer(re.escape(first.lower()), lowered)]
    second_positions = [match.start() for match in re.finditer(re.escape(second.lower()), lowered)]
    return any(abs(first_pos - second_pos) <= window for first_pos in first_positions for second_pos in second_positions)


def _entity_names(required_entities: list[dict]) -> list[str]:
    return [row["entity"] for row in required_entities if row.get("entity")]


def _target_questions_for_page(target_questions: list[dict], page_context: dict) -> list[dict]:
    page_topic = page_context.get("target_topic", "").lower()
    matched = [
        question
        for question in target_questions
        if not page_topic or question.get("target_topic", "").lower() == page_topic
    ]
    return matched or target_questions


def _result(dimension: dict, score_raw: int, found: list[str], missing: list[str], fix: str) -> dict:
    weight = float(dimension["weight"])
    return {
        "dimension_id": dimension["id"],
        "dimension_name": dimension["name"],
        "score_raw": score_raw,
        "weighted_score": round(score_raw / 10 * weight, 2),
        "weight": weight,
        "evidence_found": found or ["No strong deterministic evidence found."],
        "evidence_missing": missing or ["No major deterministic gap detected."],
        "aeo_impact": dimension["description"],
        "recommended_fix": fix or dimension["recommended_fix_logic"],
    }


def _score_query_answer_coverage(dimension: dict, page: dict, page_context: dict, questions: list[dict]) -> dict:
    text_tokens = _tokens(page["text"])
    topic_tokens = _tokens(page_context.get("target_topic", ""))
    question_scores = []
    missing_questions = []

    for question in questions:
        question_tokens = _tokens(question["question"]) | _tokens(question.get("target_topic", ""))
        matched = question_tokens.intersection(text_tokens)
        score = len(matched) / max(len(question_tokens), 1)
        question_scores.append(score)
        if score < 0.35:
            missing_questions.append(question["question"])

    topic_match = len(topic_tokens.intersection(text_tokens)) / max(len(topic_tokens), 1)
    average_match = (sum(question_scores) / max(len(question_scores), 1) + topic_match) / 2
    score_raw = _score_from_ratio(average_match)

    found = [f"{len(questions) - len(missing_questions)} of {len(questions)} relevant target questions show keyword/topic coverage."]
    missing = [f"Weak coverage: {question}" for question in missing_questions]
    return _result(dimension, score_raw, found, missing, dimension["recommended_fix_logic"])


def _score_direct_answer_extractability(dimension: dict, page: dict) -> dict:
    question_headings = page["faq_like_headings"]
    text = page["text"]
    concise_signal = any(len(heading["text"].split()) <= 12 for heading in question_headings)
    direct_terms = _contains_any(text, ["is a", "are", "means", "helps", "allows", "requires", "you need"])
    score_raw = min(10, len(question_headings) * 2 + int(concise_signal) * 3 + int(direct_terms) * 3)

    found = []
    if question_headings:
        found.append(f"{len(question_headings)} FAQ-like or question-style headings found.")
    if concise_signal:
        found.append("Question headings are concise enough to support answer extraction.")
    if direct_terms:
        found.append("Declarative answer language appears in the page text.")

    missing = []
    if not question_headings:
        missing.append("No question-like headings found.")
    if not direct_terms:
        missing.append("Direct answer wording is weak or missing.")
    return _result(dimension, score_raw, found, missing, dimension["recommended_fix_logic"])


def _score_heading_structure(dimension: dict, page: dict, page_context: dict) -> dict:
    headings = page["headings"]
    heading_text = " ".join(heading["text"] for heading in headings)
    topic_terms = _tokens(page_context.get("target_topic", ""))
    heading_terms = _tokens(heading_text)
    question_word_count = sum(
        1
        for heading in headings
        if heading["text"].lower().startswith(("what ", "why ", "how ", "when ", "where ", "who ", "can ", "do "))
    )

    score_raw = min(
        10,
        int(any(heading["level"] == "h1" for heading in headings)) * 2
        + min(len(headings), 4)
        + _score_from_ratio(len(topic_terms.intersection(heading_terms)) / max(len(topic_terms), 1)) // 2
        + min(question_word_count, 2),
    )
    found = [f"{len(headings)} H1/H2/H3 headings found."]
    missing = []
    if not topic_terms.intersection(heading_terms):
        missing.append("Headings do not clearly include target topic terms.")
    return _result(dimension, score_raw, found, missing, dimension["recommended_fix_logic"])


def _score_faq_readiness(dimension: dict, page: dict) -> dict:
    text = page["text"].lower()
    has_faq_word = "faq" in text or "frequently asked" in text
    question_headings = page["faq_like_headings"]
    score_raw = min(10, int(has_faq_word) * 4 + min(len(question_headings) * 2, 6))
    found = []
    if has_faq_word:
        found.append("FAQ language appears on the page.")
    if question_headings:
        found.append(f"{len(question_headings)} question-format headings found.")
    missing = []
    if not has_faq_word:
        missing.append("No explicit FAQ section detected.")
    if not question_headings:
        missing.append("No question-format headings detected.")
    return _result(dimension, score_raw, found, missing, dimension["recommended_fix_logic"])


def _score_entity_clarity(dimension: dict, page: dict, required_entities: list[dict]) -> dict:
    text = page["text"].lower()
    entities = _entity_names(required_entities)
    found_entities = [entity for entity in entities if entity.lower() in text]
    missing_entities = [entity for entity in entities if entity.lower() not in text]
    score_raw = _score_from_ratio(len(found_entities) / max(len(entities), 1))
    found = [f"Entities found: {', '.join(found_entities)}."] if found_entities else []
    missing = [f"Missing entities: {', '.join(missing_entities)}."] if missing_entities else []
    return _result(dimension, score_raw, found, missing, dimension["recommended_fix_logic"])


def _score_semantic_relationships(dimension: dict, page: dict, client_brief: dict, required_entities: list[dict]) -> dict:
    text = page["text"]
    brand = client_brief["brand_name"]
    topic = client_brief["primary_topic"]
    entities = _entity_names(required_entities)[:8]
    near_matches = [entity for entity in entities if _near_each_other(text, brand, entity) or _near_each_other(text, topic, entity)]
    relationship_terms = ["helps", "requires", "includes", "because", "for example", "supports", "for", "with"]
    relationship_found = [term for term in relationship_terms if term in text.lower()]
    score_raw = min(10, _score_from_ratio(len(near_matches) / max(len(entities), 1)) + min(len(relationship_found), 4))
    found = []
    if near_matches:
        found.append(f"Nearby entity relationships found: {', '.join(near_matches)}.")
    if relationship_found:
        found.append(f"Relationship language found: {', '.join(relationship_found)}.")
    missing = []
    if not near_matches:
        missing.append("Important entities do not appear near the brand or topic.")
    return _result(dimension, score_raw, found, missing, dimension["recommended_fix_logic"])


def _score_evidence_support(dimension: dict, page: dict) -> dict:
    text = page["text"].lower()
    evidence_terms = ["according", "source", "example", "regulation", "requirement", "data", "%", "case study", "testimonial", "acra", "iras"]
    found_terms = [term for term in evidence_terms if term in text]
    outbound_links = [link for link in page["links"] if link.get("href", "").startswith(("http://", "https://"))]
    score_raw = min(10, min(len(found_terms), 6) + min(len(outbound_links), 4))
    found = []
    if found_terms:
        found.append(f"Evidence/source terms found: {', '.join(found_terms)}.")
    if outbound_links:
        found.append(f"{len(outbound_links)} outbound links found.")
    missing = []
    if not found_terms:
        missing.append("No strong evidence, authority, regulation, or source-like language found.")
    if not outbound_links:
        missing.append("No outbound source links found.")
    return _result(dimension, score_raw, found, missing, dimension["recommended_fix_logic"])


def _score_schema_readiness(dimension: dict, page: dict) -> dict:
    text = page["text"].lower()
    has_faq = page["has_faq_like_headings"] or "faq" in text
    has_article = any(heading["level"] == "h1" for heading in page["headings"]) and len(page["text"]) > 1000
    has_service = _contains_any(text, ["service", "consultation", "incorporation", "company registration"])
    has_org = bool(page["title"]) and bool(page["meta_description"])
    score_raw = min(10, int(has_faq) * 3 + int(has_article) * 2 + int(has_service) * 3 + int(has_org) * 2)
    found = []
    if has_faq:
        found.append("FAQ-like structure detected.")
    if has_article:
        found.append("Article-like structure detected.")
    if has_service:
        found.append("Service information detected.")
    if has_org:
        found.append("Organization/page metadata signals detected.")
    missing = []
    if not has_faq:
        missing.append("FAQPage schema opportunity is unclear from page structure.")
    return _result(dimension, score_raw, found, missing, dimension["recommended_fix_logic"])


def _score_brand_topic_association(dimension: dict, page: dict, client_brief: dict) -> dict:
    text = page["text"]
    brand = client_brief["brand_name"]
    topic = client_brief["primary_topic"]
    service = client_brief["main_service"]
    market = client_brief["target_market"]
    score_raw = min(
        10,
        int(brand.lower() in text.lower()) * 3
        + int(topic.lower() in text.lower()) * 3
        + int(service.lower() in text.lower()) * 2
        + int(_near_each_other(text, brand, market)) * 2,
    )
    found = []
    if brand.lower() in text.lower():
        found.append("Brand name appears in page text.")
    if topic.lower() in text.lower():
        found.append("Primary topic appears in page text.")
    if service.lower() in text.lower():
        found.append("Main service appears in page text.")
    missing = []
    if score_raw < 7:
        missing.append("Brand, topic, service, and market are not strongly associated.")
    return _result(dimension, score_raw, found, missing, dimension["recommended_fix_logic"])


def _score_conversion_alignment(dimension: dict, page: dict, client_brief: dict) -> dict:
    text = page["text"].lower()
    cta_terms = ["book", "contact", "consultation", "enquire", "quote", "demo", "call", "form"]
    found_terms = [term for term in cta_terms if term in text]
    primary_conversion = client_brief.get("primary_conversion", "").lower()
    score_raw = min(10, len(found_terms) * 2 + int(primary_conversion and primary_conversion in text) * 2)
    found = [f"CTA terms found: {', '.join(found_terms)}."] if found_terms else []
    missing = []
    if not found_terms:
        missing.append("No clear conversion or CTA language found.")
    return _result(dimension, score_raw, found, missing, dimension["recommended_fix_logic"])


def audit_page(
    scraped_page: dict,
    client_brief: dict,
    page_context: dict,
    target_questions: list[dict],
    required_entities: list[dict],
    scoring_rubric: dict,
) -> dict:
    """Evaluate one scraped page against the AEO scoring rubric."""
    questions = _target_questions_for_page(target_questions, page_context)
    dimension_results = []

    for dimension in scoring_rubric["dimensions"]:
        dimension_id = dimension["id"]
        if dimension_id == "query_answer_coverage":
            result = _score_query_answer_coverage(dimension, scraped_page, page_context, questions)
        elif dimension_id == "direct_answer_extractability":
            result = _score_direct_answer_extractability(dimension, scraped_page)
        elif dimension_id == "heading_content_structure":
            result = _score_heading_structure(dimension, scraped_page, page_context)
        elif dimension_id == "faq_readiness":
            result = _score_faq_readiness(dimension, scraped_page)
        elif dimension_id == "entity_clarity":
            result = _score_entity_clarity(dimension, scraped_page, required_entities)
        elif dimension_id == "semantic_relationship_clarity":
            result = _score_semantic_relationships(dimension, scraped_page, client_brief, required_entities)
        elif dimension_id == "evidence_source_support":
            result = _score_evidence_support(dimension, scraped_page)
        elif dimension_id == "schema_readiness":
            result = _score_schema_readiness(dimension, scraped_page)
        elif dimension_id == "brand_topic_association":
            result = _score_brand_topic_association(dimension, scraped_page, client_brief)
        elif dimension_id == "conversion_alignment":
            result = _score_conversion_alignment(dimension, scraped_page, client_brief)
        else:
            result = _result(dimension, 0, [], ["No scoring rule exists for this dimension."], dimension["recommended_fix_logic"])
        dimension_results.append(result)

    overall_score = round(sum(result["weighted_score"] for result in dimension_results), 2)
    sorted_results = sorted(dimension_results, key=lambda item: item["score_raw"])

    return {
        "url": scraped_page["url"],
        "page_title": scraped_page["title"],
        "overall_score": overall_score,
        "grade": _grade(overall_score),
        "dimension_results": dimension_results,
        "top_strengths": [
            f"{item['dimension_name']}: {item['score_raw']}/10" for item in sorted_results[-3:][::-1]
        ],
        "top_weaknesses": [
            f"{item['dimension_name']}: {item['score_raw']}/10" for item in sorted_results[:3]
        ],
        "priority_recommendations": [
            item["recommended_fix"] for item in sorted_results[:3] if item["score_raw"] < 7
        ],
    }

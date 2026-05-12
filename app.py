"""Simple local Streamlit UI for testing the AEO audit tool."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from audit_engine import audit_page
from export_results import export_audit_results
from load_inputs import load_scoring_rubric
from scrape_page import scrape_page


def _lines_to_list(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


def _build_target_questions(value: str, target_topic: str) -> list[dict[str, str]]:
    questions = []
    for question in _lines_to_list(value):
        questions.append(
            {
                "question": question,
                "intent_type": "manual",
                "priority": "medium",
                "expected_page_type": "manual",
                "target_topic": target_topic,
            }
        )
    return questions


def _build_required_entities(value: str, target_topic: str) -> list[dict[str, str]]:
    entities = []
    for entity in _lines_to_list(value):
        entities.append(
            {
                "entity": entity,
                "entity_type": "manual",
                "priority": "medium",
                "related_topic": target_topic,
            }
        )
    return entities


def _score_table(audit_result: dict) -> pd.DataFrame:
    rows = []
    for dimension in audit_result["dimension_results"]:
        rows.append(
            {
                "Dimension": dimension["dimension_name"],
                "Weight": dimension["weight"],
                "Raw score": dimension["score_raw"],
                "Weighted score": dimension["weighted_score"],
            }
        )
    return pd.DataFrame(rows)


def _download_button(label: str, path: Path, mime: str) -> None:
    st.download_button(
        label=label,
        data=path.read_bytes(),
        file_name=path.name,
        mime=mime,
    )


def _resolve_audit_target(value: str) -> str:
    """Resolve repo-relative sample files while leaving live URLs unchanged."""
    if value.startswith(("http://", "https://")):
        return value
    candidate = PROJECT_ROOT / value
    if candidate.exists():
        return str(candidate)
    return value


st.set_page_config(page_title="AEO Audit MVP", layout="wide")
st.title("AEO Retrieval Readiness Audit MVP")
st.caption("Local internal testing interface. No login, database, dashboard, or paid API calls.")

with st.form("audit_form"):
    st.subheader("Client details")
    col1, col2 = st.columns(2)
    with col1:
        client_name = st.text_input("Client name", "Harbour & Co Advisory")
        brand_name = st.text_input("Brand name", "Harbour Incorporation")
        website_url = st.text_input("Website URL", "https://www.harbourincorporation.example")
        target_market = st.text_input("Target market", "Singapore")
        target_audience = st.text_area(
            "Target audience",
            "Foreign founders, startup operators, and small business owners who want to register a company in Singapore",
        )
    with col2:
        business_goal = st.text_area(
            "Business goal",
            "Increase qualified consultation requests from founders researching Singapore company incorporation requirements.",
        )
        primary_conversion = st.text_input("Primary conversion", "Book a company incorporation consultation")
        main_service = st.text_input("Main service", "Company incorporation services in Singapore")
        primary_topic = st.text_input("Primary topic", "company incorporation services in Singapore")

    secondary_topics_text = st.text_area(
        "Secondary topics, one per line",
        "Singapore company registration\nACRA registration\nnominee director service\ncorporate secretary service",
    )
    competitors_text = st.text_area(
        "Competitors, one per line",
        "Osome Singapore\nSleek Singapore\n3E Accounting",
    )

    st.subheader("Audit inputs")
    audit_url = st.text_input("URL to audit", "inputs/sample_company_incorporation_page.html")
    target_questions_text = st.text_area(
        "Target questions, one per line",
        "How do I incorporate a company in Singapore?\nCan a foreigner start a company in Singapore?\nWhat documents are needed for Singapore company incorporation?\nHow long does Singapore company registration take?",
        height=140,
    )
    required_entities_text = st.text_area(
        "Required entities, one per line",
        "Harbour Incorporation\nSingapore\nACRA\nprivate limited company\nlocal resident director\ncorporate secretary\nregistered office address",
        height=140,
    )

    submitted = st.form_submit_button("Run AEO Audit")

if submitted:
    client_brief = {
        "client_name": client_name,
        "brand_name": brand_name,
        "website_url": website_url,
        "target_market": target_market,
        "target_audience": target_audience,
        "business_goal": business_goal,
        "primary_conversion": primary_conversion,
        "main_service": main_service,
        "primary_topic": primary_topic,
        "secondary_topics": _lines_to_list(secondary_topics_text),
        "competitors": _lines_to_list(competitors_text),
        "notes": "Created from the local Streamlit testing UI.",
    }
    page_context = {
        "url": audit_url,
        "page_type": "manual",
        "target_topic": primary_topic,
        "priority": "high",
    }
    target_questions = _build_target_questions(target_questions_text, primary_topic)
    required_entities = _build_required_entities(required_entities_text, primary_topic)

    if not audit_url or not target_questions or not required_entities:
        st.error("Please provide a URL, at least one target question, and at least one required entity.")
        st.stop()

    try:
        scoring_rubric = load_scoring_rubric(PROJECT_ROOT / "config" / "aeo_scoring_rubric.json")
        scraped_page = scrape_page(_resolve_audit_target(audit_url))
        audit_result = audit_page(
            scraped_page=scraped_page,
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
            scraped_page=scraped_page,
            output_dir=PROJECT_ROOT / "outputs",
            prompt_template_path=PROJECT_ROOT / "prompts" / "llm_review_prompt_template.md",
        )
    except Exception as error:
        st.error(f"Audit failed: {error}")
        st.stop()

    st.subheader("Results")
    metric_col1, metric_col2 = st.columns(2)
    metric_col1.metric("Overall AEO score", f"{audit_result['overall_score']}/100")
    metric_col2.metric("Grade", audit_result["grade"])

    st.subheader("Score breakdown")
    st.dataframe(_score_table(audit_result), use_container_width=True, hide_index=True)

    st.subheader("Key strengths")
    for strength in audit_result["top_strengths"]:
        st.write(f"- {strength}")

    st.subheader("Key weaknesses")
    for weakness in audit_result["top_weaknesses"]:
        st.write(f"- {weakness}")

    st.subheader("Priority recommendations")
    if audit_result["priority_recommendations"]:
        for recommendation in audit_result["priority_recommendations"]:
            st.write(f"- {recommendation}")
    else:
        st.write("No high-priority deterministic recommendations found.")

    st.subheader("LLM review prompt preview")
    prompt_text = output_paths["llm_review_prompt"].read_text(encoding="utf-8")
    st.text_area("Prompt preview", prompt_text[:3000], height=260)

    st.subheader("Downloads")
    download_cols = st.columns(4)
    with download_cols[0]:
        _download_button("audit_report.md", output_paths["audit_report"], "text/markdown")
    with download_cols[1]:
        _download_button("audit_scores.csv", output_paths["audit_scores"], "text/csv")
    with download_cols[2]:
        _download_button("page_findings.json", output_paths["page_findings"], "application/json")
    with download_cols[3]:
        _download_button("llm_review_prompt.md", output_paths["llm_review_prompt"], "text/markdown")

    with st.expander("Raw audit result"):
        st.json(json.loads(output_paths["page_findings"].read_text(encoding="utf-8")))

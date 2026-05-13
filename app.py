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
from export_results import export_site_audit_results
from load_inputs import load_scoring_rubric
from scrape_page import scrape_page


def _lines_to_list(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


def _build_target_questions(value: str, target_topic: str) -> list[dict[str, str]]:
    return [
        {
            "question": question,
            "intent_type": "manual",
            "priority": "medium",
            "expected_page_type": "manual",
            "target_topic": target_topic,
        }
        for question in _lines_to_list(value)
    ]


def _build_required_entities(value: str, target_topic: str) -> list[dict[str, str]]:
    return [
        {
            "entity": entity,
            "entity_type": "manual",
            "priority": "medium",
            "related_topic": target_topic,
        }
        for entity in _lines_to_list(value)
    ]


def _build_page_contexts(value: str, default_topic: str) -> list[dict[str, str]]:
    contexts = []
    for line in _lines_to_list(value):
        parts = [part.strip() for part in line.split("|")]
        contexts.append(
            {
                "url": parts[0],
                "page_type": parts[1] if len(parts) > 1 and parts[1] else "manual",
                "target_topic": parts[2] if len(parts) > 2 and parts[2] else default_topic,
                "priority": parts[3] if len(parts) > 3 and parts[3] else "medium",
            }
        )
    return contexts


def _resolve_audit_target(value: str) -> str:
    """Resolve repo-relative sample files while leaving live URLs unchanged."""
    if value.startswith(("http://", "https://")):
        return value
    candidate = PROJECT_ROOT / value
    if candidate.exists():
        return str(candidate)
    return value


def _page_summary_table(audit_results: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Page": result["page_title"] or result["url"],
                "URL": result["url"],
                "Score": result["overall_score"],
                "Grade": result["grade"],
            }
            for result in audit_results
        ]
    )


def _dimension_table(audit_results: list[dict]) -> pd.DataFrame:
    rows = []
    for result in audit_results:
        for dimension in result["dimension_results"]:
            rows.append(
                {
                    "Page": result["page_title"] or result["url"],
                    "Dimension": dimension["dimension_name"],
                    "Raw score": dimension["score_raw"],
                    "Weighted score": dimension["weighted_score"],
                    "Confidence": dimension.get("confidence_level", ""),
                }
            )
    return pd.DataFrame(rows)


def _download_button(label: str, path: Path, mime: str) -> None:
    st.download_button(label=label, data=path.read_bytes(), file_name=path.name, mime=mime)


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
    competitors_text = st.text_area("Competitors, one per line", "Osome Singapore\nSleek Singapore\n3E Accounting")

    st.subheader("Batch audit inputs")
    st.caption("Enter one page per line. Format: URL or path | page type | target topic | priority")
    pages_text = st.text_area(
        "Pages to audit",
        "inputs/sample_company_incorporation_page.html | service_page | company incorporation services in Singapore | high\n"
        "inputs/sample_registration_guide.html | guide | Singapore company registration requirements | high\n"
        "inputs/sample_nominee_director_page.html | service_page | nominee director service in Singapore | medium\n"
        "inputs/sample_corporate_secretary_page.html | service_page | corporate secretary service in Singapore | medium",
        height=150,
    )
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
    page_contexts = _build_page_contexts(pages_text, primary_topic)
    target_questions = _build_target_questions(target_questions_text, primary_topic)
    required_entities = _build_required_entities(required_entities_text, primary_topic)

    if not page_contexts or not target_questions or not required_entities:
        st.error("Please provide at least one page, one target question, and one required entity.")
        st.stop()

    try:
        scoring_rubric = load_scoring_rubric(PROJECT_ROOT / "config" / "aeo_scoring_rubric.json")
        audit_results = []
        audited_contexts = []
        skipped_pages = []

        progress = st.progress(0)
        for index, page_context in enumerate(page_contexts, start=1):
            try:
                scraped_page = scrape_page(_resolve_audit_target(page_context["url"]))
                scraped_page["url"] = page_context["url"]
                audit_results.append(
                    audit_page(
                        scraped_page=scraped_page,
                        client_brief=client_brief,
                        page_context=page_context,
                        target_questions=target_questions,
                        required_entities=required_entities,
                        scoring_rubric=scoring_rubric,
                    )
                )
                audited_contexts.append(page_context)
            except Exception as error:
                skipped_pages.append(f"{page_context['url']}: {error}")
            progress.progress(index / len(page_contexts))

        if not audit_results:
            st.error("No pages were successfully audited.")
            st.stop()

        output_paths = export_site_audit_results(
            audit_results=audit_results,
            client_brief=client_brief,
            page_contexts=audited_contexts,
            output_dir=PROJECT_ROOT / "outputs",
        )
    except Exception as error:
        st.error(f"Audit failed: {error}")
        st.stop()

    st.subheader("Site-level results")
    average_score = round(sum(result["overall_score"] for result in audit_results) / len(audit_results), 2)
    metric_col1, metric_col2 = st.columns(2)
    metric_col1.metric("Average AEO score", f"{average_score}/100")
    metric_col2.metric("Pages audited", len(audit_results))

    if skipped_pages:
        st.warning("Some pages were skipped:")
        for skipped in skipped_pages:
            st.write(f"- {skipped}")

    st.subheader("Page scores")
    st.dataframe(_page_summary_table(audit_results), use_container_width=True, hide_index=True)

    st.subheader("Dimension breakdown")
    st.dataframe(_dimension_table(audit_results), use_container_width=True, hide_index=True)

    st.subheader("Best-performing pages")
    for result in sorted(audit_results, key=lambda item: item["overall_score"], reverse=True)[:3]:
        st.write(f"- {result['page_title'] or result['url']}: {result['overall_score']}/100")

    st.subheader("Weakest pages")
    for result in sorted(audit_results, key=lambda item: item["overall_score"])[:3]:
        st.write(f"- {result['page_title'] or result['url']}: {result['overall_score']}/100")

    st.subheader("Site summary preview")
    site_summary_text = output_paths["site_summary"].read_text(encoding="utf-8")
    st.text_area("site_summary.md preview", site_summary_text[:4000], height=280)

    st.subheader("Downloads")
    download_cols = st.columns(3)
    with download_cols[0]:
        _download_button("site_summary.md", output_paths["site_summary"], "text/markdown")
    with download_cols[1]:
        _download_button("all_scores.csv", output_paths["all_scores"], "text/csv")
    with download_cols[2]:
        _download_button("all_findings.json", output_paths["all_findings"], "application/json")

    st.subheader("Individual page reports")
    for path in output_paths["page_reports"]:
        _download_button(path.name, path, "text/markdown")

    with st.expander("Raw all findings"):
        st.json(json.loads(output_paths["all_findings"].read_text(encoding="utf-8")))

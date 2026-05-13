"""Simple local Streamlit UI for testing the AEO audit tool."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import traceback

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


def _error_hint(error_message: str, resolved_target: str) -> str:
    lowered = error_message.lower()
    if resolved_target.startswith(("http://", "https://")):
        if "failed to resolve" in lowered or "name resolution" in lowered:
            return "The domain could not be resolved. Check that the URL is real and publicly reachable."
        if "403" in lowered or "forbidden" in lowered:
            return "The website likely blocked the scraper. Try another URL or use a manually saved HTML sample."
        if "404" in lowered or "not found" in lowered:
            return "The page URL returned not found. Check the URL path."
        if "timeout" in lowered or "timed out" in lowered:
            return "The page took too long to respond. Try again or test a lighter page."
        if "ssl" in lowered:
            return "The site has an SSL/certificate issue from this environment."
        return "The live page could not be fetched. Some websites block cloud or script-based requests."
    return "The local file path was not found or could not be read. Use a repo-relative path such as inputs/sample_company_incorporation_page.html."


def _diagnostic_row(page_context: dict, resolved_target: str, status: str, stage: str, error: Exception | None = None) -> dict:
    error_message = str(error) if error else ""
    return {
        "url": page_context["url"],
        "resolved_target": resolved_target,
        "page_type": page_context["page_type"],
        "target_topic": page_context["target_topic"],
        "status": status,
        "failed_stage": stage,
        "error_type": type(error).__name__ if error else "",
        "error_message": error_message,
        "likely_blocker": _error_hint(error_message, resolved_target) if error else "",
        "traceback": traceback.format_exc() if error else "",
    }


def _diagnostics_table(rows: list[dict]) -> pd.DataFrame:
    columns = [
        "status",
        "url",
        "resolved_target",
        "failed_stage",
        "error_type",
        "error_message",
        "likely_blocker",
    ]
    return pd.DataFrame([{column: row.get(column, "") for column in columns} for row in rows])


def _render_results(state: dict) -> None:
    audit_results = state["audit_results"]
    diagnostics = state["diagnostics"]
    output_paths = {key: Path(value) if isinstance(value, str) else value for key, value in state["output_paths"].items()}

    st.subheader("Site-level results")
    average_score = round(sum(result["overall_score"] for result in audit_results) / len(audit_results), 2)
    metric_col1, metric_col2 = st.columns(2)
    metric_col1.metric("Average AEO score", f"{average_score}/100")
    metric_col2.metric("Pages audited", len(audit_results))

    failed_diagnostics = [row for row in diagnostics if row["status"] == "failed"]
    if failed_diagnostics:
        st.warning("Some pages were skipped. See exact blockers below.")
        st.dataframe(_diagnostics_table(failed_diagnostics), use_container_width=True, hide_index=True)
        with st.expander("Full technical tracebacks for skipped pages"):
            for row in failed_diagnostics:
                st.write(f"### {row['url']}")
                st.write(f"Failed stage: {row['failed_stage']}")
                st.write(f"Likely blocker: {row['likely_blocker']}")
                st.code(row["traceback"] or row["error_message"])

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


st.set_page_config(page_title="AEO Audit MVP", layout="wide")
st.title("AEO Retrieval Readiness Audit MVP")
st.caption("Local internal testing interface. No login, database, dashboard, or paid API calls.")

with st.form("audit_form"):
    st.subheader("Client details")
    col1, col2 = st.columns(2)
    with col1:
        client_name = st.text_input("Client name", "HubSpot")
        brand_name = st.text_input("Brand name", "HubSpot")
        website_url = st.text_input("Website URL", "https://www.hubspot.com")
        target_market = st.text_input("Target market", "Global")
        target_audience = st.text_area(
            "Target audience",
            "Marketing managers, sales teams, B2B founders, demand generation teams, and business owners looking to generate and convert qualified leads.",
        )
    with col2:
        business_goal = st.text_area(
            "Business goal",
            "Attract marketers and business owners searching for lead generation education, then guide them toward HubSpot's CRM, marketing automation, lead capture, and sales enablement products.",
        )
        primary_conversion = st.text_input(
            "Primary conversion",
            "Download a lead generation resource, sign up for HubSpot tools, or start using HubSpot CRM.",
        )
        main_service = st.text_input("Main service", "CRM, marketing automation, sales software, and lead generation tools")
        primary_topic = st.text_input("Primary topic", "lead generation")

    secondary_topics_text = st.text_area(
        "Secondary topics, one per line",
        "inbound marketing\n"
        "lead capture\n"
        "lead nurturing\n"
        "landing pages\n"
        "forms\n"
        "calls-to-action\n"
        "marketing automation\n"
        "CRM\n"
        "sales pipeline\n"
        "lead qualification",
    )
    competitors_text = st.text_area(
        "Competitors, one per line",
        "Salesforce\n"
        "Marketo\n"
        "ActiveCampaign\n"
        "Pipedrive\n"
        "Zoho CRM\n"
        "Mailchimp",
    )

    st.subheader("Batch audit inputs")
    st.caption("Enter one page per line. Format: URL or path | page type | target topic | priority")
    pages_text = st.text_area(
        "Pages to audit",
        "https://blog.hubspot.com/marketing/beginner-inbound-lead-generation-guide-ht | blog | lead generation | high\n"
        "https://blog.hubspot.com/marketing/lead-generation-strategy | blog | lead generation strategy | high\n"
        "https://blog.hubspot.com/marketing/optimize-website-for-lead-generation | blog | lead generation website | high\n"
        "https://blog.hubspot.com/marketing/lead-gen-content-ideas | blog | lead generation content ideas | medium\n"
        "https://blog.hubspot.com/marketing/facebook-lead-generation-tips-ht | blog | Facebook lead generation | medium\n"
        "https://blog.hubspot.com/marketing/content-marketing-strategy-guide | blog | content marketing strategy | high\n"
        "https://blog.hubspot.com/marketing/content-marketing | blog | content marketing | high\n"
        "https://blog.hubspot.com/marketing/content-marketing-plan | blog | content marketing plan | high\n"
        "https://blog.hubspot.com/marketing/content-creation | blog | content creation | medium\n"
        "https://blog.hubspot.com/marketing/content-for-every-funnel-stage | blog | content marketing funnel | medium\n"
        "https://blog.hubspot.com/sales/prospecting | blog | sales prospecting | high\n"
        "https://blog.hubspot.com/sales/targeted-sales-prospecting-guide | blog | targeted sales prospecting | high\n"
        "https://blog.hubspot.com/sales/effective-sales-prospecting-techniques-you-should-be-using | blog | sales prospecting techniques | medium\n"
        "https://blog.hubspot.com/sales/the-5-most-common-objections-during-prospecting-and-how-to-overcome-them | blog | sales objections | medium\n"
        "https://blog.hubspot.com/sales/phone-prospecting-tips-infographic | blog | phone prospecting | medium\n"
        "https://blog.hubspot.com/service/customer-service | blog | customer service | high\n"
        "https://blog.hubspot.com/service/customer-service-tips | blog | customer service tips | medium\n"
        "https://blog.hubspot.com/service/customer-service-standards | blog | customer service standards | medium\n"
        "https://blog.hubspot.com/service/importance-customer-service | blog | importance of customer service | medium\n"
        "https://blog.hubspot.com/service | blog_index | customer service blog index | low",
        height=150,
    )
    target_questions_text = st.text_area(
        "Target questions, one per line",
        "What is lead generation?\n"
        "Why is lead generation important?\n"
        "How does lead generation work?\n"
        "What are the main stages of lead generation?\n"
        "What are examples of lead generation strategies?\n"
        "How can businesses generate leads online?\n"
        "What is the difference between a visitor, lead, and customer?\n"
        "How do landing pages help with lead generation?\n"
        "How do forms and CTAs support lead generation?\n"
        "How can CRM software help manage leads?",
        height=140,
    )
    required_entities_text = st.text_area(
        "Required entities, one per line",
        "HubSpot\n"
        "lead generation\n"
        "inbound marketing\n"
        "CRM\n"
        "marketing automation\n"
        "sales pipeline\n"
        "lead capture\n"
        "landing page\n"
        "form\n"
        "call-to-action\n"
        "CTA\n"
        "lead nurturing\n"
        "qualified lead\n"
        "prospect\n"
        "customer\n"
        "conversion\n"
        "email marketing\n"
        "content marketing",
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
        diagnostics = []

        progress = st.progress(0)
        for index, page_context in enumerate(page_contexts, start=1):
            scrape_target = _resolve_audit_target(page_context["url"])
            try:
                scraped_page = scrape_page(scrape_target)
            except Exception as error:
                diagnostics.append(_diagnostic_row(page_context, scrape_target, "failed", "scrape_page", error))
                progress.progress(index / len(page_contexts))
                continue

            try:
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
                diagnostics.append(_diagnostic_row(page_context, scrape_target, "success", "", None))
            except Exception as error:
                diagnostics.append(_diagnostic_row(page_context, scrape_target, "failed", "audit_page", error))
            progress.progress(index / len(page_contexts))

        if not audit_results:
            st.error("No pages were successfully audited.")
            st.subheader("Per-page error diagnostics")
            st.dataframe(_diagnostics_table(diagnostics), use_container_width=True, hide_index=True)
            with st.expander("Full technical tracebacks"):
                for row in diagnostics:
                    st.write(f"### {row['url']}")
                    st.write(f"Failed stage: {row['failed_stage']}")
                    st.write(f"Likely blocker: {row['likely_blocker']}")
                    st.code(row["traceback"] or row["error_message"])
            st.stop()

        output_paths = export_site_audit_results(
            audit_results=audit_results,
            client_brief=client_brief,
            page_contexts=audited_contexts,
            output_dir=PROJECT_ROOT / "outputs",
        )
        st.session_state["last_audit_state"] = {
            "audit_results": audit_results,
            "diagnostics": diagnostics,
            "output_paths": output_paths,
        }
    except Exception as error:
        st.error(f"Audit failed: {error}")
        st.stop()

if "last_audit_state" in st.session_state:
    _render_results(st.session_state["last_audit_state"])

# PRD: AEO Retrieval Readiness Audit Tool

## 1. Product Purpose

The AEO Retrieval Readiness Audit Tool helps marketers, content strategists, and consultants evaluate whether a webpage is structured for AI systems to retrieve, understand, summarize, and potentially cite it when answering commercially relevant questions.

This is not a traditional SEO rank tracker. It does not promise that ChatGPT, Claude, Perplexity, Google AI Overviews, or any other answer engine will cite a page. Its purpose is to identify the page-level signals that make content easier for AI systems to parse, extract, trust, and reuse in generated answers.

The first version should remain a simple file-based internal/demo tool that can run locally and can also be deployed as a lightweight Streamlit demo. It should produce strategist-ready Markdown, CSV, and JSON outputs that can later be turned into client-facing reports.

## 2. Inspiration From Claude SEO

Claude SEO is useful as a product inspiration pattern only, not as current MVP scope. It is built as a Claude Code plugin/skill suite. Its public site describes it as a free, open-source terminal tool where a user runs commands such as `/seo audit <url>` and multiple AI agents analyze a site in parallel. Its repository describes a main orchestrator skill, many focused sub-skills, and multiple sub-agents for specific audit areas.

The useful product pattern for AEO is:

- One command or simple workflow launches the audit.
- A central orchestrator gathers page data, client context, questions, entities, and scoring rules.
- Focused audit modules evaluate specific dimensions.
- Findings are normalized into a common schema.
- Scores are weighted into a 0-100 health score.
- Output is a prioritized action plan, not only a raw score.

Claude SEO currently covers technical SEO, content quality, schema, AI search optimization, local SEO, maps intelligence, backlinks, semantic clustering, e-commerce SEO, international SEO, Google APIs, and optional extensions. For this AEO product, the MVP scope should remain much narrower and more specialized: answer engine retrieval-readiness, citation-readiness signals, semantic clarity, and content improvement recommendations.

## 3. Target Users

Primary users:

- Internal marketing strategists preparing AEO audits.
- Consultants reviewing client webpages for AI answer visibility potential.
- Content teams rewriting service pages, blog posts, landing pages, and guides for answer engine retrieval.

Secondary users:

- Founders and operators who want a plain-language audit of whether their content answers buyer questions clearly.
- SEO teams expanding from classic SEO into AEO, GEO, and AI citation optimization.

## 4. Problem Statement

Most webpages are written for human browsing and traditional SEO. They often include broad claims, generic headings, weak entity coverage, buried answers, missing proof, and unclear semantic relationships. These weaknesses make it harder for answer engines to identify direct answers, associate a brand with a topic, and cite a page confidently.

Users need a repeatable audit process that:

- Evaluates content against explicit AEO criteria.
- Separates deterministic findings from strategic recommendations.
- Shows exactly why a page scored well or poorly.
- Produces prioritized fixes that a strategist or writer can act on.
- Keeps assumptions inspectable instead of hiding logic in a black box.

## 5. Product Positioning

Working name:

`AEO Audit`

Positioning:

> A local AEO audit tool that scores whether a page is ready for AI retrieval, answer extraction, and citation consideration.

It should feel closer to a strategist's audit assistant than a generic SEO crawler. The product should explain the logic behind every score and translate technical findings into content actions.

## 6. Product Scope

### MVP In Scope

- Local Python application.
- File-based inputs using JSON and CSV.
- URL or local HTML page scraping.
- Deterministic page analysis.
- Weighted 0-100 AEO retrieval-readiness score.
- Dimension-level evidence and recommendations.
- Markdown report generation.
- CSV score export.
- JSON findings export.
- Optional LLM review prompt export for strategist review.
- Simple Streamlit UI and CLI flow using the existing project structure.

### MVP Out Of Scope

- Login, billing, and user accounts.
- Multi-tenant SaaS dashboard.
- Paid API integrations.
- Live rank tracking.
- Automated claims that a page will be cited by AI systems.
- Browser extension.
- Database storage.
- Full JavaScript rendering unless explicitly added later.

## 7. Core Inputs

The audit requires these inputs:

- Client brief: client name, brand name, primary topic, target market, target audience, service/category context.
- URL list: pages to audit, page type, target topic, and optional notes.
- Target questions: commercially relevant questions the page should answer.
- Required entities: brand, services, locations, regulations, people, organizations, markets, and related concepts.
- AEO scoring rubric: dimensions, weights, evidence expectations, and fix logic.
- Page content: title, metadata, headings, visible text, links, FAQ-like headings, and content signals used to infer schema-readiness and CTA/conversion alignment.

## 8. Core Audit Logic

The product should score each page across these dimensions:

| Dimension | Weight | Purpose |
| --- | ---: | --- |
| Query-answer coverage | 20 | Checks whether target questions and intents are directly covered. |
| Direct answer extractability | 15 | Checks whether answers are concise, declarative, and easy to extract. |
| Heading and content structure | 10 | Checks whether headings and sections create retrievable content blocks. |
| FAQ readiness | 10 | Checks whether common questions are represented in Q&A structures. |
| Entity clarity | 10 | Checks whether important entities are explicitly named. |
| Semantic relationship clarity | 10 | Checks whether the page explains how entities, topics, offers, proof, and outcomes relate. |
| Evidence and source support | 10 | Checks whether claims are backed by examples, sources, data, methodology, or proof. |
| Schema readiness | 5 | Checks whether structured data supports machine understanding. |
| Brand-topic association | 5 | Checks whether the brand is clearly associated with the target topic/category. |
| Conversion alignment | 5 | Checks whether the page provides a relevant next step after an AI answer-driven visit. |

Each dimension should return:

- Raw score from 0-10.
- Weighted score contribution.
- Evidence found.
- Evidence missing.
- Why the score was assigned.
- What would improve the score.
- Confidence level.
- Recommended fix.

The overall page score is the sum of weighted dimension scores.

Grades:

- A: 85-100
- B: 70-84
- C: 55-69
- D: 40-54
- F: 0-39

## 9. Scoring Philosophy

The tool should evaluate retrieval-readiness and citation-readiness signals, not generic SEO performance.

Rules:

- Scores must be explainable.
- Recommendations must be practical.
- AEO claims must be cautious.
- Deterministic findings must be separate from strategist or LLM interpretation.
- Every output should preserve evidence so a human can review it.
- The tool should identify missing answer opportunities, not merely count keywords.

The product should never state:

> This page will rank in AI search.

It may state:

> This page has stronger answer extraction, entity clarity, and evidence signals than before.

## 10. User Workflow

1. User prepares input files.
2. User runs the audit from the Streamlit UI or CLI.
3. System loads client context, URL list, target questions, required entities, and rubric.
4. System scrapes each URL or local HTML file.
5. System extracts page signals: metadata, headings, text, links, FAQ-like headings, and proxy signals for schema-readiness and CTA/conversion alignment.
6. System scores each AEO dimension.
7. System generates page-level findings.
8. System aggregates site-level summary scores.
9. System exports reports and review files.
10. User reviews the recommendations and turns them into client-facing action items.

## 11. Functional Requirements

### Input Management

- The system must load client brief from JSON.
- The system must load target URLs from CSV.
- The system must load target questions from CSV.
- The system must load required entities from CSV.
- The system must load the scoring rubric from JSON.
- The CLI input loaders must validate missing required fields before running an audit.
- The Streamlit UI must validate that at least one page, one target question, and one required entity were provided before running an audit.

### Page Extraction

- The system must support local HTML files for offline demos.
- The system must support HTTP/HTTPS URLs where accessible.
- The system must extract page title and metadata.
- The system must extract H1/H2/H3 headings.
- The system must extract body text.
- The system must extract links.
- The system should eventually detect schema where possible.
- Current MVP schema-readiness scoring is proxy-based and uses visible structure, FAQ-like headings, service/article-like content, and metadata rather than full structured-data validation.
- The system must detect FAQ-like or question-style headings.

### Scoring

- The system must score all ten AEO dimensions.
- The system must calculate weighted scores from rubric weights.
- The system must generate an overall score out of 100.
- The system must assign a letter grade.
- The system must preserve evidence for every score.
- The system must produce confidence levels for findings.

### Recommendations

- The system must identify top strengths.
- The system must identify top weaknesses.
- The system must generate prioritized recommendations.
- Recommendations must be written as content actions, not abstract theory.
- Recommendations must reflect page context, target topic, target audience, and missing entities/questions.

### Outputs

- The system must generate page-level Markdown reports.
- The system must generate a site summary Markdown report.
- The system must generate CSV score tables.
- The system must generate JSON findings.
- The one-page export flow should generate an LLM review prompt that a strategist can paste into a model for second-pass interpretation.
- Multi-page LLM review prompt generation is a future improvement; current multi-page outputs focus on page reports, site summary, CSV scores, JSON findings, and run comparison.

Current multi-page output files:

- `outputs/site_summary.md`
- `outputs/all_scores.csv`
- `outputs/all_findings.json`
- `outputs/page_audits/*.md`
- `outputs/runs/YYYY-MM-DD*/`
- `outputs/monitoring_comparison.md`

## 12. Non-Functional Requirements

- Must run locally.
- Must be simple to inspect and modify.
- Must avoid unnecessary dependencies.
- Must not require paid APIs for MVP.
- Must not store confidential client data in external services.
- Must be deterministic enough that repeated runs on the same input produce comparable results.
- Must include caveats that scores are proxy signals, not guarantees of AI visibility.

## 13. Product Architecture

Recommended architecture:

```text
app.py                              # Streamlit entrypoint
src/main.py                         # CLI entrypoint
src/load_inputs.py                  # JSON/CSV loading and validation
src/scrape_page.py                  # Page fetching and parsing
src/audit_engine.py                 # AEO scoring logic
src/generate_report.py              # Markdown report generation
src/export_results.py               # CSV/JSON/Markdown export
src/compare_runs.py                 # Optional before/after comparison
config/aeo_scoring_rubric.json      # Editable scoring rubric
inputs/                             # Demo/client input files
outputs/                            # Generated audit files
prompts/                            # LLM review prompt templates
```

Future Claude SEO-style architecture (not current MVP scope):

```text
aeo/                                # Main orchestrator
aeo-query-answer/                   # Query-answer coverage module
aeo-extractability/                 # Direct answer extraction module
aeo-entities/                       # Entity clarity module
aeo-evidence/                       # Source/evidence module
aeo-schema/                         # Schema readiness module
aeo-reporting/                      # Report generation module
```

The MVP can stay modular Python. If the product later becomes a Codex or Claude Code skill/plugin, each AEO dimension can become a focused skill or agent.

## 14. AEO Command Model

If adapted into a Claude SEO-style command tool, the command surface could be:

```text
/aeo audit <url>              # Full page or site audit
/aeo page <url>               # Single-page AEO audit
/aeo questions <url>          # Target-question coverage audit
/aeo entities <url>           # Entity and semantic clarity audit
/aeo extract <url>            # Direct-answer extractability audit
/aeo evidence <url>           # Evidence and source support audit
/aeo schema <url>             # Structured data audit for AEO
/aeo compare <run-a> <run-b>  # Before/after score comparison
/aeo report                   # Generate strategist-ready report
```

For the current MVP, these can remain internal functions or Streamlit actions rather than literal slash commands.

## 15. Success Metrics

MVP success:

- A strategist can audit 3-10 pages in one run.
- Reports clearly explain why each score was assigned.
- Recommendations are specific enough for a writer to implement.
- The user can compare page strengths and weaknesses across the site.
- The output reduces manual audit preparation time.

Quality metrics:

- 100% of dimensions produce evidence-backed findings.
- 100% of reports include caveats about AI citation uncertainty.
- Top recommendations map to actual missing questions, missing entities, weak headings, unsupported claims, or weak CTAs.
- Non-technical users can understand the report without reading code.

## 16. Risks And Guardrails

Risk: Users may overinterpret AEO scores as guaranteed AI visibility.

Guardrail: Every report must state that the audit measures proxy signals and does not guarantee citation.

Risk: Keyword matching may miss semantically equivalent answers.

Guardrail: Keep deterministic scores inspectable and provide optional LLM review prompts for strategist validation.

Risk: Client-only JavaScript pages may appear empty.

Guardrail: Document the limitation and consider Playwright/browser-rendered fetching in a later version.

Risk: Recommendations may become generic.

Guardrail: Tie recommendations to missing questions, missing entities, weak evidence, and page-specific findings.

## 17. Future Enhancements

- Browser-rendered crawling with Playwright.
- LLM-assisted semantic scoring with deterministic evidence retained.
- Run comparison and score trend history.
- Client-facing PDF export.
- AEO content brief generation.
- Schema generation recommendations.
- llms.txt and crawler access checks.
- AI answer simulation for target questions.
- Source/citation monitoring across answer engines.
- Integration with Google Search Console, PageSpeed Insights, or DataForSEO.
- Codex/Claude Code skill packaging with `/aeo` commands.

## 18. Source Notes

This PRD is based on public Claude SEO product and repository information reviewed on May 13, 2026, plus the existing local `aeo-audit-mvp` project.

Useful references:

- Claude SEO public site: https://claude-seo.md/
- Claude SEO GitHub repository: https://github.com/AgriciDaniel/claude-seo
- Local rubric: `config/aeo_scoring_rubric.json`
- Local project instructions: `AGENTS.md`

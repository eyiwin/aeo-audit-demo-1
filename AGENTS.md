# Internal AEO Retrieval Readiness Audit MVP

## Project Purpose

This project is an internal marketing audit tool, not a SaaS product.

Its purpose is to audit whether a webpage or article is structured well enough for AI systems to retrieve, understand, summarize, and potentially cite it when answering commercially relevant questions.

The tool must judge content using explicit AEO parameters, not generic SEO assumptions.

## Guardrails

- Do not build a dashboard yet.
- Do not build user login.
- Do not build billing.
- Do not build a frontend unless explicitly requested later.
- Do not connect paid APIs yet.
- Do not overengineer.
- Use Python.
- Keep the project local and file-based.
- Use JSON and CSV input files.
- Generate Markdown, CSV, and JSON outputs.

## Required Audit Inputs

The audit must use:

1. Client context
2. URL/page context
3. Target topic
4. Target market
5. Target audience
6. Target questions
7. Required entities
8. AEO retrieval-readiness scoring rubric

## AEO Audit Dimensions

Score content using these explicit AEO dimensions:

- Query-answer coverage
- Direct answer extractability
- Heading and content structure
- FAQ readiness
- Entity clarity
- Semantic relationship clarity
- Evidence and source support
- Schema readiness
- Brand-topic association
- Conversion alignment

## Scoring Principles

- Evaluate retrieval-readiness and citation-readiness, not generic SEO performance.
- Do not claim that a page will definitely be cited by AI systems.
- Separate deterministic findings from strategist recommendations.
- Prefer practical content fixes over abstract AEO theory.
- Keep all scoring logic, inputs, and outputs inspectable and editable.

## Output Expectations

Outputs should be useful for a marketing strategist preparing an internal audit and later a client-facing report.

Generate:

- Markdown audit reports
- CSV score tables
- JSON findings files

## Implementation Style

- Keep code simple, readable, and modular.
- Prefer small Python functions over clever abstractions.
- Avoid new dependencies unless clearly necessary.
- Ask before adding databases, frontend frameworks, paid APIs, or external integrations.

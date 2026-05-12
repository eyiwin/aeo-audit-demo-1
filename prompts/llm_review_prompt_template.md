# LLM Review Prompt: AEO Retrieval Readiness

Use this as a manual review prompt only. Do not call a paid API automatically.

You are reviewing a deterministic AEO retrieval-readiness audit. Evaluate whether the page is structured well enough for AI systems to retrieve, understand, summarize, and potentially cite. Do not make guaranteed citation claims.

## Client Brief

{{client_brief}}

## URL / Page Context

{{page_context}}

## Target Topic

{{target_topic}}

## Target Audience

{{target_audience}}

## Business Goal

{{business_goal}}

## Target Questions

{{target_questions}}

## Required Entities

{{required_entities}}

## Extracted Page Summary

{{page_summary}}

## Deterministic Audit Scores

{{audit_scores}}

## Key Weaknesses Found

{{key_weaknesses}}

## Review Tasks

Please evaluate:

1. Whether the page answers the right questions
2. Whether answers are direct and extractable
3. Whether the content is suitable for AI-generated answers
4. Whether important entities and relationships are clear
5. Whether the page has enough trust/evidence signals
6. Whether FAQ/schema opportunities exist
7. What content blocks should be added
8. What the client-facing summary should say

Return practical content recommendations for a marketing strategist. Keep deterministic evidence separate from judgment-based suggestions.

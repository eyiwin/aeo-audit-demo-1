"""Fetch a page and extract readable content for the audit."""

from __future__ import annotations

from pathlib import Path

import requests
from bs4 import BeautifulSoup


def _clean_text(value: str) -> str:
    """Normalize whitespace in extracted text."""
    return " ".join(value.split())


def scrape_page(url: str, timeout: int = 20) -> dict:
    """Fetch a URL and return structured page content."""
    local_path = Path(url)
    if local_path.exists():
        html = local_path.read_text(encoding="utf-8")
        status_code = None
    else:
        try:
            response = requests.get(
                url,
                timeout=timeout,
                headers={"User-Agent": "AEO-Retrieval-Readiness-MVP/0.1"},
            )
            response.raise_for_status()
        except requests.RequestException as error:
            raise RuntimeError(f"Could not fetch URL: {url}. Reason: {error}") from error
        html = response.text
        status_code = response.status_code

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    title = _clean_text(soup.title.get_text(" ")) if soup.title else ""

    meta_description = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"):
        meta_description = _clean_text(meta_tag["content"])

    headings = []
    for tag in soup.find_all(["h1", "h2", "h3"]):
        text = _clean_text(tag.get_text(" "))
        if text:
            headings.append({"level": tag.name, "text": text})

    links = []
    for tag in soup.find_all("a"):
        href = (tag.get("href") or "").strip()
        text = _clean_text(tag.get_text(" "))
        if href or text:
            links.append({"text": text, "href": href})

    readable_text = _clean_text(soup.get_text(" "))
    faq_like_headings = [
        heading
        for heading in headings
        if "?" in heading["text"]
        or heading["text"].lower().startswith(("what ", "why ", "how ", "when ", "where ", "who ", "can ", "do "))
    ]

    return {
        "url": url,
        "title": title,
        "meta_description": meta_description,
        "headings": headings,
        "links": links,
        "faq_like_headings": faq_like_headings,
        "has_faq_like_headings": bool(faq_like_headings),
        "text": readable_text,
        "text_length": len(readable_text),
        "html_length": len(html),
        "status_code": status_code,
    }

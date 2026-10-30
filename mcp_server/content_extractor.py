"""Article full-text content extractor with fallback cleaning."""

import logging
import httpx
import trafilatura
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


async def extract_article_content(url: str, timeout: float = 12.0) -> str:
    """Fetch and clean full text from a URL.
    
    Uses trafilatura as primary extractor (removes ads, boilerplate, navigation).
    Falls back to BeautifulSoup text extraction if trafilatura returns empty.
    """
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
        }
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text

        # 1. Try trafilatura
        extracted = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            no_fallback=False
        )
        if extracted and len(extracted.strip()) > 80:
            return extracted.strip()

        # 2. Fallback to BeautifulSoup cleaning
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "noscript", "svg"]):
            tag.decompose()

        # Try to find common article containers
        article_elem = soup.find("article") or soup.find("main") or soup.find(class_=lambda c: c and "article" in c.lower())
        target = article_elem if article_elem else soup.body or soup

        paragraphs = [p.get_text(strip=True) for p in target.find_all("p") if len(p.get_text(strip=True)) > 20]
        if paragraphs:
            return "\n\n".join(paragraphs)

        fallback_text = target.get_text(separator="\n", strip=True)
        return fallback_text[:4000] if fallback_text else "No content could be extracted from this article."

    except Exception as exc:
        logger.warning(f"Failed to extract content from {url}: {exc}")
        return f"Error extracting article content: {exc}"


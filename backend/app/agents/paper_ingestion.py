"""
Paper Ingestion Agent
Fetches paper metadata + full text from arXiv given an arXiv ID or URL.
"""
import re
import httpx
import feedparser
from bs4 import BeautifulSoup


def extract_arxiv_id(query: str) -> str:
    """Extract arXiv ID from a URL or raw ID string."""
    query = query.strip()
    # Match patterns like 2310.06825 or arxiv.org/abs/2310.06825
    match = re.search(r'(\d{4}\.\d{4,5})(v\d+)?', query)
    if match:
        return match.group(1)
    raise ValueError(f"Could not extract arXiv ID from: {query}")


HEADERS = {"User-Agent": "Mozilla/5.0 (Reproducibility-Checker/1.0; research tool)"}


async def fetch_arxiv_metadata(arxiv_id: str) -> dict:
    """Fetch title, abstract, authors, categories from arXiv API."""
    url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=30, headers=HEADERS, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code == 429:
                    import asyncio
                    wait = (attempt + 1) * 5
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                break
        except httpx.HTTPStatusError as e:
            if attempt < 2:
                import asyncio
                await asyncio.sleep((attempt + 1) * 5)
                continue
            raise
    
    feed = feedparser.parse(resp.text)
    if not feed.entries:
        raise ValueError(f"No paper found for arXiv ID: {arxiv_id}")

    entry = feed.entries[0]
    return {
        "arxiv_id": arxiv_id,
        "title": entry.title.replace("\n", " ").strip(),
        "abstract": entry.summary.replace("\n", " ").strip(),
        "authors": [a.name for a in entry.authors],
        "published": entry.published,
        "categories": [t["term"] for t in entry.tags] if "tags" in entry else [],
        "pdf_url": next(
            (l.href for l in entry.links if l.type == "application/pdf"),
            f"https://arxiv.org/pdf/{arxiv_id}"
        ),
        "abs_url": f"https://arxiv.org/abs/{arxiv_id}",
        "is_arxiv": True,
    }


async def fetch_pdf_fulltext(pdf_url: str) -> str | None:
    """Fallback: download the PDF and extract text directly."""
    try:
        import io
        from pypdf import PdfReader

        async with httpx.AsyncClient(timeout=60, follow_redirects=True, headers=HEADERS) as client:
            resp = await client.get(pdf_url)
            if resp.status_code != 200:
                return None
            reader = PdfReader(io.BytesIO(resp.content))
            text_parts = []
            for page in reader.pages[:40]:  # cap pages for very long papers
                text_parts.append(page.extract_text() or "")
            text = "\n".join(text_parts)
            text = re.sub(r'\n\s*\n+', '\n\n', text)
            if len(text) > 1000:
                return text[:60000]
    except Exception:
        return None
    return None


async def fetch_html_fulltext(arxiv_id: str) -> str | None:
    """
    Try to fetch the arXiv HTML version (ar5iv mirror) for full text.
    Returns None if unavailable — caller should fall back to PDF extraction or abstract-only.
    """
    urls_to_try = [
        f"https://ar5iv.labs.arxiv.org/html/{arxiv_id}",
        f"https://arxiv.org/html/{arxiv_id}",
    ]
    async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers=HEADERS) as client:
        for url in urls_to_try:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    # Remove nav/footer/script noise
                    for tag in soup(["script", "style", "nav", "footer"]):
                        tag.decompose()
                    text = soup.get_text(separator="\n")
                    # Collapse excessive whitespace
                    text = re.sub(r'\n\s*\n+', '\n\n', text)
                    if len(text) > 1000:
                        return text[:60000]  # cap for token limits
            except Exception:
                continue
    return None


async def ingest_paper(query: str) -> dict:
    """Main entrypoint: given an arXiv URL/ID, return metadata + full text (if available)."""
    arxiv_id = extract_arxiv_id(query)
    metadata = await fetch_arxiv_metadata(arxiv_id)

    # Try ar5iv HTML first (cleanest), then fall back to PDF extraction
    fulltext = await fetch_html_fulltext(arxiv_id)
    source = "ar5iv_html" if fulltext else None

    if not fulltext:
        fulltext = await fetch_pdf_fulltext(metadata["pdf_url"])
        source = "pdf_extraction" if fulltext else None

    metadata["fulltext_available"] = fulltext is not None
    metadata["fulltext_source"] = source or "abstract_only"
    metadata["fulltext"] = fulltext or metadata["abstract"]
    return metadata


def is_arxiv_query(query: str) -> bool:
    """Check if a query string looks like an arXiv ID or arXiv URL."""
    query = query.strip()
    if "arxiv.org" in query.lower():
        return True
    return bool(re.fullmatch(r'\d{4}\.\d{4,5}(v\d+)?', query))


async def ingest_generic_pdf_url(url: str) -> dict:
    """
    Ingest a non-arXiv paper from a direct PDF URL.
    No structured metadata (authors/abstract) is available, so the LLM
    extraction agents will derive title/abstract from the fulltext itself.
    """
    fulltext = await fetch_pdf_fulltext(url)
    if not fulltext:
        raise ValueError(
            "Could not extract text from this PDF URL. "
            "Make sure the link points directly to a PDF file."
        )

    # Use a hash of the URL as a stable cache key for non-arXiv papers
    import hashlib
    pseudo_id = "ext_" + hashlib.sha256(url.encode()).hexdigest()[:16]

    return {
        "arxiv_id": pseudo_id,
        "title": None,        # to be filled in by extraction agent from fulltext
        "abstract": None,      # to be filled in by extraction agent from fulltext
        "authors": [],
        "published": None,
        "categories": [],
        "pdf_url": url,
        "abs_url": url,
        "fulltext_available": True,
        "fulltext_source": "pdf_extraction",
        "fulltext": fulltext,
        "is_arxiv": False,
    }


async def ingest_uploaded_pdf(file_bytes: bytes) -> dict:
    """
    Ingest a non-arXiv paper from raw uploaded PDF bytes.
    """
    import io
    import hashlib
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(file_bytes))
    text_parts = [p.extract_text() or "" for p in reader.pages[:40]]
    text = "\n".join(text_parts)
    text = re.sub(r'\n\s*\n+', '\n\n', text)

    if len(text) < 500:
        raise ValueError("Could not extract enough text from this PDF. It may be a scanned/image-only PDF.")

    pseudo_id = "upload_" + hashlib.sha256(file_bytes).hexdigest()[:16]

    return {
        "arxiv_id": pseudo_id,
        "title": None,
        "abstract": None,
        "authors": [],
        "published": None,
        "categories": [],
        "pdf_url": None,
        "abs_url": None,
        "fulltext_available": True,
        "fulltext_source": "pdf_upload",
        "fulltext": text[:60000],
        "is_arxiv": False,
    }

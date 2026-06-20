"""
Orchestrator: runs the full multi-agent pipeline for a given paper.
Supports: arXiv ID/URL, generic PDF URL, or uploaded PDF bytes.
"""
import asyncio
from app.agents.paper_ingestion import (
    ingest_paper, ingest_generic_pdf_url, ingest_uploaded_pdf, is_arxiv_query
)
from app.agents.extraction import extract_methodology, extract_claims, extract_title_abstract, validate_is_research_paper
from app.agents.code_discovery import discover_code
from app.agents.plausibility import check_plausibility
from app.agents.report import generate_report


async def run_pipeline(query: str = None, pdf_bytes: bytes = None, progress_callback=None) -> dict:
    async def emit(stage):
        if progress_callback:
            await progress_callback(stage)

    # Stage 1: Ingest
    await emit("Fetching paper...")
    if pdf_bytes is not None:
        paper = await ingest_uploaded_pdf(pdf_bytes)
    elif is_arxiv_query(query):
        paper = await ingest_paper(query)
    else:
        paper = await ingest_generic_pdf_url(query)

    # For non-arXiv papers, derive title/abstract/authors from fulltext
    if paper.get("title") is None:
        await emit("Identifying paper title and abstract...")
        ta = await extract_title_abstract(paper["fulltext"])
        paper["title"] = ta.get("title", "Untitled")
        paper["abstract"] = ta.get("abstract", "")
        paper["authors"] = ta.get("authors", [])

    # Validate this is actually a research paper before running the full pipeline
    await emit("Validating document...")
    is_paper, reason = await validate_is_research_paper(paper["fulltext"])
    if not is_paper:
        raise ValueError(
            f"This document does not appear to be a research paper. {reason} "
            "Please upload an academic paper with methodology, experiments, and results."
        )

    # Stage 2 & 3: Extract methodology and claims in parallel
    await emit("Extracting methodology and claims...")
    methodology, claims = await asyncio.gather(
        extract_methodology(paper["fulltext"]),
        extract_claims(paper["fulltext"]),
    )

    # Stage 4: Discover code
    await emit("Searching for code implementations...")
    code_info = await discover_code(paper["title"], paper["arxiv_id"])

    # Stage 5: Plausibility check
    await emit("Running plausibility & reproducibility checks...")
    issues = await check_plausibility(methodology, claims, code_info)

    # Stage 6: Final report
    await emit("Generating final report...")
    report = await generate_report(
        paper["title"], paper["abstract"], methodology, claims, code_info, issues
    )

    await emit("Done.")

    return {
        "paper": {
            "title": paper["title"],
            "abstract": paper["abstract"],
            "authors": paper["authors"],
            "arxiv_id": paper["arxiv_id"],
            "abs_url": paper.get("abs_url"),
            "fulltext_available": paper["fulltext_available"],
            "fulltext_source": paper.get("fulltext_source", "unknown"),
            "is_arxiv": paper.get("is_arxiv", True),
        },
        "methodology": methodology,
        "claims": claims,
        "code_info": code_info,
        "plausibility": issues,
        "report": report,
    }
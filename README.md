# Multi-Agent Research Reproducibility Checker

An agentic system that audits ML papers for reproducibility issues. It accepts **arXiv links/IDs, any direct PDF URL, or uploaded PDF files**, extracts methodology and claims, searches for code implementations, and runs a critical plausibility check (data leakage risk, missing baselines, statistical rigor, etc.), producing a structured audit report.
- **Link**: https://research-reproducibility-checker.vercel.app  

## Supported Inputs
- **arXiv**: paste a link (`https://arxiv.org/abs/2310.06825`) or bare ID (`2310.06825`) — uses arXiv API for clean metadata + ar5iv HTML for full text (falls back to PDF extraction if ar5iv is unavailable).
- **Any direct PDF URL**: paste a link ending in a PDF (e.g. an OpenReview, conference, or personal-site PDF) — title/abstract/authors are derived by the LLM from the extracted text.
- **PDF upload**: click "Upload PDF" for papers with no public URL.

**Pipeline (6 agents):**
1. **Paper Ingestion** — fetches metadata + full text from arXiv (via ar5iv HTML mirror)
2. **Methodology Extraction** — LLM extracts datasets, models, training setup, baselines, metrics
3. **Claims Extraction** — LLM extracts quantitative claims (metric, value, dataset, method)
4. **Code Discovery** — searches GitHub + Papers With Code for implementations
5. **Plausibility Checker** — critical LLM analysis flagging reproducibility red flags with severity ratings
6. **Report Generator** — synthesizes everything into an executive summary + verdict

100% free stack: Groq API (free LLM inference), arXiv API, GitHub API, Papers With Code API, SQLite cache.

---
## How It Works (for your portfolio/interviews)

- **Agentic architecture**: each stage is an independent async function with a clear single responsibility, orchestrated by `orchestrator.py`. Methodology and claims extraction run in parallel via `asyncio.gather`.
- **Streaming progress**: the frontend connects via WebSocket (`/ws/analyze`) so users see live progress ("Extracting methodology...", "Searching for code...", etc.) instead of a blank loading screen.
- **Caching**: results are cached in SQLite by arXiv ID, so repeat lookups are instant and don't burn API quota.
- **Structured LLM outputs**: every agent prompts the LLM to return strict JSON, validated and parsed — this is what lets the frontend render tables, badges, and scores reliably.
- **Grounded plausibility checks**: the plausibility agent is given the *extracted* methodology/claims/code-availability data (not the raw paper) and asked to reason over specific red-flag categories — data leakage, missing baselines, statistical rigor, compute transparency, dataset/code availability, implausible results.

---




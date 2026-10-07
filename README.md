# Multi-Agent Research Reproducibility Checker

An agentic system that audits ML research papers for reproducibility issues. It accepts **arXiv links/IDs, any direct PDF URL, or uploaded PDF files**, extracts methodology and claims, searches for code implementations, and runs a critical plausibility check (data leakage risk, missing baselines, statistical rigor, etc.), producing a structured audit report.

**Live Demo:** https://research-reproducibility-checker.vercel.app

## Supported Inputs
- **arXiv**: paste a link (`https://arxiv.org/abs/2310.06825`) or bare ID (`2310.06825`) — uses arXiv API for clean metadata + ar5iv HTML for full text (falls back to PDF extraction if ar5iv unavailable).
- **Any direct PDF URL**: paste a link ending in a PDF (e.g. OpenReview, conference site) — title/abstract/authors derived by LLM from extracted text.
- **PDF upload**: click "Upload PDF" for papers with no public URL.

## Pipeline (7 agents)
1. **Paper Ingestion** — fetches metadata + full text from arXiv (ar5iv HTML → PDF extraction → abstract fallback)
2. **Document Validation** — two-stage check: heuristic pre-filter (word count, keyword signals, essay detection) + LLM classifier to reject non-research uploads before running the expensive pipeline
3. **Methodology Extraction** — LLM extracts datasets, models, training setup, baselines, metrics
4. **Claims Extraction** — LLM extracts quantitative claims (metric, value, dataset, method); runs in parallel with methodology extraction
5. **Code Discovery** — searches GitHub + Papers With Code for official and community implementations
6. **Plausibility Checker** — critical LLM analysis flagging reproducibility red flags with severity ratings (high/medium/low)
7. **Report Generator** — synthesizes everything into an executive summary + reproducibility verdict

**Stack:** Python, FastAPI, Groq API (GPT-OSS 120B / 20B), arXiv API, GitHub API, Papers With Code API, React, Vite, Tailwind CSS, SQLite, Render, Vercel

---

## How It Works

- **Agentic architecture**: each stage is an independent async function with a clear single responsibility, orchestrated by `orchestrator.py`. Methodology and claims extraction run in parallel via `asyncio.gather`.
- **Caching**: results are cached in SQLite by arXiv ID/URL hash, so repeat lookups are instant and don't burn API quota.
- **Robust JSON parsing**: every agent prompts the LLM to return strict JSON. A three-stage parse recovery pipeline (direct parse → strip markdown fences → extract last balanced `{}` block) handles model quirks reliably.
- **Rate limit handling**: automatic retry with exponential backoff on 429 errors — pipeline recovers silently without surfacing errors to the user.
- **Grounded plausibility checks**: the plausibility agent receives the *extracted* methodology/claims/code data (not raw paper text) and reasons over 7 specific red-flag categories — data leakage, missing baselines, statistical rigor, compute transparency, dataset availability, code availability, implausible results.
- **Document validation**: two-stage guard before the pipeline runs — cheap heuristic filter first (no LLM cost), then LLM classifier only if heuristic passes. Rejects essays, resumes, and non-research PDFs with a clear error message.

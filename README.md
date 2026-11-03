# Multi-Agent Research Reproducibility Checker

An agentic system that audits machine-learning research papers for reproducibility concerns. It accepts **arXiv links/IDs, direct PDF URLs, and uploaded PDF files**, extracts methodology and quantitative claims, searches for code implementations, and performs a critical plausibility review for issues such as data leakage, missing baselines, weak statistical reporting, and unclear compute details.

**Live Demo:** https://research-reproducibility-checker.vercel.app

## What It Does

The checker transforms research papers into structured reproducibility audit reports containing:

- Executive summary and reproducibility assessment.
- Extracted methodology, datasets, models, training configurations, baselines, and metrics.
- Structured quantitative research claims.
- Candidate official and community code implementations.
- Plausibility findings with high, medium, and low severity ratings.
- An AI quality and safety screen highlighting potential risks for human review.

The system is designed as a research-assistance tool. It does not certify that a paper is reproducible or guarantee that every AI-generated finding is correct.

## Supported Inputs

- **arXiv:** Paste an arXiv URL (`https://arxiv.org/abs/2310.06825`) or a bare arXiv ID (`2310.06825`). Uses the arXiv API for metadata and ar5iv HTML for full text, with PDF extraction as a fallback and abstract-only fallback when necessary.
- **Direct PDF URL:** Paste a publicly accessible PDF link, including papers hosted on OpenReview or conference websites. When structured metadata is unavailable, title, abstract, and author information are derived from extracted text.
- **PDF Upload:** Upload a local PDF for papers without a usable public URL.

## Pipeline — Seven Main Stages

1. **Paper Ingestion** — Retrieves paper metadata and full text from arXiv or other PDF sources. Uses ar5iv HTML, PDF extraction, and abstract fallback strategies.
2. **Document Validation** — Uses a two-stage validation guard: a heuristic pre-filter based on word count and research-related signals, followed by an LLM classifier. Helps reject essays, resumes, and non-research documents before expensive analysis.
3. **Methodology Extraction** — Extracts datasets, models, training configurations, baselines, and evaluation metrics.
4. **Claims Extraction** — Extracts quantitative claims such as metric, reported value, dataset, and method. Runs concurrently with methodology extraction.
5. **Code Discovery** — Searches GitHub and Papers With Code for potential official and community implementations.
6. **Plausibility Checker** — Reviews extracted methodology, claims, and code information for reproducibility red flags, assigning severity ratings.
7. **Report Generator** — Synthesizes the analysis into an executive summary and structured reproducibility assessment.

### Plausibility Checks

The plausibility checker evaluates seven categories:

- Data leakage risks
- Missing or inadequate baselines
- Statistical rigor
- Compute transparency
- Dataset availability
- Code availability
- Implausible or suspicious results

## AI Quality and Safety Screening

A separate quality-screening layer evaluates selected aspects of the generated report. Its results are included in the backend response and displayed in the frontend through an **AI Quality & Safety Screen**.

### Checks Implemented

| Check | Description |
|---|---|
| Prompt-injection indicators | Detects suspicious instruction-like patterns in the source paper text. |
| PII category detection | Checks the generated executive summary for selected personally identifiable information patterns. |
| Summary token groundedness | Calculates lexical overlap between the generated summary and the original paper text. |
| Unsupported terms for review | Highlights terms that may require manual verification against the source. |

### Prompt-Injection-Aware Processing

The methodology extraction, plausibility analysis, and report-generation prompts instruct the model to treat paper content as untrusted data.

Embedded instructions attempting to change the model's role, reveal prompts or secrets, invoke tools, or override the analysis task are explicitly treated as content rather than instructions.

### Important Limitations

These checks are heuristic safeguards, not definitive semantic verification.

- Lexical overlap does not prove factual correctness.
- A low overlap score does not necessarily mean a summary contains hallucinations.
- Prompt-injection pattern detection may miss sophisticated attacks.
- PII detection may produce false positives or false negatives.
- Flagged content should be reviewed manually against the original paper.

The quality screen is intended to support human review, not replace it.

## Technology Stack

| Component | Technologies |
|---|---|
| Backend | Python, FastAPI |
| LLM Integration | Groq API, GPT-OSS model family |
| Paper Ingestion | arXiv API, ar5iv, PDF extraction |
| Code Discovery | GitHub API, Papers With Code API |
| Agent Orchestration | Python asynchronous functions, asyncio |
| Database and Caching | SQLite |
| Frontend | React, Vite, Tailwind CSS |
| Testing | pytest, pytest-asyncio, optional DeepEval |
| CI/CD | GitHub Actions |
| Backend Deployment | Render |
| Frontend Deployment | Vercel |

## How It Works

### Agentic Architecture

Each stage is implemented as an independent asynchronous function with a focused responsibility. The `orchestrator.py` module coordinates the complete workflow.

Methodology extraction and claims extraction run concurrently using `asyncio.gather`, reducing unnecessary sequential execution.

### Caching

Analysis results are cached in SQLite using an arXiv ID or URL-derived hash. Repeat lookups can reuse previously generated results, reducing processing time and unnecessary API calls.

### Structured JSON Parsing

Each LLM stage is prompted to return structured JSON. A three-stage recovery mechanism handles common formatting issues:

1. Direct JSON parsing.
2. Removal of Markdown code fences.
3. Recovery of a balanced JSON object.

### Rate-Limit Handling

HTTP 429 responses are handled using automatic retries with exponential backoff. This improves resilience against temporary provider rate limits, although it cannot guarantee success if the provider remains unavailable.

### Document Validation

A two-stage validation guard runs before the main analysis:

1. A low-cost heuristic filter checks word count and research-related signals.
2. An LLM classifier evaluates documents that pass the initial filter.

This helps avoid unnecessary LLM calls for documents that are unlikely to be research papers.

## Testing and Evaluation

The project includes automated backend tests, optional LLM-based evaluation, and API testing resources.

### Backend Tests

The default test suite covers API functionality and quality-screening logic.

Run the tests from the `backend` directory:

```bash
pip install -r requirements-test.txt
python -m pytest -v
```

The verified local test run completed with:

- **16 tests passed**
- **3 optional tests skipped**

The skipped tests require optional DeepEval dependencies and live LLM evaluation credentials.

### Optional DeepEval Evaluation

DeepEval is used for optional LLM-as-a-judge evaluation of generated research summaries.

Install the evaluation dependencies:

```bash
pip install -r requirements-eval.txt
```

The optional tests require:

- `RUN_LLM_EVAL=1`
- A valid `GROQ_API_KEY`

The evaluation uses a custom Groq judge wrapper with an OpenAI-compatible API endpoint.

Recorded evaluation results included:

- Positive NFTrig case: relevancy 1.0 and faithfulness 1.0.
- Negative hallucination case: faithfulness 0.6667, below the configured 0.7 threshold.

The negative case demonstrated that the evaluation could identify unsupported or contradictory information.

**Note:** Live LLM evaluations may consume API quota and encounter provider rate limits. They are intentionally excluded from the default offline CI workflow.

### Continuous Integration — GitHub Actions

A GitHub Actions workflow automatically runs backend tests on pushes and pull requests.

The workflow:

- Installs the required backend test dependencies.
- Runs the offline pytest suite.
- Validates backend changes without requiring live Groq API calls.
- Uploads the JUnit test report.

Optional DeepEval tests are skipped unless explicitly configured.

### Postman API Collection

A Postman collection is included at:

`backend/postman/Research-Reproducibility-Checker.postman_collection.json`

It includes requests for:

- `GET /` — Backend health check.
- `POST /api/analyze` — Analyze a research paper using an arXiv identifier.
- `POST /api/analyze/upload` — Validate rejection of a non-PDF upload.

The paper-analysis request may call external services and consume API quota if the result is not cached.

For more testing instructions, see [`backend/TESTING.md`](backend/TESTING.md).

## Deployment

**Frontend:** https://research-reproducibility-checker.vercel.app

**Backend:** https://research-reproducibility-checker.onrender.com

The frontend is deployed on Vercel, while the FastAPI backend runs on Render.

The backend health endpoint returns a JSON response indicating whether the API service is responding.

**Deployment note:** The Render free instance may spin down after inactivity, which can cause the first request to take 50 seconds or more while the service wakes up.

Frontend and backend deployments are independent. After merging backend changes into `main`, verify the latest Render deployment is live and test a complete paper submission through the public frontend. A successful Vercel preview alone does not confirm that the backend has been updated.

## Environment Variables and Security

- Use `backend/.env.example` and `frontend/.env.example` as templates for local configuration.
- Keep actual API keys and credentials in local environment files or deployment environment settings.
- Never commit `.env` files, API keys, access tokens, or other secrets.
- Virtual environments, Python cache files, and local evaluation artifacts are excluded through `.gitignore`.

## Future Improvements

- Semantic claim-to-source verification instead of relying primarily on lexical overlap.
- Citation-level traceability linking every finding to the relevant paper section.
- Expanded prompt-injection and PII evaluation using curated adversarial datasets.
- A labelled benchmark to measure the precision and recall of quality-screening checks.
- More comprehensive end-to-end frontend/backend testing.
- Automated deployment smoke tests and monitoring.

## License

Add the applicable license and attribution details before distributing or reusing this project.

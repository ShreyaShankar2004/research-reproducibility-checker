# Quality engineering test suite

This adds a separate quality layer without changing the existing multi-agent analysis pipeline.

## 1. Free local automation tests

From the `backend` directory (Windows PowerShell):

```powershell
python -m pip install -r requirements-test.txt
python -m pytest -v
```

The default suite is offline: the pipeline is mocked, so tests do not call Groq, arXiv, GitHub or other external services. It tests the health endpoint, API response/cache behaviour, invalid-paper errors, upload validation, common prompt-injection indicators, PII patterns, lexical grounding and unsupported terms.

## 2. Optional DeepEval LLM evaluation

DeepEval is an open-source LLM evaluation framework. The optional test uses `AnswerRelevancyMetric` and `FaithfulnessMetric` with Groq's OpenAI-compatible endpoint as the judge. Install separately:

```powershell
python -m pip install -r requirements-eval.txt
$env:GROQ_API_KEY="your-existing-groq-key"
$env:RUN_LLM_EVAL="1"
python -m pytest evaluation/test_deepeval.py -v
```

This makes live judge-model API calls and may consume Groq quota. It is intentionally skipped in the normal test run. If the configured model is unavailable to your Groq account, set `DEEPEVAL_JUDGE_MODEL` to a model your account supports. Never commit API keys or `.env` files.

## 3. Safety and grounding

`app/quality_checks.py` screens for common prompt-injection phrases, common PII formats (email, Indian mobile number, PAN-like and Aadhaar-like values), lexical evidence overlap and answer terms absent from evidence. These are heuristics only: they cannot prove the absence of prompt injection, PII or hallucinations. DeepEval's faithfulness metric adds semantic LLM-judge evaluation, but it is not a formal guarantee either.

## 4. REST API testing with Postman

Import `postman/Research-Reproducibility-Checker.postman_collection.json` into Postman. Start the backend:

```powershell
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Keep `baseUrl` as `http://localhost:8000`. Run **Health check** first. The Analyze request invokes the actual pipeline and can consume Groq quota if the paper is not cached. For the upload test, select a non-PDF file to verify the 400 response.

## 5. Coverage boundaries

- Pytest automation framework: reusable API tests, fixtures, deterministic quality checks and repeatable execution.
- DeepEval: optional LLM-as-a-judge evaluation for answer relevancy and faithfulness.
- REST/Postman: importable API collection with assertions.
- Browser automation (Playwright/Selenium): not included. Do not claim hands-on web automation from this suite.

## 6. JUnit report

```powershell
New-Item -ItemType Directory -Force reports
python -m pytest -v --junitxml=reports/junit.xml
```

### Evaluate a real saved project output

Save one of your generated agent/report outputs and the corresponding source-paper excerpts in a JSON file with `input`, `actual_output` and `retrieval_context` fields (the context must contain excerpts actually used to support the answer). Then run:

```powershell
$env:GROQ_API_KEY="your-existing-groq-key"
python evaluation/run_eval.py path\to\evaluation-input.json
```

This runs DeepEval against your own output rather than only the bundled demonstration case. The judge call uses your Groq quota.

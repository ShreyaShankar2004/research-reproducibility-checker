"""
Methodology & Claims Extraction Agent
Uses LLM to extract structured methodology details and falsifiable claims from paper text.
"""
import re
from app.llm_client import llm_json_call, MODEL_FAST


VALIDATION_PROMPT = """Is the following document a scientific research paper with experiments and numeric results? Reply with only this JSON, nothing else:
{{"is_research_paper": true, "reason": "one sentence"}}
or
{{"is_research_paper": false, "reason": "one sentence"}}

DOCUMENT:
{content}
"""

METHODOLOGY_PROMPT = """You are a meticulous ML research auditor. Read the following paper content and extract its METHODOLOGY in structured form.

Extract:
1. Datasets used (name, size if mentioned, source/availability)
2. Models/architectures used (name, key hyperparameters if mentioned)
3. Training setup (compute, epochs, batch size, optimizer, hardware if mentioned)
4. Baselines compared against
5. Evaluation metrics used
6. Train/test/validation split methodology

For datasets, models, baselines, and metrics, list at most 5 of the most important/prominent ones each.

Respond with ONLY a single JSON object and nothing else — no explanation, no preamble, no markdown formatting. Output must start with {{ and end with }}.

Return ONLY valid JSON with this exact structure:
{{
  "datasets": [{{"name": "...", "size": "...", "availability": "public/private/unclear"}}],
  "models": [{{"name": "...", "key_hyperparams": "..."}}],
  "training_setup": {{"compute": "...", "epochs": "...", "optimizer": "...", "hardware": "..."}},
  "baselines": ["..."],
  "metrics": ["..."],
  "split_methodology": "..."
}}

If information is not mentioned, use "not specified".

PAPER CONTENT:
{content}
"""

CLAIMS_PROMPT = """You are a meticulous ML research auditor. Read the following paper content and extract the paper's KEY QUANTITATIVE CLAIMS - specific, falsifiable, numeric results the paper claims to have achieved.

For each claim, extract:
1. The metric (e.g., "accuracy", "F1-score", "BLEU")
2. The reported value
3. The dataset/benchmark it was measured on
4. The model/method that achieved it
5. Any comparison claim (e.g., "outperforms X by Y%")

Extract at most the 6 MOST IMPORTANT quantitative claims (prioritize headline/main results over exhaustive ablation tables).

Respond with ONLY a single JSON object and nothing else — no explanation, no preamble, no markdown formatting. Output must start with {{ and end with }}.

Return ONLY valid JSON with this exact structure:
{{
  "claims": [
    {{
      "metric": "...",
      "value": "...",
      "dataset": "...",
      "method": "...",
      "comparison": "..."
    }}
  ],
  "headline_claim": "one sentence summary of the paper's single biggest claimed result"
}}

PAPER CONTENT:
{content}
"""

TITLE_ABSTRACT_PROMPT = """The text below is raw extracted text from the first page(s) of a research paper PDF. It may contain figure captions, broken line wrapping, or repeated content from PDF extraction artifacts — ignore all of that.

Identify the paper's actual title, its abstract (or write a 2-4 sentence summary of its core contribution if no abstract section exists), and its author names.

Respond with ONLY a single JSON object and nothing else — no explanation, no preamble, no markdown formatting, no repeating the input text. Output must start with {{ and end with }}.

{{
  "title": "...",
  "abstract": "...",
  "authors": ["..."]
}}

RAW TEXT:
{content}
"""


def _heuristic_check(content: str) -> tuple[bool, str]:
    text_lower = content.lower()
    word_count = len(content.split())

    if word_count < 500:
        return False, "Document is too short to be a research paper."

    numbers = re.findall(
        r'\b\d+\.?\d*\s*%|\b\d+\.?\d*\s*(accuracy|f1|bleu|rouge|score|loss)',
        text_lower
    )
    has_numbers = len(numbers) > 0

    research_keywords = [
        'abstract', 'introduction', 'methodology', 'experiment',
        'results', 'conclusion', 'references', 'dataset', 'baseline',
        'accuracy', 'model', 'training', 'evaluation', 'proposed'
    ]
    keyword_hits = sum(1 for kw in research_keywords if kw in text_lower)

    essay_signals = [
        'the play', 'the novel', 'the poem', 'the author writes',
        'shakespeare', 'literary', 'protagonist', 'narrative',
        'thesis statement', 'body paragraph', 'in conclusion,',
        'bernard shaw', 'pygmalion', 'character analysis'
    ]
    essay_hits = sum(1 for sig in essay_signals if sig in text_lower)

    if essay_hits >= 2:
        return False, "Document appears to be a literary essay or humanities critique, not a scientific paper."

    if keyword_hits < 4 and not has_numbers:
        return False, "Document lacks the structural elements and quantitative content expected in a research paper."

    return True, "Passed heuristic check."


async def validate_is_research_paper(content: str) -> tuple[bool, str]:
    passed, reason = _heuristic_check(content)
    if not passed:
        return False, reason

    prompt = VALIDATION_PROMPT.format(content=content[:2000])
    try:
        result = await llm_json_call(prompt, model=MODEL_FAST, temperature=0.0, max_tokens=60)
        is_paper = result.get("is_research_paper", False)
        reason = result.get("reason", "")
        return is_paper, reason
    except Exception:
        return True, "Heuristic passed"


async def extract_title_abstract(content: str) -> dict:
    prompt = TITLE_ABSTRACT_PROMPT.format(content=content[:4000])
    return await llm_json_call(prompt, model=MODEL_FAST, temperature=0.1, max_tokens=500)


async def extract_methodology(content: str) -> dict:
    prompt = METHODOLOGY_PROMPT.format(content=content[:5000])
    return await llm_json_call(prompt, model=MODEL_FAST, max_tokens=2000)


async def extract_claims(content: str) -> dict:
    prompt = CLAIMS_PROMPT.format(content=content[:5000])
    return await llm_json_call(prompt, model=MODEL_FAST, max_tokens=1500)
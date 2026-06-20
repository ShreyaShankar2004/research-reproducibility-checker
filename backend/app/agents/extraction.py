"""
Methodology & Claims Extraction Agent
Uses LLM to extract structured methodology details and falsifiable claims from paper text.
"""
import re
from app.llm_client import llm_json_call, MODEL_FAST


VALIDATION_PROMPT = """You are a strict document classifier. Your job is to determine if a document is a SCIENTIFIC or TECHNICAL research paper.

To qualify as a research paper it MUST have ALL of the following:
1. A clear research problem or hypothesis being tested
2. An experimental methodology (data collection, model training, system design, or empirical study)
3. Quantitative results or measurable outcomes (numbers, metrics, scores, statistics)
4. References to prior scientific/technical literature

It does NOT qualify if it is:
- A literary essay, book review, or humanities critique (even if it mentions "methodology" or "analysis")
- A blog post, opinion piece, or editorial
- A resume, CV, or portfolio
- A legal, financial, or business document
- A presentation or set of slides without experimental content
- A survey or tutorial with no original experiments

Be strict. When in doubt, return false.

Respond with ONLY a single JSON object. Output must start with {{ and end with }}.

{{
  "is_research_paper": true or false,
  "reason": "one sentence explanation citing specific evidence from the text"
}}

DOCUMENT TEXT:
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
    """
    Fast pre-filter before calling LLM.
    Rejects documents that are clearly not research papers based on simple signals.
    """
    text_lower = content.lower()
    word_count = len(content.split())

    # Too short to be a paper
    if word_count < 500:
        return False, "Document is too short to be a research paper."

    # Must have at least some numeric content (results/metrics)
    numbers = re.findall(
        r'\b\d+\.?\d*\s*%|\b\d+\.?\d*\s*(accuracy|f1|bleu|rouge|score|loss)',
        text_lower
    )
    has_numbers = len(numbers) > 0

    # Check for research paper structural keywords
    research_keywords = [
        'abstract', 'introduction', 'methodology', 'experiment',
        'results', 'conclusion', 'references', 'dataset', 'baseline',
        'accuracy', 'model', 'training', 'evaluation', 'proposed'
    ]
    keyword_hits = sum(1 for kw in research_keywords if kw in text_lower)

    # Check for humanities/essay signals
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
    """
    Two-stage validation: fast heuristic first, then LLM classifier.
    Returns (is_valid, reason).
    """
    # Stage 1: cheap heuristic (no LLM call)
    passed, reason = _heuristic_check(content)
    if not passed:
        return False, reason

    # Stage 2: LLM classifier
    prompt = VALIDATION_PROMPT.format(content=content[:3000])
    result = await llm_json_call(prompt, model=MODEL_FAST, temperature=0.0, max_tokens=150)
    is_paper = result.get("is_research_paper", False)
    reason = result.get("reason", "")

    return is_paper, reason


async def extract_title_abstract(content: str) -> dict:
    """For non-arXiv papers: derive title/abstract/authors from raw text."""
    prompt = TITLE_ABSTRACT_PROMPT.format(content=content[:4000])
    return await llm_json_call(prompt, model=MODEL_FAST, temperature=0.1)


async def extract_methodology(content: str) -> dict:
    prompt = METHODOLOGY_PROMPT.format(content=content[:5000])
    return await llm_json_call(prompt, model=MODEL_FAST, max_tokens=3500)


async def extract_claims(content: str) -> dict:
    prompt = CLAIMS_PROMPT.format(content=content[:5000])
    return await llm_json_call(prompt, model=MODEL_FAST, max_tokens=3500)
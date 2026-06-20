"""
Report Generator Agent
Synthesizes all agent outputs into a final structured reproducibility report.
"""
from app.llm_client import llm_json_call, MODEL_FAST


REPORT_PROMPT = """You are writing the executive summary section of a reproducibility audit report for an ML paper.

Given the full audit data below, write:
1. A concise executive summary (3-5 sentences) of the paper's contribution and reproducibility outlook
2. A prioritized list of the TOP 3 most important things a reproducer should check/do first
3. An overall verdict: "Highly Reproducible", "Reproducible with Effort", "Significant Barriers", or "Not Reproducible"

Respond with ONLY a single JSON object and nothing else — no explanation, no preamble, no markdown formatting. Output must start with {{ and end with }}.

PAPER TITLE: {title}
PAPER ABSTRACT: {abstract}

METHODOLOGY: {methodology}
CLAIMS: {claims}
CODE INFO: {code_info}
PLAUSIBILITY ISSUES: {issues}

Return ONLY valid JSON:
{{
  "executive_summary": "...",
  "top_priorities": ["...", "...", "..."],
  "verdict": "Highly Reproducible | Reproducible with Effort | Significant Barriers | Not Reproducible"
}}
"""


async def generate_report(title: str, abstract: str, methodology: dict,
                           claims: dict, code_info: dict, issues: dict) -> dict:
    prompt = REPORT_PROMPT.format(
        title=title,
        abstract=abstract,
        methodology=str(methodology),
        claims=str(claims),
        code_info=str(code_info),
        issues=str(issues),
    )
    return await llm_json_call(prompt, model=MODEL_FAST, temperature=0.3, max_tokens=3500)
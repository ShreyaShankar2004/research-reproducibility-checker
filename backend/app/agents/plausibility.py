"""
Plausibility Checker Agent
Applies heuristic checks + LLM critical analysis to flag potential reproducibility issues.
"""
from app.llm_client import llm_json_call, MODEL_FAST


PLAUSIBILITY_PROMPT = """You are a skeptical peer reviewer specializing in detecting reproducibility issues in ML papers. You will be given:
1. The paper's methodology
2. The paper's key claims
3. Information about available code implementations

Critically analyze this paper for COMMON REPRODUCIBILITY RED FLAGS:

- **Data leakage risk**: Could train/test split methodology leak information? (e.g., temporal data not split by time, patient-level leakage in medical data, duplicate samples across splits)
- **Missing baselines**: Are the comparisons fair? Is the paper comparing against weak or outdated baselines, or is the comparison set incomplete?
- **Statistical rigor**: Are results reported with confidence intervals/std dev/multiple seeds, or single-run point estimates? Are improvements within noise margins?
- **Compute/resource transparency**: Is the compute budget disclosed? Could results be due to compute advantage over baselines rather than the proposed method?
- **Dataset availability**: Is the dataset public, and if not, how does that affect reproducibility?
- **Code availability**: Is there an official implementation? If not, how hard would reproduction be given the methodology detail provided?
- **Implausible results**: Do any claimed numbers seem too good relative to known benchmarks/SOTA for that task/dataset (based on your general knowledge)?

For each issue found, rate severity as "high", "medium", or "low" and explain WHY, citing specific details from the methodology/claims provided.

Limit to the 5 most significant issues.

Respond with ONLY a single JSON object and nothing else — no explanation, no preamble, no markdown formatting. Output must start with {{ and end with }}.

METHODOLOGY:
{methodology}

CLAIMS:
{claims}

CODE AVAILABILITY:
{code_info}

Return ONLY valid JSON with this structure:
{{
  "issues": [
    {{
      "category": "data_leakage | missing_baselines | statistical_rigor | compute_transparency | dataset_availability | code_availability | implausible_results",
      "severity": "high | medium | low",
      "description": "specific explanation referencing details from the paper",
      "recommendation": "what the authors should do / what a reproducer should check"
    }}
  ],
  "overall_reproducibility_score": "1-10 integer, where 10 = fully reproducible with code+data+clear methodology, 1 = essentially impossible to reproduce",
  "overall_assessment": "2-3 sentence summary of reproducibility outlook"
}}
"""


async def check_plausibility(methodology: dict, claims: dict, code_info: dict) -> dict:
    prompt = PLAUSIBILITY_PROMPT.format(
        methodology=str(methodology),
        claims=str(claims),
        code_info=str(code_info),
    )
    return await llm_json_call(prompt, model=MODEL_FAST, temperature=0.3, max_tokens=3500)
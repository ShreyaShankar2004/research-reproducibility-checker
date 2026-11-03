
"""Run DeepEval against a saved research-paper analysis."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from deepeval import evaluate
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
from deepeval.test_case import LLMTestCase

from groq_judge import GroqJudge


def evaluate_payload(payload: dict) -> None:
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("Set GROQ_API_KEY before running DeepEval.")

    required = {"input", "actual_output", "retrieval_context"}
    missing = required - payload.keys()

    if missing:
        raise ValueError(
            f"Missing required JSON fields: {', '.join(sorted(missing))}"
        )

    if not isinstance(payload["retrieval_context"], list):
        raise ValueError(
            "retrieval_context must be a JSON array of paper excerpts."
        )

    judge = GroqJudge(
        model_name=os.getenv(
            "DEEPEVAL_JUDGE_MODEL",
            "openai/gpt-oss-20b",
        )
    )

    case = LLMTestCase(
        input=payload["input"],
        actual_output=payload["actual_output"],
        retrieval_context=payload["retrieval_context"],
    )

    results = evaluate(
        test_cases=[case],
        metrics=[
            AnswerRelevancyMetric(threshold=0.7, model=judge),
            FaithfulnessMetric(threshold=0.7, model=judge),
        ],
    )

    print("\nDeepEval Evaluation Results:")
    print(results)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate a saved LLM response with DeepEval."
    )

    parser.add_argument(
        "input_json",
        type=Path,
        help="JSON containing input, actual_output and retrieval_context",
    )

    args = parser.parse_args()

    if not args.input_json.exists():
        raise FileNotFoundError(
            f"Evaluation input file not found: {args.input_json}"
        )

    payload = json.loads(
        args.input_json.read_text(encoding="utf-8")
    )

    evaluate_payload(payload)


if __name__ == "__main__":
    main()

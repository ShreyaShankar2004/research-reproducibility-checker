
"""Optional LLM-as-judge tests using Groq and DeepEval."""

import os
import json
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from deepeval import assert_test
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
from deepeval.test_case import LLMTestCase

from evaluation.groq_judge import GroqJudge


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LLM_EVAL") != "1" or not os.getenv("GROQ_API_KEY"),
    reason="Set RUN_LLM_EVAL=1 and GROQ_API_KEY to run optional live judge tests.",
)


@pytest.fixture(scope="module")
def groq_judge():
    model_name = os.getenv(
        "DEEPEVAL_JUDGE_MODEL",
        "openai/gpt-oss-20b",
    )
    return GroqJudge(model_name=model_name)


def test_reproducibility_summary_is_relevant_and_grounded(groq_judge):
    context = [
        "The paper evaluates a ResNet-50 model on CIFAR-10.",
        "It reports 91.2% test accuracy using SGD for 100 epochs.",
        "The paper does not disclose the random seed or exact train-validation split.",
    ]

    output = (
        "The study evaluates ResNet-50 on CIFAR-10 and reports 91.2% test accuracy. "
        "The random seed and exact train-validation split are not disclosed."
    )

    case = LLMTestCase(
        input="Summarise the paper's model, dataset, result and reproducibility gaps.",
        actual_output=output,
        retrieval_context=context,
    )

    assert_test(
        case,
        [
            AnswerRelevancyMetric(threshold=0.7, model=groq_judge),
            FaithfulnessMetric(threshold=0.7, model=groq_judge),
        ],
    )

def test_nftrig_correct_answer_is_faithful(groq_judge):
    path = Path(__file__).with_name("nftrig_eval.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    case = LLMTestCase(
        input=payload["input"],
        actual_output=payload["actual_output"],
        retrieval_context=payload["retrieval_context"],
    )

    metric = FaithfulnessMetric(
        threshold=0.7,
        model=groq_judge,
    )

    metric.measure(case)

    assert metric.score >= 0.7, (
        f"Correct NFTrig answer failed faithfulness: {metric.score}"
    )


def test_nftrig_hallucination_is_detected(groq_judge):
    path = Path(__file__).with_name("nftrig_hallucination_test.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    case = LLMTestCase(
        input=payload["input"],
        actual_output=payload["actual_output"],
        retrieval_context=payload["retrieval_context"],
    )

    metric = FaithfulnessMetric(
        threshold=0.7,
        model=groq_judge,
    )

    metric.measure(case)

    assert metric.score < 0.7, (
        f"Evaluator failed to detect hallucination: {metric.score}"
    )
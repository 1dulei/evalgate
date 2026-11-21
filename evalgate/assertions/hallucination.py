"""
Hallucination & Groundedness Assertion for EvalGate.
Measures context fidelity and factuality against reference documents.
"""
import re
from typing import Set
from ..core.models import Assertion, AssertionResult, AssertionType


def _tokenize(text: str) -> Set[str]:
    # Extract lowercased ASCII words + CJK bigrams for bilingual Chinese/English support
    ascii_tokens = re.findall(r"[a-z0-9]+", text.lower())
    stopwords = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "for", "of", "and", "or", "that", "this", "it", "with", "as"}
    result = {t for t in ascii_tokens if t not in stopwords and len(t) > 1}

    cjk_chunks = re.findall(r"[\u4e00-\u9fff]+", text)
    cjk_stop = {"请问", "什么", "如何", "怎么", "可以", "根据", "我们", "这是"}
    for chunk in cjk_chunks:
        if len(chunk) == 1:
            result.add(chunk)
        else:
            for i in range(len(chunk) - 1):
                bg = chunk[i:i+2]
                if bg not in cjk_stop:
                    result.add(bg)
    return result


def evaluate_hallucination(assertion: Assertion, actual_text: str, context: str = "") -> AssertionResult:
    """
    Computes groundedness score: ratio of significant response claims grounded in context.
    Threshold defaults to 0.70.
    """
    threshold = float(assertion.threshold or 0.70)
    ref_context = (assertion.value or context or "").strip()

    if not ref_context:
        return AssertionResult(
            type=AssertionType.HALLUCINATION,
            passed=True,
            score=1.0,
            message="No reference context provided; groundedness check skipped.",
            expected="N/A",
            actual=actual_text
        )

    resp_tokens = _tokenize(actual_text)
    ctx_tokens = _tokenize(ref_context)

    if not resp_tokens:
        return AssertionResult(
            type=AssertionType.HALLUCINATION,
            passed=False,
            score=0.0,
            message="Response is empty; cannot evaluate groundedness",
            expected=f">= {threshold*100}% grounded tokens",
            actual="Empty response"
        )

    overlap = resp_tokens.intersection(ctx_tokens)
    grounded_ratio = len(overlap) / len(resp_tokens)
    score = round(grounded_ratio, 3)
    passed = score >= threshold

    msg = (
        f"Groundedness score {score*100:.1f}% satisfies threshold >= {threshold*100:.1f}%"
        if passed
        else f"Hallucination detected: Groundedness {score*100:.1f}% fell below threshold {threshold*100:.1f}% ({len(resp_tokens - ctx_tokens)} ungrounded terms)"
    )

    return AssertionResult(
        type=AssertionType.HALLUCINATION,
        passed=passed,
        score=score,
        message=msg,
        expected=f">= {threshold}",
        actual=score
    )

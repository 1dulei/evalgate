"""
Exact and Substring Assertions for EvalGate.
"""
from typing import Any
from ..core.models import Assertion, AssertionResult, AssertionType


def evaluate_exact(assertion: Assertion, actual_text: str, latency_ms: float) -> AssertionResult:
    atype = assertion.type
    expected = assertion.value

    if atype == AssertionType.EQUALS:
        passed = actual_text.strip() == str(expected).strip()
        score = 1.0 if passed else 0.0
        msg = "Response matches exact expected output" if passed else f"Mismatch. Expected: '{expected}', Got: '{actual_text[:60]}...'"
        return AssertionResult(type=atype, passed=passed, score=score, message=msg, expected=expected, actual=actual_text)

    elif atype == AssertionType.CONTAINS:
        passed = str(expected).lower() in actual_text.lower()
        score = 1.0 if passed else 0.0
        msg = f"Response contains '{expected}'" if passed else f"Response missing required keyword: '{expected}'"
        return AssertionResult(type=atype, passed=passed, score=score, message=msg, expected=expected, actual=actual_text)

    elif atype == AssertionType.NOT_CONTAINS:
        passed = str(expected).lower() not in actual_text.lower()
        score = 1.0 if passed else 0.0
        msg = f"Response safely does not contain '{expected}'" if passed else f"Response leaked forbidden keyword: '{expected}'"
        return AssertionResult(type=atype, passed=passed, score=score, message=msg, expected=expected, actual=actual_text)

    elif atype == AssertionType.LATENCY_MAX:
        limit = float(expected)
        passed = latency_ms <= limit
        score = 1.0 if passed else max(0.0, 1.0 - (latency_ms - limit) / limit)
        msg = f"Latency {latency_ms:.1f}ms <= limit {limit}ms" if passed else f"Latency SLA breached: {latency_ms:.1f}ms > {limit}ms"
        return AssertionResult(type=atype, passed=passed, score=score, message=msg, expected=limit, actual=latency_ms)

    return AssertionResult(type=atype, passed=False, score=0.0, message=f"Unknown assertion type: {atype}")

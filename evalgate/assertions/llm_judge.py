"""
LLM-as-judge assertion: asks a second model whether the answer contradicts the reference context.

Token-overlap groundedness (see hallucination.py) cannot tell "2 小时以上免费" from "2 小时以上扣费"
because both sentences reuse the same words. This judge catches logical contradictions, at the cost
of an extra model call. When no judge provider is configured the assertion is reported as SKIPPED,
never as passed.
"""
import json
import re
from typing import Optional

from ..core.models import Assertion, AssertionResult, AssertionType
from ..core.providers import BaseProvider

JUDGE_SYSTEM_PROMPT = (
    "You are a strict fact-checking judge. Compare the ANSWER with the REFERENCE. "
    "Reply with JSON only: {\"verdict\": \"consistent\" | \"contradiction\" | \"unsupported\", \"reason\": \"<one sentence>\"}. "
    "Use \"contradiction\" if any claim in the ANSWER conflicts with the REFERENCE (numbers, conditions, negations). "
    "Use \"unsupported\" if the ANSWER adds material facts not present in the REFERENCE."
)


def _parse_verdict(raw: str) -> Optional[dict]:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except Exception:
        return None
    if str(data.get("verdict", "")).lower() not in ("consistent", "contradiction", "unsupported"):
        return None
    return data


def evaluate_llm_judge(
    assertion: Assertion,
    actual_text: str,
    context: str,
    judge: Optional[BaseProvider],
) -> AssertionResult:
    reference = (assertion.value or context or "").strip()
    if judge is None:
        return AssertionResult(
            type=AssertionType.LLM_JUDGE,
            passed=True,
            score=0.0,
            message="SKIPPED: no judge provider configured (run with --judge to enable)",
            skipped=True,
        )
    if not reference:
        return AssertionResult(
            type=AssertionType.LLM_JUDGE,
            passed=True,
            score=0.0,
            message="SKIPPED: no reference context to judge against",
            skipped=True,
        )

    prompt = f"REFERENCE:\n{reference}\n\nANSWER:\n{actual_text}"
    resp = judge.complete(prompt, system_prompt=JUDGE_SYSTEM_PROMPT)
    if resp.get("error"):
        return AssertionResult(
            type=AssertionType.LLM_JUDGE,
            passed=False,
            score=0.0,
            message=f"Judge call failed: {resp['error']}",
        )

    verdict = _parse_verdict(resp.get("content", ""))
    if verdict is None:
        return AssertionResult(
            type=AssertionType.LLM_JUDGE,
            passed=False,
            score=0.0,
            message="Judge returned an unparseable verdict",
            actual=resp.get("content", "")[:120],
        )

    label = verdict["verdict"].lower()
    passed = label == "consistent"
    return AssertionResult(
        type=AssertionType.LLM_JUDGE,
        passed=passed,
        score=1.0 if passed else 0.0,
        message=f"Judge verdict: {label} — {verdict.get('reason', '')}".strip(),
        expected="consistent",
        actual=label,
    )

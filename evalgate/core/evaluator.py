"""
Core Evaluation & Regression Diff Engine for EvalGate.
"""
import json
from typing import List, Dict, Any, Optional
from .models import (
    TestCase, TestResult, AssertionResult, AssertionType, SuiteSummary
)
from .providers import BaseProvider
from ..assertions.exact import evaluate_exact
from ..assertions.schema import evaluate_json_schema
from ..assertions.hallucination import evaluate_hallucination
from ..assertions.llm_judge import evaluate_llm_judge
from ..assertions.redteam import evaluate_redteam


class EvalEngine:
    def __init__(
        self,
        provider: BaseProvider,
        min_pass_rate: float = 0.95,
        judge_provider: Optional[BaseProvider] = None,
        provider_name: str = "mock",
    ):
        self.provider = provider
        self.min_pass_rate = min_pass_rate
        self.judge_provider = judge_provider
        self.provider_name = provider_name

    def run_case(self, case: TestCase) -> TestResult:
        resp = self.provider.complete(case.prompt, system_prompt=case.system_prompt)
        actual_text = resp.get("content", "")
        latency_ms = float(resp.get("latency_ms", 0.0))
        err = resp.get("error")

        if err:
            return TestResult(
                case_id=case.id,
                description=case.description,
                prompt=case.prompt,
                response="",
                passed=False,
                score=0.0,
                latency_ms=latency_ms,
                assertion_results=[],
                error=err,
                tags=case.tags
            )

        assertion_results: List[AssertionResult] = []
        for assertion in case.assertions:
            if assertion.type in (
                AssertionType.EQUALS,
                AssertionType.CONTAINS,
                AssertionType.NOT_CONTAINS,
                AssertionType.LATENCY_MAX,
            ):
                ar = evaluate_exact(assertion, actual_text, latency_ms)
            elif assertion.type == AssertionType.JSON_SCHEMA:
                ar = evaluate_json_schema(assertion, actual_text)
            elif assertion.type == AssertionType.HALLUCINATION:
                ar = evaluate_hallucination(assertion, actual_text, context=case.context or "")
            elif assertion.type == AssertionType.LLM_JUDGE:
                ar = evaluate_llm_judge(assertion, actual_text, case.context or "", self.judge_provider)
            elif assertion.type == AssertionType.REDTEAM:
                ar = evaluate_redteam(assertion, actual_text)
            else:
                ar = AssertionResult(
                    type=assertion.type,
                    passed=False,
                    score=0.0,
                    message=f"Unsupported assertion: {assertion.type}"
                )
            assertion_results.append(ar)

        # Skipped assertions (e.g. llm_judge without a judge provider) neither pass nor fail a case
        # and are excluded from the score.
        scored = [r for r in assertion_results if not r.skipped]
        if not scored:
            passed = True
            avg_score = 1.0
        else:
            passed = all(r.passed for r in scored)
            avg_score = round(sum(r.score for r in scored) / len(scored), 3)

        return TestResult(
            case_id=case.id,
            description=case.description,
            prompt=case.prompt,
            response=actual_text,
            passed=passed,
            score=avg_score,
            latency_ms=latency_ms,
            assertion_results=assertion_results,
            tags=case.tags
        )

    def run_suite(self, suite_name: str, cases: List[TestCase]) -> SuiteSummary:
        results = [self.run_case(c) for c in cases]
        total = len(results)
        passed_count = sum(1 for r in results if r.passed)
        failed_count = total - passed_count
        pass_rate = round(passed_count / total, 4) if total > 0 else 1.0
        avg_latency = round(sum(r.latency_ms for r in results) / total, 2) if total > 0 else 0.0
        avg_score = round(sum(r.score for r in results) / total, 3) if total > 0 else 1.0

        # Check critical redteam failures
        redteam_failures = [
            r.case_id for r in results
            for ar in r.assertion_results
            if ar.type == AssertionType.REDTEAM and not ar.passed
        ]
        skipped = sum(1 for r in results for ar in r.assertion_results if ar.skipped)

        if redteam_failures:
            passed_gate = False
            gate_reason = f"BLOCKED: Critical Red-Team vulnerability in {', '.join(redteam_failures)}"
        elif pass_rate < self.min_pass_rate:
            passed_gate = False
            gate_reason = f"BLOCKED: Pass rate {pass_rate*100:.1f}% < required gate {self.min_pass_rate*100:.1f}%"
        else:
            passed_gate = True
            gate_reason = f"PASSED: Pass rate {pass_rate*100:.1f}% >= {self.min_pass_rate*100:.1f}% & 0 Red-Team leaks"

        return SuiteSummary(
            suite_name=suite_name,
            total_cases=total,
            passed_cases=passed_count,
            failed_cases=failed_count,
            pass_rate=pass_rate,
            avg_latency_ms=avg_latency,
            avg_score=avg_score,
            results=results,
            passed_gate=passed_gate,
            gate_reason=gate_reason,
            provider=self.provider_name,
            skipped_assertions=skipped,
        )


def compute_regression_diff(baseline: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compares two evaluation JSON snapshots (e.g. Prompt v2.1 vs Prompt v2.2)
    and identifies regressions, improvements, and score deltas.
    """
    base_map = {r["case_id"]: r for r in baseline.get("results", [])}
    cand_map = {r["case_id"]: r for r in candidate.get("results", [])}

    regressions = []
    improvements = []
    unchanged = 0

    for cid, cand_r in cand_map.items():
        base_r = base_map.get(cid)
        if not base_r:
            continue
        if base_r["passed"] and not cand_r["passed"]:
            regressions.append({
                "case_id": cid,
                "description": cand_r.get("description", ""),
                "score_delta": round(cand_r["score"] - base_r["score"], 3),
                "latency_delta_ms": round(cand_r["latency_ms"] - base_r["latency_ms"], 2)
            })
        elif not base_r["passed"] and cand_r["passed"]:
            improvements.append({
                "case_id": cid,
                "description": cand_r.get("description", ""),
                "score_delta": round(cand_r["score"] - base_r["score"], 3)
            })
        else:
            unchanged += 1

    return {
        "baseline_pass_rate": baseline.get("pass_rate", 0.0),
        "candidate_pass_rate": candidate.get("pass_rate", 0.0),
        "pass_rate_delta": round(candidate.get("pass_rate", 0.0) - baseline.get("pass_rate", 0.0), 4),
        "regressions": regressions,
        "improvements": improvements,
        "unchanged_count": unchanged,
        "has_regression": len(regressions) > 0
    }

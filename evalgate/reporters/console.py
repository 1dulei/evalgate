"""
Console ASCII table and JSON serialization reporter for EvalGate.
"""
import json
from dataclasses import asdict
from typing import Dict, Any
from ..core.models import SuiteSummary


def summary_to_dict(summary: SuiteSummary) -> Dict[str, Any]:
    return asdict(summary)


def format_console_report(summary: SuiteSummary) -> str:
    lines = []
    sep = "=" * 86
    lines.append(sep)
    lines.append(f"  EVALGATE QUALITY HARNESS  |  Suite: {summary.suite_name}")
    lines.append(sep)
    lines.append(f"  Cases: {summary.total_cases}  |  Passed: {summary.passed_cases}  |  Failed: {summary.failed_cases}  |  Pass Rate: {summary.pass_rate*100:.1f}%")
    lines.append(f"  Avg Score: {summary.avg_score:.3f}  |  Avg Latency: {summary.avg_latency_ms:.1f}ms  |  Skipped assertions: {summary.skipped_assertions}")
    provider_note = "  (canned demo responses, NOT real model output)" if summary.provider == "mock" else ""
    lines.append(f"  Provider: {summary.provider}{provider_note}")
    lines.append("-" * 86)
    lines.append(f"  {'ID':<16} {'STATUS':<8} {'SCORE':<7} {'LATENCY':<10} {'DESCRIPTION'}")
    lines.append("-" * 86)

    for r in summary.results:
        status = "PASS" if r.passed else "FAIL"
        desc = (r.description[:40] + "...") if len(r.description) > 43 else r.description
        lines.append(f"  {r.case_id:<16} {status:<8} {r.score:<7.2f} {r.latency_ms:<8.1f}ms {desc}")
        if not r.passed:
            for ar in r.assertion_results:
                if not ar.passed and not ar.skipped:
                    lines.append(f"     └─ [{ar.type.value}] {ar.message}")
            if r.error:
                lines.append(f"     └─ [ERROR] {r.error}")

    lines.append(sep)
    gate_badge = "[CI GATE: PASS]" if summary.passed_gate else "[CI GATE: BLOCKED]"
    lines.append(f"  {gate_badge}  {summary.gate_reason}")
    lines.append(sep)
    return "\n".join(lines)

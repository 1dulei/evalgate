"""
Command Line Interface for EvalGate.
Usage:
  python -m evalgate run --config examples/ai_tutor_benchmark.json --html report.html --json out.json --fail-on-gate
  python -m evalgate diff --baseline base.json --candidate cand.json
"""
import argparse
import json
import os
import sys
from .core.loader import load_suite_file, build_test_cases
from .core.providers import MockProvider, HttpLLMProvider
from .core.evaluator import EvalEngine, compute_regression_diff
from .reporters.console import format_console_report, summary_to_dict
from .reporters.html_reporter import generate_html_report


def cmd_run(args: argparse.Namespace) -> int:
    raw = load_suite_file(args.config)
    suite_name = raw.get("suite", "EvalGate Suite")
    min_pass_rate = args.min_pass_rate if args.min_pass_rate is not None else float(raw.get("min_pass_rate", 0.95))
    cases = build_test_cases(raw)

    judge = None
    if args.provider == "http":
        api_key = args.api_key or os.environ.get("OPENAI_API_KEY", "")
        api_base = args.api_base or os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
        provider = HttpLLMProvider(api_base=api_base, api_key=api_key, model=args.model)
        provider_name = f"http:{args.model}"
        if args.judge:
            judge = HttpLLMProvider(api_base=api_base, api_key=api_key, model=args.judge_model or args.model)
    else:
        mock_overrides = raw.get("mock_responses", {})
        provider = MockProvider(overrides=mock_overrides)
        provider_name = "mock"

    engine = EvalEngine(
        provider=provider,
        min_pass_rate=min_pass_rate,
        judge_provider=judge,
        provider_name=provider_name,
    )
    summary = engine.run_suite(suite_name=suite_name, cases=cases)

    print(format_console_report(summary))

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(summary_to_dict(summary), f, ensure_ascii=False, indent=2)
        print(f"Saved JSON snapshot -> {args.json_out}")

    if args.html_out:
        html_doc = generate_html_report(summary)
        with open(args.html_out, "w", encoding="utf-8") as f:
            f.write(html_doc)
        print(f"Saved interactive HTML scorecard -> {args.html_out}")

    if args.fail_on_gate and not summary.passed_gate:
        return 1
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    with open(args.baseline, "r", encoding="utf-8") as f:
        base = json.load(f)
    with open(args.candidate, "r", encoding="utf-8") as f:
        cand = json.load(f)

    diff = compute_regression_diff(base, cand)
    print("=" * 72)
    print("  EVALGATE REGRESSION DIFF")
    print("=" * 72)
    print(f"  Baseline Pass Rate : {diff['baseline_pass_rate']*100:.1f}%")
    print(f"  Candidate Pass Rate: {diff['candidate_pass_rate']*100:.1f}%  (Delta: {diff['pass_rate_delta']*100:+.1f}%)")
    print(f"  Regressions: {len(diff['regressions'])}  |  Improvements: {len(diff['improvements'])}  |  Unchanged: {diff['unchanged_count']}")
    for reg in diff["regressions"]:
        print(f"  [REGRESSION] {reg['case_id']} (score {reg['score_delta']:+.2f}): {reg['description']}")
    for imp in diff["improvements"]:
        print(f"  [IMPROVED]   {imp['case_id']} (score {imp['score_delta']:+.2f}): {imp['description']}")
    print("=" * 72)
    return 1 if (args.fail_on_regression and diff["has_regression"]) else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="evalgate", description="EvalGate — release-gate evaluation for LLM features")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Execute an evaluation benchmark suite")
    run_p.add_argument("--config", "-c", required=True, help="Path to JSON or YAML benchmark config")
    run_p.add_argument("--provider", choices=["mock", "http"], default="mock", help="Model provider")
    run_p.add_argument("--api-base", default=None, help="OpenAI-compatible base URL")
    run_p.add_argument("--api-key", default=None, help="API key (or OPENAI_API_KEY env)")
    run_p.add_argument("--model", default="gpt-4o-mini", help="Model identifier")
    run_p.add_argument("--judge", action="store_true", help="Enable llm_judge assertions (http provider only)")
    run_p.add_argument("--judge-model", default=None, help="Model used as judge (defaults to --model)")
    run_p.add_argument("--min-pass-rate", type=float, default=None, help="Override CI gate pass rate threshold")
    run_p.add_argument("--json", dest="json_out", default=None, help="Write JSON snapshot path")
    run_p.add_argument("--html", dest="html_out", default=None, help="Write interactive HTML scorecard path")
    run_p.add_argument("--fail-on-gate", action="store_true", help="Exit 1 when CI gate is blocked")

    diff_p = sub.add_parser("diff", help="Compare two JSON evaluation snapshots for prompt regressions")
    diff_p.add_argument("--baseline", required=True, help="Baseline JSON snapshot")
    diff_p.add_argument("--candidate", required=True, help="Candidate JSON snapshot")
    diff_p.add_argument("--fail-on-regression", action="store_true", help="Exit 1 if any case regressed")

    args = parser.parse_args(argv)
    if args.command == "run":
        return cmd_run(args)
    elif args.command == "diff":
        return cmd_diff(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())

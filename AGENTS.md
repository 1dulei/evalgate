# AGENTS.md — EvalGate Engineering Guidelines

- **Zero External Runtime Dependencies**: Keep core evaluation, HTTP completions, schema checks, and HTML reporting strictly on Python 3.10+ standard library so CI pipelines run in `< 1s` cold start.
- **Zero Tolerance Safety Gate**: Any `AssertionType.REDTEAM` failure must unconditionally block `SuiteSummary.passed_gate`, even when aggregate `pass_rate >= min_pass_rate`.
- **Verification**: Run `python -m unittest discover -s tests -v` before every commit.

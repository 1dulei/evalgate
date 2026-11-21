"""
Suite and test case loader supporting JSON and YAML-subset configs.
"""
import json
import os
from typing import List, Dict, Any, Optional
from .models import TestCase, Assertion, AssertionType


def parse_simple_yaml(text: str) -> Dict[str, Any]:
    """
    Lightweight zero-dependency YAML subset parser for EvalGate test suites.
    Falls back gracefully if pyyaml is absent.
    """
    try:
        import yaml
        return yaml.safe_load(text)
    except ImportError:
        pass

    # Simple line-based fallback parser for YAML suites
    # If the file begins with { or [, use JSON parser directly
    text_stripped = text.strip()
    if text_stripped.startswith("{") or text_stripped.startswith("["):
        return json.loads(text_stripped)

    # For simple YAML structure
    result: Dict[str, Any] = {"suite": "default", "tests": []}
    lines = text.splitlines()
    current_test: Optional[Dict[str, Any]] = None
    current_assertions: List[Dict[str, Any]] = []

    for line in lines:
        raw_line = line
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("suite:"):
            result["suite"] = line.split(":", 1)[1].strip().strip('"\'')
        elif line.startswith("min_pass_rate:"):
            result["min_pass_rate"] = float(line.split(":", 1)[1].strip())
        elif line.startswith("- id:"):
            if current_test:
                current_test["assertions"] = current_assertions
                result["tests"].append(current_test)
            current_test = {"id": line.split(":", 1)[1].strip().strip('"\'')}
            current_assertions = []
        elif current_test is not None:
            if line.startswith("prompt:"):
                current_test["prompt"] = line.split(":", 1)[1].strip().strip('"\'')
            elif line.startswith("description:"):
                current_test["description"] = line.split(":", 1)[1].strip().strip('"\'')
            elif line.startswith("context:"):
                current_test["context"] = line.split(":", 1)[1].strip().strip('"\'')
            elif line.startswith("- type:"):
                atype = line.split(":", 1)[1].strip().strip('"\'')
                current_assertions.append({"type": atype})
            elif line.startswith("value:") and current_assertions:
                val = line.split(":", 1)[1].strip().strip('"\'')
                # Try parsing as JSON if dict/number
                try:
                    val = json.loads(val)
                except Exception:
                    pass
                current_assertions[-1]["value"] = val
            elif line.startswith("threshold:") and current_assertions:
                current_assertions[-1]["threshold"] = float(line.split(":", 1)[1].strip())

    if current_test:
        current_test["assertions"] = current_assertions
        result["tests"].append(current_test)

    return result


def load_suite_file(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Suite config not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if path.endswith(".json"):
        return json.loads(content)
    else:
        return parse_simple_yaml(content)


def build_test_cases(raw_data: Dict[str, Any]) -> List[TestCase]:
    cases = []
    raw_tests = raw_data.get("tests", [])
    for rt in raw_tests:
        assertions = []
        for ra in rt.get("assertions", []):
            atype_str = ra.get("type", "contains").lower()
            try:
                atype = AssertionType(atype_str)
            except ValueError:
                atype = AssertionType.CONTAINS
            assertions.append(Assertion(
                type=atype,
                value=ra.get("value"),
                threshold=float(ra.get("threshold", 0.8)),
                meta=ra.get("meta", {})
            ))

        cases.append(TestCase(
            id=rt.get("id", f"case_{len(cases)+1}"),
            description=rt.get("description", ""),
            prompt=rt.get("prompt", ""),
            system_prompt=rt.get("system_prompt"),
            context=rt.get("context"),
            assertions=assertions,
            tags=rt.get("tags", [])
        ))
    return cases

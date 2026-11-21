"""
JSON Schema & Structured Output Assertion for EvalGate.
"""
import json
import re
from typing import Dict, Any, List
from ..core.models import Assertion, AssertionResult, AssertionType


def evaluate_json_schema(assertion: Assertion, actual_text: str) -> AssertionResult:
    """
    Validates that the actual response can be parsed as valid JSON and conforms
    to the required keys and types defined in assertion.value (dict).
    """
    # Extract JSON substring if wrapped in markdown code fence
    cleaned = actual_text.strip()
    if "```json" in cleaned:
        match = re.search(r"```json\s*(.*?)\s*```", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1).strip()
    elif "```" in cleaned:
        match = re.search(r"```\s*(.*?)\s*```", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1).strip()

    try:
        data = json.loads(cleaned)
    except Exception as e:
        return AssertionResult(
            type=AssertionType.JSON_SCHEMA,
            passed=False,
            score=0.0,
            message=f"JSON Parse Error: Output is not valid JSON ({e})",
            expected=assertion.value,
            actual=actual_text[:100]
        )

    expected_schema: Dict[str, Any] = assertion.value or {}
    if not isinstance(expected_schema, dict):
        return AssertionResult(
            type=AssertionType.JSON_SCHEMA,
            passed=True,
            score=1.0,
            message="Valid JSON output",
            expected=expected_schema,
            actual=data
        )

    required_fields: List[str] = expected_schema.get("required", [])
    properties: Dict[str, Any] = expected_schema.get("properties", {})

    missing_fields = []
    type_mismatches = []

    for field in required_fields:
        if field not in data:
            missing_fields.append(field)

    for key, spec in properties.items():
        if key in data:
            expected_type = spec.get("type") if isinstance(spec, dict) else spec
            val = data[key]
            # bool is a subclass of int in Python, so it must be excluded from numeric checks explicitly.
            is_bool = isinstance(val, bool)
            if expected_type == "string" and not isinstance(val, str):
                type_mismatches.append(f"Field '{key}' expected string, got {type(val).__name__}")
            elif expected_type in ("number", "float") and (is_bool or not isinstance(val, (int, float))):
                type_mismatches.append(f"Field '{key}' expected number, got {type(val).__name__}")
            elif expected_type == "integer" and (is_bool or not isinstance(val, int)):
                type_mismatches.append(f"Field '{key}' expected integer, got {type(val).__name__}")
            elif expected_type == "boolean" and not isinstance(val, bool):
                type_mismatches.append(f"Field '{key}' expected boolean, got {type(val).__name__}")
            elif expected_type == "array" and not isinstance(val, list):
                type_mismatches.append(f"Field '{key}' expected list/array, got {type(val).__name__}")
            elif expected_type == "object" and not isinstance(val, dict):
                type_mismatches.append(f"Field '{key}' expected object, got {type(val).__name__}")

    errors = []
    if missing_fields:
        errors.append(f"Missing required fields: {', '.join(missing_fields)}")
    if type_mismatches:
        errors.append(f"Type violations: {'; '.join(type_mismatches)}")

    passed = len(errors) == 0
    score = 1.0 if passed else max(0.0, 1.0 - (len(missing_fields) * 0.4 + len(type_mismatches) * 0.3))

    msg = "Structured JSON matches schema perfectly" if passed else f"Schema violations: {' | '.join(errors)}"
    return AssertionResult(
        type=AssertionType.JSON_SCHEMA,
        passed=passed,
        score=score,
        message=msg,
        expected=expected_schema,
        actual=data
    )

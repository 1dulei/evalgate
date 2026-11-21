"""
Core data models for EvalGate evaluation harness.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AssertionType(str, Enum):
    EQUALS = "equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    JSON_SCHEMA = "json_schema"
    HALLUCINATION = "hallucination"
    LLM_JUDGE = "llm_judge"
    REDTEAM = "redteam"
    LATENCY_MAX = "latency_max"


@dataclass
class Assertion:
    type: AssertionType
    value: Any = None
    threshold: float = 0.8
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestCase:
    id: str
    description: str
    prompt: str
    system_prompt: Optional[str] = None
    context: Optional[str] = None
    assertions: List[Assertion] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class AssertionResult:
    type: AssertionType
    passed: bool
    score: float
    message: str
    expected: Any = None
    actual: Any = None
    skipped: bool = False


@dataclass
class TestResult:
    case_id: str
    description: str
    prompt: str
    response: str
    passed: bool
    score: float
    latency_ms: float
    assertion_results: List[AssertionResult] = field(default_factory=list)
    error: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class SuiteSummary:
    suite_name: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    avg_latency_ms: float
    avg_score: float
    results: List[TestResult]
    passed_gate: bool
    gate_reason: str
    provider: str = "mock"
    skipped_assertions: int = 0

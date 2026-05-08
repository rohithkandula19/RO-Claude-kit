"""Production hardening for Claude agents.

Modules:
- ``injection`` — prompt-injection scanners (pattern + LLM) for input and output.
- ``guardrails`` — tool allowlists and human-in-the-loop approval gates.
- ``validation`` — structured-output validation with retry-on-failure.
- ``tracing`` — provider-agnostic trace emitter + PII redaction.
"""
from .guardrails import ApprovalGate, ToolAllowlist
from .injection import InjectionScanner, OutputLeakScanner, ScanResult
from .tracing import TraceEmitter, redact_pii
from .validation import OutputValidator, ValidationFailure

__all__ = [
    "ApprovalGate",
    "InjectionScanner",
    "OutputLeakScanner",
    "OutputValidator",
    "ScanResult",
    "ToolAllowlist",
    "TraceEmitter",
    "ValidationFailure",
    "redact_pii",
]

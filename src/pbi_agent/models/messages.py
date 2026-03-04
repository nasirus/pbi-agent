from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# Pricing per 1M tokens: (base_input, cached_input, output)
_MODEL_PRICING: dict[str, tuple[float, float, float]] = {
    "gpt-5.3-codex": (1.75, 0.175, 14.00),
    "claude-opus-4-6": (5.00, 0.50, 25.00),
    "claude-sonnet-4-6": (3.00, 0.30, 15.00),
}
_DEFAULT_PRICING: tuple[float, float, float] = (1.75, 0.175, 14.00)


def _pricing_for_model(model: str) -> tuple[float, float, float]:
    """Return (input, cached_input, output) per-MTok prices for *model*."""
    if model in _MODEL_PRICING:
        return _MODEL_PRICING[model]
    # Fuzzy match: check if any known key is a prefix of the model string.
    for key, prices in _MODEL_PRICING.items():
        if model.startswith(key):
            return prices
    return _DEFAULT_PRICING


@dataclass(slots=True)
class TokenUsage:
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""

    @property
    def non_cached_input_tokens(self) -> int:
        return max(self.input_tokens - self.cached_input_tokens, 0)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def estimated_cost_usd(self) -> float:
        p_input, p_cached, p_output = _pricing_for_model(self.model)
        return (
            (self.non_cached_input_tokens / 1_000_000.0) * p_input
            + (self.cached_input_tokens / 1_000_000.0) * p_cached
            + (self.output_tokens / 1_000_000.0) * p_output
        )

    def add(self, other: "TokenUsage") -> None:
        self.input_tokens += other.input_tokens
        self.cached_input_tokens += other.cached_input_tokens
        self.output_tokens += other.output_tokens


@dataclass(slots=True)
class ToolCall:
    call_id: str
    name: str
    arguments: dict | str | None


@dataclass(slots=True)
class ApplyPatchCall:
    call_id: str
    operation: dict


@dataclass(slots=True)
class ShellCall:
    call_id: str
    action: dict


@dataclass(slots=True)
class CompletedResponse:
    response_id: str | None
    text: str
    usage: TokenUsage = field(default_factory=TokenUsage)
    function_calls: list[ToolCall] = field(default_factory=list)
    apply_patch_calls: list[ApplyPatchCall] = field(default_factory=list)
    shell_calls: list[ShellCall] = field(default_factory=list)
    # Provider-specific opaque data (e.g. raw Anthropic content blocks for
    # history replay).  The session layer never inspects this; only the
    # provider that created the response uses it.
    provider_data: Any = None

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.function_calls or self.apply_patch_calls or self.shell_calls)


@dataclass(slots=True)
class AgentOutcome:
    response_id: str | None
    text: str
    tool_errors: bool = False

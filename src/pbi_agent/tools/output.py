from __future__ import annotations

MAX_OUTPUT_CHARS = 1_000


def bound_output(text: str, *, limit: int = MAX_OUTPUT_CHARS) -> tuple[str, bool]:
    """Bound text output while preserving both the beginning and the end."""
    if len(text) <= limit:
        return text, False

    omitted_chars = len(text)

    while True:
        marker = f"\n... {omitted_chars} chars omitted ...\n"
        available = limit - len(marker)
        if available <= 0:
            return text[:limit], True

        head = (available + 1) // 2
        tail = available // 2
        new_omitted_chars = len(text) - head - tail
        if new_omitted_chars == omitted_chars:
            return f"{text[:head]}{marker}{text[-tail:]}", True
        omitted_chars = new_omitted_chars

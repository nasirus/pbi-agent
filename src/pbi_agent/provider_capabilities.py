from __future__ import annotations

IMAGE_ENABLED_PROVIDERS = frozenset({"openai", "anthropic", "google"})


def provider_supports_images(provider: str) -> bool:
    return provider.strip().lower() in IMAGE_ENABLED_PROVIDERS

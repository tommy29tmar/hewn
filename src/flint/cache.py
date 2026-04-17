from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CachePolicy:
    provider: str
    kind: str
    minimum_input_tokens: int | None
    docs_url: str
    notes: str


def resolve_cache_policy(provider: str, model: str) -> CachePolicy:
    provider_key = provider.strip().lower()
    model_key = model.strip().lower()

    if provider_key == "openai":
        return CachePolicy(
            provider="openai",
            kind="automatic prompt caching",
            minimum_input_tokens=1024,
            docs_url="https://platform.openai.com/docs/guides/prompt-caching",
            notes="Caching is automatic at 1024+ prompt tokens. Requests below that still expose cached_tokens, but hits remain zero.",
        )

    if provider_key == "anthropic":
        if any(token in model_key for token in ("mythos", "opus-4-6", "opus-4.6", "opus 4.6", "opus-4-5", "opus-4.5", "opus 4.5")):
            minimum = 4096
        elif any(token in model_key for token in ("sonnet-4-6", "sonnet-4.6", "sonnet 4.6")):
            minimum = 2048
        elif any(token in model_key for token in ("haiku-4-5", "haiku-4.5", "haiku 4.5")):
            minimum = 4096
        elif "haiku" in model_key:
            minimum = 2048
        else:
            minimum = 1024
        return CachePolicy(
            provider="anthropic",
            kind="prompt caching",
            minimum_input_tokens=minimum,
            docs_url="https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching",
            notes="Anthropic cache floors vary by model generation: Claude Sonnet 4 is 1024, Sonnet 4.6 is 2048, and some 4.5/4.6 Opus and Haiku models require 4096.",
        )

    if provider_key == "gemini":
        if "2.5-pro" in model_key or "2_5_pro" in model_key or "2.5 pro" in model_key:
            minimum = 4096
        elif "2.5-flash" in model_key or "2_5_flash" in model_key or "2.5 flash" in model_key:
            minimum = 1024
        else:
            minimum = None
        return CachePolicy(
            provider="gemini",
            kind="implicit/explicit context caching",
            minimum_input_tokens=minimum,
            docs_url="https://ai.google.dev/gemini-api/docs/caching",
            notes="Gemini 2.5 models support implicit caching; explicit caching is also available on supported paid tiers.",
        )

    return CachePolicy(
        provider=provider_key or "unknown",
        kind="unknown",
        minimum_input_tokens=None,
        docs_url="",
        notes="No built-in cache policy for this provider.",
    )


def cache_eligibility(input_tokens: int | None, policy: CachePolicy) -> dict[str, object]:
    if input_tokens is None:
        return {
            "eligible": None,
            "threshold_gap_tokens": None,
            "threshold_ratio": None,
        }
    if policy.minimum_input_tokens is None:
        return {
            "eligible": None,
            "threshold_gap_tokens": None,
            "threshold_ratio": None,
        }
    gap = input_tokens - policy.minimum_input_tokens
    return {
        "eligible": input_tokens >= policy.minimum_input_tokens,
        "threshold_gap_tokens": gap,
        "threshold_ratio": round(input_tokens / policy.minimum_input_tokens, 4),
    }

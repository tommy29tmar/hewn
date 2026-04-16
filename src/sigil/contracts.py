from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ContractFamily:
    name: str
    origin_provider: str
    label: str


KNOWN_FAMILIES: tuple[ContractFamily, ...] = (
    ContractFamily(name="baseline", origin_provider="plain", label="Baseline terse"),
    ContractFamily(name="gemini-nano", origin_provider="gemini", label="Gemini nano"),
    ContractFamily(name="claude-nano", origin_provider="anthropic", label="Claude nano"),
    ContractFamily(name="compact-v4", origin_provider="openai", label="Compact v4"),
    ContractFamily(name="capsule-mini", origin_provider="sigil", label="Capsule mini"),
    ContractFamily(name="bridge", origin_provider="sigil", label="Bridge capsule"),
    ContractFamily(name="wire-lite", origin_provider="sigil", label="Wire lite"),
    ContractFamily(name="slot-pack", origin_provider="sigil", label="Slot pack"),
    ContractFamily(name="draft2schema", origin_provider="sigil", label="Draft2Schema"),
    ContractFamily(name="unknown", origin_provider="unknown", label="Unknown"),
)


def _family(name: str) -> ContractFamily:
    for family in KNOWN_FAMILIES:
        if family.name == name:
            return family
    raise KeyError(name)


def infer_contract_family(prompt_path: str | None = None, variant_name: str | None = None) -> ContractFamily:
    prompt = Path(prompt_path).name.lower() if prompt_path else ""
    variant = (variant_name or "").lower()
    combined = f"{prompt} {variant}"
    if "baseline_terse" in prompt or variant.startswith("baseline"):
        return _family("baseline")
    if "gemini_nano" in prompt or "gemini-transfer" in variant or "openai-gemini-nano" in variant:
        return _family("gemini-nano")
    if "claude_nano" in prompt or "claude-nano" in variant:
        return _family("claude-nano")
    if "capsule_mini" in prompt or "capsule-mini" in variant:
        return _family("capsule-mini")
    if "bridge" in prompt or "bridge" in variant:
        return _family("bridge")
    if "compact_v4" in prompt or "compact-v4" in variant:
        return _family("compact-v4")
    if "wire_lite" in prompt or "wire-lite" in variant:
        return _family("wire-lite")
    if "slot_pack" in prompt or "slot-pack" in variant:
        return _family("slot-pack")
    if "draft2schema" in combined:
        return _family("draft2schema")
    return _family("unknown")

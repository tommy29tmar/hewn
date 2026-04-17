from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class CalibrationJob:
    category: str
    task_file: Path
    variant_name: str
    variant_spec: str
    max_output_tokens: int
    prompt_family: str


MICRO_OPENAI_CANDIDATES: tuple[CalibrationJob, ...] = (
    CalibrationJob(
        category="debugging",
        task_file=ROOT / "evals" / "tasks_debug_micro.jsonl",
        variant_name="sigil-debug-direct-minimal",
        variant_spec="sigil-debug-direct-minimal@sigil=prompts/debug_direct_sigil_minimal.txt",
        max_output_tokens=80,
        prompt_family="direct-minimal",
    ),
    CalibrationJob(
        category="debugging",
        task_file=ROOT / "evals" / "tasks_debug_micro.jsonl",
        variant_name="sigil-debug-direct-compact",
        variant_spec="sigil-debug-direct-compact@sigil=prompts/debug_direct_sigil_compact.txt",
        max_output_tokens=160,
        prompt_family="direct-compact",
    ),
    CalibrationJob(
        category="debugging",
        task_file=ROOT / "evals" / "tasks_debug_micro.jsonl",
        variant_name="sigil-debug-direct-compact-v4",
        variant_spec="sigil-debug-direct-compact-v4@sigil=prompts/debug_direct_sigil_compact_v4.txt",
        max_output_tokens=90,
        prompt_family="direct-compact-v4",
    ),
    CalibrationJob(
        category="debugging",
        task_file=ROOT / "evals" / "tasks_debug_micro.jsonl",
        variant_name="sigil-debug-wire-lite-micro",
        variant_spec="sigil-debug-wire-lite-micro@schema-debug_wire_lite=prompts/debug_wire_lite.txt",
        max_output_tokens=220,
        prompt_family="wire-lite",
    ),
    CalibrationJob(
        category="architecture",
        task_file=ROOT / "evals" / "tasks_architecture_micro.jsonl",
        variant_name="sigil-architecture-direct-minimal",
        variant_spec="sigil-architecture-direct-minimal@sigil=prompts/architecture_direct_sigil_minimal.txt",
        max_output_tokens=80,
        prompt_family="direct-minimal",
    ),
    CalibrationJob(
        category="architecture",
        task_file=ROOT / "evals" / "tasks_architecture_micro.jsonl",
        variant_name="sigil-architecture-direct-compact",
        variant_spec="sigil-architecture-direct-compact@sigil=prompts/architecture_direct_sigil_compact.txt",
        max_output_tokens=160,
        prompt_family="direct-compact",
    ),
    CalibrationJob(
        category="architecture",
        task_file=ROOT / "evals" / "tasks_architecture_micro.jsonl",
        variant_name="sigil-architecture-direct-compact-v4",
        variant_spec="sigil-architecture-direct-compact-v4@sigil=prompts/architecture_direct_sigil_compact_v4.txt",
        max_output_tokens=90,
        prompt_family="direct-compact-v4",
    ),
    CalibrationJob(
        category="architecture",
        task_file=ROOT / "evals" / "tasks_architecture_micro.jsonl",
        variant_name="sigil-architecture-wire-lite-micro",
        variant_spec="sigil-architecture-wire-lite-micro@schema-architecture_wire_lite=prompts/architecture_wire_lite.txt",
        max_output_tokens=220,
        prompt_family="wire-lite",
    ),
    CalibrationJob(
        category="code_review",
        task_file=ROOT / "evals" / "tasks_review_micro.jsonl",
        variant_name="sigil-review-direct-minimal",
        variant_spec="sigil-review-direct-minimal@sigil=prompts/review_direct_sigil_minimal.txt",
        max_output_tokens=80,
        prompt_family="direct-minimal",
    ),
    CalibrationJob(
        category="code_review",
        task_file=ROOT / "evals" / "tasks_review_micro.jsonl",
        variant_name="sigil-review-direct-compact",
        variant_spec="sigil-review-direct-compact@sigil=prompts/review_direct_sigil_compact.txt",
        max_output_tokens=160,
        prompt_family="direct-compact",
    ),
    CalibrationJob(
        category="code_review",
        task_file=ROOT / "evals" / "tasks_review_micro.jsonl",
        variant_name="sigil-review-direct-compact-v4",
        variant_spec="sigil-review-direct-compact-v4@sigil=prompts/review_direct_sigil_compact_v4.txt",
        max_output_tokens=90,
        prompt_family="direct-compact-v4",
    ),
    CalibrationJob(
        category="code_review",
        task_file=ROOT / "evals" / "tasks_review_micro.jsonl",
        variant_name="sigil-review-wire-lite-micro",
        variant_spec="sigil-review-wire-lite-micro@schema-review_wire_lite=prompts/review_wire_lite.txt",
        max_output_tokens=220,
        prompt_family="wire-lite",
    ),
    CalibrationJob(
        category="refactoring",
        task_file=ROOT / "evals" / "tasks_refactor_micro.jsonl",
        variant_name="sigil-refactor-direct-minimal",
        variant_spec="sigil-refactor-direct-minimal@sigil=prompts/refactor_direct_sigil_minimal.txt",
        max_output_tokens=80,
        prompt_family="direct-minimal",
    ),
    CalibrationJob(
        category="refactoring",
        task_file=ROOT / "evals" / "tasks_refactor_micro.jsonl",
        variant_name="sigil-refactor-direct-compact",
        variant_spec="sigil-refactor-direct-compact@sigil=prompts/refactor_direct_sigil_compact.txt",
        max_output_tokens=160,
        prompt_family="direct-compact",
    ),
    CalibrationJob(
        category="refactoring",
        task_file=ROOT / "evals" / "tasks_refactor_micro.jsonl",
        variant_name="sigil-refactor-direct-compact-v4",
        variant_spec="sigil-refactor-direct-compact-v4@sigil=prompts/refactor_direct_sigil_compact_v4.txt",
        max_output_tokens=90,
        prompt_family="direct-compact-v4",
    ),
    CalibrationJob(
        category="refactoring",
        task_file=ROOT / "evals" / "tasks_refactor_micro.jsonl",
        variant_name="sigil-refactor-wire-lite-micro",
        variant_spec="sigil-refactor-wire-lite-micro@schema-refactor_wire_lite=prompts/refactor_wire_lite.txt",
        max_output_tokens=220,
        prompt_family="wire-lite",
    ),
)


MICRO_ANTHROPIC_CANDIDATES: tuple[CalibrationJob, ...] = tuple(
    job for job in MICRO_OPENAI_CANDIDATES if job.prompt_family in {"direct-minimal", "direct-compact", "direct-compact-v4"}
)

MICRO_ANTHROPIC_EXTRA_CANDIDATES: tuple[CalibrationJob, ...] = (
    CalibrationJob(
        category="debugging",
        task_file=ROOT / "evals" / "tasks_debug_micro.jsonl",
        variant_name="sigil-debug-capsule-mini",
        variant_spec="sigil-debug-capsule-mini@sigil=prompts/debug_direct_sigil_capsule_mini.txt",
        max_output_tokens=72,
        prompt_family="capsule-mini",
    ),
    CalibrationJob(
        category="architecture",
        task_file=ROOT / "evals" / "tasks_architecture_micro.jsonl",
        variant_name="sigil-architecture-capsule-mini",
        variant_spec="sigil-architecture-capsule-mini@sigil=prompts/architecture_direct_sigil_capsule_mini.txt",
        max_output_tokens=72,
        prompt_family="capsule-mini",
    ),
)

MICRO_GEMINI_CANDIDATES: tuple[CalibrationJob, ...] = tuple(
    job for job in MICRO_OPENAI_CANDIDATES if job.prompt_family in {"direct-minimal", "direct-compact", "direct-compact-v4", "wire-lite"}
)

MICRO_GEMINI_EXTRA_CANDIDATES: tuple[CalibrationJob, ...] = (
    CalibrationJob(
        category="debugging",
        task_file=ROOT / "evals" / "tasks_debug_micro.jsonl",
        variant_name="sigil-debug-gemini-nano",
        variant_spec="sigil-debug-gemini-nano@sigil=prompts/debug_direct_sigil_gemini_nano.txt",
        max_output_tokens=80,
        prompt_family="gemini-nano",
    ),
    CalibrationJob(
        category="architecture",
        task_file=ROOT / "evals" / "tasks_architecture_micro.jsonl",
        variant_name="sigil-architecture-gemini-nano",
        variant_spec="sigil-architecture-gemini-nano@sigil=prompts/architecture_direct_sigil_gemini_nano.txt",
        max_output_tokens=80,
        prompt_family="gemini-nano",
    ),
    CalibrationJob(
        category="code_review",
        task_file=ROOT / "evals" / "tasks_review_micro.jsonl",
        variant_name="sigil-review-gemini-nano",
        variant_spec="sigil-review-gemini-nano@sigil=prompts/review_direct_sigil_gemini_nano.txt",
        max_output_tokens=80,
        prompt_family="gemini-nano",
    ),
    CalibrationJob(
        category="refactoring",
        task_file=ROOT / "evals" / "tasks_refactor_micro.jsonl",
        variant_name="sigil-refactor-gemini-nano",
        variant_spec="sigil-refactor-gemini-nano@sigil=prompts/refactor_direct_sigil_gemini_nano.txt",
        max_output_tokens=80,
        prompt_family="gemini-nano",
    ),
    CalibrationJob(
        category="debugging",
        task_file=ROOT / "evals" / "tasks_debug_micro.jsonl",
        variant_name="sigil-debug-slot-pack-micro",
        variant_spec="sigil-debug-slot-pack-micro@schema-debug_slot_pack=prompts/debug_slot_pack_schema.txt",
        max_output_tokens=180,
        prompt_family="slot-pack",
    ),
    CalibrationJob(
        category="code_review",
        task_file=ROOT / "evals" / "tasks_review_micro.jsonl",
        variant_name="sigil-review-slot-pack-micro",
        variant_spec="sigil-review-slot-pack-micro@schema-review_slot_pack=prompts/review_slot_pack_schema.txt",
        max_output_tokens=180,
        prompt_family="slot-pack",
    ),
)


def default_openai_micro_jobs() -> tuple[CalibrationJob, ...]:
    return MICRO_OPENAI_CANDIDATES


def default_anthropic_micro_jobs() -> tuple[CalibrationJob, ...]:
    return (*MICRO_ANTHROPIC_CANDIDATES, *MICRO_ANTHROPIC_EXTRA_CANDIDATES)


def default_gemini_micro_jobs() -> tuple[CalibrationJob, ...]:
    return (*MICRO_GEMINI_CANDIDATES, *MICRO_GEMINI_EXTRA_CANDIDATES)


def model_slug(model: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in model).strip("_").lower()


def run_path_for_job(model: str, job: CalibrationJob, run_dir: Path) -> Path:
    return run_dir / f"{model_slug(model)}_{job.variant_name}.jsonl"


def tasks_hybrid_micro_path() -> Path:
    return ROOT / "evals" / "tasks_hybrid_micro.jsonl"


def tasks_hybrid_nano_extended_path() -> Path:
    return ROOT / "evals" / "tasks_hybrid_nano_extended.jsonl"


MULTI_IR_OPENAI_EXTENDED_CANDIDATES: tuple[CalibrationJob, ...] = (
    CalibrationJob(
        category="debugging",
        task_file=ROOT / "evals" / "tasks_debug_micro_extended.jsonl",
        variant_name="sigil-debug-direct-compact-v4",
        variant_spec="sigil-debug-direct-compact-v4@sigil=prompts/debug_direct_sigil_compact_v4.txt",
        max_output_tokens=90,
        prompt_family="direct-compact-v4",
    ),
    CalibrationJob(
        category="debugging",
        task_file=ROOT / "evals" / "tasks_debug_micro_extended.jsonl",
        variant_name="sigil-debug-direct-compact-v4-cap72",
        variant_spec="sigil-debug-direct-compact-v4-cap72@sigil=prompts/debug_direct_sigil_compact_v4.txt",
        max_output_tokens=72,
        prompt_family="direct-compact-v4-cap72",
    ),
    CalibrationJob(
        category="debugging",
        task_file=ROOT / "evals" / "tasks_debug_micro_extended.jsonl",
        variant_name="sigil-debug-capsule-mini72",
        variant_spec="sigil-debug-capsule-mini72@sigil=prompts/debug_direct_sigil_capsule_mini.txt",
        max_output_tokens=72,
        prompt_family="capsule-mini",
    ),
    CalibrationJob(
        category="debugging",
        task_file=ROOT / "evals" / "tasks_debug_micro_extended.jsonl",
        variant_name="sigil-debug-capsule-mini64",
        variant_spec="sigil-debug-capsule-mini64@sigil=prompts/debug_direct_sigil_capsule_mini.txt",
        max_output_tokens=64,
        prompt_family="capsule-mini64",
    ),
    CalibrationJob(
        category="debugging",
        task_file=ROOT / "evals" / "tasks_debug_nano_extended.jsonl",
        variant_name="sigil-debug-openai-gemini-nano",
        variant_spec="sigil-debug-openai-gemini-nano@sigil=prompts/debug_direct_sigil_gemini_nano.txt",
        max_output_tokens=72,
        prompt_family="openai-gemini-nano",
    ),
    CalibrationJob(
        category="debugging",
        task_file=ROOT / "evals" / "tasks_debug_nano_extended.jsonl",
        variant_name="sigil-debug-openai-gemini-nano-cap56",
        variant_spec="sigil-debug-openai-gemini-nano-cap56@sigil=prompts/debug_direct_sigil_gemini_nano.txt",
        max_output_tokens=56,
        prompt_family="openai-gemini-nano-cap56",
    ),
    CalibrationJob(
        category="debugging",
        task_file=ROOT / "evals" / "tasks_debug_bridge_extended.jsonl",
        variant_name="sigil-debug-openai-bridge",
        variant_spec="sigil-debug-openai-bridge@sigil=prompts/debug_direct_sigil_bridge.txt",
        max_output_tokens=72,
        prompt_family="bridge",
    ),
    CalibrationJob(
        category="architecture",
        task_file=ROOT / "evals" / "tasks_architecture_micro_extended.jsonl",
        variant_name="sigil-architecture-direct-compact-v4",
        variant_spec="sigil-architecture-direct-compact-v4@sigil=prompts/architecture_direct_sigil_compact_v4.txt",
        max_output_tokens=90,
        prompt_family="direct-compact-v4",
    ),
    CalibrationJob(
        category="architecture",
        task_file=ROOT / "evals" / "tasks_architecture_micro_extended.jsonl",
        variant_name="sigil-architecture-direct-compact-v4-cap72",
        variant_spec="sigil-architecture-direct-compact-v4-cap72@sigil=prompts/architecture_direct_sigil_compact_v4.txt",
        max_output_tokens=72,
        prompt_family="direct-compact-v4-cap72",
    ),
    CalibrationJob(
        category="architecture",
        task_file=ROOT / "evals" / "tasks_architecture_nano_extended.jsonl",
        variant_name="sigil-architecture-openai-gemini-nano",
        variant_spec="sigil-architecture-openai-gemini-nano@sigil=prompts/architecture_direct_sigil_gemini_nano.txt",
        max_output_tokens=72,
        prompt_family="openai-gemini-nano",
    ),
    CalibrationJob(
        category="architecture",
        task_file=ROOT / "evals" / "tasks_architecture_bridge_extended.jsonl",
        variant_name="sigil-architecture-openai-bridge",
        variant_spec="sigil-architecture-openai-bridge@sigil=prompts/architecture_direct_sigil_bridge.txt",
        max_output_tokens=72,
        prompt_family="bridge",
    ),
    CalibrationJob(
        category="architecture",
        task_file=ROOT / "evals" / "tasks_architecture_micro_extended.jsonl",
        variant_name="sigil-architecture-capsule-mini72",
        variant_spec="sigil-architecture-capsule-mini72@sigil=prompts/architecture_direct_sigil_capsule_mini.txt",
        max_output_tokens=72,
        prompt_family="capsule-mini",
    ),
    CalibrationJob(
        category="architecture",
        task_file=ROOT / "evals" / "tasks_architecture_micro_extended.jsonl",
        variant_name="sigil-architecture-capsule-mini64",
        variant_spec="sigil-architecture-capsule-mini64@sigil=prompts/architecture_direct_sigil_capsule_mini.txt",
        max_output_tokens=64,
        prompt_family="capsule-mini64",
    ),
    CalibrationJob(
        category="code_review",
        task_file=ROOT / "evals" / "tasks_review_nano_extended.jsonl",
        variant_name="sigil-review-direct-compact-v4",
        variant_spec="sigil-review-direct-compact-v4@sigil=prompts/review_direct_sigil_compact_v4.txt",
        max_output_tokens=90,
        prompt_family="direct-compact-v4",
    ),
    CalibrationJob(
        category="code_review",
        task_file=ROOT / "evals" / "tasks_review_nano_extended.jsonl",
        variant_name="sigil-review-direct-compact-v4-cap72",
        variant_spec="sigil-review-direct-compact-v4-cap72@sigil=prompts/review_direct_sigil_compact_v4.txt",
        max_output_tokens=72,
        prompt_family="direct-compact-v4-cap72",
    ),
    CalibrationJob(
        category="code_review",
        task_file=ROOT / "evals" / "tasks_review_nano_extended.jsonl",
        variant_name="sigil-review-openai-gemini-nano",
        variant_spec="sigil-review-openai-gemini-nano@sigil=prompts/review_direct_sigil_gemini_nano.txt",
        max_output_tokens=72,
        prompt_family="openai-gemini-nano",
    ),
    CalibrationJob(
        category="refactoring",
        task_file=ROOT / "evals" / "tasks_refactor_micro_extended.jsonl",
        variant_name="sigil-refactor-direct-compact-v4",
        variant_spec="sigil-refactor-direct-compact-v4@sigil=prompts/refactor_direct_sigil_compact_v4.txt",
        max_output_tokens=90,
        prompt_family="direct-compact-v4",
    ),
    CalibrationJob(
        category="refactoring",
        task_file=ROOT / "evals" / "tasks_refactor_micro_extended.jsonl",
        variant_name="sigil-refactor-direct-compact-v4-cap72",
        variant_spec="sigil-refactor-direct-compact-v4-cap72@sigil=prompts/refactor_direct_sigil_compact_v4.txt",
        max_output_tokens=72,
        prompt_family="direct-compact-v4-cap72",
    ),
)


MULTI_IR_ANTHROPIC_EXTENDED_CANDIDATES: tuple[CalibrationJob, ...] = (
    CalibrationJob(
        category="debugging",
        task_file=ROOT / "evals" / "tasks_debug_micro_extended.jsonl",
        variant_name="sigil-debug-capsule-mini72",
        variant_spec="sigil-debug-capsule-mini72@sigil=prompts/debug_direct_sigil_capsule_mini.txt",
        max_output_tokens=72,
        prompt_family="capsule-mini",
    ),
    CalibrationJob(
        category="debugging",
        task_file=ROOT / "evals" / "tasks_debug_nano_extended.jsonl",
        variant_name="sigil-debug-claude-nano",
        variant_spec="sigil-debug-claude-nano@sigil=prompts/debug_direct_sigil_claude_nano.txt",
        max_output_tokens=64,
        prompt_family="claude-nano",
    ),
    CalibrationJob(
        category="debugging",
        task_file=ROOT / "evals" / "tasks_debug_nano_extended.jsonl",
        variant_name="sigil-debug-claude-nano-cap56",
        variant_spec="sigil-debug-claude-nano-cap56@sigil=prompts/debug_direct_sigil_claude_nano.txt",
        max_output_tokens=56,
        prompt_family="claude-nano-cap56",
    ),
    CalibrationJob(
        category="debugging",
        task_file=ROOT / "evals" / "tasks_debug_nano_extended.jsonl",
        variant_name="sigil-debug-gemini-transfer",
        variant_spec="sigil-debug-gemini-transfer@sigil=prompts/debug_direct_sigil_gemini_nano.txt",
        max_output_tokens=64,
        prompt_family="gemini-transfer",
    ),
    CalibrationJob(
        category="debugging",
        task_file=ROOT / "evals" / "tasks_debug_nano_extended.jsonl",
        variant_name="sigil-debug-gemini-transfer-cap56",
        variant_spec="sigil-debug-gemini-transfer-cap56@sigil=prompts/debug_direct_sigil_gemini_nano.txt",
        max_output_tokens=56,
        prompt_family="gemini-transfer-cap56",
    ),
    CalibrationJob(
        category="debugging",
        task_file=ROOT / "evals" / "tasks_debug_bridge_extended.jsonl",
        variant_name="sigil-debug-bridge",
        variant_spec="sigil-debug-bridge@sigil=prompts/debug_direct_sigil_bridge.txt",
        max_output_tokens=64,
        prompt_family="bridge",
    ),
    CalibrationJob(
        category="architecture",
        task_file=ROOT / "evals" / "tasks_architecture_micro_extended.jsonl",
        variant_name="sigil-architecture-capsule-mini72",
        variant_spec="sigil-architecture-capsule-mini72@sigil=prompts/architecture_direct_sigil_capsule_mini.txt",
        max_output_tokens=72,
        prompt_family="capsule-mini",
    ),
    CalibrationJob(
        category="architecture",
        task_file=ROOT / "evals" / "tasks_architecture_nano_extended.jsonl",
        variant_name="sigil-architecture-claude-nano",
        variant_spec="sigil-architecture-claude-nano@sigil=prompts/architecture_direct_sigil_claude_nano.txt",
        max_output_tokens=56,
        prompt_family="claude-nano",
    ),
    CalibrationJob(
        category="architecture",
        task_file=ROOT / "evals" / "tasks_architecture_nano_extended.jsonl",
        variant_name="sigil-architecture-gemini-transfer",
        variant_spec="sigil-architecture-gemini-transfer@sigil=prompts/architecture_direct_sigil_gemini_nano.txt",
        max_output_tokens=72,
        prompt_family="gemini-transfer",
    ),
    CalibrationJob(
        category="architecture",
        task_file=ROOT / "evals" / "tasks_architecture_micro_extended.jsonl",
        variant_name="sigil-architecture-capsule-mini64",
        variant_spec="sigil-architecture-capsule-mini64@sigil=prompts/architecture_direct_sigil_capsule_mini.txt",
        max_output_tokens=64,
        prompt_family="capsule-mini64",
    ),
    CalibrationJob(
        category="architecture",
        task_file=ROOT / "evals" / "tasks_architecture_bridge_extended.jsonl",
        variant_name="sigil-architecture-bridge",
        variant_spec="sigil-architecture-bridge@sigil=prompts/architecture_direct_sigil_bridge.txt",
        max_output_tokens=64,
        prompt_family="bridge",
    ),
    CalibrationJob(
        category="code_review",
        task_file=ROOT / "evals" / "tasks_review_nano_extended.jsonl",
        variant_name="sigil-review-claude-nano",
        variant_spec="sigil-review-claude-nano@sigil=prompts/review_direct_sigil_claude_nano.txt",
        max_output_tokens=64,
        prompt_family="claude-nano",
    ),
    CalibrationJob(
        category="code_review",
        task_file=ROOT / "evals" / "tasks_review_nano_extended.jsonl",
        variant_name="sigil-review-claude-nano-cap56",
        variant_spec="sigil-review-claude-nano-cap56@sigil=prompts/review_direct_sigil_claude_nano.txt",
        max_output_tokens=56,
        prompt_family="claude-nano-cap56",
    ),
    CalibrationJob(
        category="code_review",
        task_file=ROOT / "evals" / "tasks_review_nano_extended.jsonl",
        variant_name="sigil-review-gemini-transfer",
        variant_spec="sigil-review-gemini-transfer@sigil=prompts/review_direct_sigil_gemini_nano.txt",
        max_output_tokens=72,
        prompt_family="gemini-transfer",
    ),
    CalibrationJob(
        category="refactoring",
        task_file=ROOT / "evals" / "tasks_refactor_nano_extended.jsonl",
        variant_name="sigil-refactor-claude-nano",
        variant_spec="sigil-refactor-claude-nano@sigil=prompts/refactor_direct_sigil_claude_nano.txt",
        max_output_tokens=64,
        prompt_family="claude-nano",
    ),
    CalibrationJob(
        category="refactoring",
        task_file=ROOT / "evals" / "tasks_refactor_nano_extended.jsonl",
        variant_name="sigil-refactor-claude-nano-cap56",
        variant_spec="sigil-refactor-claude-nano-cap56@sigil=prompts/refactor_direct_sigil_claude_nano.txt",
        max_output_tokens=56,
        prompt_family="claude-nano-cap56",
    ),
    CalibrationJob(
        category="refactoring",
        task_file=ROOT / "evals" / "tasks_refactor_nano_extended.jsonl",
        variant_name="sigil-refactor-gemini-transfer",
        variant_spec="sigil-refactor-gemini-transfer@sigil=prompts/refactor_direct_sigil_gemini_nano.txt",
        max_output_tokens=64,
        prompt_family="gemini-transfer",
    ),
    CalibrationJob(
        category="refactoring",
        task_file=ROOT / "evals" / "tasks_refactor_nano_extended.jsonl",
        variant_name="sigil-refactor-gemini-transfer-cap56",
        variant_spec="sigil-refactor-gemini-transfer-cap56@sigil=prompts/refactor_direct_sigil_gemini_nano.txt",
        max_output_tokens=56,
        prompt_family="gemini-transfer-cap56",
    ),
)


MULTI_IR_GEMINI_EXTENDED_CANDIDATES: tuple[CalibrationJob, ...] = (
    CalibrationJob(
        category="debugging",
        task_file=ROOT / "evals" / "tasks_debug_nano_extended.jsonl",
        variant_name="sigil-debug-gemini-nano",
        variant_spec="sigil-debug-gemini-nano@sigil=prompts/debug_direct_sigil_gemini_nano.txt",
        max_output_tokens=80,
        prompt_family="gemini-nano",
    ),
    CalibrationJob(
        category="debugging",
        task_file=ROOT / "evals" / "tasks_debug_nano_extended.jsonl",
        variant_name="sigil-debug-gemini-nano-cap64",
        variant_spec="sigil-debug-gemini-nano-cap64@sigil=prompts/debug_direct_sigil_gemini_nano.txt",
        max_output_tokens=64,
        prompt_family="gemini-nano-cap64",
    ),
    CalibrationJob(
        category="debugging",
        task_file=ROOT / "evals" / "tasks_debug_micro_extended.jsonl",
        variant_name="sigil-debug-capsule-mini72",
        variant_spec="sigil-debug-capsule-mini72@sigil=prompts/debug_direct_sigil_capsule_mini.txt",
        max_output_tokens=72,
        prompt_family="capsule-mini",
    ),
    CalibrationJob(
        category="debugging",
        task_file=ROOT / "evals" / "tasks_debug_bridge_extended.jsonl",
        variant_name="sigil-debug-bridge",
        variant_spec="sigil-debug-bridge@sigil=prompts/debug_direct_sigil_bridge.txt",
        max_output_tokens=72,
        prompt_family="bridge",
    ),
    CalibrationJob(
        category="architecture",
        task_file=ROOT / "evals" / "tasks_architecture_nano_extended.jsonl",
        variant_name="sigil-architecture-gemini-nano",
        variant_spec="sigil-architecture-gemini-nano@sigil=prompts/architecture_direct_sigil_gemini_nano.txt",
        max_output_tokens=80,
        prompt_family="gemini-nano",
    ),
    CalibrationJob(
        category="architecture",
        task_file=ROOT / "evals" / "tasks_architecture_nano_extended.jsonl",
        variant_name="sigil-architecture-gemini-nano-cap64",
        variant_spec="sigil-architecture-gemini-nano-cap64@sigil=prompts/architecture_direct_sigil_gemini_nano.txt",
        max_output_tokens=64,
        prompt_family="gemini-nano-cap64",
    ),
    CalibrationJob(
        category="architecture",
        task_file=ROOT / "evals" / "tasks_architecture_micro_extended.jsonl",
        variant_name="sigil-architecture-capsule-mini72",
        variant_spec="sigil-architecture-capsule-mini72@sigil=prompts/architecture_direct_sigil_capsule_mini.txt",
        max_output_tokens=72,
        prompt_family="capsule-mini",
    ),
    CalibrationJob(
        category="architecture",
        task_file=ROOT / "evals" / "tasks_architecture_bridge_extended.jsonl",
        variant_name="sigil-architecture-bridge",
        variant_spec="sigil-architecture-bridge@sigil=prompts/architecture_direct_sigil_bridge.txt",
        max_output_tokens=72,
        prompt_family="bridge",
    ),
    CalibrationJob(
        category="code_review",
        task_file=ROOT / "evals" / "tasks_review_nano_extended.jsonl",
        variant_name="sigil-review-gemini-nano",
        variant_spec="sigil-review-gemini-nano@sigil=prompts/review_direct_sigil_gemini_nano.txt",
        max_output_tokens=80,
        prompt_family="gemini-nano",
    ),
    CalibrationJob(
        category="code_review",
        task_file=ROOT / "evals" / "tasks_review_nano_extended.jsonl",
        variant_name="sigil-review-gemini-nano-cap64",
        variant_spec="sigil-review-gemini-nano-cap64@sigil=prompts/review_direct_sigil_gemini_nano.txt",
        max_output_tokens=64,
        prompt_family="gemini-nano-cap64",
    ),
    CalibrationJob(
        category="refactoring",
        task_file=ROOT / "evals" / "tasks_refactor_nano_extended.jsonl",
        variant_name="sigil-refactor-gemini-nano",
        variant_spec="sigil-refactor-gemini-nano@sigil=prompts/refactor_direct_sigil_gemini_nano.txt",
        max_output_tokens=80,
        prompt_family="gemini-nano",
    ),
    CalibrationJob(
        category="refactoring",
        task_file=ROOT / "evals" / "tasks_refactor_nano_extended.jsonl",
        variant_name="sigil-refactor-gemini-nano-cap64",
        variant_spec="sigil-refactor-gemini-nano-cap64@sigil=prompts/refactor_direct_sigil_gemini_nano.txt",
        max_output_tokens=64,
        prompt_family="gemini-nano-cap64",
    ),
)


def baseline_micro_run_path(model: str, run_dir: Path) -> Path:
    return run_dir / f"{model_slug(model)}_baseline_hybrid_micro.jsonl"


def baseline_multi_ir_extended_run_path(model: str, run_dir: Path) -> Path:
    return run_dir / f"{model_slug(model)}_baseline_hybrid_nano_extended.jsonl"


def calibration_label(objective: str, allow_plain_candidates: bool = False) -> str:
    if allow_plain_candidates:
        return f"selective_{objective}"
    return objective


def profile_path(model: str, objective: str, out_dir: Path, allow_plain_candidates: bool = False) -> Path:
    label = calibration_label(objective, allow_plain_candidates)
    return out_dir / f"{model_slug(model)}_micro_{label}_router.json"


def routed_run_path(model: str, objective: str, run_dir: Path, allow_plain_candidates: bool = False) -> Path:
    label = calibration_label(objective, allow_plain_candidates)
    return run_dir / f"{model_slug(model)}_hybrid_micro_{label}.jsonl"


def multi_ir_extended_profile_path(model: str, objective: str, out_dir: Path, allow_plain_candidates: bool = False) -> Path:
    label = calibration_label(objective, allow_plain_candidates)
    return out_dir / f"{model_slug(model)}_multi_ir_extended_{label}_router.json"


def multi_ir_extended_routed_run_path(
    model: str,
    objective: str,
    run_dir: Path,
    allow_plain_candidates: bool = False,
) -> Path:
    label = calibration_label(objective, allow_plain_candidates)
    return run_dir / f"{model_slug(model)}_hybrid_multi_ir_extended_{label}.jsonl"


def build_profile_name(model: str, objective: str, allow_plain_candidates: bool = False) -> str:
    label = calibration_label(objective, allow_plain_candidates)
    return f"{model_slug(model)}_micro_{label}_router"


def build_multi_ir_extended_profile_name(model: str, objective: str, allow_plain_candidates: bool = False) -> str:
    label = calibration_label(objective, allow_plain_candidates)
    return f"{model_slug(model)}_multi_ir_extended_{label}_router"


def load_profile(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def default_openai_multi_ir_extended_jobs() -> tuple[CalibrationJob, ...]:
    return MULTI_IR_OPENAI_EXTENDED_CANDIDATES


def default_anthropic_multi_ir_extended_jobs() -> tuple[CalibrationJob, ...]:
    return MULTI_IR_ANTHROPIC_EXTENDED_CANDIDATES


def default_gemini_multi_ir_extended_jobs() -> tuple[CalibrationJob, ...]:
    return MULTI_IR_GEMINI_EXTENDED_CANDIDATES


def render_claude_code_md(*, profile: dict[str, Any], model: str, provider: str = "anthropic") -> str:
    categories = profile.get("categories") or {}
    lines = [
        "# SIGIL Calibration",
        "",
        f"- Provider: `{provider}`",
        f"- Model: `{model}`",
        f"- Profile: `{profile.get('name', 'unnamed')}`",
        "",
        "## Policy",
        "",
        "- Use normal human-language answers by default.",
        "- Use raw SIGIL only when the caller explicitly asks for SIGIL, compact capsules, or benchmark-style symbolic output.",
        "- When generating raw SIGIL, follow the calibrated transport family for the task category below.",
        "- Prefer compact atoms and local repairability over explanatory prose inside clauses.",
        "",
        "## Category Routing",
        "",
    ]
    for category in ("debugging", "architecture", "code_review", "refactoring"):
        chosen = categories.get(category, "unassigned")
        lines.append(f"- `{category}` -> `{chosen}`")
    lines.extend(
        [
            "",
            "## Raw SIGIL Rules",
            "",
            "- Start with `@flint v0 hybrid`.",
            "- Keep one clause per line.",
            "- Use only atoms/calls joined by `∧`, `→`, `⇒`.",
            "- Avoid prose inside clauses.",
            "- Omit `[AUDIT]` unless the caller asks for the expanded form.",
            "",
            "## Notes",
            "",
            "- This file is calibration metadata, not a claim that one prompt fits every model equally well.",
            "- Recalibrate when you change provider, model family, or task mix.",
        ]
    )
    return "\n".join(lines) + "\n"

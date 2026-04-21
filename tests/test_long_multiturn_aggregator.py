from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "claude_code_max_long_multiturn_4var_table.py"

spec = importlib.util.spec_from_file_location("long_multiturn_aggregator", SCRIPT_PATH)
AGG = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(AGG)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    payload = "\n".join(json.dumps(row) for row in rows) + "\n"
    path.write_text(payload, encoding="utf-8")


def make_corpus(scenarios: dict[str, list[dict]]) -> list[dict]:
    return [{"scenario_id": scenario_id, "turns": turns} for scenario_id, turns in scenarios.items()]


def make_turn(turn_id: str, expected_shape: str, must_include: list[str] | None = None) -> dict:
    return {
        "id": turn_id,
        "expected_shape": expected_shape,
        "must_include": must_include or [],
        "prompt": f"Prompt for {turn_id}",
    }


def make_row(
    scenario_id: str,
    turn_id: str,
    *,
    content: str | None,
    output_tokens: int = 10,
    elapsed_ms: int = 1000,
    exit_code: int = 0,
    tool_uses: list[dict] | None = None,
    error: str | None = None,
) -> dict:
    row = {
        "scenario_id": scenario_id,
        "turn_id": turn_id,
        "variant": "plain",
        "session_id": "sess",
        "content": content,
        "tool_uses": tool_uses or [],
        "usage": {"output_tokens": output_tokens, "input_tokens": 5},
        "elapsed_ms": elapsed_ms,
        "exit_code": exit_code,
    }
    if error is not None:
        row["error"] = error
    return row


def valid_ir_doc(label: str = "ok") -> str:
    return (
        "@flint v0 hybrid\n"
        f"G: goal_{label}\n"
        "C: constraint_one ∧ constraint_two\n"
        "P: plan_step\n"
        "V: verify_step\n"
        "A: answer_step\n"
    )


def invalid_ir_doc() -> str:
    return "@flint v0 hybrid\nG: goal_only\nA: answer_only\n"


def valid_tool_ir(label: str = "ok") -> dict:
    return {
        "G": f"goal_{label}",
        "C": ["constraint_one", "constraint_two"],
        "P": ["plan_step"],
        "V": ["verify_step"],
        "A": ["answer_step"],
        "audit": "short audit",
    }


def invalid_tool_ir() -> dict:
    return {
        "G": "goal_bad",
        "C": ["constraint_one"],
        "P": ["plan_step"],
        "V": ["verify_step"],
    }


def test_parse_on_ir_turns_math(tmp_path: Path) -> None:
    task_path = tmp_path / "tasks.jsonl"
    out_dir = tmp_path / "runs"
    out_dir.mkdir()

    write_jsonl(
        task_path,
        make_corpus(
            {
                "scenario-a": [make_turn(f"t{i}", "ir") for i in range(1, 6)],
            }
        ),
    )
    rows = [
        make_row("scenario-a", "t1", content=valid_ir_doc("one")),
        make_row("scenario-a", "t2", content=valid_ir_doc("two")),
        make_row("scenario-a", "t3", content=invalid_ir_doc()),
        make_row(
            "scenario-a",
            "t4",
            content="handled via flint tool",
            tool_uses=[{"name": "mcp__flint__submit_flint_ir", "input": valid_tool_ir("three")}],
        ),
        make_row(
            "scenario-a",
            "t5",
            content="handled via flint tool",
            tool_uses=[{"name": "mcp__flint__submit_flint_ir", "input": invalid_tool_ir()}],
        ),
    ]
    write_jsonl(out_dir / "plain_r1.jsonl", rows)

    report = AGG.build_report(task_path=task_path, out_dir=out_dir, cells=[("plain claude", "plain")])
    summary = report["headline"]["plain claude"]

    assert summary["ir_turn_count"] == 5
    assert summary["parse_hits"] == 3
    assert summary["parse_on_ir_turns"] == pytest.approx(60.0)


def test_parse_on_ir_turns_with_zero_ir_turns_reports_na(tmp_path: Path) -> None:
    task_path = tmp_path / "tasks.jsonl"
    out_dir = tmp_path / "runs"
    out_dir.mkdir()

    write_jsonl(
        task_path,
        make_corpus(
            {
                "scenario-a": [make_turn(f"t{i}", "prose") for i in range(1, 11)],
            }
        ),
    )
    rows = [make_row("scenario-a", f"t{i}", content=f"plain prose response {i}") for i in range(1, 11)]
    write_jsonl(out_dir / "plain_r1.jsonl", rows)

    report = AGG.build_report(task_path=task_path, out_dir=out_dir, cells=[("plain claude", "plain")])
    summary = report["headline"]["plain claude"]

    assert summary["ir_turn_count"] == 0
    assert summary["parse_on_ir_turns"] is None
    assert AGG.format_percent(summary["parse_on_ir_turns"]) == "n/a"


def test_infra_error_n_counts_expected_failure_modes(tmp_path: Path) -> None:
    task_path = tmp_path / "tasks.jsonl"
    out_dir = tmp_path / "runs"
    out_dir.mkdir()

    write_jsonl(
        task_path,
        make_corpus(
            {
                "scenario-a": [make_turn(f"t{i}", "prose") for i in range(1, 6)],
            }
        ),
    )
    rows = [
        make_row("scenario-a", "t1", content="valid text despite exit failure", exit_code=1),
        make_row("scenario-a", "t2", content=""),
        make_row("scenario-a", "t3", content="text with error field", error="tool timeout"),
        make_row("scenario-a", "t4", content="Error: upstream failed"),
        make_row("scenario-a", "t5", content="Normal prose answer"),
    ]
    write_jsonl(out_dir / "plain_r1.jsonl", rows)

    report = AGG.build_report(task_path=task_path, out_dir=out_dir, cells=[("plain claude", "plain")])
    summary = report["headline"]["plain claude"]

    assert summary["n"] == 5
    assert summary["infra_error_n"] == 4
    assert summary["class_total"] == 1
    assert summary["class_hits"] == 1
    assert summary["class_acc"] == pytest.approx(100.0)
    assert summary["must_total"] == 0
    assert summary["total_out"] == 10
    assert summary["mean_lat"] == pytest.approx(1.0)


def test_class_acc_is_unchanged_from_current_behavior(tmp_path: Path) -> None:
    task_path = tmp_path / "tasks.jsonl"
    out_dir = tmp_path / "runs"
    out_dir.mkdir()

    write_jsonl(
        task_path,
        make_corpus(
            {
                "scenario-a": [
                    make_turn("t1", "ir"),
                    make_turn("t2", "prose"),
                    make_turn("t3", "ir"),
                    make_turn("t4", "prose"),
                ],
            }
        ),
    )
    rows = [
        make_row("scenario-a", "t1", content=valid_ir_doc("hit")),
        make_row("scenario-a", "t2", content="plain prose response"),
        make_row("scenario-a", "t3", content="plain prose but expected ir"),
        make_row("scenario-a", "t4", content="", error="infra failure"),
    ]
    write_jsonl(out_dir / "plain_r1.jsonl", rows)

    report = AGG.build_report(task_path=task_path, out_dir=out_dir, cells=[("plain claude", "plain")])
    summary = report["headline"]["plain claude"]

    assert summary["class_total"] == 3
    assert summary["class_hits"] == 2
    assert summary["class_acc"] == pytest.approx(200 / 3)


def test_per_scenario_breakdown_matches_headline_totals(tmp_path: Path) -> None:
    task_path = tmp_path / "tasks.jsonl"
    out_dir = tmp_path / "runs"
    out_dir.mkdir()

    write_jsonl(
        task_path,
        make_corpus(
            {
                "alpha-session": [
                    make_turn("t1", "ir", ["alpha", "fix"]),
                    make_turn("t2", "prose", ["summary"]),
                ],
                "beta-session": [
                    make_turn("t1", "ir", ["beta", "plan"]),
                    make_turn("t2", "prose", ["memo"]),
                ],
            }
        ),
    )

    rows_by_prefix = {
        "plain": [
            make_row("alpha-session", "t1", content="missed ir response alpha fix"),
            make_row("alpha-session", "t2", content="summary for leadership"),
            make_row("beta-session", "t1", content=valid_ir_doc("beta")),
            make_row("beta-session", "t2", content="memo with memo"),
        ],
        "cccaveman": [
            make_row("alpha-session", "t1", content=valid_ir_doc("alpha")),
            make_row("alpha-session", "t2", content="plain prose without keyword"),
            make_row("beta-session", "t1", content="beta plan but prose"),
            make_row("beta-session", "t2", content="memo with memo"),
        ],
        "flint": [
            make_row("alpha-session", "t1", content=valid_ir_doc("alpha")),
            make_row("alpha-session", "t2", content="summary with summary"),
            make_row("beta-session", "t1", content=valid_ir_doc("beta")),
            make_row("beta-session", "t2", content="memo with memo"),
        ],
        "flint_mcp": [
            make_row(
                "alpha-session",
                "t1",
                content="tool transport alpha fix",
                tool_uses=[{"name": "mcp__flint__submit_flint_ir", "input": valid_tool_ir("alpha")}],
            ),
            make_row("alpha-session", "t2", content="summary with summary"),
            make_row(
                "beta-session",
                "t1",
                content="tool transport beta plan",
                tool_uses=[{"name": "mcp__flint__submit_flint_ir", "input": valid_tool_ir("beta")}],
            ),
            make_row("beta-session", "t2", content="memo with memo"),
        ],
    }
    for prefix, rows in rows_by_prefix.items():
        write_jsonl(out_dir / f"{prefix}_r1.jsonl", rows)

    report = AGG.build_report(task_path=task_path, out_dir=out_dir, cells=AGG.CELLS)
    scenario_rows = report["scenario_rows"]

    assert len(scenario_rows) == len(AGG.CELLS) * 2

    for label, _ in AGG.CELLS:
        combined = AGG.new_counts()
        rows = [row for row in scenario_rows if row["variant"] == label]
        assert len(rows) == 2
        for row in rows:
            AGG.merge_counts(combined, {key: row[key] for key in AGG.RAW_COUNT_KEYS})
        recomputed = AGG.finalize_counts(combined)
        headline = report["headline"][label]
        for key in AGG.RAW_COUNT_KEYS:
            assert recomputed[key] == headline[key]
        assert recomputed["class_acc"] == pytest.approx(headline["class_acc"])
        assert recomputed["ir_hit"] == pytest.approx(headline["ir_hit"])
        assert recomputed["tool_hit"] == pytest.approx(headline["tool_hit"])
        assert recomputed["must_include"] == pytest.approx(headline["must_include"])
        assert recomputed["mean_lat"] == pytest.approx(headline["mean_lat"])
        if headline["parse_on_ir_turns"] is None:
            assert recomputed["parse_on_ir_turns"] is None
        else:
            assert recomputed["parse_on_ir_turns"] == pytest.approx(headline["parse_on_ir_turns"])

    rendered = AGG.render_report(report, cells=AGG.CELLS)
    assert "Per-scenario breakdown:" in rendered
    assert "S1 = alpha-session" in rendered
    assert "S2 = beta-session" in rendered


def test_prose_code_detection_via_fenced_block(tmp_path: Path) -> None:
    """Content with a fenced code block (and no IR prefix) is detected as prose_code."""
    corpus = make_corpus(
        {
            "code-session": [
                make_turn("t1", "prose_code"),
                make_turn("t2", "prose"),
            ],
        }
    )
    task_path = tmp_path / "corpus.jsonl"
    write_jsonl(task_path, corpus)

    out_dir = tmp_path / "runs"
    out_dir.mkdir()

    fenced_content = (
        "Short analysis: fix applies.\n\n"
        "```python\n"
        "def verify(t):\n"
        "    return jwt.decode(t, SECRET, algorithms=['HS256'])\n"
        "```\n"
    )
    plain_prose = "Short retrospective. Team learn from incident. Share lesson."

    rows = [
        make_row("code-session", "t1", content=fenced_content),
        make_row("code-session", "t2", content=plain_prose),
    ]
    write_jsonl(out_dir / "plain_r1.jsonl", rows)

    report = AGG.build_report(task_path=task_path, out_dir=out_dir, cells=[("plain claude", "plain")])
    summary = report["headline"]["plain claude"]
    # t1: detected prose_code, expected prose_code -> hit
    # t2: detected prose, expected prose -> hit
    assert summary["class_acc"] == pytest.approx(100.0)


def test_prose_code_not_confused_with_ir(tmp_path: Path) -> None:
    """An IR response on a prose_code turn is not accidentally credited."""
    corpus = make_corpus(
        {
            "mixed": [make_turn("t1", "prose_code")],
        }
    )
    task_path = tmp_path / "corpus.jsonl"
    write_jsonl(task_path, corpus)

    out_dir = tmp_path / "runs"
    out_dir.mkdir()

    rows = [make_row("mixed", "t1", content=AGG.valid_ir_doc() if hasattr(AGG, "valid_ir_doc") else valid_ir_doc())]
    write_jsonl(out_dir / "plain_r1.jsonl", rows)

    report = AGG.build_report(task_path=task_path, out_dir=out_dir, cells=[("plain claude", "plain")])
    summary = report["headline"]["plain claude"]
    # detected ir, expected prose_code -> miss
    assert summary["class_acc"] == pytest.approx(0.0)


def test_prose_findings_expected_accepts_prose_family(tmp_path: Path) -> None:
    """Findings route is a prose sub-shape, not an IR parse target."""
    corpus = make_corpus(
        {
            "findings": [make_turn("t1", "prose_findings")],
        }
    )
    task_path = tmp_path / "corpus.jsonl"
    write_jsonl(task_path, corpus)

    out_dir = tmp_path / "runs"
    out_dir.mkdir()

    content = (
        "1. Hook path fragile - integrations/claude-code/flint-drift-fix-settings.json:9. "
        "Trigger: installed hook path stale. Fix: write absolute path at install.\n"
        "2. MCP import missing - integrations/claude-code/mcp-config.json:4. "
        "Trigger: optional mcp extra not installed. Fix: install extra or doctor check.\n"
    )
    write_jsonl(out_dir / "plain_r1.jsonl", [make_row("findings", "t1", content=content)])

    report = AGG.build_report(task_path=task_path, out_dir=out_dir, cells=[("plain claude", "plain")])
    summary = report["headline"]["plain claude"]
    assert summary["class_acc"] == pytest.approx(100.0)
    assert summary["ir_turn_count"] == 0

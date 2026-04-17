from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flint.calibration import (  # noqa: E402
    baseline_multi_ir_extended_run_path,
    build_multi_ir_extended_profile_name,
    default_anthropic_multi_ir_extended_jobs,
    default_gemini_multi_ir_extended_jobs,
    default_openai_multi_ir_extended_jobs,
    multi_ir_extended_profile_path,
    multi_ir_extended_routed_run_path,
    run_path_for_job,
    tasks_hybrid_nano_extended_path,
)


def run_command(args: list[str]) -> None:
    completed = subprocess.run(args, cwd=ROOT, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def provider_runner(provider: str) -> Path:
    mapping = {
        "openai": ROOT / "evals" / "run_openai.py",
        "anthropic": ROOT / "evals" / "run_anthropic.py",
        "gemini": ROOT / "evals" / "run_gemini.py",
    }
    return mapping[provider]


def default_jobs(provider: str):
    if provider == "openai":
        return default_openai_multi_ir_extended_jobs()
    if provider == "anthropic":
        return default_anthropic_multi_ir_extended_jobs()
    if provider == "gemini":
        return default_gemini_multi_ir_extended_jobs()
    raise KeyError(provider)


def rerendered_run_path(path: Path) -> Path:
    return path.with_name(f"{path.stem}_rerendered.jsonl")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Calibrate a provider-aware multi-IR SIGIL profile on the extended corpus.")
    parser.add_argument("--provider", choices=["openai", "anthropic", "gemini"], required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--objective", choices=["efficiency", "balanced", "quality"], default="efficiency")
    parser.add_argument("--granularity", choices=["category", "task"], default="category")
    parser.add_argument("--allow-plain-candidates", action="store_true")
    parser.add_argument("--run-dir", type=Path, default=ROOT / "evals" / "runs")
    parser.add_argument("--profile-dir", type=Path, default=ROOT / "profiles")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--skip-baseline", action="store_true")
    parser.add_argument("--verbosity", choices=["low", "medium", "high"], default="low")
    parser.add_argument("--thinking-budget", type=int, default=None)
    parser.add_argument("--cache-system-prompt", action="store_true")
    parser.add_argument("--max-retries", type=int, default=0)
    parser.add_argument("--retry-backoff-seconds", type=float, default=1.5)
    parser.add_argument("--skip-rerender", action="store_true", help="Use raw candidate runs without local rerender.")
    args = parser.parse_args(argv)

    runner = provider_runner(args.provider)
    jobs = default_jobs(args.provider)
    target_tasks = tasks_hybrid_nano_extended_path()
    args.run_dir.mkdir(parents=True, exist_ok=True)
    args.profile_dir.mkdir(parents=True, exist_ok=True)
    baseline_run: Path | None = None

    if not args.skip_baseline:
        baseline_run = baseline_multi_ir_extended_run_path(args.model, args.run_dir)
        baseline_cmd = [
            sys.executable,
            str(runner),
            "--tasks",
            str(target_tasks),
            "--out",
            str(baseline_run),
            "--model",
            args.model,
            "--variant",
            "baseline-terse=prompts/baseline_terse.txt",
            "--max-output-tokens",
            "140",
            "--max-retries",
            str(args.max_retries),
            "--retry-backoff-seconds",
            str(args.retry_backoff_seconds),
        ]
        if args.provider == "openai":
            baseline_cmd.extend(["--verbosity", args.verbosity])
        if args.provider in {"anthropic", "gemini"} and args.thinking_budget is not None:
            baseline_cmd.extend(["--thinking-budget", str(args.thinking_budget)])
        if args.provider == "anthropic" and args.cache_system_prompt:
            baseline_cmd.append("--cache-system-prompt")
        if args.overwrite:
            baseline_cmd.append("--overwrite")
        run_command(baseline_cmd)

    run_paths: list[Path] = []
    for job in jobs:
        out_path = run_path_for_job(args.model, job, args.run_dir)
        command = [
            sys.executable,
            str(runner),
            "--tasks",
            str(job.task_file),
            "--out",
            str(out_path),
            "--model",
            args.model,
            "--variant",
            job.variant_spec,
            "--max-output-tokens",
            str(job.max_output_tokens),
            "--max-retries",
            str(args.max_retries),
            "--retry-backoff-seconds",
            str(args.retry_backoff_seconds),
        ]
        if args.provider == "openai":
            command.extend(["--verbosity", args.verbosity])
        if args.provider in {"anthropic", "gemini"} and args.thinking_budget is not None:
            command.extend(["--thinking-budget", str(args.thinking_budget)])
        if args.provider == "anthropic" and args.cache_system_prompt:
            command.append("--cache-system-prompt")
        if args.overwrite:
            command.append("--overwrite")
        run_command(command)
        selected_path = out_path
        if not args.skip_rerender:
            selected_path = rerendered_run_path(out_path)
            run_command(
                [
                    sys.executable,
                    str(ROOT / "evals" / "rerender_run.py"),
                    str(out_path),
                    str(selected_path),
                ]
            )
        run_paths.append(selected_path)

    profile_out = multi_ir_extended_profile_path(args.model, args.objective, args.profile_dir, args.allow_plain_candidates)
    suggest_cmd = [
        sys.executable,
        str(ROOT / "evals" / "suggest_profile.py"),
        str(target_tasks),
        str(profile_out),
        "--objective",
        args.objective,
        "--granularity",
        args.granularity,
        "--name",
        build_multi_ir_extended_profile_name(args.model, args.objective, args.allow_plain_candidates),
    ]
    if args.allow_plain_candidates:
        suggest_cmd.append("--allow-plain-candidates")
        if baseline_run is not None:
            suggest_cmd.extend(["--run", str(baseline_run)])
    for path in run_paths:
        suggest_cmd.extend(["--run", str(path)])
    run_command(suggest_cmd)

    if not args.skip_baseline:
        routed_out = multi_ir_extended_routed_run_path(args.model, args.objective, args.run_dir, args.allow_plain_candidates)
        routed_cmd = [
            sys.executable,
            str(ROOT / "evals" / "build_routed_run.py"),
            str(target_tasks),
            str(profile_out),
            str(routed_out),
        ]
        for path in run_paths:
            routed_cmd.extend(["--source-run", str(path)])
        routed_cmd.extend(["--baseline-run", str(baseline_multi_ir_extended_run_path(args.model, args.run_dir))])
        run_command(routed_cmd)
        run_command(
            [
                sys.executable,
                str(ROOT / "evals" / "measure.py"),
                str(target_tasks),
                str(routed_out),
                "--baseline",
                "baseline-terse",
                "--json",
            ]
        )

    print(f"profile: {profile_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

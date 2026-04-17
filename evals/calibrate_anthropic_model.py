from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flint.calibration import (  # noqa: E402
    baseline_micro_run_path,
    build_profile_name,
    default_anthropic_micro_jobs,
    profile_path,
    routed_run_path,
    run_path_for_job,
    tasks_hybrid_micro_path,
)


def run_command(args: list[str]) -> None:
    completed = subprocess.run(args, cwd=ROOT, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Calibrate SIGIL transport for a specific Anthropic model.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--objective", choices=["efficiency", "balanced", "quality"], default="efficiency")
    parser.add_argument(
        "--allow-plain-candidates",
        action="store_true",
        help="Allow non-SIGIL baseline variants to compete during routing.",
    )
    parser.add_argument("--run-dir", type=Path, default=ROOT / "evals" / "runs")
    parser.add_argument("--profile-dir", type=Path, default=ROOT / "profiles")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--skip-baseline", action="store_true")
    parser.add_argument("--thinking-budget", type=int, default=None)
    parser.add_argument("--cache-system-prompt", action="store_true")
    parser.add_argument("--max-retries", type=int, default=0)
    parser.add_argument("--retry-backoff-seconds", type=float, default=1.5)
    args = parser.parse_args(argv)

    jobs = default_anthropic_micro_jobs()
    args.run_dir.mkdir(parents=True, exist_ok=True)
    args.profile_dir.mkdir(parents=True, exist_ok=True)

    if not args.skip_baseline:
        baseline_run = baseline_micro_run_path(args.model, args.run_dir)
        baseline_cmd = [
            sys.executable,
            str(ROOT / "evals" / "run_anthropic.py"),
            "--tasks",
            str(tasks_hybrid_micro_path()),
            "--out",
            str(baseline_run),
            "--model",
            args.model,
            "--variant",
            "baseline-terse=prompts/baseline_terse.txt",
            "--max-output-tokens",
            "220",
            "--max-retries",
            str(args.max_retries),
            "--retry-backoff-seconds",
            str(args.retry_backoff_seconds),
        ]
        if args.thinking_budget is not None:
            baseline_cmd.extend(["--thinking-budget", str(args.thinking_budget)])
        if args.cache_system_prompt:
            baseline_cmd.append("--cache-system-prompt")
        if args.overwrite:
            baseline_cmd.append("--overwrite")
        run_command(baseline_cmd)

    run_paths: list[Path] = []
    for job in jobs:
        out_path = run_path_for_job(args.model, job, args.run_dir)
        run_paths.append(out_path)
        command = [
            sys.executable,
            str(ROOT / "evals" / "run_anthropic.py"),
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
        if args.thinking_budget is not None:
            command.extend(["--thinking-budget", str(args.thinking_budget)])
        if args.cache_system_prompt:
            command.append("--cache-system-prompt")
        if args.overwrite:
            command.append("--overwrite")
        run_command(command)

    profile_out = profile_path(args.model, args.objective, args.profile_dir, args.allow_plain_candidates)
    suggest_cmd = [
        sys.executable,
        str(ROOT / "evals" / "suggest_profile.py"),
        str(tasks_hybrid_micro_path()),
        str(profile_out),
        "--objective",
        args.objective,
        "--name",
        build_profile_name(args.model, args.objective, args.allow_plain_candidates),
    ]
    if args.allow_plain_candidates:
        suggest_cmd.append("--allow-plain-candidates")
    for path in run_paths:
        suggest_cmd.extend(["--run", str(path)])
    run_command(suggest_cmd)

    if not args.skip_baseline:
        routed_out = routed_run_path(args.model, args.objective, args.run_dir, args.allow_plain_candidates)
        routed_cmd = [
            sys.executable,
            str(ROOT / "evals" / "build_routed_run.py"),
            str(tasks_hybrid_micro_path()),
            str(profile_out),
            str(routed_out),
        ]
        for path in run_paths:
            routed_cmd.extend(["--source-run", str(path)])
        routed_cmd.extend(["--baseline-run", str(baseline_micro_run_path(args.model, args.run_dir))])
        run_command(routed_cmd)
        run_command(
            [
                sys.executable,
                str(ROOT / "evals" / "measure.py"),
                str(tasks_hybrid_micro_path()),
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

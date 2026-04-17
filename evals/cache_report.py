from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flint.cache import CachePolicy, cache_eligibility, resolve_cache_policy  # noqa: E402
from flint.eval_common import load_jsonl  # noqa: E402


def summarize_variant(rows: list[dict[str, object]], policy: CachePolicy) -> dict[str, object]:
    input_values = [usage for row in rows if (usage := ((row.get("usage") or {}).get("input_tokens"))) is not None]
    cached_values = [usage for row in rows if (usage := ((row.get("usage") or {}).get("cached_tokens"))) is not None]
    hit_count = sum(1 for row in rows if ((row.get("usage") or {}).get("cached_tokens") or 0) > 0)

    eligible_rows = 0
    gap_values: list[int] = []
    ratio_values: list[float] = []
    if policy.minimum_input_tokens is not None:
        for value in input_values:
            eligibility = cache_eligibility(value, policy)
            if eligibility["eligible"] is not None:
                eligible_rows += int(bool(eligibility["eligible"]))
            if eligibility["threshold_gap_tokens"] is not None:
                gap_values.append(int(eligibility["threshold_gap_tokens"]))
            if eligibility["threshold_ratio"] is not None:
                ratio_values.append(float(eligibility["threshold_ratio"]))

    summary = {
        "count": len(rows),
        "avg_input_tokens": round(mean(input_values), 2) if input_values else None,
        "max_input_tokens": max(input_values) if input_values else None,
        "avg_cached_tokens": round(mean(cached_values), 2) if cached_values else None,
        "cache_hit_rate": round(hit_count / len(rows), 4) if rows else None,
        "eligible_rate": round(eligible_rows / len(input_values), 4)
        if input_values and policy.minimum_input_tokens is not None
        else None,
        "avg_threshold_gap_tokens": round(mean(gap_values), 2) if gap_values else None,
        "avg_threshold_ratio": round(mean(ratio_values), 4) if ratio_values else None,
    }

    if not input_values or policy.minimum_input_tokens is None:
        summary["verdict"] = "unknown"
    elif max(input_values) < policy.minimum_input_tokens:
        summary["verdict"] = "too_small_for_cache"
    elif hit_count == 0:
        summary["verdict"] = "eligible_but_no_cache_hits"
    else:
        summary["verdict"] = "cache_active"
    return summary


def summarize_run(run_path: Path, provider: str, model: str) -> dict[str, object]:
    rows = load_jsonl(run_path)
    policy = resolve_cache_policy(provider, model)
    variants: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        variants[str(row["variant"])].append(row)

    return {
        "run": str(run_path),
        "provider": provider,
        "model": model,
        "policy": {
            "kind": policy.kind,
            "minimum_input_tokens": policy.minimum_input_tokens,
            "docs_url": policy.docs_url,
            "notes": policy.notes,
        },
        "variants": {
            name: summarize_variant(group, policy)
            for name, group in sorted(variants.items())
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report whether a benchmark run is large enough for provider-side caching.")
    parser.add_argument("run", type=Path)
    parser.add_argument("--provider", required=True, choices=["openai", "anthropic", "gemini"])
    parser.add_argument("--model", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    summary = summarize_run(args.run, args.provider, args.model)

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

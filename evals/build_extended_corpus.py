from __future__ import annotations

import argparse
import json
from pathlib import Path


def debug_row(
    *,
    task_id: str,
    anchors: list[str],
    ctx: str,
    rule: str,
    need: str,
    issue: str,
    deliver: str,
    must_include: list[str],
    exact_literals: list[str],
) -> dict[str, object]:
    prompt = "\n".join(
        [
            "[capsule micro debugging]",
            f"anchors: {' | '.join(json.dumps(item, ensure_ascii=False) for item in anchors)}",
            f"ctx: {ctx}",
            f"rule: {rule}",
            f"need: {need}",
            f"issue: {issue}",
            f"deliver: {deliver}",
        ]
    )
    return {
        "id": task_id,
        "category": "debugging",
        "mode": "hybrid",
        "prompt": prompt,
        "must_include": must_include,
        "exact_literals": exact_literals,
        "capsule": "micro",
    }


def architecture_row(
    *,
    task_id: str,
    anchors: list[str],
    team: str,
    ddl: str,
    store: str,
    ops: str,
    traffic: str,
    split: str,
    deliver: str,
    must_include: list[str],
    exact_literals: list[str],
) -> dict[str, object]:
    prompt = "\n".join(
        [
            "[capsule micro architecture]",
            f"anchors: {' | '.join(json.dumps(item, ensure_ascii=False) for item in anchors)}",
            f"team: {team}",
            f"ddl: {json.dumps(ddl, ensure_ascii=False)}",
            f"store: {json.dumps(store, ensure_ascii=False)}",
            f"ops: {ops}",
            f"traffic: {traffic}",
            f"split: {split}",
            f"deliver: {deliver}",
        ]
    )
    return {
        "id": task_id,
        "category": "architecture",
        "mode": "hybrid",
        "prompt": prompt,
        "must_include": must_include,
        "exact_literals": exact_literals,
        "capsule": "micro",
    }


def review_row(
    *,
    task_id: str,
    anchors: list[str],
    diff: str,
    ctx: str,
    deliver: str,
    must_include: list[str],
    exact_literals: list[str],
) -> dict[str, object]:
    prompt = "\n".join(
        [
            "[capsule micro review]",
            f"anchors: {' | '.join(json.dumps(item, ensure_ascii=False) for item in anchors)}",
            f"diff: {diff}",
            f"ctx: {ctx}",
            f"deliver: {deliver}",
        ]
    )
    return {
        "id": task_id,
        "category": "code_review",
        "mode": "hybrid",
        "prompt": prompt,
        "must_include": must_include,
        "exact_literals": exact_literals,
        "capsule": "micro",
    }


def refactor_row(
    *,
    task_id: str,
    anchors: list[str],
    target: str,
    order: str,
    db_err: str,
    deliver: str,
    must_include: list[str],
    exact_literals: list[str],
) -> dict[str, object]:
    prompt = "\n".join(
        [
            "[capsule micro refactor]",
            f"anchors: {' | '.join(json.dumps(item, ensure_ascii=False) for item in anchors)}",
            f"target: {target}",
            f"order: {order}",
            f"db_err: {json.dumps(db_err, ensure_ascii=False)}",
            f"deliver: {deliver}",
        ]
    )
    return {
        "id": task_id,
        "category": "refactoring",
        "mode": "hybrid",
        "prompt": prompt,
        "must_include": must_include,
        "exact_literals": exact_literals,
        "capsule": "micro",
    }


def build_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = [
        debug_row(
            task_id="debug-auth-expiry",
            anchors=["<", "401"],
            ctx="auth_mw expiry",
            rule="expMs<nowMs=>401",
            need="allow skew30 only",
            issue="skew30 boundary refresh_loop",
            deliver="min_fix reg_test",
            must_include=["auth", "grace", "test", "regression"],
            exact_literals=["<", "401"],
        ),
        debug_row(
            task_id="debug-refresh-rotation-race",
            anchors=["refresh_token", "409"],
            ctx="refresh rotation",
            rule="reuse(old_refresh_token)=>409",
            need="reject replay only once",
            issue="parallel refresh race duplicates 409 loop",
            deliver="min_fix verify",
            must_include=["refresh", "race", "verify", "minimal"],
            exact_literals=["refresh_token", "409"],
        ),
        debug_row(
            task_id="debug-webhook-ts-skew",
            anchors=["300", "401"],
            ctx="webhook verify timestamp",
            rule="abs(now-ts)>300=>401",
            need="allow provider skew only",
            issue="edge timestamp rejects valid webhook",
            deliver="min_fix reg_test",
            must_include=["webhook", "skew", "test", "verify"],
            exact_literals=["300", "401"],
        ),
        debug_row(
            task_id="debug-ms-sec-mismatch",
            anchors=["1000", "401"],
            ctx="oauth callback expiry",
            rule="exp<now=>401",
            need="normalize ms sec once",
            issue="ms sec mismatch rejects fresh token",
            deliver="min_fix regression",
            must_include=["normalize", "expiry", "regression", "minimal"],
            exact_literals=["1000", "401"],
        ),
        debug_row(
            task_id="debug-cache-ttl-boundary",
            anchors=["ttl", "304"],
            ctx="etag cache freshness",
            rule="age>=ttl=>stale",
            need="serve fresh on exact boundary",
            issue="boundary stale loop revalidates forever",
            deliver="min_fix verify",
            must_include=["cache", "boundary", "verify", "fresh"],
            exact_literals=["ttl", "304"],
        ),
        debug_row(
            task_id="debug-rate-limit-reset-edge",
            anchors=["429", "retry-after"],
            ctx="limiter reset window",
            rule="now>reset=>allow",
            need="release exactly at reset once",
            issue="retry storm at reset edge",
            deliver="min_fix reg_test",
            must_include=["limit", "retry", "test", "boundary"],
            exact_literals=["429", "retry-after"],
        ),
        debug_row(
            task_id="debug-null-session-healthcheck",
            anchors=["401", "session"],
            ctx="auth guard public ping",
            rule="!session=>401",
            need="preserve healthcheck bypass only",
            issue="null session breaks public ping route",
            deliver="minimal_fix verify",
            must_include=["session", "bypass", "verify", "minimal"],
            exact_literals=["401", "session"],
        ),
        debug_row(
            task_id="debug-billing-grace-edge",
            anchors=["24h", "402"],
            ctx="billing overdue middleware",
            rule="overdue=>402",
            need="encode grace24h exactly",
            issue="boundary charge loop",
            deliver="min_fix reg_test",
            must_include=["billing", "grace", "test", "boundary"],
            exact_literals=["24h", "402"],
        ),
        architecture_row(
            task_id="arch-small-team",
            anchors=["6", "4 months", "PostgreSQL"],
            team="6",
            ddl="4 months",
            store="PostgreSQL",
            ops="pt_devops",
            traffic="modest",
            split="post_release",
            deliver="default_arch short_why",
            must_include=["modular_monolith", "team", "deadline"],
            exact_literals=["6", "4 months", "PostgreSQL"],
        ),
        architecture_row(
            task_id="arch-sso-admin-console",
            anchors=["8", "6 weeks", "PostgreSQL"],
            team="8",
            ddl="6 weeks",
            store="PostgreSQL",
            ops="lean_platform",
            traffic="modest",
            split="later_if_enterprise",
            deliver="default_arch short_why",
            must_include=["modular_monolith", "sso", "ops"],
            exact_literals=["8", "6 weeks", "PostgreSQL"],
        ),
        architecture_row(
            task_id="arch-analytics-jobs",
            anchors=["5", "8 weeks", "BigQuery"],
            team="5",
            ddl="8 weeks",
            store="BigQuery",
            ops="pt_dataops",
            traffic="batch_heavy",
            split="worker_later",
            deliver="default_arch short_why",
            must_include=["batch", "queue", "ops"],
            exact_literals=["5", "8 weeks", "BigQuery"],
        ),
        architecture_row(
            task_id="arch-multi-tenant-core",
            anchors=["10", "3 months", "PostgreSQL"],
            team="10",
            ddl="3 months",
            store="PostgreSQL",
            ops="full_platform",
            traffic="steady",
            split="region_later",
            deliver="default_arch short_why",
            must_include=["tenant", "modular_monolith", "boundaries"],
            exact_literals=["10", "3 months", "PostgreSQL"],
        ),
        architecture_row(
            task_id="arch-webhook-ingest",
            anchors=["4", "5 weeks", "PostgreSQL"],
            team="4",
            ddl="5 weeks",
            store="PostgreSQL",
            ops="pt_devops",
            traffic="bursty",
            split="queue_first",
            deliver="default_arch short_why",
            must_include=["queue", "ops", "deadline"],
            exact_literals=["4", "5 weeks", "PostgreSQL"],
        ),
        architecture_row(
            task_id="arch-search-index-sync",
            anchors=["7", "10 weeks", "PostgreSQL"],
            team="7",
            ddl="10 weeks",
            store="PostgreSQL",
            ops="small_platform",
            traffic="read_heavy",
            split="indexer_module",
            deliver="default_arch short_why",
            must_include=["index", "module", "ops"],
            exact_literals=["7", "10 weeks", "PostgreSQL"],
        ),
        architecture_row(
            task_id="arch-audit-heavy-fintech",
            anchors=["9", "12 weeks", "PostgreSQL"],
            team="9",
            ddl="12 weeks",
            store="PostgreSQL",
            ops="platform_plus_sec",
            traffic="steady",
            split="compliance_ready",
            deliver="default_arch short_why",
            must_include=["audit", "compliance", "boundaries"],
            exact_literals=["9", "12 weeks", "PostgreSQL"],
        ),
        architecture_row(
            task_id="arch-ml-enrichment-pipeline",
            anchors=["6", "9 weeks", "PostgreSQL"],
            team="6",
            ddl="9 weeks",
            store="PostgreSQL",
            ops="pt_mlops",
            traffic="async_enrichment",
            split="worker_sidecar",
            deliver="default_arch short_why",
            must_include=["async", "worker", "modular"],
            exact_literals=["6", "9 weeks", "PostgreSQL"],
        ),
        review_row(
            task_id="security-review-header-auth",
            anchors=["x-user-id", "401"],
            diff="- const userId=session.userId;+ const userId=req.headers['x-user-id'] || session.userId;if(!userId)return res.status(401).end();",
            ctx="public_api_gateway",
            deliver="risk mitigation verify",
            must_include=["risk", "verify", "header", "auth"],
            exact_literals=["x-user-id", "401"],
        ),
        review_row(
            task_id="security-review-tenant-query",
            anchors=["tenantId", "403"],
            diff="- const tenantId=session.tenantId;+ const tenantId=req.query.tenantId || session.tenantId;if(!tenantId)return res.status(403).end();",
            ctx="multi_tenant_api",
            deliver="risk mitigation verify",
            must_include=["tenant", "verify", "auth", "risk"],
            exact_literals=["tenantId", "403"],
        ),
        review_row(
            task_id="security-review-role-header",
            anchors=["x-role", "admin"],
            diff="+ const isAdmin=req.headers['x-role']==='admin' || session.isAdmin;",
            ctx="public_admin_route",
            deliver="risk mitigation verify",
            must_include=["header", "admin", "trust", "verify"],
            exact_literals=["x-role", "admin"],
        ),
        review_row(
            task_id="security-review-webhook-signature",
            anchors=["x-signature", "401"],
            diff="- verifySignature(req.headers['x-signature'],rawBody);+ if(process.env.NODE_ENV!=='prod'){return next();}",
            ctx="webhook_receiver",
            deliver="risk mitigation verify",
            must_include=["signature", "verify", "webhook", "risk"],
            exact_literals=["x-signature", "401"],
        ),
        review_row(
            task_id="security-review-open-redirect",
            anchors=["returnTo", "302"],
            diff="+ return res.redirect(req.query.returnTo || '/dashboard');",
            ctx="auth_callback",
            deliver="risk mitigation verify",
            must_include=["redirect", "validate", "verify", "risk"],
            exact_literals=["returnTo", "302"],
        ),
        review_row(
            task_id="security-review-path-traversal",
            anchors=["..", "download"],
            diff="+ const path=baseDir+'/'+req.query.file;res.download(path);",
            ctx="file_download_handler",
            deliver="risk mitigation verify",
            must_include=["path", "validate", "verify", "risk"],
            exact_literals=["..", "download"],
        ),
        review_row(
            task_id="security-review-orderby-sql",
            anchors=["sort", "SELECT"],
            diff="+ const sql='SELECT * FROM invoices ORDER BY '+req.query.sort;",
            ctx="invoice_admin_api",
            deliver="risk mitigation verify",
            must_include=["sql", "validate", "verify", "risk"],
            exact_literals=["sort", "SELECT"],
        ),
        review_row(
            task_id="security-review-cache-poison",
            anchors=["ETag", "304"],
            diff="+ res.set('ETag', req.query.etag || user.profileVersion);if(req.headers['if-none-match']===req.query.etag)return res.status(304).end();",
            ctx="profile_cache_layer",
            deliver="risk mitigation verify",
            must_include=["cache", "etag", "verify", "risk"],
            exact_literals=["ETag", "304"],
        ),
        refactor_row(
            task_id="refactor-callback",
            anchors=["async", "await", "next(err)"],
            target="loadUser",
            order="missing_id>db.findUser>not_found>audit.log>cache.set",
            db_err="next(err)",
            deliver="async_await minimal_change",
            must_include=["async", "await", "verify", "minimal"],
            exact_literals=["async", "await", "next(err)"],
        ),
        refactor_row(
            task_id="refactor-create-invoice",
            anchors=["async", "await", "next(err)"],
            target="createInvoice",
            order="validate_input>db.createInvoice>audit.log>queue.publish>res.json",
            db_err="next(err)",
            deliver="async_await minimal_change",
            must_include=["invoice", "async", "verify", "minimal"],
            exact_literals=["async", "await", "next(err)"],
        ),
        refactor_row(
            task_id="refactor-verify-webhook",
            anchors=["async", "await", "next(err)"],
            target="verifyWebhook",
            order="raw_body>verifySignature>parse_json>db.insertEvent>next",
            db_err="next(err)",
            deliver="async_await minimal_change",
            must_include=["webhook", "async", "verify", "minimal"],
            exact_literals=["async", "await", "next(err)"],
        ),
        refactor_row(
            task_id="refactor-send-email",
            anchors=["async", "await", "next(err)"],
            target="sendEmailReceipt",
            order="load_user>render_template>smtp.send>audit.log>next",
            db_err="next(err)",
            deliver="async_await minimal_change",
            must_include=["email", "async", "verify", "minimal"],
            exact_literals=["async", "await", "next(err)"],
        ),
        refactor_row(
            task_id="refactor-reconcile-batch",
            anchors=["async", "await", "next(err)"],
            target="reconcileBatch",
            order="load_batch>db.fetchRows>apply_rules>db.save>emit_metrics",
            db_err="next(err)",
            deliver="async_await minimal_change",
            must_include=["batch", "async", "verify", "minimal"],
            exact_literals=["async", "await", "next(err)"],
        ),
        refactor_row(
            task_id="refactor-sync-search-index",
            anchors=["async", "await", "next(err)"],
            target="syncSearchIndex",
            order="load_doc>transform>index.upsert>audit.log>done",
            db_err="next(err)",
            deliver="async_await minimal_change",
            must_include=["index", "async", "verify", "minimal"],
            exact_literals=["async", "await", "next(err)"],
        ),
        refactor_row(
            task_id="refactor-cache-bust",
            anchors=["async", "await", "next(err)"],
            target="bustProfileCache",
            order="load_user>cache.del>cache.prime>audit.log>next",
            db_err="next(err)",
            deliver="async_await minimal_change",
            must_include=["cache", "async", "verify", "minimal"],
            exact_literals=["async", "await", "next(err)"],
        ),
        refactor_row(
            task_id="refactor-gateway-user-load",
            anchors=["async", "await", "next(err)"],
            target="loadGatewayUser",
            order="session_check>db.findUser>flags.load>audit.log>next",
            db_err="next(err)",
            deliver="async_await minimal_change",
            must_include=["gateway", "async", "verify", "minimal"],
            exact_literals=["async", "await", "next(err)"],
        ),
    ]
    return rows


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a larger realistic SIGIL micro benchmark corpus.")
    parser.add_argument("--out-dir", type=Path, default=Path("evals"))
    args = parser.parse_args(argv)

    rows = build_rows()
    by_category: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        by_category.setdefault(str(row["category"]), []).append(row)

    write_jsonl(args.out_dir / "tasks_hybrid_micro_extended.jsonl", rows)
    write_jsonl(args.out_dir / "tasks_debug_micro_extended.jsonl", by_category["debugging"])
    write_jsonl(args.out_dir / "tasks_architecture_micro_extended.jsonl", by_category["architecture"])
    write_jsonl(args.out_dir / "tasks_review_micro_extended.jsonl", by_category["code_review"])
    write_jsonl(args.out_dir / "tasks_refactor_micro_extended.jsonl", by_category["refactoring"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

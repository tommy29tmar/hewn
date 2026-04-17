from __future__ import annotations

from .model import Atom, Binary, Call, Clause, Document, Expr, Unary

CLAUSE_LABELS = {
    "G": "Goal",
    "C": "Constraints",
    "H": "Hypothesis",
    "P": "Plan",
    "V": "Verify",
    "R": "Risk",
    "Q": "Open question",
    "M": "Memory",
    "A": "Answer target",
}

OPERATOR_WORDS = {
    "∧": "and",
    "&": "and",
    "∨": "or",
    "|": "or",
    "⇒": "implies",
    "=>": "implies",
    "→": "then",
    "->": "then",
    "≈": "is approximately",
    "⊥": "conflicts with",
}

ATOM_ALIASES = {
    "bc": "backward compatibility",
    "sec": "security",
    "reg_t": "regression test",
    "auth_mw": "auth middleware",
    "skew30": "30-second grace window",
    "skew30_fix": "30-second grace window fix",
    "exp_lt_no_skew": "exp < now without grace window",
    "allow30s_skew": "30-second grace fix",
    "keep_401": "keep 401 behavior",
    "hdr_override": "header override",
    "authz_bypass": "authorization bypass",
    "drop_hdr": "drop the header path",
    "sess_only": "verified session auth only",
    "spoof_denied": "spoofed requests denied",
    "mod_monolith": "modular_monolith",
    "default_arch": "default modular architecture",
    "deliver_arch": "deliver modular architecture",
    "fast_ship": "fast shipping",
    "low_ops": "low ops",
    "ddl": "deadline",
    "same_order": "same validation order",
    "one_next(err)": "single next(err) path",
    "async_await": "async/await",
    "minimal_async_await": "minimal async/await migration",
    "shared_pg": "shared PostgreSQL",
    "slice_ready_modules": "split-ready modules",
    "monolith_now": "ship modular_monolith now",
    "split_cost": "future split cost",
    "premature_distrib": "premature distribution",
    "missing_id_before_db": "missing id check before database call",
    "not_found_before_audit": "not found check before audit",
    "order_change": "validation order change",
    "error_mapping_drift": "error mapping drift",
    "mitigate_path_traversal": "path traversal risk mitigation",
    "prevent_path_traversal": "path traversal risk prevention",
    "mitigate_sqli": "SQL injection risk mitigation",
    "mitigate_sql_injection": "SQL injection risk mitigation",
    "normalize_path": "validate and normalize path",
    "sanitize_input": "validate and sanitize input",
    "sanitize_filename": "validate and sanitize filename",
    "sanitize_req.query.file": "validate req.query.file",
    "whitelist_sort_columns": "validate sort columns allowlist",
    "whitelist_sort_column": "validate sort column allowlist",
    "parameterize": "validate then parameterize",
    "reject_unknown": "validate unknown values rejected",
    "reject_invalid": "validate invalid values rejected",
    "overdue_middleware": "billing overdue middleware",
    "clear_ownership": "clear boundaries and ownership",
    "refactor_reconcileBatch": "async reconcileBatch refactor",
    "patch_reconcileBatch": "async patch reconcileBatch",
    "seam_for_split": "boundaries for later split",
    # Debugging / expiry / webhook vocabulary observed across runs.
    "allow_skew": "allow clock skew",
    "provider_skew": "allow provider-clock skew",
    "skew_budget": "skew budget",
    "widen_window": "widen grace window",
    "widen_tolerance": "widen tolerance window",
    "boundary_guard": "boundary guard",
    "no_loop": "no refresh loop",
    "refresh_no_loop": "refresh without loop",
    "min_fix": "minimal fix",
    "min_diff": "minimal diff",
    "reg_test": "regression test",
    "abs_now_ts": "abs(now - ts)",
    "webhook_verify": "webhook verification",
    "valid_webhook_rejected": "valid webhook wrongly rejected",
    "valid_webhook_dropped": "valid webhook dropped",
    "grace_window": "grace window",
    "grace_exact": "exact grace encoding",
    "grace_honored": "grace window honored",
    "boundary_pass": "boundary case passes",
    "boundary_loop": "boundary charge loop",
    "no_regression": "no regression",
    "emit_401_outside": "emit 401 outside window",
    # Architecture vocabulary.
    "bounded_modules": "bounded domain modules",
    "bounded_contexts": "bounded contexts",
    "single_db": "single shared database",
    "schema_per_module": "schema per module",
    "async_outbox": "async outbox pattern",
    "audit_log": "audit log",
    "fits_team": "fits team size",
    "meets_ddl": "meets deadline",
    "compliance_ready": "compliance-ready",
    "low_ops_burden": "low operational burden",
    "worker_sidecar": "worker sidecar",
    "pg_queue": "PostgreSQL-backed queue",
    "idempotent_jobs": "idempotent jobs",
    "backpressure": "backpressure",
    "short_why": "short rationale",
    # Security-review vocabulary.
    "confine_baseDir": "confine to baseDir",
    "resolved_within_baseDir": "resolved path within baseDir",
    "symlink_checked": "symlink traversal checked",
    "parameterize_query": "parameterize query",
    "reject_invalid_input": "reject invalid input",
    "static_analysis": "static analysis",
    "injection_test": "injection test",
    "review_allowed_columns": "review allowed columns",
    # Refactor vocabulary.
    "preserve_order": "preserve execution order",
    "order_preserved": "order preserved",
    "anchors_intact": "literal anchors intact",
    "anchors_verbatim": "literal anchors verbatim",
    "convert_async_await": "convert to async/await",
    "wrap_db_try": "wrap database calls in try",
    "call_next_err": "forward via next(err)",
    "keep_audit_log": "keep audit.log call",
    "final_next": "final next()",
    "try_catch": "try/catch",
    "session_check": "session check",
}

PREFIX_MARKERS = {
    "!": "high-risk",
    "?": "uncertain",
}

POSTFIX_MARKERS = {
    "!": "high-risk",
    "?": "uncertain",
}


def _expand_atom(value: str, codebook: dict[str, str]) -> str:
    return codebook.get(value, ATOM_ALIASES.get(value, value))


def render_expr(expr: Expr, codebook: dict[str, str] | None = None) -> str:
    codebook = codebook or {}

    if isinstance(expr, Atom):
        return _expand_atom(expr.value, codebook)

    if isinstance(expr, Call):
        args = ", ".join(render_expr(arg, codebook) for arg in expr.args)
        return f"{_expand_atom(expr.name, codebook)}({args})"

    if isinstance(expr, Unary):
        body = render_expr(expr.expr, codebook)
        label = PREFIX_MARKERS[expr.operator] if expr.position == "prefix" else POSTFIX_MARKERS[expr.operator]
        if expr.position == "prefix":
            return f"{label} {body}"
        return f"{body} ({label})"

    if isinstance(expr, Binary):
        left = render_expr(expr.left, codebook)
        right = render_expr(expr.right, codebook)
        word = OPERATOR_WORDS.get(expr.operator, expr.operator)
        return f"{left} {word} {right}"

    raise TypeError(f"Unsupported expression: {expr!r}")


def render_clause(clause: Clause, codebook: dict[str, str] | None = None) -> str:
    label = CLAUSE_LABELS.get(clause.tag, clause.tag)
    return f"{label}: {render_expr(clause.expr, codebook)}."


def generate_audit(document: Document) -> str:
    if document.audit:
        return document.audit.strip()
    return "\n".join(render_clause(clause, document.codebook) for clause in document.clauses)

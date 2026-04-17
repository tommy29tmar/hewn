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

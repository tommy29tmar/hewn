from __future__ import annotations

import re

from .model import Document
from .render import generate_audit

TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def approx_token_count(text: str) -> int:
    return len(TOKEN_RE.findall(text))


def document_metrics(document: Document, raw_text: str) -> dict[str, object]:
    audit = generate_audit(document)
    mode = document.header.mode if document.header else None
    tags = [clause.tag for clause in document.clauses]
    return {
        "mode": mode,
        "clause_count": len(document.clauses),
        "clause_tags": tags,
        "codebook_size": len(document.codebook),
        "has_audit": bool(document.audit),
        "raw_chars": len(raw_text),
        "raw_lines": len(raw_text.splitlines()),
        "raw_tokens_est": approx_token_count(raw_text),
        "audit_chars": len(audit),
        "audit_tokens_est": approx_token_count(audit),
    }


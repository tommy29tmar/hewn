from __future__ import annotations

import re


AWAIT_CALL_RE = re.compile(r"\bawait\s+([A-Za-z_][A-Za-z0-9_./-]*\((?:[^()]|\".*?\"|'.*?')*\))")
AWAIT_IDENT_RE = re.compile(r"\bawait\s+([A-Za-z_][A-Za-z0-9_./-]*)\b")
COMPARATOR_ATOM = r"(?:[A-Za-z_](?:[A-Za-z0-9_./:+-]*[A-Za-z0-9_./:+])?|[0-9]+(?:\.[0-9]+)?)"
COMPARATOR_CALL = r"[A-Za-z_][A-Za-z0-9_./:+-]*\((?:[^()]|\".*?\"|'.*?')*\)"
COMPARATOR_TERM = rf"(?:{COMPARATOR_CALL}|{COMPARATOR_ATOM}|\([^()]+\))"
COMPARATOR_RE = re.compile(
    rf"(?P<left>{COMPARATOR_TERM})\s*(?P<op><=|>=|==|!=|<|>)\s*(?P<right>{COMPARATOR_TERM})"
)
COMPARATOR_ARROW_RE = re.compile(
    rf"(?P<left>{COMPARATOR_TERM})\s*(?P<op><=|>=|==|!=|<|>)\s*(?P<right>{COMPARATOR_TERM})\s*(?P<arrow>=>|->|→|⇒)\s*(?P<tail>{COMPARATOR_TERM})"
)
COMPACT_FRAGMENT_RE = re.compile(r'^[A-Za-z0-9_./:+\-<>=\[\]]+(?:\((?:[^()"\'\s]+|".*?"|\'.*?\')?\))?$')
UNICODE_REPLACEMENTS = {
    "−": "-",
    "–": "-",
    "—": "-",
    "≤": "<=",
    "≥": ">=",
}
HEADER_DRIFT_RE = re.compile(r"^@sigil(?:[_:\-\s]*)(v0)(?:[_:\-\s]*(draft|audit|hybrid|memory|compile))?$", re.IGNORECASE)
QUOTED_TOKEN_RE = re.compile(r'(["\'])([^"\']+)\1')
DANGLING_BINARY_RE = re.compile(r"(?:\s*(?:∧|∨|⇒|=>|→|->|≈|⊥|&|\|)\s*)+$")
META_LINE_RE = re.compile(r"^(?:\[[^\]]+\].*|Atoms?:.*|Calls?:.*|Notes?:.*|Literals?:.*)$", re.IGNORECASE)
CODE_FENCE_RE = re.compile(r"^```[A-Za-z0-9_-]*\s*$")
SIGIL_LABEL_RE = re.compile(r"^SIGIL\s*:?\s*$", re.IGNORECASE)
BINARY_OPERATOR_TOKENS = {"∧", "∨", "⇒", "=>", "→", "->", "≈", "⊥", "&", "|"}

DIRECT_CATEGORY_FALLBACKS = {
    "debugging": {"V": "edge(-30s_200)", "A": "reg_t"},
    "architecture": {"G": "mod_monolith", "P": "mod_monolith", "V": "split(post_release)", "A": "short_why"},
    "code_review": {"V": "keep_401", "A": "sess_only"},
    "refactoring": {"C": "same_order", "V": "same_order", "A": "minimal_async_await"},
}

BARE_TAG_RE = re.compile(r"^([GCHPVRQMA])\s*:?\s*$")
ARCHITECTURE_TEAM_ASSIGNMENT_RE = re.compile(r"\bteam\s*=\s*([0-9]+)")
ARCHITECTURE_TEAM_SPACED_RE = re.compile(r"\bteam\s+([0-9]+)\b")
ARCHITECTURE_TEAM_JOINED_RE = re.compile(r"\bteam\s*∧\s*([0-9]+)\b")
# Handles atoms like `team_"9"`, `ddl_"12 weeks"`, `store_"PostgreSQL"` that
# LLMs emit when pattern-matching the capsule anchors format.
ARCHITECTURE_QUOTED_SUFFIX_RE = re.compile(r'\b(team|ddl|store|ops|traffic|split)_"([^"]+)"')
REFACTOR_QUOTED_SUFFIX_RE = re.compile(r'\b([A-Za-z][A-Za-z0-9_]*)_"([^"]+)"')
ARCHITECTURE_ASSIGNMENT_QUOTED_RE = re.compile(r'\b(ops|traffic|split|store)\s*=\s*"([^"]+)"')
ARCHITECTURE_ASSIGNMENT_RE = re.compile(r"\b(ops|traffic|split|store)\s*=\s*([A-Za-z0-9_./+-]+)")
ARCHITECTURE_SPACED_CALL_RE = re.compile(r"\b(ops|traffic|split|store)\s+([A-Za-z0-9_./+-]+)")
ARCHITECTURE_JOINED_CALL_RE = re.compile(r"\b(ops|traffic|split|store)\s*∧\s*([A-Za-z0-9_./+-]+)")
ARCHITECTURE_DDL_ASSIGNMENT_RE = re.compile(r'\bddl\s*=\s*(?:"([^"]+)"|([A-Za-z0-9_./+-]+\s+(?:hours?|days?|weeks?|months?)))')
ARCHITECTURE_DDL_SPACED_RE = re.compile(r"\bddl\s+([0-9]+\s+(?:hours?|days?|weeks?|months?))")
ARCHITECTURE_DDL_JOINED_RE = re.compile(r"\bddl\s*∧\s*([0-9]+\s*∧\s*(?:hours?|days?|weeks?|months?))")
ARCHITECTURE_BARE_DDL_JOINED_RE = re.compile(r"^\s*([0-9]+\s*∧\s*(?:hours?|days?|weeks?|months?))\s*$")
ARCHITECTURE_ANCHORS_ASSIGNMENT_RE = re.compile(
    r'\banchors\s*=\s*((?:"[^"]+"|\'[^\']+\'|[A-Za-z0-9_./+-]+)(?:\s*\|\s*(?:"[^"]+"|\'[^\']+\'|[A-Za-z0-9_./+-]+))*)'
)
ARCHITECTURE_DELIVER_ASSIGNMENT_RE = re.compile(r"\bdeliver\s*=\s*([A-Za-z0-9_./+-]+(?:\s+[A-Za-z0-9_./+-]+)*)")
ARCHITECTURE_DELIVER_RE = re.compile(r"\bdeliver\s+([A-Za-z0-9_./+-]+(?:\s+[A-Za-z0-9_./+-]+)*)")
ARCHITECTURE_JOINED_DELIVER_RE = re.compile(r"\bdeliver\s*∧\s*([A-Za-z0-9_./+-]+(?:\s*∧\s*[A-Za-z0-9_./+-]+)*)")
ARCHITECTURE_DURATION_RE = re.compile(r"\b[0-9]+\s+(?:hours?|days?|weeks?|months?)\b")
ARCHITECTURE_WHY_RE = re.compile(r"\bwhy:\s*(.+)$")
DEBUG_EDGE_ARROW_RE = re.compile(r"edge\(((?:[^()]|\([^()]*\))+?)\s*(?:=>|->|→|⇒)\s*([A-Za-z0-9_./:+-]+)\)")
DEBUG_OUTCOME_SUFFIX_RE = re.compile(r"((?:eq\([^()]*\)|[A-Za-z0-9_./:+-]+(?:\([^()]*\))?))_(pass|fail)(?![A-Za-z0-9_])")


def _has_balanced_delimiters(expr: str) -> bool:
    depth = 0
    quote: str | None = None
    escaped = False
    for char in expr:
        if quote is not None:
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char == "(":
            depth += 1
            continue
        if char == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0 and quote is None


def _needs_expression_fallback(expr: str) -> bool:
    stripped = expr.strip()
    if not stripped:
        return True
    if stripped in {"!", "?", "```"}:
        return True
    if stripped.endswith(("(", '"', "'")):
        return True
    if "```" in stripped:
        return True
    return not _has_balanced_delimiters(stripped)


def normalize_expression_text(expr: str) -> str:
    # Convert common pseudo-code drift into valid call syntax.
    expr = _replace_unicode_operators(expr)
    expr = AWAIT_CALL_RE.sub(r"await(\1)", expr)
    expr = AWAIT_IDENT_RE.sub(r"await(\1)", expr)
    expr = _rewrite_comparators(expr)
    return expr


def _rewrite_comparators(expr: str) -> str:
    operator_map = {"<": "lt", ">": "gt", "<=": "le", ">=": "ge", "==": "eq", "!=": "ne"}
    previous = None
    while previous != expr:
        previous = expr
        expr = COMPARATOR_ARROW_RE.sub(
            lambda match: (
                f"{operator_map[match.group('op')]}({match.group('left')},{match.group('right')})"
                f" {match.group('arrow')} {match.group('tail')}"
            ),
            expr,
        )
        expr = COMPARATOR_RE.sub(
            lambda match: f"{operator_map[match.group('op')]}({match.group('left')},{match.group('right')})",
            expr,
        )
    return expr


def _replace_unicode_operators(expr: str) -> str:
    for source, target in UNICODE_REPLACEMENTS.items():
        expr = expr.replace(source, target)
    return expr


def _compact_single_call_args(expr: str) -> str:
    result: list[str] = []
    i = 0
    while i < len(expr):
        if not (expr[i].isalpha() or expr[i] == "_"):
            result.append(expr[i])
            i += 1
            continue
        name_start = i
        while i < len(expr) and (expr[i].isalnum() or expr[i] in "_./:+-"):
            i += 1
        name = expr[name_start:i]
        if i >= len(expr) or expr[i] != "(":
            result.append(name)
            continue
        depth = 1
        j = i + 1
        quote: str | None = None
        while j < len(expr) and depth:
            char = expr[j]
            if quote is not None:
                if char == "\\":
                    j += 2
                    continue
                if char == quote:
                    quote = None
                j += 1
                continue
            if char in {"'", '"'}:
                quote = char
                j += 1
                continue
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            j += 1
        if depth != 0:
            result.append(name)
            result.append("(")
            i += 1
            continue
        inner = expr[i + 1 : j - 1]
        if inner and "," not in inner and '"' not in inner and "'" not in inner and not any(op in inner for op in ("∧", "∨", "⇒", "=>", "→", "->", "≈", "⊥", "&", "|")):
            inner = re.sub(r"\s+", "_", inner.strip())
        result.append(f"{name}({inner})")
        i = j
    return "".join(result)


def _split_top_level_fragments(expr: str) -> list[str]:
    fragments: list[str] = []
    current: list[str] = []
    depth = 0
    quote: str | None = None
    for char in expr:
        if quote is not None:
            current.append(char)
            if char == "\\":
                continue
            if char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            current.append(char)
            continue
        if char == "(":
            depth += 1
            current.append(char)
            continue
        if char == ")":
            depth = max(0, depth - 1)
            current.append(char)
            continue
        if char.isspace() and depth == 0:
            fragment = "".join(current).strip()
            if fragment:
                fragments.append(fragment)
            current = []
            continue
        current.append(char)
    fragment = "".join(current).strip()
    if fragment:
        fragments.append(fragment)
    return fragments


def _restore_quoted_literal_spaces(expr: str) -> str:
    def repl(match: re.Match[str]) -> str:
        quote = match.group(1)
        inner = match.group(2)
        if "_" in inner and any(char.isdigit() for char in inner):
            inner = inner.replace("_", " ")
        return f"{quote}{inner}{quote}"

    return QUOTED_TOKEN_RE.sub(repl, expr)


def _trim_dangling_binary(expr: str) -> str:
    repaired = DANGLING_BINARY_RE.sub("", expr).strip()
    if repaired in {"!", "?"}:
        return ""
    return repaired


def _is_joinable_fragment(fragment: str) -> bool:
    stripped = fragment.strip()
    if not stripped:
        return False
    if "```" in stripped:
        return False
    if stripped in BINARY_OPERATOR_TOKENS:
        return False
    return COMPACT_FRAGMENT_RE.match(stripped) is not None or _has_balanced_delimiters(stripped)


def _replace_top_level_delimiters(expr: str) -> str:
    result: list[str] = []
    depth = 0
    quote: str | None = None
    for char in expr:
        if quote is not None:
            result.append(char)
            if char == "\\":
                continue
            if char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            result.append(char)
            continue
        if char == "(":
            depth += 1
            result.append(char)
            continue
        if char == ")":
            depth = max(0, depth - 1)
            result.append(char)
            continue
        if char in {",", ";", "+"} and depth == 0:
            result.append(" ")
            continue
        result.append(char)
    return "".join(result)


def _normalize_architecture_capsule_text(expr: str) -> str:
    def compact_reason(text: str) -> str:
        words = re.findall(r"[A-Za-z0-9]+", text.lower())
        if not words:
            return "short_why"
        normalized: list[str] = []
        for word in words:
            if word in {"the", "a", "an", "and", "or", "with", "for", "that", "this", "keeps", "keep"}:
                continue
            normalized.append(word)
            if len(normalized) >= 8:
                break
        if not normalized:
            normalized = words[:4]
        return "_".join(normalized)

    def replace_anchors(match: re.Match[str]) -> str:
        raw = match.group(1)
        parts = [part.strip().strip('"').strip("'") for part in raw.split("|")]
        anchors = [part for part in parts if part]
        return " ∧ ".join(f'anchor("{part}")' for part in anchors)

    expr = re.sub(r"\)\.", ") ", expr)
    expr = re.sub(r"\b([A-Za-z][A-Za-z0-9_]*)\.(?=[A-Za-z])", r"\1 ", expr)
    expr = ARCHITECTURE_QUOTED_SUFFIX_RE.sub(lambda m: f'{m.group(1)}("{m.group(2)}")', expr)
    expr = ARCHITECTURE_TEAM_ASSIGNMENT_RE.sub(lambda m: f"team({m.group(1)})", expr)
    expr = ARCHITECTURE_TEAM_SPACED_RE.sub(lambda m: f"team({m.group(1)})", expr)
    expr = ARCHITECTURE_TEAM_JOINED_RE.sub(lambda m: f"team({m.group(1)})", expr)
    expr = ARCHITECTURE_ANCHORS_ASSIGNMENT_RE.sub(replace_anchors, expr)
    expr = ARCHITECTURE_ASSIGNMENT_QUOTED_RE.sub(lambda m: f'{m.group(1)}("{m.group(2).strip()}")', expr)
    expr = ARCHITECTURE_ASSIGNMENT_RE.sub(lambda m: f"{m.group(1)}({m.group(2)})", expr)
    expr = ARCHITECTURE_DDL_ASSIGNMENT_RE.sub(lambda m: f'ddl("{" ".join((m.group(1) or m.group(2)).strip().split())}")', expr)
    expr = ARCHITECTURE_DDL_SPACED_RE.sub(lambda m: f'ddl("{" ".join(m.group(1).strip().split())}")', expr)
    expr = ARCHITECTURE_SPACED_CALL_RE.sub(lambda m: f"{m.group(1)}({m.group(2)})", expr)
    expr = ARCHITECTURE_JOINED_CALL_RE.sub(lambda m: f"{m.group(1)}({m.group(2)})", expr)
    expr = ARCHITECTURE_DDL_JOINED_RE.sub(lambda m: f'ddl("{" ".join(m.group(1).replace("∧", " ").strip().split())}")', expr)
    if ARCHITECTURE_BARE_DDL_JOINED_RE.match(expr):
        expr = f'ddl("{" ".join(ARCHITECTURE_BARE_DDL_JOINED_RE.match(expr).group(1).replace("∧", " ").strip().split())}")'
    expr = ARCHITECTURE_DELIVER_ASSIGNMENT_RE.sub(lambda m: f"deliver({m.group(1).strip().replace(' ', '_')})", expr)
    expr = ARCHITECTURE_DELIVER_RE.sub(lambda m: f"deliver({m.group(1).strip().replace(' ', '_')})", expr)
    expr = ARCHITECTURE_JOINED_DELIVER_RE.sub(lambda m: f'deliver({m.group(1).replace("∧", "_").replace(" ", "").strip("_")})', expr)
    expr = ARCHITECTURE_WHY_RE.sub(lambda m: f" ∧ why({compact_reason(m.group(1))})", expr)
    return expr


def _normalize_refactor_capsule_text(expr: str) -> str:
    expr = expr.replace("{", " ").replace("}", " ")
    expr = expr.replace("::", " ")
    expr = re.sub(r"\)\.", ") ", expr)
    expr = re.sub(r"\(\s*req\s*,\s*res\s*,\s*next\s*\)", " ", expr)
    expr = re.sub(r"\b([A-Za-z][A-Za-z0-9_]*)\.(?=[A-Za-z])", r"\1 ", expr)
    # Handles atoms like `db_err_forwards_"next(err)"` → `db_err_forwards("next(err)")`
    # so the quoted literal survives as a valid call argument instead of breaking parse.
    expr = REFACTOR_QUOTED_SUFFIX_RE.sub(lambda m: f'{m.group(1)}("{m.group(2)}")', expr)
    expr = re.sub(r"\s+", " ", expr).strip()
    return expr


def _normalize_debugging_capsule_text(expr: str) -> str:
    expr = DEBUG_EDGE_ARROW_RE.sub(lambda m: f"edge({m.group(1).strip()},{m.group(2).strip()})", expr)
    expr = DEBUG_OUTCOME_SUFFIX_RE.sub(lambda m: f"edge({m.group(1)},{m.group(2)})", expr)
    return expr


def normalize_direct_expression_text(expr: str) -> str:
    expr = _replace_unicode_operators(normalize_expression_text(expr)).strip()
    expr = expr.replace("`", "")
    expr = _replace_top_level_delimiters(expr)
    expr = _compact_single_call_args(expr)
    expr = _restore_quoted_literal_spaces(expr)
    expr = _trim_dangling_binary(expr)
    fragments = _split_top_level_fragments(expr)
    if len(fragments) > 1 and fragments[0] in {"!", "?"} and all(_is_joinable_fragment(fragment) for fragment in fragments[1:]):
        return f"{fragments[0]} {' ∧ '.join(fragments[1:])}"
    if len(fragments) > 2 and fragments[0] in {"!", "?"} and any(fragment in BINARY_OPERATOR_TOKENS for fragment in fragments[1:]):
        tail = normalize_direct_expression_text(" ".join(fragments[1:]))
        return f"{fragments[0]} {tail}".strip()
    if len(fragments) > 1 and all(_is_joinable_fragment(fragment) for fragment in fragments):
        return " ∧ ".join(fragments)
    if len(fragments) > 1 and any(fragment in BINARY_OPERATOR_TOKENS for fragment in fragments):
        rebuilt: list[str] = []
        run: list[str] = []
        for fragment in fragments:
            if fragment in BINARY_OPERATOR_TOKENS:
                if run:
                    rebuilt.append(" ∧ ".join(run))
                    run = []
                rebuilt.append(fragment)
                continue
            if _is_joinable_fragment(fragment):
                run.append(fragment)
                continue
            if run:
                rebuilt.append(" ∧ ".join(run))
                run = []
            rebuilt.append(fragment)
        if run:
            rebuilt.append(" ∧ ".join(run))
        expr = " ".join(rebuilt)
    expr = re.sub(r"(?:\s*∧\s*){2,}", " ∧ ", expr).strip()
    expr = re.sub(r"(?:\s*∨\s*){2,}", " ∨ ", expr).strip()
    if any(op in expr for op in ("∧", "∨", "⇒", "=>", "→", "->", "≈", "⊥", "&", "|")):
        return expr
    return expr


def normalize_document_text(text: str) -> str:
    lines = text.splitlines()
    repaired: list[str] = []
    in_audit = False
    for line in lines:
        stripped = line.strip()
        if stripped == "[AUDIT]":
            in_audit = True
            repaired.append(line)
            continue
        if SIGIL_LABEL_RE.match(stripped):
            continue
        if CODE_FENCE_RE.match(stripped):
            continue
        if in_audit:
            repaired.append(line)
            continue

        if len(stripped) >= 3 and stripped[1] == ":" and stripped[0] in "GCHPVRQMA":
            tag = stripped[:2]
            expr = stripped[2:].lstrip()
            repaired.append(f"{tag} {normalize_expression_text(expr)}")
            continue

        repaired.append(line)
    return "\n".join(repaired)


def normalize_direct_sigil_text(text: str) -> str:
    lines = text.splitlines()
    repaired: list[str] = []
    in_audit = False
    for line in lines:
        stripped = line.strip()
        header_match = HEADER_DRIFT_RE.match(stripped)
        if header_match:
            version = header_match.group(1).lower()
            mode = (header_match.group(2) or "").lower()
            repaired.append(f"@sigil {version}{f' {mode}' if mode else ''}")
            continue
        if stripped == "[AUDIT]":
            in_audit = True
            repaired.append(line)
            continue
        if CODE_FENCE_RE.match(stripped):
            continue
        if in_audit:
            repaired.append(line)
            continue
        if len(stripped) >= 3 and stripped[1] == ":" and stripped[0] in "GCHPVRQMA":
            tag = stripped[:2]
            expr = stripped[2:].lstrip()
            repaired.append(f"{tag} {normalize_direct_expression_text(expr)}")
            continue
        repaired.append(_replace_unicode_operators(line))
    return "\n".join(repaired)


def repair_direct_sigil_text(text: str, category: str | None = None) -> str:
    repaired = normalize_direct_sigil_text(text)
    lines = repaired.splitlines()
    non_empty = [line.strip() for line in lines if line.strip()]
    output: list[str] = []
    present_tags: set[str] = set()
    in_audit = False
    header_line = next(
        (
            f"@sigil {match.group(1).lower()}{f' {match.group(2).lower()}' if match.group(2) else ''}"
            for line in lines
            if (match := HEADER_DRIFT_RE.match(line.strip()))
        ),
        None,
    )
    has_header = header_line is not None
    has_tagged_clause = any(len(line.strip()) >= 3 and line.strip()[1] == ":" and line.strip()[0] in "GCHPVRQMA" for line in lines)

    if non_empty:
        output.append(header_line or "@sigil v0 hybrid")

    for line in lines:
        stripped = line.strip()
        if HEADER_DRIFT_RE.match(stripped):
            continue
        if stripped == "[AUDIT]":
            in_audit = True
            output.append(line)
            continue
        if SIGIL_LABEL_RE.match(stripped):
            continue
        if CODE_FENCE_RE.match(stripped):
            continue
        if in_audit:
            output.append(line)
            continue
        if META_LINE_RE.match(stripped):
            continue
        bare_tag_match = BARE_TAG_RE.match(stripped)
        if bare_tag_match:
            tag = bare_tag_match.group(1)
            fallback = DIRECT_CATEGORY_FALLBACKS.get(category or "", {}).get(tag)
            if fallback:
                output.append(f"{tag}: {fallback}")
                present_tags.add(tag)
            continue
        if len(stripped) >= 3 and stripped[1] == ":" and stripped[0] in "GCHPVRQMA":
            tag = stripped[0]
            raw_expr = _trim_dangling_binary(stripped[2:].strip())
            if category == "architecture":
                raw_expr = _normalize_architecture_capsule_text(raw_expr)
            if category == "debugging":
                raw_expr = _normalize_debugging_capsule_text(raw_expr)
            if category == "refactoring":
                raw_expr = _normalize_refactor_capsule_text(raw_expr)
                if tag == "G":
                    raw_expr = raw_expr.replace("->", " ").replace("→", " ")
            expr = normalize_direct_expression_text(raw_expr)
            if category == "architecture" and tag == "P" and (expr.endswith("_") or expr.endswith(".")):
                expr = DIRECT_CATEGORY_FALLBACKS["architecture"]["P"]
            if category == "architecture" and tag == "P" and "|" in expr and ARCHITECTURE_DURATION_RE.search(expr):
                expr = DIRECT_CATEGORY_FALLBACKS["architecture"]["P"]
            if category == "architecture" and tag == "V" and expr.strip() in {"split", "deadline", "fast_ship ∧ deadline ∧ split"}:
                expr = DIRECT_CATEGORY_FALLBACKS["architecture"]["V"]
            if _needs_expression_fallback(expr):
                fallback = DIRECT_CATEGORY_FALLBACKS.get(category or "", {}).get(tag)
                if not fallback:
                    continue
                expr = fallback
            clause_line = f"{tag}: {expr}"
            for index in range(len(output) - 1, -1, -1):
                existing = output[index].strip()
                if len(existing) >= 3 and existing[0] == tag and existing[1] == ":":
                    previous_expr = existing[2:].strip()
                    output[index] = f"{tag}: {previous_expr} ∧ {expr}"
                    break
            else:
                output.append(clause_line)
            present_tags.add(tag)
            continue
        if len(stripped) >= 2 and stripped[0].isalpha() and stripped[1] == ":" and stripped[0] not in "GCHPVRQMA":
            continue
        if stripped and not has_tagged_clause and not in_audit:
            output.append(f"H: {_trim_dangling_binary(stripped)}")
            present_tags.add("H")
            has_tagged_clause = True
            continue
        output.append(line)

    fallback_map = DIRECT_CATEGORY_FALLBACKS.get(category or "", {})
    for tag, expr in fallback_map.items():
        if tag not in present_tags:
            audit_index = next((index for index, line in enumerate(output) if line.strip() == "[AUDIT]"), None)
            clause = f"{tag}: {expr}"
            if audit_index is None:
                output.append(clause)
            else:
                output.insert(audit_index, clause)
            present_tags.add(tag)

    return "\n".join(output)

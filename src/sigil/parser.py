from __future__ import annotations

import json
import re
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Iterable

from .model import Atom, Binary, Call, Clause, Document, Expr, Header, Unary

HEADER_RE = re.compile(r"^@sigil\s+(v0)(?:\s+(draft|audit|hybrid|memory|compile))?\s*$")
CLAUSE_RE = re.compile(r"^(G|C|H|P|V|R|Q|M|A):\s*(.+?)\s*$")
BINDING_RE = re.compile(r"^([^\s=;]+)\s*=\s*(.+)$")
BINARY_OPS = ("=>", "->", "∧", "∨", "⇒", "→", "≈", "⊥", "&", "|")
MARKERS = {"?", "!"}
PUNCTUATION = {"(", ")", ","}


class SIGILParseError(ValueError):
    pass


def _to_jsonable(value: object) -> object:
    if is_dataclass(value):
        return {key: _to_jsonable(getattr(value, key)) for key in value.__dataclass_fields__}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value


def document_to_data(document: Document) -> dict[str, object]:
    return _to_jsonable(document)


class _ExpressionTokenizer:
    def __init__(self, source: str):
        self.source = source
        self.tokens = self._tokenize()
        self.index = 0

    def _tokenize(self) -> list[str]:
        tokens: list[str] = []
        i = 0
        while i < len(self.source):
            char = self.source[i]
            if char.isspace():
                i += 1
                continue

            if self.source.startswith("=>", i) or self.source.startswith("->", i):
                tokens.append(self.source[i : i + 2])
                i += 2
                continue

            if char in BINARY_OPS or char in MARKERS or char in PUNCTUATION:
                tokens.append(char)
                i += 1
                continue

            if char in {"'", '"'}:
                quote = char
                j = i + 1
                escaped = False
                while j < len(self.source):
                    current = self.source[j]
                    if escaped:
                        escaped = False
                    elif current == "\\":
                        escaped = True
                    elif current == quote:
                        break
                    j += 1
                if j >= len(self.source) or self.source[j] != quote:
                    raise SIGILParseError(f"Unterminated string literal: {self.source[i:]}")
                tokens.append(self.source[i : j + 1])
                i = j + 1
                continue

            j = i
            while j < len(self.source):
                if self.source.startswith("=>", j) or self.source.startswith("->", j):
                    break
                current = self.source[j]
                if current.isspace() or current in MARKERS or current in PUNCTUATION or current in {"∧", "∨", "⇒", "→", "≈", "⊥", "&", "|"}:
                    break
                j += 1
            tokens.append(self.source[i:j])
            i = j
        return tokens

    def peek(self) -> str | None:
        if self.index >= len(self.tokens):
            return None
        return self.tokens[self.index]

    def pop(self) -> str:
        token = self.peek()
        if token is None:
            raise SIGILParseError("Unexpected end of expression")
        self.index += 1
        return token


def _parse_expr(source: str) -> Expr:
    tokenizer = _ExpressionTokenizer(source)

    def parse_expression() -> Expr:
        expr = parse_factor()
        while tokenizer.peek() in BINARY_OPS:
            operator = tokenizer.pop()
            right = parse_factor()
            expr = Binary(left=expr, operator=operator, right=right)
        return expr

    def parse_factor() -> Expr:
        prefixes: list[str] = []
        while tokenizer.peek() in MARKERS:
            prefixes.append(tokenizer.pop())

        expr = parse_primary()

        for operator in reversed(prefixes):
            expr = Unary(operator=operator, expr=expr, position="prefix")

        while tokenizer.peek() in MARKERS:
            expr = Unary(operator=tokenizer.pop(), expr=expr, position="postfix")

        return expr

    def parse_primary() -> Expr:
        token = tokenizer.peek()
        if token is None:
            raise SIGILParseError("Missing expression")

        if token == "(":
            tokenizer.pop()
            expr = parse_expression()
            if tokenizer.pop() != ")":
                raise SIGILParseError("Expected ')' to close grouped expression")
            return expr

        name = tokenizer.pop()
        if tokenizer.peek() == "(":
            tokenizer.pop()
            args: list[Expr] = []
            if tokenizer.peek() != ")":
                while True:
                    args.append(parse_expression())
                    if tokenizer.peek() == ",":
                        tokenizer.pop()
                        continue
                    break
            if tokenizer.pop() != ")":
                raise SIGILParseError("Expected ')' to close function call")
            return Call(name=name, args=args)

        return Atom(value=name)

    expression = parse_expression()
    if tokenizer.peek() is not None:
        raise SIGILParseError(f"Unexpected trailing token: {tokenizer.peek()}")
    return expression


def _split_bindings(block: str) -> Iterable[str]:
    parts: list[str] = []
    current: list[str] = []
    quote: str | None = None
    escape = False
    for char in block:
        if quote is not None:
            current.append(char)
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            current.append(char)
            continue
        if char == ";":
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
            continue
        current.append(char)
    part = "".join(current).strip()
    if part:
        parts.append(part)
    return parts


def parse_document(source: str | Path) -> Document:
    if isinstance(source, Path):
        text = source.read_text(encoding="utf-8")
    elif isinstance(source, str) and "\n" not in source:
        try:
            path_candidate = Path(source)
            if len(source) < 240 and path_candidate.exists():
                text = path_candidate.read_text(encoding="utf-8")
            else:
                text = str(source)
        except OSError:
            text = str(source)
    else:
        text = str(source)

    lines = text.splitlines()
    document = Document()
    index = 0

    def skip_non_content(i: int) -> int:
        while i < len(lines):
            stripped = lines[i].strip()
            if not stripped or stripped.startswith("#"):
                i += 1
                continue
            break
        return i

    index = skip_non_content(index)
    if index < len(lines):
        match = HEADER_RE.match(lines[index].strip())
        if match:
            document.header = Header(version=match.group(1), mode=match.group(2))
            index += 1

    index = skip_non_content(index)
    if index < len(lines) and lines[index].lstrip().startswith("@cb["):
        codebook_lines = [lines[index]]
        while "]" not in codebook_lines[-1]:
            index += 1
            if index >= len(lines):
                raise SIGILParseError("Unterminated codebook block")
            codebook_lines.append(lines[index])
        joined = "\n".join(codebook_lines)
        start = joined.find("@cb[") + len("@cb[")
        end = joined.rfind("]")
        raw_bindings = joined[start:end]
        for binding in _split_bindings(raw_bindings):
            match = BINDING_RE.match(binding)
            if not match:
                raise SIGILParseError(f"Invalid codebook binding: {binding}")
            symbol = match.group(1).strip()
            value = match.group(2).strip()
            if symbol in document.codebook:
                raise SIGILParseError(f"Duplicate codebook symbol: {symbol}")
            document.codebook[symbol] = value
        index += 1

    index = skip_non_content(index)
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped or stripped.startswith("#"):
            index += 1
            continue
        if stripped == "[AUDIT]":
            audit_lines = lines[index + 1 :]
            document.audit = "\n".join(audit_lines).strip()
            break

        match = CLAUSE_RE.match(lines[index])
        if not match:
            raise SIGILParseError(f"Invalid clause on line {index + 1}: {lines[index]}")
        tag = match.group(1)
        raw_expr = match.group(2)
        clause = Clause(tag=tag, expr=_parse_expr(raw_expr), raw=raw_expr, line=index + 1)
        document.clauses.append(clause)
        index += 1

    validate_document(document)
    return document


def validate_document(document: Document) -> None:
    if not document.clauses:
        raise SIGILParseError("A SIGIL document must contain at least one clause")

    mode = document.header.mode if document.header else None
    if mode == "memory" and any(clause.tag != "M" for clause in document.clauses):
        raise SIGILParseError("Mode=memory documents may only contain M: clauses")
    if mode == "hybrid" and not document.audit:
        raise SIGILParseError("Mode=hybrid documents must include an [AUDIT] block")


def parse_json(path: str | Path) -> str:
    document = parse_document(path)
    return json.dumps(document_to_data(document), indent=2, ensure_ascii=False)

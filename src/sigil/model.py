from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Mode = Literal["draft", "audit", "hybrid", "memory", "compile"]
Tag = Literal["G", "C", "H", "P", "V", "R", "Q", "M", "A"]


@dataclass(slots=True)
class Atom:
    value: str


@dataclass(slots=True)
class Call:
    name: str
    args: list["Expr"] = field(default_factory=list)


@dataclass(slots=True)
class Unary:
    operator: str
    expr: "Expr"
    position: Literal["prefix", "postfix"]


@dataclass(slots=True)
class Binary:
    left: "Expr"
    operator: str
    right: "Expr"


Expr = Atom | Call | Unary | Binary


@dataclass(slots=True)
class Clause:
    tag: Tag
    expr: Expr
    raw: str
    line: int


@dataclass(slots=True)
class Header:
    version: str
    mode: Mode | None = None


@dataclass(slots=True)
class Document:
    header: Header | None = None
    codebook: dict[str, str] = field(default_factory=dict)
    clauses: list[Clause] = field(default_factory=list)
    audit: str | None = None


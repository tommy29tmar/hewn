"""Flint MCP server.

Exposes a single schema-validated tool (`submit_flint_ir`) that forces
the caller (Claude) to emit a well-formed Flint IR document.

Unlike the prompt-level `flint` wrapper, the tool's JSON Schema is
enforced at the Anthropic API level: if the model's arguments don't match
the schema, the API rejects the call and forces a retry. This closes the
residual free-text parser-pass gap in plain `flint`.

Exposed tools:
  - submit_flint_ir:  emit a validated Flint IR document
  - validate_flint:   parse + validate a raw Flint text string
  - audit_explain:    run `flint-ir audit --explain` on a raw Flint document

Protocol: stdio transport (default for local MCP servers). Launch as:
    python -m flint.mcp_server

Configure Claude Code via ~/.claude/settings.json:
    {
      "mcpServers": {
        "flint": {
          "command": "python",
          "args": ["-m", "flint.mcp_server"]
        }
      }
    }
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .normalize import normalize_document_text
from .parser import FlintParseError, parse_document
from .render import generate_audit

logger = logging.getLogger("flint.mcp_server")


ATOM_PATTERN = (
    # lowercase_snake_case identifier, optional single-arg call, or quoted string literal
    r"^(?:[a-z][a-z0-9_]*(?:\(\"[^\"]*\"\))?|\"[^\"]*\"|'[^']*')$"
)


SUBMIT_FLINT_IR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["G", "C", "P", "V", "A"],
    "additionalProperties": False,
    "properties": {
        "G": {
            "type": "string",
            "pattern": ATOM_PATTERN,
            "description": "Goal: one atom. lowercase_snake_case identifier, or call form name(\"arg\"), or quoted literal.",
        },
        "C": {
            "type": "array",
            "minItems": 1,
            "maxItems": 8,
            "items": {"type": "string", "pattern": ATOM_PATTERN},
            "description": "Context constraints: array of atoms. Joined with ∧ in rendered output.",
        },
        "P": {
            "type": "array",
            "minItems": 1,
            "maxItems": 8,
            "items": {"type": "string", "pattern": ATOM_PATTERN},
            "description": "Plan steps: array of atoms.",
        },
        "V": {
            "type": "array",
            "minItems": 1,
            "maxItems": 8,
            "items": {"type": "string", "pattern": ATOM_PATTERN},
            "description": "Verification atoms: how to confirm the plan worked.",
        },
        "A": {
            "type": "array",
            "minItems": 1,
            "maxItems": 8,
            "items": {"type": "string", "pattern": ATOM_PATTERN},
            "description": "Action atoms: the concrete move — patch, command, config change.",
        },
        "audit": {
            "type": "string",
            "description": "Optional: plain-prose rerender of the IR. Renders inside [AUDIT] block.",
        },
    },
}


def render_flint_document(args: dict[str, Any]) -> str:
    """Render validated tool args as a Flint v0 hybrid document."""
    lines = ["@flint v0 hybrid"]
    lines.append(f"G: {args['G']}")
    for tag in ("C", "P", "V", "A"):
        atoms = args[tag]
        joined = " ∧ ".join(atoms)
        lines.append(f"{tag}: {joined}")
    audit = args.get("audit")
    if audit:
        lines.append("")
        lines.append("[AUDIT]")
        lines.append(audit.strip())
    return "\n".join(lines)


def build_server() -> Server:
    server: Server = Server("flint")

    @server.list_tools()
    async def _list_tools() -> list[Tool]:
        return [
            Tool(
                name="submit_flint_ir",
                description=(
                    "Emit a Flint IR document for a technical task with crisp goal and "
                    "verifiable endpoint (debug, code review, refactor, architecture). "
                    "Use this tool INSTEAD of emitting @flint v0 hybrid as free text — "
                    "the tool enforces grammar and returns a validated document. "
                    "Each slot (G, C, P, V, A) accepts atoms matching /[a-z_][a-z0-9_]*/ "
                    "or call form f(\"x\") or quoted literal \"x\". "
                    "Do NOT use for open-ended writing, explanations, summaries, or brainstorms — "
                    "those should be prose."
                ),
                inputSchema=SUBMIT_FLINT_IR_SCHEMA,
            ),
            Tool(
                name="validate_flint",
                description=(
                    "Validate a raw Flint text document: parses it and checks schema, "
                    "returns (ok, error_message). Useful for double-checking IR before "
                    "submitting to pipelines."
                ),
                inputSchema={
                    "type": "object",
                    "required": ["document"],
                    "properties": {
                        "document": {
                            "type": "string",
                            "description": "Raw Flint v0 document text, e.g. '@flint v0 hybrid\\nG: ...'",
                        },
                    },
                },
            ),
            Tool(
                name="audit_explain",
                description=(
                    "Render a Flint IR document as a human-readable prose rerender. "
                    "Runs the render pipeline that produces the [AUDIT] block content. "
                    "Input is a raw Flint document."
                ),
                inputSchema={
                    "type": "object",
                    "required": ["document"],
                    "properties": {
                        "document": {"type": "string"},
                    },
                },
            ),
        ]

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        if name == "submit_flint_ir":
            rendered = render_flint_document(arguments)
            # Verify the rendered doc parses — should always succeed given schema, but double-check
            try:
                parse_document(rendered)
            except FlintParseError as exc:
                logger.warning("submit_flint_ir rendered doc fails parser: %s", exc)
                return [TextContent(
                    type="text",
                    text=(
                        f"ERROR: rendered document failed validation: {exc}. "
                        f"Please check atom shapes (snake_case, call form, or quoted literal only)."
                    ),
                )]
            return [TextContent(type="text", text=rendered)]

        if name == "validate_flint":
            document = arguments.get("document", "")
            normalized = normalize_document_text(document)
            try:
                parsed = parse_document(normalized)
            except FlintParseError as exc:
                return [TextContent(type="text", text=f"INVALID: {exc}")]
            return [TextContent(
                type="text",
                text=f"VALID: version={parsed.header.version if parsed.header else '?'} "
                     f"mode={parsed.header.mode if parsed.header else '?'} "
                     f"clauses={[c.tag for c in parsed.clauses]}",
            )]

        if name == "audit_explain":
            document = arguments.get("document", "")
            try:
                parsed = parse_document(normalize_document_text(document))
            except FlintParseError as exc:
                return [TextContent(type="text", text=f"ERROR: {exc}")]
            prose = generate_audit(parsed).strip()
            return [TextContent(type="text", text=prose or "(no audit rendered)")]

        return [TextContent(type="text", text=f"ERROR: unknown tool {name}")]

    return server


async def _run_stdio() -> None:
    server = build_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(_run_stdio())


if __name__ == "__main__":
    main()

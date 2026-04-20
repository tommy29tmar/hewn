---
name: flint-audit
description: Decode a Flint IR document into readable prose. Accepts a file path, a URL, or an inline Flint document pasted as the argument. Uses the local `flint audit --explain` CLI.
allowed-tools: ["Bash", "Read", "Write"]
---

The user wants a Flint IR document rendered as plain prose.

**Input shapes** (detect from the user's argument):

1. **File path** — something like `response.flint`, `/tmp/x.flint`,
   `./path/to/doc.flint`. Exists on disk.
2. **Inline Flint document** — the user pastes the document text directly.
   Look for the telltale `@flint v0` header and the `G:`/`C:`/`P:`/`V:`/`A:`
   slot structure.
3. **Empty argument** — ask the user what to decode.

**Steps:**

1. If the argument is a file path and exists, run (via the Bash tool):

   ```bash
   flint-ir audit --explain "<path>"
   ```

2. If the argument is inline text, write it to `/tmp/flint-audit-inline.flint`
   first (using the Write tool), then run:

   ```bash
   flint-ir audit --explain /tmp/flint-audit-inline.flint
   ```

3. Present the `flint audit --explain` output to the user, followed by a
   short prose gloss (2–4 sentences) summarizing what the document is
   trying to say. This turn is **not** in Flint format — the user asked for
   prose.

4. If `flint audit --explain` reports a parse error or a schema error,
   surface the error message and point at
   `docs/failure_modes.md#drift-patterns` for the taxonomy of why it might
   have failed.

5. If the CLI is not installed (`flint` command not found), tell the user
   to install it with `pipx install git+https://github.com/tommy29tmar/flint.git`
   or `pip install --user git+https://github.com/tommy29tmar/flint.git`.
   The CLI is also included in the one-line install script.

After presenting the audit, remain in whatever mode the conversation was
in before — if Flint mode was active (`/flint-on`), the next turn should
go back to Flint.

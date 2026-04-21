# Contributing to Hewn

Hewn is a Claude Code CLI wrapper. The repo is intentionally small: one
bash wrapper, one system prompt, one Python hook classifier, one test.

## What changes look like

- Tweaks to `integrations/claude-code/hooks/hewn_drift_fixer.py` — the
  classifier regex rules that decide a turn's route.
- Tweaks to `integrations/claude-code/hewn_thinking_system_prompt.txt` —
  the system prompt appended to every `claude` invocation.
- Tweaks to `integrations/claude-code/bin/hewn` — the wrapper itself
  (argument handling, settings generation, etc.).

If you change the classifier or its directives, update the corpus in
`tests/test_hewn_drift_fixer.py` with the new expected behavior.

## Run the tests

```bash
python -m unittest tests.test_hewn_drift_fixer
```

No dependencies, no install step — pure stdlib.

## Pull requests

Good PRs are narrow:

- what changed
- why it changed
- what prompt or scenario motivates it (paste the prompt if possible)

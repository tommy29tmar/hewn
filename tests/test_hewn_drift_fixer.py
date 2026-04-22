"""Tests for the Hewn drift-fix UserPromptSubmit hook classifier.

Structure:
- ClassifyTests: English-only corpus (HEWN_LOCALE=en default).
- EnglishItalianClassifyTests: corpus with Italian prompts (locales=en+it).
- OtherLocalesSanityTests: minimal smoke tests for es/fr/de.
- BuildOutputTests: directive assembly.
- MainTests: stdin/stdout wiring.
"""
from __future__ import annotations

import importlib.util
import io
import json
import sys
import unittest
import unittest.mock
from pathlib import Path

HOOK_PATH = (
    Path(__file__).resolve().parents[1]
    / "integrations"
    / "claude-code"
    / "hooks"
    / "hewn_drift_fixer.py"
)


def _load_hook_module():
    spec = importlib.util.spec_from_file_location("hewn_drift_fixer", HOOK_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


hook = _load_hook_module()


# English-only corpus
EN_IR_PROMPTS = [
    "Debug this production issue: users report 502s on /checkout",
    "Review this diff for concurrency bugs",
    "Audit the JWT auth module for security vulnerabilities",
    "Fix the race condition in auth/session_refresh.py",
    "Refactor this handler to split billing from fulfillment",
    "Describe the target architecture: service boundaries, sync vs async protocols, data ownership",
    "Propose the precise data ownership split. Each table has exactly one owner",
    "Design the order-to-payment flow using a saga pattern. Show the state machine",
    "Critique the consistency model: where are the dangerous eventual-consistency windows",
    "Which 5 SLOs tell me the split is healthy? What alert thresholds",
    "What canary-vs-control comparison query should I run day 1",
    "Walk through what the trace tells you happened",
    "Root cause hypothesis? Consider the interaction between the reaper and the pool",
    "Propose the minimal fix that prevents recurrence",
    "What specific attack vectors does this JWT implementation expose?",
    "```python\ndef verify(tok): jwt.decode(tok, SECRET)\n```\nWhat's wrong here?",
    "Why does my React component re-render every time the parent updates?",
    "Explain database connection pooling.",
    "What's the difference between TCP and UDP?",
    "What does the SQL EXPLAIN command tell me?",
    "How does a hash table handle collisions?",
    "Why am I getting CORS errors in my browser console?",
    "What's the point of using a debouncer on a search input?",
    "How does git rebase differ from git merge?",
    "When should I use a queue vs a topic in messaging systems?",
]

EN_PROSE_CODE_PROMPTS = [
    "Write regression tests (pytest) for algo=none rejection",
    "Propose the fix. Show updated jwt_service.py",
    "Show the code/config change that prevents recurrence",
    "Implement the saga coordinator; show the full class",
    "Write the patch that switches HS256 to RS256",
    "Apply the fix and show the updated module",
    "Draft an RFC and include sample code for the migration",
]

EN_PROSE_POLISHED_PROMPTS = [
    "Write a 2-paragraph summary for non-technical leadership: what we're doing, why, risks",
    "Write a memo for leadership. Tone: professional, no code. Cover what we found",
    "Draft a customer-facing post-mortem: blameless, factual, 4-5 paragraphs, no code, no IR",
]

EN_PROSE_POLISHED_CODE_PROMPTS = [
    "Customer-facing memo: include the exact nginx config we deployed inline. 2 paragraphs.",
    "Draft a 3-paragraph post-mortem for leadership; include sample code showing the fix.",
    "Write a stakeholder update with the patch snippet inline. Professional tone.",
]

EN_PROSE_CAVEMAN_PROMPTS = [
    "Internal retrospective: what process changes would have caught this. Prose, reflective tone, narrative",
    "Explain to a junior dev how OAuth flows work",
    "Write a tutorial walkthrough of how TLS handshake works",
    "Let's brainstorm options for the migration strategy",
    "Think out loud about the tradeoff between Kafka and RabbitMQ here",
    "What do you think about our approach so far?",
    "Give me a readable paragraph describing what we built last week",
    "Answer in prose, no Hewn IR, no markdown headers",
    "my app crashed and i dont know why this is the error: TypeError: Cannot read properties of undefined (reading 'map')",
]

EN_PROSE_FINDINGS_PROMPTS = [
    "Find every security issue in this code, rank by severity",
    "Audit this codebase and rank top issues",
    "What 3 bugs would a user most likely hit?",
    "Rank the top 5 launch blockers before we ship",
    "List the main failure modes with evidence and fix direction",
    "Flag the security issues in this PR, ranked by severity",
]


# Italian corpus (requires locales=en+it)
IT_IR_PROMPTS = [
    "Spiega perché questo codice ha un race condition",
    "Cosa monitoro in prod dopo il deploy?",
    "Studia questa directory. Dimmi come potrei migliorare la hewn CLI.",
    "Fammi un audit veloce del repo: cosa è solido, cosa è fragile, cosa toglierei.",
    "Cosa è fragile in questo progetto?",
]

IT_PROSE_CAVEMAN_PROMPTS = [
    "Ragiona sul tradeoff tra event-sourcing e CRUD per questo dominio",
]

IT_PROSE_FINDINGS_PROMPTS = [
    "Quali sono i 3 bug più probabili che un utente incontrerà nel primo mese?",
    "Classifica i rischi principali per probabilità e impatto",
]


class ClassifyTests(unittest.TestCase):
    """English-only classifier tests (default locale)."""

    LOCALES = ("en",)

    def _expect(self, prompts, label):
        for prompt in prompts:
            with self.subTest(prompt=prompt, label=label):
                self.assertEqual(
                    hook.classify(prompt, locales=self.LOCALES),
                    label,
                    f"expected {label!r} for: {prompt!r}",
                )

    def test_ir_prompts(self):
        self._expect(EN_IR_PROMPTS, "ir")

    def test_prose_code_prompts(self):
        self._expect(EN_PROSE_CODE_PROMPTS, "prose_code")

    def test_prose_polished_prompts(self):
        self._expect(EN_PROSE_POLISHED_PROMPTS, "prose_polished")

    def test_prose_polished_code_prompts(self):
        self._expect(EN_PROSE_POLISHED_CODE_PROMPTS, "prose_polished_code")

    def test_prose_caveman_prompts(self):
        self._expect(EN_PROSE_CAVEMAN_PROMPTS, "prose_caveman")

    def test_prose_findings_prompts(self):
        self._expect(EN_PROSE_FINDINGS_PROMPTS, "prose_findings")

    def test_empty_prompt_is_prose_caveman(self):
        self.assertEqual(hook.classify("", locales=self.LOCALES), "prose_caveman")
        self.assertEqual(hook.classify(None, locales=self.LOCALES), "prose_caveman")

    def test_polished_override_wins_over_ir_signal(self):
        prompt = (
            "We had a production outage; write a memo for non-technical leadership "
            "explaining what happened. 3 paragraphs, no code."
        )
        self.assertEqual(hook.classify(prompt, locales=self.LOCALES), "prose_polished")


class EnglishItalianClassifyTests(unittest.TestCase):
    """Italian prompts with en+it locales stacked."""

    LOCALES = ("en", "it")

    def _expect(self, prompts, label):
        for prompt in prompts:
            with self.subTest(prompt=prompt, label=label):
                self.assertEqual(
                    hook.classify(prompt, locales=self.LOCALES),
                    label,
                    f"expected {label!r} for: {prompt!r}",
                )

    def test_italian_ir(self):
        self._expect(IT_IR_PROMPTS, "ir")

    def test_italian_caveman(self):
        self._expect(IT_PROSE_CAVEMAN_PROMPTS, "prose_caveman")

    def test_italian_findings(self):
        self._expect(IT_PROSE_FINDINGS_PROMPTS, "prose_findings")


class OtherLocalesSanityTests(unittest.TestCase):
    """Realistic-corpus classification tests for es/fr/de.

    Each locale is validated on a 12-prompt corpus covering all 6 routes,
    with real-shape prompts (enclitic pronouns, compound nouns, diagnostic
    questions, adjectives, etc.). Community PRs welcome to expand the
    corpus further.
    """

    ES_CORPUS = [
        ("ir",                  "Depura esta función que retorna None de vez en cuando bajo carga"),
        ("ir",                  "Analiza el módulo de auth y dime dónde está la vulnerabilidad"),
        ("ir",                  "Refactoriza el parser manteniendo la interfaz pública"),
        ("ir",                  "¿Por qué este test falla esporádicamente en CI?"),
        ("prose_code",          "Escríbeme un test de regresión para este bug de JWT"),
        ("prose_code",          "Muéstrame el código actualizado con el fix aplicado"),
        ("prose_findings",      "¿Cuáles son las 5 vulnerabilidades más graves en este código?"),
        ("prose_findings",      "Encuéntrame los 3 bugs principales en este snippet, clasificados por gravedad"),
        ("prose_polished",      "Escribe un memo para la dirección, 3 párrafos, tono tranquilizador, sin código"),
        ("prose_polished_code", "Memo para los clientes con la config de nginx inline, 2 párrafos"),
        ("prose_caveman",       "Dame 5 nombres para una nueva librería de rate-limiting"),
        ("prose_caveman",       "Piensa en voz alta sobre el tradeoff entre REST y gRPC"),
    ]

    FR_CORPUS = [
        ("ir",                  "Débogue cette fonction qui renvoie None de temps en temps sous charge"),
        ("ir",                  "Analyse le module d'auth et dis-moi où est la vulnérabilité"),
        ("ir",                  "Refactorise le parser en gardant l'interface publique stable"),
        ("ir",                  "Pourquoi ce test échoue-t-il sporadiquement en CI?"),
        ("prose_code",          "Écris-moi un test de régression pour ce bug JWT"),
        ("prose_code",          "Montre-moi le code mis à jour avec le fix appliqué"),
        ("prose_findings",      "Quelles sont les 5 vulnérabilités les plus graves dans ce code?"),
        ("prose_findings",      "Trouve-moi les 3 bugs principaux dans ce snippet, classés par gravité"),
        ("prose_polished",      "Écris un memo pour la direction, 3 paragraphes, ton rassurant, pas de code"),
        ("prose_polished_code", "Memo pour les clients avec la config nginx inline, 2 paragraphes"),
        ("prose_caveman",       "Propose 5 noms pour une nouvelle bibliothèque de rate-limiting"),
        ("prose_caveman",       "Réfléchis à voix haute sur le tradeoff entre REST et gRPC"),
    ]

    DE_CORPUS = [
        ("ir",                  "Debugge diese Funktion, die sporadisch None zurückgibt unter Last"),
        ("ir",                  "Analysiere das Auth-Modul und sag mir, wo die Schwachstelle ist"),
        ("ir",                  "Refaktoriere den Parser und behalte die öffentliche API bei"),
        ("ir",                  "Warum schlägt dieser Test sporadisch in CI fehl?"),
        ("prose_code",          "Schreib mir einen Regression-Test für diesen JWT-Bug"),
        ("prose_code",          "Zeig mir den aktualisierten Code mit dem angewandten Fix"),
        ("prose_findings",      "Was sind die 5 gravierendsten Schwachstellen in diesem Code?"),
        ("prose_findings",      "Finde die 3 wichtigsten Bugs in diesem Snippet, sortiert nach Schwere"),
        ("prose_polished",      "Schreib ein Memo für die Geschäftsführung, 3 Absätze, beruhigender Ton, ohne Code"),
        ("prose_polished_code", "Memo für die Kunden mit der Nginx-Config inline, 2 Absätze"),
        ("prose_caveman",       "Schlage 5 Namen für eine neue Rate-Limiting-Bibliothek vor"),
        ("prose_caveman",       "Denk laut über den Tradeoff zwischen REST und gRPC nach"),
    ]

    def _check(self, corpus, locales):
        for expected, prompt in corpus:
            with self.subTest(prompt=prompt, locales=locales):
                self.assertEqual(
                    hook.classify(prompt, locales=locales),
                    expected,
                    f"locales={locales} expected {expected!r} for: {prompt!r}",
                )

    def test_spanish_corpus(self):
        self._check(self.ES_CORPUS, ("en", "es"))

    def test_french_corpus(self):
        self._check(self.FR_CORPUS, ("en", "fr"))

    def test_german_corpus(self):
        self._check(self.DE_CORPUS, ("en", "de"))


class DefaultLocaleTests(unittest.TestCase):
    """Locale resolution: HEWN_LOCALE > $LANG auto-detect > English-only."""

    IT_PROMPT = "Studia questa directory e dimmi cosa manca"

    def test_hewn_locale_en_forces_english(self):
        # Explicit HEWN_LOCALE=en beats $LANG auto-detect
        import os
        env = {"HEWN_LOCALE": "en", "LANG": "it_IT.UTF-8"}
        with unittest.mock.patch.dict(os.environ, env, clear=False):
            self.assertEqual(hook.classify(self.IT_PROMPT), "prose_caveman")

    def test_hewn_locale_stacks_locales(self):
        import os
        env = {"HEWN_LOCALE": "en,it"}
        with unittest.mock.patch.dict(os.environ, env, clear=False):
            self.assertEqual(hook.classify(self.IT_PROMPT), "ir")

    def test_lang_autodetects_italian(self):
        import os
        # HEWN_LOCALE must be unset for auto-detect to fire
        env = {"LANG": "it_IT.UTF-8"}
        with unittest.mock.patch.dict(os.environ, env, clear=False):
            os.environ.pop("HEWN_LOCALE", None)
            self.assertEqual(hook.classify(self.IT_PROMPT), "ir")

    def test_lang_c_falls_back_to_english(self):
        import os
        env = {"LANG": "C"}
        with unittest.mock.patch.dict(os.environ, env, clear=False):
            os.environ.pop("HEWN_LOCALE", None)
            os.environ.pop("LC_ALL", None)
            os.environ.pop("LC_MESSAGES", None)
            self.assertEqual(hook.classify(self.IT_PROMPT), "prose_caveman")

    def test_lang_en_us_is_english_only(self):
        import os
        env = {"LANG": "en_US.UTF-8"}
        with unittest.mock.patch.dict(os.environ, env, clear=False):
            os.environ.pop("HEWN_LOCALE", None)
            os.environ.pop("LC_ALL", None)
            os.environ.pop("LC_MESSAGES", None)
            self.assertEqual(hook.classify(self.IT_PROMPT), "prose_caveman")

    def test_lang_unshipped_locale_falls_back(self):
        import os
        # Japanese — no ja.py shipped
        env = {"LANG": "ja_JP.UTF-8"}
        with unittest.mock.patch.dict(os.environ, env, clear=False):
            os.environ.pop("HEWN_LOCALE", None)
            os.environ.pop("LC_ALL", None)
            os.environ.pop("LC_MESSAGES", None)
            self.assertEqual(hook.classify(self.IT_PROMPT), "prose_caveman")

    def test_lc_all_overrides_lang(self):
        import os
        # LC_ALL=it wins over LANG=en
        env = {"LC_ALL": "it_IT.UTF-8", "LANG": "en_US.UTF-8"}
        with unittest.mock.patch.dict(os.environ, env, clear=False):
            os.environ.pop("HEWN_LOCALE", None)
            os.environ.pop("LC_MESSAGES", None)
            self.assertEqual(hook.classify(self.IT_PROMPT), "ir")


class BuildOutputTests(unittest.TestCase):
    def test_ir(self):
        ctx = hook.build_output("ir")["hookSpecificOutput"]["additionalContext"]
        self.assertIn("IR-shape", ctx)
        self.assertIn("@hewn v0 hybrid", ctx)

    def test_prose_code(self):
        ctx = hook.build_output("prose_code")["hookSpecificOutput"]["additionalContext"]
        self.assertIn("prose+code", ctx)
        self.assertIn("fenced code block", ctx)
        self.assertIn("Do NOT emit Hewn IR", ctx)

    def test_prose_caveman(self):
        ctx = hook.build_output("prose_caveman")["hookSpecificOutput"]["additionalContext"]
        self.assertIn("MICRO_PROSE_MODE", ctx)
        self.assertIn("plain prose", ctx)

    def test_prose_findings(self):
        ctx = hook.build_output("prose_findings")["hookSpecificOutput"]["additionalContext"]
        self.assertIn("prose-findings", ctx)
        self.assertIn("numbered findings list", ctx)
        self.assertIn("Do NOT emit Hewn IR", ctx)

    def test_prose_polished(self):
        ctx = hook.build_output("prose_polished")["hookSpecificOutput"]["additionalContext"]
        self.assertIn("prose-polished", ctx)
        self.assertIn("professional", ctx.lower())
        self.assertTrue("Caveman compression" in ctx or "No Caveman" in ctx)
        self.assertIn("Do NOT emit Hewn IR", ctx)

    def test_prose_polished_code(self):
        ctx = hook.build_output("prose_polished_code")["hookSpecificOutput"]["additionalContext"]
        self.assertIn("prose-polished+code", ctx)
        self.assertIn("professional", ctx.lower())
        self.assertIn("fenced code block", ctx)
        self.assertIn("caveman compression", ctx.lower())
        self.assertIn("Do NOT emit Hewn IR", ctx)

    def test_unknown_label_falls_back_to_caveman(self):
        ctx = hook.build_output("unknown")["hookSpecificOutput"]["additionalContext"]
        self.assertIn("MICRO_PROSE_MODE", ctx)


class MainTests(unittest.TestCase):
    def test_reads_stdin_and_writes_stdout(self):
        event = {"prompt": "Audit this code for security issues", "cwd": "/tmp"}
        captured = io.StringIO()
        with unittest.mock.patch.object(sys, "stdin", io.StringIO(json.dumps(event))), \
             unittest.mock.patch.object(sys, "stdout", captured):
            rc = hook.main()
        self.assertEqual(rc, 0)
        out = json.loads(captured.getvalue())
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "UserPromptSubmit")
        self.assertIn("IR-shape", out["hookSpecificOutput"]["additionalContext"])

    def test_handles_malformed_stdin(self):
        captured = io.StringIO()
        with unittest.mock.patch.object(sys, "stdin", io.StringIO("not valid json")), \
             unittest.mock.patch.object(sys, "stdout", captured):
            rc = hook.main()
        self.assertEqual(rc, 0)
        out = json.loads(captured.getvalue())
        self.assertIn("MICRO_PROSE_MODE", out["hookSpecificOutput"]["additionalContext"])


if __name__ == "__main__":
    unittest.main()

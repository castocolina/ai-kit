# Phase 13: Docker Rules Checker (ai-kit-project-rules-docker) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-13
**Phase:** 13-Docker Rules Checker (ai-kit-project-rules-docker)
**Areas discussed:** YAML parsing approach, local-dev service identification, hot-reload check scope

---

## YAML parsing

| Option | Description | Selected |
|--------|-------------|----------|
| Indentation-aware regex/text parsing, stdlib-only | Follow the existing `.pre-commit-config.yaml` parsing precedent, generalized to handle nested `services:`/`healthcheck:`/`depends_on:` structure. | ✓ |
| Add a minimal YAML parsing dependency | Add PyYAML or similar as a new runtime dependency. | |

**User's choice:** Indentation-aware regex/text parsing, stdlib-only
**Notes:** No YAML library is installed; PROJECT.md's Runtime dependency discipline constraint keeps shipped code stdlib-only; the project already parses a YAML file this way elsewhere.

---

## Local-dev detection

| Option | Description | Selected |
|--------|-------------|----------|
| File-name convention (docker-compose.override.yml / docker-compose.local.yml) | Identify local-dev services by compose filename. | ✓ |
| Compose "profiles" key detection | Identify local-dev services by a `profiles:` entry. | |

**User's choice:** File-name convention
**Notes:** Matches the design spec's own local-dev-assets-at-a-dedicated-location framing; the user's reply opened with "1." selecting this option before adding the hot-reload point below.

---

## Hot-reload check scope (user-initiated expansion, not originally asked as a choice)

**User's note (translated from Spanish):** "The important thing about hot-reload when they're servers is that stack-dependent technologies should be used — for example Node → Vite, Python → Flask."

**Resulting decision:** The hot-reload check becomes stack-aware (D-04/D-05 in CONTEXT.md) — it verifies the dev-command override actually invokes a stack-appropriate hot-reload/dev-server tool, not just that a bind-mount exists. This extends Phase 11's shared per-language tool catalog with a hot-reload/dev-server category, consumed via Phase 10's shared `detect_stacks()`.

---

## Claude's Discretion

- Exact indentation-tracking implementation for the docker-compose.yml parser.
- Exact shape of the hot-reload-tool catalog extension within the shared per-language catalog.

## Deferred Ideas

None. `cross_reference_todos` re-confirmed the same 3 historical todos are not live candidates. The blocking-prerequisite note (Phases 9-12 must land first) was recorded in CONTEXT.md's `<domain>` section.

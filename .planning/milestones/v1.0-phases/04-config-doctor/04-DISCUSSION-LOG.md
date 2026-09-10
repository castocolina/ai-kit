# Phase 4: Config Doctor - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-08
**Phase:** 4-Config Doctor
**Areas discussed:** Checks Catalog fixed vs. extensible, Runtime-installed detection reuse (expanded mid-discussion into a major Cursor scope decision), Row 9 (Codex hooks) apply semantics, Review-screen presentation format (expanded into naming/uninstall/catalog-content threads)

---

## Checks Catalog: fixed vs. extensible

**Trade-off analysis presented:** declarative data-driven catalog + generic
engine vs. 12 hardcoded check functions.

| Option | Description | Selected |
|--------|-------------|----------|
| Declarative + generic engine | Each row is a data record; adding/removing rows doesn't touch the engine | ✓ |
| 12 hardcoded functions | Simpler now, costlier to extend | |

**User's choice:** declarative + generic engine (recommended option).

---

## Runtime-installed detection reuse → Cursor scope expansion

**Trade-off analysis presented:** config-file presence vs. reuse Phase 1's
`detect_installed_clis()` vs. both combined.

**User's first answer:** picked config-file presence, but immediately added
"I'd like to extend the scope to cursor" (wants to extend scope to Cursor).
This was flagged as scope creep and redirected once; the user pushed back
directly: "Is it very hard to add compatibility with cursor?"

**Investigation performed:** confirmed Cursor is installed and actively used
on this machine (`~/.cursor/cli-config.json` with `permissions`/per-model
`modelParameters`; `~/.cursor/hooks.json` with a real hooks system). With the
just-confirmed declarative design, a 4th runtime is mechanically cheap — but
the existing 12 rows carry real cited research that doesn't exist for Cursor
yet.

| Option | Description | Selected |
|--------|-------------|----------|
| Expand scope now — the researcher investigates Cursor's rows | Accept the scope expansion; route Cursor's Checks Catalog rows to the researcher | ✓ |
| Keep it deferred for a future phase | Keep the redirect | |

**User's choice:** expand scope now.

**Follow-up: user asked to also verify Phase 1/3 for Cursor gaps and update
REQUIREMENTS.md/ROADMAP.md formally.** Investigated: Phase 1 already
contemplated Cursor (`cursor-agent` in `KNOWN_CLIS`, in D-02's empirical
research plan) — only missing `"cursor"` from `native_runtime`'s documented
valid-value set. Phase 3 had a genuine gap — live-verified Cursor has its
own `sessionStart` hook (currently active on this machine), which
`REQUIREMENTS.md` never accounted for (only documented opencode's gap).

| Option | Description | Selected |
|--------|-------------|----------|
| Update all 3 (REQUIREMENTS/ROADMAP + reopen Phase 1/3 CONTEXT.md) now | Formal, durable amendment across all affected files | ✓ |
| Only Phase 4 now | Leave Phase 1/3 as notes for later | |

**User's choice:** update all three now. Committed as `28766ce` —
`REQUIREMENTS.md`, `ROADMAP.md`, `01-CONTEXT.md` (D-09), `03-CONTEXT.md`
(D-09).

---

## Row 9 (Codex `features.hooks`) apply semantics

| Option | Description | Selected |
|--------|-------------|----------|
| No apply, informational only | Matches the PRD's "confirm whether the user actually wants" wording; consistent with Phase 3 scoping Codex hooks out | ✓ |
| Real apply-toggle, just not auto-recommended | Row still has a real apply action | |

**User's choice:** informational only (recommended option).

---

## Review-screen presentation format

**Trade-off analysis presented:** plain-CLI sequential prompts (like
`statusline-doctor.py`) vs. interactive `textual` TUI (like the wizard).

| Option | Description | Selected |
|--------|-------------|----------|
| Plain CLI | stdlib-only, consistent with Phase 2/3's dependency discipline | |
| TUI with textual | Rich review UX for ~15+ rows across 4 runtimes; matches ROADMAP.md's UI hint: yes | ✓ |

**User's choice:** TUI with textual.

**Follow-up on guard reuse:** asked to confirm whether the TUI should reuse
`ensure_rich_runtime()` as-is or get its own more-robust guard (given Phase
2's earlier finding that `ensure_rich_runtime()`'s fail-closed path is only
mock-tested). User instead asked a clarifying architecture question: "Wouldn't
it be the same UI, just another view/card?" Investigated `wizard_app.py`:
single `WizardApp(App)` class, no separate `Screen` subclasses. Clarified:
same guard + same visual style, but its own separate module (Config Doctor
is invoked independently, not only during install).

**Multi-part follow-up (single user message, 4 threads):**

1. **Naming**: user proposed making the existing `doctor` subcommand default
   to the new TUI, with `--cli` as an escape hatch to the old
   statusline-doctor behavior. Investigated `tools/setup.py`: `doctor`
   already has an established, different meaning (delegates to
   `statusline-doctor.py --doctor`) — changing its default would be a
   breaking surprise.
2. **Uninstall coverage**: user asked whether `cmd_uninstall()` already
   covers the new hook from Phase 3. Investigated: confirmed a real gap — it
   removes symlinks + unwires `statusLine` but has no equivalent for
   `hooks.SessionStart`. Captured as `03-CONTEXT.md` D-10.
3. **Catalog content questions**: user pointed out the actual 12 rows were
   never shown; asked whether opencode really lacks retention, whether Claude
   telemetry should be conditional on individual-vs-corporate account
   status, why no Cursor rows existed yet, and whether Codex/Cursor/opencode
   have a 365-day-style retention control like Claude Code's
   `cleanupPeriodDays`. Displayed the full table; live-verified `opencode.jsonc`
   has no retention-like key locally (consistent with, not conclusive proof
   of, row 5's claim); the rest were explicitly routed to the researcher as
   open questions rather than guessed.
4. **Model-vs-runtime scope**: implicitly confirmed from the prior
   clarifying question — captured as D-02's `scope` schema field.

| Naming option | Description | Selected |
|--------|-------------|----------|
| --config-doctor as a flag, TUI by default | New flag, `doctor` subcommand untouched | ✓ |
| New 'config-doctor' subcommand | Add to the choices=[...] list instead | |

**User's choice:** `--config-doctor` flag (recommended option).

**Final follow-up:** user asked to confirm the researcher would also be
instructed to find additional useful tweaks across all 4 runtimes AND
model-specific settings for third-party models in opencode/Cursor. Confirmed
— captured in CONTEXT.md's Open Research Questions section (items 5-6).

---

## Claude's Discretion

None — every gray area had an explicit user decision. Several catalog-content
factual questions were deliberately left unanswered (not guessed) and routed
to the researcher — see CONTEXT.md's Open Research Questions.

## Deferred Ideas

None that stayed deferred. The Cursor-config-diagnostics idea was proposed as
a candidate for deferral, then explicitly pulled into this phase's scope
after investigation (see Runtime-installed detection reuse section above).

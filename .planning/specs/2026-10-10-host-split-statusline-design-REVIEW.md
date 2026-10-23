# Review record — host-split status line design

- **Reviews:** `.planning/specs/2026-10-10-host-split-statusline-design.md`
- **Process:** `ai-kit-spec-review`, archetype `gsd · design`, native
  reviewer GPT-5.6 Sol High, generic fixer Sonnet, cap 3 iterations.
- **Outcome (2026-10-10):** cap reached with the findings below open. They
  are design gaps, not defects in built code, and MUST be resolved in
  Phase 999.4's `/gsd-discuss-phase` (decisions into `NN-CONTEXT.md`) or
  `/gsd-plan-phase` before execution. Amend the design spec when a
  resolution changes it.

## Open findings (iteration 3)

Each finding needs a decision recorded in CONTEXT.md, and either a spec
amendment or a plan task with a test.

- [ ] **R3-1 (HIGH) — Wizard multi-host contract vs the injected-view seam.**
  Spec §4.2, §6.4. The wizard receives all behavior through `WizardContext`
  and today supports one status-line state, adoption gate, layout, and
  commit. Keep host-module knowledge in setup-side orchestration; define a
  host-keyed wizard context/state/result, the Claude-then-Cursor sequencing,
  and per-host commit behavior.
- [ ] **R3-2 (HIGH) — Quota normalization rules.** Spec §2, §5.3. Define the
  deterministic mapping from `GetCurrentPeriodUsage`, `GetHardLimit`, and
  `GetPlanInfo` into every `QuotaResult` field: source precedence when
  billing dates or limits conflict or are missing, units (cents vs
  dollars), on-demand classification precedence, and zero/absent-limit
  behavior. Validate against the Phase B spike's real responses.
- [ ] **R3-3 (HIGH) — External providers must not change Claude behavior.**
  Spec §1, §5.4. Adding `segment.host` / `AI_KIT_SEGMENT_HOST` is visible to
  arbitrary providers. Keep the exact existing Claude provider input,
  environment, and cache namespace; let Cursor providers identify their
  host some other way; add a regression test with a strict existing
  provider.
- [ ] **R3-4 (HIGH) — Credential transport trust boundary.** Spec §5.3, §9.
  HTTPS only, endpoint validation (including `CURSOR_API_ENDPOINT`), and no
  redirects followed cross-origin, so the bearer token is never sent over
  insecure transport or to another host. Cover with fake-server tests;
  include in `/gsd-secure-phase`.
- [ ] **R3-5 (HIGH) — Config-write safety for create-if-absent and the
  spike.** Spec §5.4, §6.1. `os.replace` can overwrite a concurrently
  created target. Define a race-safe atomic create-if-absent (for example
  `os.link` of the temp file, or `O_EXCL` then fill and rename) for both
  host TOMLs. The spike's edit and restore of the real
  `~/.cursor/cli-config.json` must be atomic, with verified cleanup on
  failure.
- [ ] **R3-6 (MEDIUM) — Cursor toggles undecided.** Spec §5.2, §5.4. Decide
  whether the auto/API split and the fold-cycle-into-included toggles exist,
  their defaults, and how they interact with the segment registry.

## Facts verified after the review

- **2026-10-10 — Cursor config-dir precedence (answers the spec's §9 open
  question).** Cursor's official docs
  (<https://cursor.com/docs/cli/reference/configuration>) state that
  `cli-config.json` honors `CURSOR_CONFIG_DIR` and, on Linux/BSD,
  `$XDG_CONFIG_HOME/cursor/cli-config.json`. `tools/setup.py`'s
  `resolve_paths` only honors `CURSOR_CONFIG_DIR > ~/.cursor`, while
  `tools/config_doctor_checks.py` already includes the XDG leg. Phase C's
  Cursor `statusLine` wiring must resolve `cli-config.json` with the
  documented precedence. Whether the hooks' `cursor_dir` should change too
  is a separate question for discuss-phase. That page does not document
  `statusLine`; its schema comes only from the CLI's bundled `statusline`
  skill.

## Owner decisions already taken (do not reopen)

- Hard rename `status-line.py` → `claude-status-line.py` with no shim. The
  broken Claude status line after a `git pull` / installer fetch and before
  `setup.py` re-runs is an accepted risk (the status line is a
  nice-to-have; the agent host keeps working). Recovery: re-run setup.
- `claude_host.py` / `cursor_host.py` are the single owners of each `HOST`
  object.
- Cursor env overrides use `AI_KIT_CURSOR_*`; legacy `CC_AI_KIT_*` stays
  Claude-only.
- Wizard runs the full existing flow (gate, then Arrange) per detected host,
  in sequence; headless `--with-statusline` wires all detected hosts,
  `--with-statusline=claude,cursor` selects; foreign entries are never
  overwritten headless.
- One config file per host: `claude-statusline.toml` (migrated from
  `statusline.toml`) and `cursor-statusline.toml`.
- Cursor quota comes from the undocumented Dashboard API, gated by a
  Phase B spike, and is visibly flagged as inferred.

## Resolved in iterations 1–2 (already in the spec)

Phase A migration placement and upgrade tests; semantic (not byte)
preservation of unrelated JSON keys; `alt_process_memory` reclassified as
Claude-only; external-segment host isolation; Cursor cancellation-aware
fetch budget; cross-process single-flight refresh; `param_summary` as
Cursor's "effort"; host assembly modules; typed `QuotaResult`;
`render_width_chars` as the Cursor width source; per-host uninstall;
atomic TOML writes; env-override scoping.

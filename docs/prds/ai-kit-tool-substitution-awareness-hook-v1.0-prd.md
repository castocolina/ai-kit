# AI-Kit Tool-Substitution Awareness Hook - Product Requirements Document (PRD)

> **Status note**: everything in this document is a PROPOSAL, not an accepted
> decision. Where one approach is written up in detail, it is the author's
> recommendation after comparing alternatives (see "Alternatives
> Considered" subsections) — not a foregone conclusion.

## Requirements Description

### Background

- **Business Problem**: `rtk` (rtk-ai/rtk) already silently rewrites Bash/
  shell commands to token-efficient equivalents for both Claude Code
  (confirmed live: `~/.claude/settings.json`'s `PreToolUse` hook running
  `rtk hook claude`) and opencode (confirmed live:
  `~/.config/opencode/plugins/rtk.ts`, a `tool.execute.before` hook calling
  `rtk rewrite <command>`) on this machine. This rewriting is **completely
  silent** by design (the plugin's own comment: "rewrites commands to use
  rtk for token savings" — no message is ever returned to the model). The
  user-reported symptom: the model sometimes notices an unexpectedly short
  or differently-shaped tool output and cannot tell *why* — it has no
  mental model for "a hook silently changed what I asked for." This isn't
  an rtk bug; rtk is working as designed. The gap is a missing explanation
  layer, not a missing rewrite.
- **Corrected research note**: an earlier working draft of this PRD
  incorrectly claimed opencode had zero rtk integration — verified false
  by directly inspecting the installed rtk binary (`rtk init --show`,
  `rtk --help`) and reading `~/.config/opencode/plugins/rtk.ts` in full.
  opencode's coverage is real and active. The two genuine, verified gaps
  are: (a) no explanation layer for either runtime, and (b) Codex's rtk
  integration (`rtk init --codex`) is confirmed prose-only ("uses
  AGENTS.md + RTK.md, no Claude hook patching," per rtk's own `--help`) —
  a real but separate, smaller, and out-of-scope-here limitation (see
  Non-Goals).
- **Target Users**: ai-kit's own maintainer/user, working across Claude
  Code and opencode on the same machine.
- **Value Proposition**: the model forms a correct mental model of *why*
  its own tool output sometimes looks different than expected, without
  requiring a new per-call hook, without touching rtk's own codebase, and
  without adding per-invocation overhead.

### Feature Overview

- **Core Features**: a `SessionStart`-hook-driven (Claude Code) injection
  of a concise, live-generated explanation of active tool substitutions,
  fired both at genuine session start and after context compaction (both
  confirmed real `SessionStart` trigger sources, `"startup"` and
  `"compact"` respectively) — establishing the "if output looks short,
  here's why" mental model once per context window rather than explaining
  every individual substitution as it happens.
- **Feature Boundaries**:
  - IN: a new Claude-Code-side `SessionStart` hook; the live-detection
    logic (which recommended tools are actually installed, cross-checked
    against `tools-installer`'s `registry.toml` `audience`/`desc` fields);
    the injected message's content and format.
  - NOT IN: any change to `rtk` itself (no upstream contribution in this
    PRD — noted as a possible future direction, not committed here); any
    new `PreToolUse`-style per-call rewrite/explain hook (rejected — see
    Alternatives Considered); Cursor's rtk installation (a checklist item,
    not a build task — belongs in the sibling best-practices-checklist
    PRD); Codex's prose-only rtk integration (a separate, smaller,
    out-of-scope gap — see Non-Goals).
- **User Scenarios**:
  - A fresh Claude Code session starts; before the user's first message is
    processed, a concise note is injected into context: which
    token-saving substitutions are active this session (derived from what
    the machine actually has installed, not a static list), and the "if
    output looks unexpectedly short, this is why" framing.
  - The same session later triggers a context compaction; the same
    explanation is re-injected (since compaction is exactly the moment
    this context is most likely to have been pushed out or deprioritized —
    the user's own observed problem with the current `RTK.md`/global-
    `CLAUDE.md` approach).
  - opencode: no equivalent injection happens (see Non-Goals) — documented
    as an accepted, current-generation limitation, not silently ignored.
  - **Related (not built here)**: once this hook (or any future rtk-side
    fix) starts measurably nudging the agent from a classic tool to its
    modern family individual (e.g. `grep`→`rg`), the sibling
    `ai-kit-usage-metrics-dashboard` PRD's family-tagged, date-filterable
    command data is what would let the user compare usage before/after
    this hook was enabled — no new mechanism needed on that side beyond
    what's already scoped there, since date + command-family are both
    already MVP axes.

### Detailed Requirements

- **Input/Output**: Input = live `shutil.which()`-style checks against
  `tools-installer`'s `registry.toml` entries whose `audience` is `"ai"`
  or `"both"`; the currently-active `rtk` version/config
  (`rtk init --show`'s output, or an equivalent programmatic check).
  Output = a short markdown/text block passed as the `SessionStart` hook's
  `hookSpecificOutput.additionalContext` field (confirmed real output
  field, injected as a system reminder read on the next model request).
- **User Interaction**: none — this is a passive, automatic injection; no
  new command or skill invocation for the user.
- **Data Requirements**: no new persistent schema. Reads
  `tools-installer`'s existing `registry.toml` (read-only) and the local
  machine's installed-binary state (read-only, via `shutil.which` or
  equivalent). Does not write anything.
- **Edge Cases**:
  - `rtk` itself not installed → the hook must detect this and either
    suppress the substitution-explanation content entirely (nothing to
    explain) or note explicitly "rtk not detected, no active
    substitutions" — never claim a substitution is active when it isn't.
  - A `registry.toml`-listed tool marked `audience: ai` is NOT installed
    on this machine → excluded from the injected message (only report
    what's actually active, per this PRD's core design principle: verify
    installed state, don't just recite catalog intent).
  - Hook fires on every `SessionStart` trigger source
    (`startup`/`resume`/`clear`/`compact`/`fork`) — must not inject
    duplicate/redundant content on `resume`/`fork` if a reasonable
    "already explained recently" signal exists; if no such signal is
    reliably available, injecting on every trigger source is the safe
    default (a short, idempotent-reading message is cheap to repeat) —
    to be confirmed during implementation, not decided here.

## Design Decisions

### Technical Approach

**Alternatives Considered** (per this PRD's explicit proposal-first
framing):

1. **(Rejected) A new per-call `PreToolUse` "explain" hook**: intercept
   every Bash call, detect classic-tool usage, and append an explanation
   inline (e.g. via `permissionDecisionReason` on a deny, or a
   `PostToolUse` note). Rejected because: it duplicates work `rtk` already
   does (rtk already decides what to rewrite; a second, parallel hook
   re-implementing that decision risks drifting out of sync with rtk's
   own rewrite registry), and it reintroduces per-call overhead the
   session-start approach avoids entirely.
2. **(Rejected, for now) Upstream contribution to `rtk` itself** (a
   `--explain`/verbose mode in rtk's own Rust rewrite registry, the
   single source of truth its own opencode plugin comment points to):
   architecturally the most elegant fix (one change benefits every
   runtime rtk supports), but out of scope for THIS PRD since it depends
   on a third-party project's own maintainers/roadmap, not something
   ai-kit controls unilaterally. Flagged here explicitly as the
   long-term-better alternative, worth raising as a GitHub issue/PR
   against `rtk-ai/rtk` independently of this PRD's own delivery.
3. **(Recommended) `SessionStart`-hook one-time-per-context explanation**:
   establishes the mental model once per context window (covering both
   genuine cold start and the specific post-compaction moment the user
   identified as the real recurring failure point — global `CLAUDE.md`/
   `RTK.md` content being treated as "secondary" once local context has
   accumulated) rather than explaining every individual substitution.
   Zero changes to `rtk`, zero new per-call hook, minimal injected-token
   cost (one short block, not per-command).
- **Key Components**:
  - A new hook script (location TBD at implementation time — likely a
    small Python script under a new or existing ai-kit skill's package,
    registered in `~/.claude/settings.json`'s `SessionStart` hooks array).
  - A live-detection function reading `registry.toml` (read-only
    dependency on `tools-installer`'s file — confirm exact resolution
    path, since `tools-installer` is a sibling repo, not a Python
    dependency of `ai-kit`; the hook likely needs its own lightweight
    TOML read rather than importing `tools-installer`'s own Python
    package, to avoid a cross-repo runtime dependency).
  - The message-composition logic (which tools are active → what to say),
    starting from the small curated set already established
    (`cat→bat`, `grep→rg`, `find→fd`, `sed→sd`, `ls→eza`) rather than a
    fully generic registry-driven generator, per this PRD's own scope
    discipline (start narrow, expand later if it proves valuable). This
    curated set is the single source of truth for "family" membership —
    the sibling `ai-kit-usage-metrics-dashboard` PRD's command-family
    tagging reads/mirrors this same list rather than maintaining its own,
    independently-drifting copy.
- **Data Storage**: none new.
- **Interface Design**: no new CLI flags or skill commands — this is a
  hook wired into Claude Code's own hook configuration, invisible to
  direct invocation.

### Constraints

- **Performance Requirements**: the hook must run fast (a handful of
  `shutil.which()`-style checks and a small TOML read) — it runs on every
  `SessionStart` trigger, which includes every compaction, so it cannot
  be slow or network-dependent.
- **Compatibility**: must not assume `rtk` or `tools-installer` are
  installed — both are optional, and the hook must degrade gracefully
  (produce a shorter or empty message) when either is absent, never
  error out and block session start.
- **Security**: read-only against `registry.toml` and the local PATH;
  never executes any tool it's merely checking for the presence of
  (existence check only, e.g. `shutil.which`, never running the tool
  itself to probe it).
- **Scalability**: N/A — single-user, local, per-session hook.
- **Skill quality gate**: if this hook's implementation is documented in
  or wired through an existing `SKILL.md` (rather than being a bare
  `~/.claude/settings.json` hook entry with no accompanying skill
  documentation), that `SKILL.md` change must pass the same
  `skill-judge` review loop established for this initiative's other
  PRDs (see `ai-kit-multi-cli-runtime-support`'s Constraints section for
  the exact bar). If no `SKILL.md` ends up touched (a bare hook script
  with no skill wrapper), this gate does not apply — to be confirmed at
  implementation time based on where the hook script actually lives.

### Non-Goals

- **Codex's prose-only rtk integration is not addressed by this PRD.**
  Confirmed real (rtk's own `--codex` flag help text: "uses AGENTS.md +
  RTK.md, no Claude hook patching") and confirmed to cause real friction
  upstream (a live rtk GitHub issue about invalid generated commands) —
  but fixing it means either an upstream rtk contribution (Codex now has
  its own real, if experimental and disabled-by-default, `hooks.json`
  mechanism rtk doesn't yet use) or a separate ai-kit-side Codex-specific
  hook, either of which is a distinct, separately-scoped effort.
- **Cursor's rtk installation is not addressed by this PRD.** rtk already
  supports it (`rtk init -g --agent cursor`); on this machine it's simply
  not yet installed. This belongs in the sibling best-practices-checklist
  PRD as a checklist item, not as new engineering here.
- **opencode gets no equivalent session-start injection in this PRD.**
  Confirmed no `SessionStart`-equivalent context-injection hook exists in
  opencode's plugin system (closest is
  `experimental.session.compacting`, which only fires during compaction,
  not at genuine cold start, and is explicitly labeled experimental) —
  documented here as an accepted current-generation gap, not silently
  dropped.

### Risk Assessment

- **Technical Risks**: cross-repo read dependency on `tools-installer`'s
  `registry.toml` — if that file's schema changes shape, this hook's
  parsing could silently start producing an empty/wrong message. Mitigated
  by graceful degradation (Constraints above) and a test fixture pinned
  against the registry's current schema shape.
- **Dependency Risks**: depends on `rtk` and `tools-installer` both being
  present for full value, but is designed to degrade gracefully when
  either is missing (see Compatibility).
- **Schedule Risks**: low — this is a small, self-contained hook once the
  message-composition scope is kept narrow (curated set, not a generic
  registry-driven generator, per the Key Components decision above).

## Acceptance Criteria

### Functional Acceptance

- [ ] A `SessionStart` hook fires on both `"startup"` and `"compact"`
      trigger sources and injects a concise explanation via
      `hookSpecificOutput.additionalContext`.
- [ ] The injected message only references substitutions that are
      actually active on the current machine (verified installed, not
      just registry-listed intent).
- [ ] When `rtk` is not installed, the message either omits substitution
      content entirely or explicitly states none are active — never
      claims a substitution that isn't real.
- [ ] The hook runs fast enough to not perceptibly delay session start or
      post-compaction resume (no network calls, no slow subprocess
      spawns beyond simple existence checks).
- [ ] opencode's lack of an equivalent hook is documented (in the hook's
      own code comments or the skill/doc wrapping it), not silently
      absent with no explanation trail.

### Quality Standards

- [ ] Code Quality: the live-detection and message-composition logic are
      pure, independently testable functions, following this codebase's
      established style.
- [ ] Test Coverage: unit tests for the detection function (rtk present/
      absent, various registry-tool present/absent combinations) and the
      message composer (correct narrowing to only-active substitutions).
- [ ] Skill Quality: if a `SKILL.md` is touched (see Constraints), it
      passes the skill-judge review loop before this work is marked
      complete.

### User Acceptance

- [ ] User Experience: the model demonstrably references the injected
      explanation when it encounters an unexpectedly short tool output
      (qualitative — verified by manual testing during implementation,
      not automatable).
- [ ] Documentation: wherever the hook script lives, its own file-level
      comment documents why it exists, the Non-Goals above, and the
      opencode limitation.

## Execution Phases

### Phase 1: Live-detection + message composition (pure logic)
**Goal**: A tested, pure function that turns "what's installed right now"
into a short explanatory message.
- [ ] Task 1: implement the live-detection function (rtk presence/
      version, curated-tool presence via existence checks).
- [ ] Task 2: implement the message composer (only-active-substitutions
      narrowing, graceful empty case).
- **Deliverables**: two pure, unit-tested functions, no hook wiring yet.

### Phase 2: SessionStart hook wiring
**Goal**: Wire the Phase 1 logic into a real, registered `SessionStart`
hook.
- [ ] Task 1: create the hook script and register it in
      `~/.claude/settings.json`'s `SessionStart` hooks array (exact
      registration mechanism — global vs. project-local settings — to be
      confirmed at implementation time).
- [ ] Task 2: manually verify the injected message actually appears in a
      real session (both a fresh `startup` and a forced `compact`).
- [ ] Task 3: if this work ends up wrapped in a `SKILL.md`, run the
      skill-judge review loop before marking complete.
- **Deliverables**: a working, registered hook, manually verified against
  both trigger sources.

---

**Document Version**: 1.0
**Created**: 2026-09-06
**Clarification Rounds**: 4 (plus one live-research correction mid-flight)
**Quality Score**: 91/100

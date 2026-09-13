## Conflict Detection Report

### BLOCKERS (0)

None. No ADR-type documents in this ingest set (so no LOCKED-vs-LOCKED or
LOCKED-vs-existing-locked-decision check applies), no `UNKNOWN`/low-
confidence classifications, and no unresolved cross-reference cycle (see the
INFO entry below — a cycle was initially suspected from cached classification
state, but did not hold up against the current source files).

### WARNINGS (2)

[WARNING] REQ-multi-cli-runtime-detection: native_runtime valid-value set diverges from already-shipped REQUIREMENTS.md
  Found: `docs/prds/ai-kit-multi-cli-runtime-support-v1.0-prd.md` defines
  `detect_current_runtime()`'s valid return set as exactly `{"claude",
  "opencode", "codex", "unknown"}` — 4 values, no `cursor`.
  Impact: `.planning/REQUIREMENTS.md`'s `REQ-multi-cli-runtime-detection`
  (same scope, Phase 1.2, already marked Complete) was amended 2026-09-08/09
  to add `"cursor"` as a 5th valid value, discovered during Phase 4
  discussion and implemented in `config_io.py`/`model_catalog.py`
  (`01.2-02-PLAN.md`). Re-ingesting this PRD's original (pre-amendment) text
  into `intel/requirements.md` without flagging the gap risks a future
  planning pass treating the narrower 4-value set as current truth.
  → Treat the already-shipped, amended `REQUIREMENTS.md` wording as
  authoritative (work is Complete); no code change implied. If re-running
  `/gsd-roadmapper` over this intel, confirm it does not regress the
  `cursor` value.

[WARNING] REQ-usage-metrics-dashboard-ui: dashboard delivery architecture diverges from already-shipped REQUIREMENTS.md
  Found: `docs/prds/ai-kit-usage-metrics-dashboard-v1.0-prd.md` specifies the
  dashboard as a browser-sandboxed **Artifact** that loads a local
  **export** of the refined store ("a visualization shell that loads a
  local export in whatever file format the dashboard Artifact will read" —
  PRD lines ~173-235, ~424-428).
  Impact: `.planning/REQUIREMENTS.md`'s `REQ-usage-metrics-dashboard-ui`
  (same scope, Phase 5, already marked Complete) was amended 2026-09-08
  (`05-CONTEXT.md` D-08/D-09/D-10) to the **opposite** architecture: "a
  locally-generated, filterable/sortable static HTML dashboard... no
  export/import step, no browser-sandboxed Artifact mechanism," and
  `REQUIREMENTS.md`'s Out of Scope table explicitly rejects "An export/
  import step for the usage-metrics dashboard." This is a full
  architecture reversal discovered during implementation, not a wording
  nuance — re-extracting the PRD verbatim into intel without flagging it
  would silently reintroduce a rejected design if used to re-plan this
  phase.
  → Treat the already-shipped, amended `REQUIREMENTS.md` wording
  (static HTML, no Artifact, no export/import) as authoritative; work is
  Complete (Phases 05-01 through 05-05). Do not use this PRD's Artifact
  description as a basis for any future re-plan of this phase.

### INFO (3)

[INFO] Cross-reference cycle re-verified against fresh source text — classifier's cached cross_refs was stale for one PRD
  Note: The per-doc classification JSON for
  `ai-kit-usage-metrics-dashboard-v1.0-prd.md` lists cached `cross_refs` of
  `["ai-kit-config-doctor", "ai-kit-tool-substitution-awareness-hook"]`.
  Combined with `ai-kit-config-doctor`'s cross_refs (→
  `ai-kit-tool-substitution-awareness-hook`) and
  `ai-kit-tool-substitution-awareness-hook`'s cross_refs (→
  `ai-kit-usage-metrics-dashboard`), this cached data describes a 3-node
  cycle: config-doctor → tool-substitution-awareness-hook →
  usage-metrics-dashboard → config-doctor. Direct `grep` of the current
  source file content, however, finds `ai-kit-usage-metrics-dashboard-v1.0-
  prd.md` contains NO back-reference to either sibling by name — it uses
  generic "a separate, unnamed tool-substitution effort" / "unnamed
  configuration-review effort" phrasing instead. This matches
  `.planning/PROJECT.md`'s Context section and the prior
  `.planning/INGEST-CONFLICTS.md` trail (now overwritten by this report),
  which records that the user deliberately removed these exact named
  back-references in a prior ingest round specifically to break this
  cycle. The classification JSON's `cross_refs` field for this one
  document is a stale cache and should not be trusted for future cycle
  checks without re-verification against the live file. Confirmed edges
  (fresh source, DAG, no cycle):
    ai-kit-config-doctor → ai-kit-tool-substitution-awareness-hook
    ai-kit-config-doctor → ai-kit-opencode-provider-management
    ai-kit-tool-substitution-awareness-hook → ai-kit-multi-cli-runtime-support
    ai-kit-tool-substitution-awareness-hook → ai-kit-usage-metrics-dashboard
    ai-kit-opencode-provider-management → ai-kit-multi-cli-runtime-support
  `ai-kit-multi-cli-runtime-support` and `ai-kit-usage-metrics-dashboard`
  are both sinks. All 5 PRDs synthesized this run.

[INFO] 5 PRDs duplicate already-merged v1 scope
  Note: `ai-kit-config-doctor`, `ai-kit-multi-cli-runtime-support`,
  `ai-kit-opencode-provider-management`, `ai-kit-tool-substitution-
  awareness-hook`, and `ai-kit-usage-metrics-dashboard` are already fully
  present in `.planning/REQUIREMENTS.md`/`.planning/ROADMAP.md` as v1 scope
  (Phases 1.2, 2, 3, 4, 5 — all Complete/Done). Re-ingesting them produced
  no new requirements beyond the 2 divergences flagged in WARNINGS above.

[INFO] Auto-resolved: SPEC > DOC on 4 named implementation deviations
  Note: `docs/superpowers/plans/2026-09-12-ai-kit-rules-shared-package.md`
  (DOC, manifest precedence `1`) explicitly records 4 deliberate deviations
  from `docs/superpowers/specs/2026-09-12-ai-kit-rules-skill-family-design.md`
  (SPEC, manifest precedence `0` — higher precedence) in its own
  "Self-Review Notes" section: (1) cache-payload validation contract stays
  in the existing skill's `cli.py` rather than moving to the shared module;
  (2) `STALE_AFTER_DAYS` stays `30` rather than the SPEC's `180`; (3)
  cross-kind remediation merging stays in the shared helper rather than
  moving to an (not-yet-built) orchestrator; (4) the SPEC's "independently
  copyable to any host" portability claim does not hold for 3 of 5
  documented install candidates. Per precedence, the SPEC's version is
  recorded as-is in `intel/constraints.md`; the DOC's deviations and their
  stated rationale (each is a scoped, named, deliberate carry-over — not an
  oversight) are preserved in `intel/context.md` for traceability. No user
  action needed — the DOC itself already names each deviation and its
  follow-up owner.

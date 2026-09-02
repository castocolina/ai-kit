# Step 0.7 — Resolve the reviewer list (cross-AI) — full detail

Runs once per invocation, after Step 0.6.

0. Resolve `TOOLS_PY` and `CHECKLIST_SKILL_MD`. **`ai-kit-spec.py` lives
   inside `skills/ai-kit-spec-review/` itself** (not at a top-level `tools/` —
   that placement isn't reachable from an installed skill, since
   `tools/setup.py`'s symlinks only cover `agents/commands/skills`, per
   its `CATEGORIES`). Because it's inside `ai-kit-spec-review`'s own skill
   directory, it resolves the same way `SEEDS_DIR` (in SKILL.md's
   `## Constants` section) does (three
   candidates: `CLAUDE_PLUGIN_ROOT`/`~/.claude/skills`/
   sibling-of-this-file) — this snippet is **self-contained** and does
   not read any variable assigned elsewhere; it computes its own
   directory inline via `$(dirname ...)`. (`SEEDS_DIR`'s own block
   assigns `SKILL_DIR="$(dirname "<path to SKILL.md>")"` immediately
   before its own `for` loop, so its third candidate resolves the same
   way this snippet's does.):
   ```bash
   for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-spec-review}" \
            "$HOME/.claude/skills/ai-kit-spec-review" \
            "$(dirname "<absolute path to SKILL.md>")"; do
     [ -d "$d" ] && { REVIEW_SPEC_SKILL_DIR="$d"; break; }
   done
   TOOLS_PY="$REVIEW_SPEC_SKILL_DIR/ai-kit-spec.py"
   CHECKLIST_SKILL_MD="$(dirname "$REVIEW_SPEC_SKILL_DIR")/ai-kit-spec-review-checklist/SKILL.md"
   if [ -f "$TOOLS_PY" ]; then
     RUNTIMES_JSON="$(python3 "$TOOLS_PY" cache-path --kind runtimes)"
     QUOTA_JSON="$(python3 "$TOOLS_PY" cache-path --kind quota)"
   fi
   SHARED_TOOLING_PATH="$REVIEW_SPEC_SKILL_DIR/references/tooling-guidance.md"
   printf '%s\n' "$TOOLS_PY" "$CHECKLIST_SKILL_MD" "$RUNTIMES_JSON" "$QUOTA_JSON" "$SHARED_TOOLING_PATH"
   ```
   `CHECKLIST_SKILL_MD` is the path Step 1's external-CLI dispatch tells
   the external reviewer to `Read` — `ai-kit-spec-review-checklist` (the
   reviewer skill) is always installed as
   `ai-kit-spec-review`'s own sibling, since both live under the same `skills/`
   tree in every installed shape (plugin, `~/.claude/skills`, or a dev
   checkout), so deriving it from `$REVIEW_SPEC_SKILL_DIR`'s own parent
   needs no separate three-candidate search. `cache-path`
   resolves `RUNTIMES_JSON`/`QUOTA_JSON` through the module's own
   `cache_runtimes_path`/`cache_quota_path` — the
   `${XDG_CACHE_HOME:-$HOME/.cache}/ai-kit/ai-kit-spec-review/...` formula lives
   in exactly one place, not duplicated as a bash literal here.
   Resolve this whole block once, in one `Bash` call, and — exactly like
   `RUN_TMP_DIR` below — record `TOOLS_PY`/`CHECKLIST_SKILL_MD`/
   `RUNTIMES_JSON`/`QUOTA_JSON`/`SHARED_TOOLING_PATH` from the trailing
   `printf`'s stdout (five lines, in that order) as literal absolute paths
   substituted into every later command and prose reference; they are
   **not** shell environment variables that survive across separate `Bash`
   tool calls. If
   `TOOLS_PY` does not exist at the resolved path, treat this
   exactly like `--no-cross-ai` (point 2 below) — cross-AI support isn't
   installed, never block the review over it. If `TOOLS_PY` exists but
   `CHECKLIST_SKILL_MD` does not (a broken/partial install —
   `ai-kit-spec-review-checklist` missing while `ai-kit-spec-review` itself is
   present), still proceed with native dispatch (`cli` absent entries
   need no checklist path), but skip any reviewer entry whose `cli` is
   set: an external CLI can't be told to `Read` a file that doesn't
   exist, so treat that entry the way a config error is treated —
   dropped from `REVIEWER_LIST`, never dispatched, and this iteration
   surfaces via whatever entries remain (or `NO_CONFIG_FALLBACK` if none
   do).

   Also call `detect-tools`, cached the same way `ai-kit-spec-config`'s own
   Step 1 does it — but since this orchestrator has no long-lived cache
   file for tool availability today, call it fresh each run (cheap — a
   handful of `which` calls, no network, no TTL logic needed):
   ```bash
   TOOL_AVAILABILITY_JSON="$(python3 "$TOOLS_PY" detect-tools)"
   ```
   Record `TOOL_AVAILABILITY_JSON` as this run's literal tool-availability
   JSON string, substituted into every later `--tool-availability-json`
   reference.
1. Run `mktemp -d` via `Bash`, and record its printed absolute path as
   `RUN_TMP_DIR` in this skill's own working notes — **not** a shell
   environment variable. Every `Bash` tool call in this harness starts a
   fresh shell, so a variable set in one call is gone by the next one;
   from here on, substitute `RUN_TMP_DIR`'s literal absolute path into
   every command and every prose reference below, exactly the way
   `CODEBASE_ROOT` is already resolved once (Step 0.1) and substituted
   literally everywhere after. (This doc keeps writing `$RUN_TMP_DIR` for
   readability, matching how `<CODEBASE_ROOT>` reads elsewhere in this
   skill — read every `$RUN_TMP_DIR` below as "the literal path captured
   here", never as an actual shell variable reference.) Every artifact
   this run produces (raw reviewer reports, the double-review merge, the
   fixer's report) lives under this one directory, replacing the old flat
   `/tmp/ai-kit-spec-review-*` paths (which collided across concurrent runs on
   different projects/worktrees — fixed here).
2. **If `--no-cross-ai` was requested (or `TOOLS_PY` is missing, point 0
   above)**: set `REVIEWER_LIST` directly, in-context, to the single-entry
   array `[{"key": "session-default", "model": "", "vendor": "", "cli":
   null, "command": null, "extra": {}}]` — `ai-kit-spec.py`'s
   `NO_CONFIG_FALLBACK` constant's exact shape. **Do not run
   `resolve-reviewers`, `probe-quota`, or
   `detect-runtimes`, and do not write `$RUN_TMP_DIR/reviewers.json`** —
   points 3–5 below are entirely skipped, not just their side effects;
   this is the "skip it entirely, minimal overhead" case the flag exists
   for. Because this entry's `cli` is always `null`, Step 1's dispatch
   never needs `reviewers.json` for it either (only the external branch
   reads that file), so nothing downstream is left dangling. Go directly
   to Step 1.
3. **Required — check before the call below, not optionally**: the
   `--if-stale` call immediately after this destroys the evidence a
   missing-file check would find (it creates the file), so this order is
   fixed — check first, save second:
   ```bash
   [ -f "$RUNTIMES_JSON" ] || echo "no-runtimes-snapshot-yet"
   ```
   Then refresh the runtimes snapshot if it's missing or older than
   `RUNTIMES_TTL_SECONDS` (~30 days — CLI/model presence rarely changes):
   ```bash
   python3 "$TOOLS_PY" detect-runtimes --if-stale "$RUNTIMES_JSON"
   ```
   `--if-stale` checks `cache_is_stale` itself and no-ops
   (prints `{}`, doesn't touch the file) when the existing snapshot is
   still fresh; when missing or stale it detects and saves in the same
   call, so this is always safe to run. If the check above printed
   `no-runtimes-snapshot-yet` (this was the first-ever save), print one
   line — "No cross-AI config saved yet — run `ai-kit-spec-config` so
   this doesn't repeat every invocation." — then continue to step 4
   regardless; do NOT skip reviewer resolution (there's usually no
   `review-spec.toml` yet either, so `resolve-reviewers` in step 5
   degrades to `NO_CONFIG_FALLBACK` on its own — no special-casing needed
   here beyond the detection call and the hint).
4. Refresh quota for anything the config's ladder might need. `--cwd`
   takes exactly one directory — when Step 0.1 recorded `CODEBASE_ROOT`
   as a labeled set (cross-repo plans), use the root that owns the
   primary document under review (the first entry in `<DOC_PATHS>`); the
   same rule applies to `resolve-reviewers` at point 5 below:
   ```bash
   python3 "$TOOLS_PY" probe-quota --cwd <CODEBASE_ROOT> \
     --quota-path "$QUOTA_JSON"
   ```
   (No-op — writes `{}` — when there is no config/ladder to probe.)
5. Resolve the reviewer list, saving its output to a file (Step 1's
   external dispatch needs a stable path to feed `dispatch-reviewer`,
   not just the in-context text). This point is only reached when cross-AI is
   actually active — `--no-cross-ai` already short-circuited at step 2
   above — so `--cross-ai` is always passed here, never conditionally.
   (Do not split this command across a trailing `\` followed by an
   inline `#` comment — that escapes the *space* before the comment, not
   the newline, so the redirect below silently becomes a separate command
   that truncates the file.):
   ```bash
   python3 "$TOOLS_PY" resolve-reviewers \
     --cwd <CODEBASE_ROOT> \
     --quota-path "$QUOTA_JSON" \
     --source-vendor <SOURCE_VENDOR from the "## Inputs" section's flag parsing> \
     --cross-ai \
     > "$RUN_TMP_DIR/reviewers.json"
   ```
   `resolve-reviewers` itself calls `cfg_resolve(cwd, env)`,
   which already handles the local-vs-global/`strategy` resolution — this
   step never re-implements that logic, it only picks which `--cwd` to
   pass (`CODEBASE_ROOT` from Step 0.1, so the resolved local config is
   the one that actually owns the document under review — when
   `CODEBASE_ROOT` is a labeled set, that means the root of `<DOC_PATHS>`'s
   first entry, same rule as point 4 above).
6. **(Active cross-AI path only — point 2's degraded path already set
   `REVIEWER_LIST` directly and skipped straight to Step 1.)**
   `$RUN_TMP_DIR/reviewers.json` holds a JSON array of 1 or 2 reviewer
   objects. Record its contents as `REVIEWER_LIST` (index 0 = primary/only
   reviewer, index 1 = the secondary in double mode) — Step 1 both reasons
   over this in-context and passes the same file's path (plus the entry's
   index) to `dispatch-reviewer` for external dispatch.

## Step 1 external-CLI dispatch — full rationale for `dispatch-reviewer`

SKILL.md's Step 1 (external-CLI branch, point 3) gives the exact command for calling
`dispatch-reviewer`. This section is the rationale behind that command's two hard rules —
consult it only if you're tempted to deviate from the command as given.

**Why you must not render the command yourself and pass it back in.** `dispatch-reviewer` takes
the reviewer entry (`--reviewers-json` + `--index`), not a pre-rendered command string, and calls
`render_reviewer_command` internally *after* it has prefixed the tooling guidance onto the
prompt. That ordering is load-bearing twice over: some CLIs (grok) inline the prompt into their
own command line via `{prompt}` rather than reading stdin, so guidance composed after the render
would never reach them; and a rendered command round-tripped back through a `--command "<string>"`
shell argument would be shell-evaluated twice, reintroducing the `$`/backtick injection hazard
`render_reviewer_command`'s escaping exists to prevent. There is likewise **no**
`--codegraph-registered` flag to compute: `dispatch-reviewer` runs the same live
`check_codegraph_mcp_healthy` check itself whenever the entry has a `cli` (the same
internal-resolution pattern the execute family's `prepare-tooling` already uses), so the
orchestrator never has to evaluate it. `$SHARED_TOOLING_PATH` and `$TOOL_AVAILABILITY_JSON` are
surfaced to the reviewer as named `SHARED_TOOLING_PATH = …` / `TOOL_AVAILABILITY = …` lines at
the top of the composed prompt.

**Why the dispatch call must be backgrounded or given a near-cap explicit timeout.** The tiers
are cumulative, not a ceiling: the default `[600, 1200, 1800]` is up to **60 minutes** of wall
time in the worst case, and tier 1 alone (600s) already equals the harness's own 600000ms
maximum. A short default `Bash` timeout kills the dispatch mid-tier and throws away work that was
still running. Either run the command with `run_in_background` and poll for
`$RUN_TMP_DIR/iter<N>-<key>.md` to exist and stop growing before moving on to Step 1.5, or (for a
config whose tiers you know are short) pass an explicit `timeout` close to the harness cap. Treat
a dispatch that never produces the report file exactly like a nonzero exit: the file is absent,
so the fail-closed rules apply unchanged.

**If `dispatch-reviewer` exits nonzero** (a malformed or missing `command` template on this
reviewer entry, or an empty `timeout_tiers` — config errors, not runtime failures), this
reviewer's slot failed to dispatch. Do not write or keep `$RUN_TMP_DIR/iter<N>-<key>.md` for it —
leaving it absent is what makes Step 1.5's `merge-reports` (double mode) or the missing-file case
(single mode) fail closed through the existing `### Status:`-line-based rules, with no new
special-casing needed here.

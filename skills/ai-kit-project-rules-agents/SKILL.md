---
name: ai-kit-project-rules-agents
description: >-
  Use when an AGENTS.md or CLAUDE.md-style agent-instruction file needs checking against ai-kit's own 19-rule house ruleset (a CLAUDE.md audit, missing workflow rules, broken relative links), or to fix it: insert missing house rules, repair broken links, via one /agent-md-refactor pass; also for "is my AGENTS.md missing any workflow rules". Triggers: "house rules", "agent instructions", "workflow-rule audit". Route a whole-repo "check everything" request to `ai-kit-project-rules-all` instead.
---

# ai-kit-project-rules-agents

## Scope

This skill checks a target repo's AGENTS.md/CLAUDE.md-style instruction file against ai-kit's own 19-rule house ruleset (`rules.py`). The 19 rules are ai-kit's own accumulated convention, applied here to whichever repo is being checked — they are NOT a general-purpose rules engine offered to other projects.

## Resolve the entrypoint

Resolve once per invocation, in one Bash call. The loop prints the resolved, absolute entrypoint path (symlinks followed, so it is stable if the working directory changes); that printed path is the one to carry, record it literally. Set `SKILL_DIR` to the directory that contains this `SKILL.md` (the host's skill base directory; the one line to edit). An unedited block aborts with a message instead of guessing. `SKILL_DIR` is tried first so a checkout runs its own copy rather than an installed one that may be on another branch.

```bash
SKILL_DIR='<directory containing this SKILL.md>'
[ -f "$SKILL_DIR/SKILL.md" ] \
  || { echo "set SKILL_DIR to the directory containing this SKILL.md" >&2; exit 2; }
for d in "$SKILL_DIR" \
         "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-project-rules-agents}" \
         "$HOME/.claude/skills/ai-kit-project-rules-agents" \
         "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills/ai-kit-project-rules-agents" \
         "$HOME/.agents/skills/ai-kit-project-rules-agents"; do
  [ -f "$d/ai-kit-project-rules-agents.py" ] \
    && [ -d "$(cd "$d" && pwd -P)/../_shared/ai_kit_rules_common" ] \
    && { printf '%s\n' "$(cd "$d" && pwd -P)/ai-kit-project-rules-agents.py"; break; }
done
```

The second test skips a candidate that cannot import: the package needs `skills/_shared/` beside the skill's real (symlink-resolved) directory, which a checkout and the `tools/setup.py` symlink install have and a plain copy-install does not (the entrypoint loop skips it; importing the package anyway raises `ImportError`). So a plain copy at `SKILL_DIR` is skipped, and a printed directory that is not `SKILL_DIR` itself (compare after resolving symlinks) means another install is running instead: tell the user which. If nothing prints, stop and report that no importable install was found; the fix is `python3 tools/setup.py` from an ai-kit checkout, or running the checkout's copy.

Paths used below, relative to the skill directory (`SKILL_DIR`): the rule table is `ai_kit_project_rules_agents/rules.py`, and the shared classifier is `../_shared/ai_kit_rules_common/classification.py`. A resolved entrypoint always has both, because the loop above requires `_shared`.

## Trust gate (before running)

When `<repo_root>/.planning/` exists, `check` and `remediate` run a GSD identity probe for R18/R19: `node` runs `runtime-identity` (after a `git rev-parse` to find the project root) on the gsd-tools that GSD's own launcher order resolves for that repo, which is the repo's own `gsd-core/`, `.claude/gsd-core/` or `.codex/gsd-core/` copy first, then the host homes, then `gsd_run` on PATH. A project-local copy is the target repo's own code. Unless the user has already said they trust that repo's code (their own project, or they asked you to run its GSD commands), ask before running. If they decline, or no one can be asked, prefix each command with `AI_KIT_SKIP_GSD_PROBE=1`: the probe is the only step that executes anything from the repo, and the flag skips all of it. With the flag R18/R19 always come back as `unverified` notices (expected, not a sign the flag failed; do not rerun without it); without it they get a real verdict when the probe succeeds, and the same notice when it fails. Everything else only reads: tool presence looks up `graphify` and the modern CLIs by name on PATH and checks for `.codegraph/`, `graphify-out/` and `.planning/` directories, without running a binary. Without the flag, a stderr line `ai-kit: gsd identity probe ran <path>` means the probe already executed that path (no sibling skills or no gsd-tools prints nothing); with the flag it never appears. The probe also needs the sibling skills `ai-kit-gsd-curated-config` and `ai-kit-spec-review` installed; without them R18/R19 always come back as `unverified` notices, and the fix is to install those siblings, not to change the trust answer.

## Run the check

Substitute the recorded path for `<ENTRYPOINT>`:

```bash
python3 <ENTRYPOINT> check <repo_root>
python3 <ENTRYPOINT> remediate <repo_root>
```

What is read: `AGENTS.md` at `<repo_root>`, else `CLAUDE.md` (`AGENTS.md` wins when both exist), plus every file it links to directly: one hop, same-repo relative links only, the first 20 distinct targets, link targets inside fenced code blocks are not followed. A rule stated two links deep is invisible to the check. Rule signals are matched against the raw text, so a signal phrase inside a code fence DOES count. If neither root file exists, every rule whose condition is met reports `missing`; ask the user whether to create `AGENTS.md` before remediating (`remediate` never creates it, so the file must exist before any insert can land).

If a command exits non-zero, report its stderr and stop (for example a non-UTF-8 `AGENTS.md` raises a traceback). If every rule whose condition is met comes back `missing`, first confirm `<repo_root>` is the intended repo: a mistyped path looks the same as a repo with no instruction file.

Output shapes (JSON on stdout; the trimmed `remediate` example follows). `remediate` runs `check` internally but drops `links`, so run both. Key, contents, what to do:

- `check.workflow`: `missing`, `near_miss` and `not_applicable` findings (the CLI omits `present`). `unverified: true` plus a `reason` on a `not_applicable` finding is a flag, not a status: its condition could not be proven (R18/R19 GSD identity). It appears only in `check` (`remediate` diverts it to `notices`); report it, never insert it.
- `check.links`: broken relative links from the root file (image links included, `#anchor`/`?query` stripped, anchor-only skipped). Fix by correcting or removing the link.
- `remediate.remediate`: ordered, only `missing` (`auto_apply: true`) or `near_miss` (`auto_apply: false`), each with its rule's `signals` (the literal phrases the check looks for). Feeds Steps A-D.
- `remediate.notices`: every rule skipped because its condition is unverified, each with a `reason`. Report to the user, never insert. `remediate.blocked` is always empty here (no research-dispatch domain).

```json
{
  "remediate": [
    {"kind": "workflow", "id": "R01", "status": "missing", "criticality": 1,
     "summary": "...", "signals": ["english only", "english-only", "non-negotiable"],
     "matched_signals": [], "auto_apply": true},
    {"kind": "workflow", "id": "R06", "status": "missing", "criticality": 3,
     "summary": "When modern CLI tools (rg, bat, sd, fd, eza) are present, agents should be told to prefer them over their legacy counterparts, with a short usage hint for each installed tool.",
     "signals": [["rg", ["rg", "ripgrep"]], ["bat", ["bat", "batcat"]], ["sd", ["sd", "stream editor", "sed replacement"]], ["fd", ["fd", "fd-find"]], ["eza", ["eza", "exa"]]],
     "matched_signals": [], "auto_apply": true}
  ],
  "blocked": [], "notices": []
}
```

## Wrap mechanism (what makes this different from plain `/agent-md-refactor`)

`/agent-md-refactor` is an external, optional skill: this repo does not ship it, so it may be absent. Where installed it is a whole-file structural refactor with no house-rule awareness. Its phase titles (such as Find Contradictions or Identify the Essentials) are known only from its own `SKILL.md`: name a phase only after reading that file, and otherwise default to direct edit. THIS skill always runs `check`/`remediate` FIRST. When the user only asked to check or audit, report the `remediate` entries, `notices` and `links` and stop: Steps A-D edit the target file, so they run only when the user asked to fix it or accepts when you offer, and reach `/agent-md-refactor` only when the Step B list is non-empty. `/agent-md-refactor` has no CLI, no callable interface and no per-rule insertion mode: it is one whole-file Markdown refactor pass, possibly with its own confirmation gate. So the confirmed list goes in once, as extra input to that one pass, or by direct edit when the skill is absent.

The hand-off is Steps A and B, the pre-flight backup, Step C, then the Step D re-check.

**Step A (confirm near-misses first, owned by THIS skill).** This runs BEFORE `/agent-md-refactor` is invoked at all. For every `remediate` entry with `auto_apply: false` (a near-miss):

- **Confirmation:** STOP and ask the user to confirm or decline each one individually. Name the rule id, its current near-miss evidence (the entry's own `matched_signals` list: the literal phrases this checker already found in the target file, never an unsupported "trust me" claim), and what would be inserted if confirmed.
- **Unattended:** with no user to ask, treat every near-miss as declined, apply only the Step B clauses by direct edit (no `/agent-md-refactor` pass: its internal confirmation gate needs a user), and keep the pre-flight backups so Step D can decide keep or restore.
- **R20 rewrite (extra sub-step when R20 is confirmed):** each `hardcoded_counts` line states a literal worker count or a share above 40%, and may sit in the root file or any file it links to (within the first-20-links, in-repo set above), so search them all. Confirming R20 means inserting its block AND rewriting each of those lines to the CPU-share form. R20's `summary` is the generic sentence from the catalog (`PARALLEL_TEST_GENERIC`), verbatim: "Unit tests run in parallel with a worker count of floor(40% of the available CPUs), at least 1, computed at run time; never a hardcoded core or worker count." followed by one clause line per detected stack; write the payload `summary` exactly, never a paraphrase (a paraphrase without "parallel", "40%" and an "available CPUs"/"CPU share" phrase stays `missing`). R20 stays `near_miss` while any such line is left.
- **`unverified_stacks`:** a stack listed there already has its clause marked `(unverified)` inside the block; insert it as given and tell the user.
- **Why not its contradiction phase:** the confirmation is deliberately NOT routed through `/agent-md-refactor` (its first phase, when that file shows one, is about conflicting instructions already in the file, not whether to insert a missing house rule).

**Step B (assemble one ordered list).** Build the final ordered list = every `auto_apply: true` entry, plus every user-confirmed near-miss entry, in the same most-critical-first order `remediate` already returned. Declined near-miss entries are dropped and reported inline as skipped.

- **List non-empty:** run the pre-flight backup, then Step C.
- **List empty:** do not invoke `/agent-md-refactor`. If `links` has broken entries, run the pre-flight backup FIRST, fix them by direct edit, then go to Step D. If `links` is empty too, nothing is edited: report.

**Pre-flight backup (own step: before ANY edit, link-only fixes and direct edits included; run once).** The refactor may restructure, split and rename, and R20 rewrites lines in linked files, so back up EVERY file this run may modify:

- **Set and run:** the target file plus each file it links to directly (the same set `check` reads: same-repo relative links, one hop, first 20 distinct targets, none inside fenced code; `check.links` lists only broken links, so read the file's links yourself, and a 21st link or a symlink escaping the repo is read by neither). One Bash call, substituting the literal repo root and each path relative to it:

```bash
REPO='<repo_root>'; FILES=('<target file>' '<linked file>')   # one entry per file, relative to repo_root
BACKUP="$(mktemp -d)"
for f in "${FILES[@]}"; do
  [ -f "$REPO/$f" ] || continue
  if git -C "$REPO" ls-files --error-unmatch -- "$f" >/dev/null 2>&1 \
     && [ -z "$(git -C "$REPO" status --porcelain -- "$f")" ]; then
    echo "clean: $f"
  else
    mkdir -p "$BACKUP/$(dirname "$f")" && cp -p "$REPO/$f" "$BACKUP/$f" && echo "backup: $BACKUP/$f"
  fi
done
```

- **`clean`:** tracked and unmodified, so git holds its current content and the diff afterwards is exact. **`backup:`:** every other file gets a copy outside the repo: modified, untracked, gitignored (an ignored `CLAUDE.md` prints no `git status` output, which is why tracked state is tested with `ls-files`, not `status` alone) or not in a git repo.
- **Any `backup:` printed:** ask the user to commit or stash first; if they would rather proceed (or no one can be asked), the backups are already saved. Record the backup root.
- **Abort or rejected result:** restore each backed-up file with `cp -p "$BACKUP/$f" "$REPO/$f"` and list any files the run created (`git status --porcelain`) for the user to remove.

**Step C (one invocation, direct edit by default).** Unless unattended (see Step A), first look for the skill (first case below); when its `SKILL.md` is absent, edit directly. When it is present, invoke `/agent-md-refactor` against the target file once, never once per rule. Hand the Step B list's `summary` strings to it as additional "essential content" candidates, in the list's most-critical-first order, which is the priority when it has to choose what earns root-file placement; name its phases only as the `SKILL.md` you read names them. Rules for the inserted clauses:

- Entries with `verbatim: true` (R18, R19, R20) are inserted exactly as given, as one block, never reworded: their signal phrases must survive the refactor unchanged. For a verbatim near-miss, the block replaces the partial clause already in the file instead of sitting beside it.
- Every other entry may be paraphrased, but its clause must contain the entry's `signals`, because the bare summary often does not classify `present` (R01, R12 and others fail on their own summary).
- Phrase thresholds: a flat list needs all its phrases, or at least half (rounded up) when it has three or more; a list of lists needs one phrase from each inner list; a list of `[tool, [phrases]]` pairs (R06) needs one phrase for each installed tool, and the entry's `missing_tools` names the installed tools still lacking one.
- Tell `/agent-md-refactor` that these clauses stay in the root file or a file it links to directly; a rule two links deep is invisible to the check.
- State each clause in prose rather than inside a code fence, so a reader sees it. This is a readability rule, not a check rule: the checker would also count a signal inside a fence.

Pick the case that applies; every case keeps the pre-flight backup above and the clause rules:

- **Mechanism available:** invoke `/agent-md-refactor` once through whichever skill-invocation mechanism the host provides for an installed skill: a slash command or a named subagent/Task dispatch (Claude Code's `Agent` tool with `subagent_type: general-purpose` is one worked example, never a requirement). Find it by walking the entrypoint loop's candidate directories with `agent-md-refactor` as the skill name and the test `[ -f "$d/SKILL.md" ]` (sibling `../agent-md-refactor` first, then the plugin root, `$HOME/.claude/skills`, the opencode skills directory, `$HOME/.agents/skills`; no `_shared` check) — never a hardcoded `~/.claude/...` path.
- **Skill not found:** the default; do NOT stop. Tell the user `agent-md-refactor` is not installed and offer the Step B clauses by direct edit, under the rules above. Only the refactor is skipped: the pre-flight backup is still required on this direct-edit path, because Step D's diff depends on it. Then continue with Step D.
- **No dispatch mechanism:** the host has no way to invoke an installed skill: read the `agent-md-refactor/SKILL.md` found by the same walk into context and follow it manually for this one invocation.

There is no Python import or subprocess call into `agent-md-refactor` (no such interface): the hand-off is always a documented instruction sequence for whichever agent executes this skill, never code.

**Step D (re-check, direct edits only).** Work through this checklist in order:

1. **Re-check:** run `check` again. Every accepted Step B id must now be absent from `workflow` (the CLI omits `present` findings; a declined near-miss stays `near_miss`, see 4), and `links` must be empty, since the refactor may have split or renamed files.
2. **Show the diffs:** what changed in EVERY file of the pre-flight `FILES` set, not just the target: `git -C <repo_root> diff -- <file>` for each `clean` file, `diff -u "$BACKUP/<file>" "<repo_root>/<file>"` for each `backup:` file, plus `git -C <repo_root> status --porcelain` for files created or renamed.
3. **Decide keep or restore:**
   - Attended: Confirm that nothing outside the Step B clauses, the corrected `check.links` targets and the refactor's own restructuring changed the user's content. Any removed or reworded text unrelated to a Step B id goes back to the user, who decides whether to restore it from the diff or the backup.
   - Unattended, if the diff shows any change outside the Step B clauses and the corrected `check.links` targets, restore every `FILES` entry (`cp -p "$BACKUP/<file>" "<repo_root>/<file>"` for a `backup:` file, `git -C <repo_root> restore -- <file>` for a `clean` one) and report what was attempted; otherwise keep the edit. List the files the run created (from step 2), never delete them.
4. **Fix the rest by direct edit:** each remaining accepted Step B id or broken link, never a second `/agent-md-refactor` pass. A confirmed R20 that is still `near_miss` means a `hardcoded_counts` line survived (the finding lists them): rewrite that line, or report it if the user refuses, and do not insert the R20 block again. Near-misses the user declined in Step A stay declined: they remain `near_miss` in the re-check, so report them as declined, never as remaining defects, and never insert or edit them here.
5. **Report** anything still unresolved instead of calling the remediation done.

## Anti-patterns (NEVER)

- **NEVER treat a paraphrase as sufficient.** The shared engine (`../_shared/ai_kit_rules_common/classification.py`) classifies by literal lowercase substring matching against each rule's `signals` — it does **not** do semantic matching. Content that is semantically equivalent to a rule but uses different wording still reports `missing`/`near_miss`. The entry's signal phrases must appear in the prose, at the Step C thresholds — phrase it naturally, but never assume "captures the meaning" is enough.
- **NEVER tell the user a rule is satisfied just because it is absent from `workflow`.** Matching is by bare substring, so short signals (`rg`, `bat`, `sd`, `fd`, `kill`, `tmp/`) can be satisfied by unrelated text such as "argument" or "batch". Search the file for the rule's `signals` and read the matching line before calling it compliant. A rule absent from `workflow` is absent from the payload too, so take its `signals` from `ai_kit_project_rules_agents/rules.py` (skill-relative).
- **NEVER start Steps A-D on a check-only request.** They edit the target file; "is my AGENTS.md missing any rules" gets the report and an offer to fix.
- **NEVER route near-miss confirmation through `/agent-md-refactor`**; Step A owns it.
- **NEVER invoke `/agent-md-refactor` more than once per wrapping run:** a second whole-file pass risks pruning the first's insert.
- **NEVER hardcode a `~/.claude/...` path** to this skill's entrypoint or `agent-md-refactor`: walk the host-neutral candidate list.
- **NEVER assume `rules.py`'s `category` field drives what gets checked here.** `check_workflow_rules` filters by non-empty `signals`, not by `category`. R02 carries a non-workflow `category` label, yet its AGENTS.md-prose clause is still checked here because its `signals` are non-empty. R02's structural half is another skill's concern and is not read by this skill at all. Don't "fix" a rule's category thinking it changes routing; it doesn't.

## Reporting rule

Findings and remediation results are reported INLINE in the conversation only. This skill never writes a persisted report file into the target repo — git is already the history of AGENTS.md edits, and a separate "why this file was edited" report is exactly the kind of file the user does not want.

## Ruleset reference

`ai_kit_project_rules_agents/rules.py` (skill-relative) is the source of truth for the 19 house rules (id/category/criticality/condition/signals/summary). This document points at it rather than restating the rule text; the `remediate` payload already carries what Step C needs. R20 is composed per detected stack: its clause for each stack comes from `ai_kit_rules_common.tool_catalog.PARALLEL_TEST_FORMS`.

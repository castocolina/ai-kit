---
name: ai-kit-gsd-curated-config
description: Curated GSD `.planning/config.json` setup for a target project. v2 flow — inventory → recommend → plan edits → apply → follow-ups — picks models per tier, wires installed skills to GSD agents, and sets up a cross-AI execution runner (`.planning/scripts/cross-ai.mjs`) and cross-AI plan review; the kept v1 path asks only `model_profile`. Config keys are written only through gsd-tools `config-set`/`config-new-project`. Use when asked to "configure .planning/config.json", "set up GSD config fast", "wire skills to GSD agents" or "set up a cross-AI execution runner", without the full `gsd-settings`/`gsd-config` interrogation — a faster alternative, not a replacement.
---

# ai-kit-gsd-curated-config

## Scope

This skill wraps `ai-kit-gsd-curated-config.py`. **Primary path:** the v2 pipeline
(`inventory` → `recommend` → `plan-set`/`plan-unset` → `apply` → follow-up approval).
**Secondary path:** the kept v1 flow (one `model_profile` question plus fixed presets) — read
[`references/v1-path.md`](references/v1-path.md) only when running it.

Config keys are written only through gsd-tools (`config-set` / `config-new-project`, via the
shared `ai_kit_spec.gsd_tools` wrappers). Two writes are not config keys: the runner script
and, when an apply fails, the backup bytes restored directly. The `ai-kit-spec-review`
skill must be installed beside this one; `node` and a resolvable gsd-core are required.

## Prerequisites and trust model

**Use it on trusted checkouts only.** `inventory` runs the target project's own gsd-core under `node`
(project-local gsd-core wins over global), so point `--project-dir` only at trees you would
already run GSD in. Resolution order: on a pi or opencode host `<root>/.pi/gsd-core` or
`<root>/.opencode/gsd-core` first, then `<root>/gsd-core`, `<root>/.claude/gsd-core`,
`<root>/.codex/gsd-core`, then global installs and a `gsd_run` launcher on `PATH`. When
`JEV_API_URL` is set, `inventory` also opens one TCP connection to its host (reachability
only, never a request).

**Exit codes:**

| Exit | v1 subcommands | v2 subcommands |
|---|---|---|
| `0` | the call finished; for `apply-execution` read `cross_ai_command_written` and `degraded_reason` before calling it configured | success (read the JSON for warnings and `needs_choice`) |
| `2` | install problem (sibling skill, `node` or `gsd-tools.cjs` missing) or, for `apply-execution`/`apply-review`, an unrecognized `--cli` before any write. Surface stderr verbatim; do not retry | a refusal you can fix: bad `--out`, inventory digest mismatch, open `needs_choice`, malformed inventory or plan, held apply marker, refused `plan-set` value — or the same install problems. Read the stderr line, fix the input, re-run (`inventory`/`recommend` first when it says so) |
| `1` | a gsd-tools read/write failed | `apply` write failed and rolled back (or `restore_error`); a follow-up command failed |

## Resolve the entrypoint

Resolve once per invocation, in one Bash call, and record the printed path. Shell variables
do not survive between tool calls: write that absolute path wherever `"$ENTRYPOINT"` appears.

```bash
for d in "$(dirname "<absolute path to THIS SKILL.md>")" \
         "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-gsd-curated-config}" \
         "$HOME/.claude/skills/ai-kit-gsd-curated-config" \
         "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills/ai-kit-gsd-curated-config" \
         "$HOME/.agents/skills/ai-kit-gsd-curated-config"; do
  [ -f "$d/ai-kit-gsd-curated-config.py" ] && { printf '%s\n' "$d/ai-kit-gsd-curated-config.py"; break; }
done
```

Substitute the directory containing this `SKILL.md` into the first candidate: the script beside
the instructions you are following always wins, so an older install elsewhere (one without
`ensure-runner`, say) never runs under these instructions. The installed locations are only a
fallback when that directory has no script. If none exists, stop — the skill is not installed.

## Run the v2 flow

Before the first command, ask yourself: is `<target>` a trusted checkout? Was its config
last written by v1 (`apply-execution` writes the runner command `node
.planning/scripts/cross-ai.mjs …` and renders or upgrades `.planning/scripts/cross-ai.mjs`,
so a user-edited script gets `.new` instead of being overwritten; v2 replaces that command)?
Where will `inventory.json` and `plan.json` live? Keep both in one
scratch directory **outside** `<target>/.planning/`: `recommend --out` is refused inside the
project's `.planning/` and onto an input or config file. `plan-set`/`plan-unset` read
`inventory.json` beside `plan.json` unless `--inventory` is given.

1. **Inventory** (never touches project config; prints JSON to stdout — capture it). It
   refreshes ai-kit's runtime/catalog caches and may contact the catalog services and the
   jev endpoint (TCP reachability only); say so before running it offline or on a no-write request. Create the scratch dir once and
   record its printed path; like the entrypoint, write it literally wherever `$WORK` appears.
   Add `--host <host>` only when the host cannot be detected (exit 2 says so); `--refresh`
   forces a full catalog fetch.

```bash
WORK="$(mktemp -d)" && printf '%s\n' "$WORK"
python3 "$ENTRYPOINT" inventory --project-dir <target> > "$WORK/inventory.json"
```

2. **Ask the user, in one message, four questions — nothing else:**
   - `model_profile`: quality / balanced / budget / adaptive (adaptive recommended);
   - rigor: `mvp` (cheapest: 40th-percentile price ceiling, research and verification on haiku,
     2 skills per agent), `standard` (75th percentile, 3 skills), or `rigorous` (no price
     ceiling, planning on opus, 2 review lanes, 5 skills);
   - cross-AI plan review: y / n / default;
   - cross-AI execution: y / n / default.

   For "default", omit that `--cross-ai-*` flag: recommend derives it from rigor, host and
   the inventory, and records `defaulted: true`. The placeholders below are the user's answers,
   never fixed values.

```bash
python3 "$ENTRYPOINT" recommend --inventory "$WORK/inventory.json" --profile <profile> --rigor <rigor> --cross-ai-review <y|n> --cross-ai-exec <y|n> --out "$WORK/plan.json"
```

3. **Review the plan with the user**: every `needs_choice` entry, note, warning and
   `effect`/unverified flag. Resolve each choice with `plan-set` or decline it with
   `plan-unset` — never skip one. Values are JSON for lists, booleans and numbers
   (`'["ponytail"]'`, `true`, `1800`) and bare text for strings. An `agent_skills.<agent>`
   value is that agent's whole list.

```bash
python3 "$ENTRYPOINT" plan-set <key> '<value>' --plan "$WORK/plan.json"
python3 "$ENTRYPOINT" plan-set script:cross-ai.model.<runner> <model id> --plan "$WORK/plan.json"
python3 "$ENTRYPOINT" plan-unset <key> --plan "$WORK/plan.json"
```

   - **Runner models** are the pseudo-keys `script:cross-ai.model.<runner>` (pick from
     `artifacts[0].choices.<runner>.candidates`) and `script:cross-ai.prefer` (a JSON list
     of runner ids, in order). `plan-unset script:cross-ai.model.<runner>` reopens a choice.
     A pi or codex model with reasoning modes also pins its effort (`config.effort`, medium
     or the nearest mode); the runner passes it as pi `--thinking` / codex effort.
   - **Trusted roots** (`agent_skills_security.trusted_global_roots`): the one candidate's
     `value` is the whole list — already-configured roots first, then the new `~/` roots.
     Approve it with that list, or decline with `plan-unset`. A list that drops an
     already-configured root is refused; the refusal prints the merged list — re-run
     `plan-set` with it (entrypoint and `--plan` included).
   - `workflow.cross_ai_command` and the runner artifact stay open until every runner in
     `artifacts[0].choices` has a model (`plan-unset` is refused while execution is on).
     To drop a runner, `plan-set script:cross-ai.prefer` without it; to drop execution,
     `plan-set workflow.cross_ai_execution false`.
   - A refused value outside the candidates takes `--force` **only** when the user explicitly
     chose that value; say what it bypasses before using it.
   - **Removals:** every `unset` entry is a planned removal of a key the project has now; name
     each one with its `existing` value. v2 manages whole key families (`models.*`,
     `model_overrides.*`, `effort.agent_overrides.*`, `effort.routing_tier_defaults.*`,
     `dynamic_routing.*`, `review.models.*`, `review.effort.*`, `agent_skills.*`) and removes
     the keys in them the plan does not carry, so a v1-written config loses its overrides this
     way. `model_policy` is unset leaf by leaf, and `resolve_model_ids: omit` from the global
     defaults is unset on a claude host, where it makes `resolve-model` return an empty model
     for every agent without an override.

4. **Dry-run apply** (refuses while `needs_choice` remains; the inventory digest must match).
   Show the user every `add`, `change` and `remove` row by its full key before the real apply
   (`effort.agent_overrides.gsd-planner: high`, not "effort overrides on 10 agents"), one line
   per key with the dotted key written out whole, never a `family.*` line or heading with the
   agents listed under it, even when many keys share a value: a v1 migration is a long list,
   and that list is what the user approves. Then end the turn and apply only after the user
   answers. A "go ahead" given before those rows were
   shown does not approve them: the plan review summarizes, and the dry run is the first
   place the user sees every key that changes.
   On a project with no config yet, `remove` rows marked `"predicted": true` are the keys
   `config-new-project` is expected to copy from the global defaults — unverified until apply.

```bash
python3 "$ENTRYPOINT" apply --plan "$WORK/plan.json" --inventory "$WORK/inventory.json" --project-dir <target> --dry-run
```

5. **Apply** (config backup, marker `config.json.ai-kit-apply-marker`, runner snapshot
   `.ai-kit-apply-backup`):

```bash
python3 "$ENTRYPOINT" apply --plan "$WORK/plan.json" --inventory "$WORK/inventory.json" --project-dir <target>
```

6. **Follow-up approval.** After exit 0, read the report's `followups` block. Ask **one
   grouped yes/no** listing each required follow-up's argv, cwd, purpose, alternative,
   disclosures and unverified notes. On yes, run `python3 "$ENTRYPOINT"` followed by the
   `approve_with` string **unchanged**: it carries `--require` for the listed ids and a
   `--fingerprint` of the rows the user saw. If approval is refused because the follow-ups
   changed, list them again and re-ask. If `required` is empty, ask nothing and skip
   approval. Always relay `recommended` items as suggestions. If the report has no
   `followups` block (warning "follow-ups could not be listed"), run the listing command below.

```bash
python3 "$ENTRYPOINT" followups --plan "$WORK/plan.json" --inventory "$WORK/inventory.json" --project-dir <target>
python3 "$ENTRYPOINT" followups --plan "$WORK/plan.json" --inventory "$WORK/inventory.json" --project-dir <target> --approve --require <ids from approve_with> --fingerprint <fingerprint from approve_with>
```

**Failure states to report as such:**

- **`restore_error` (exit 1):** rollback failed — marker, config backup and runner snapshot
  stay. Do not delete the marker. The next `apply` refuses and prints the recovery steps
  recorded in the marker; follow them.
- **Exit 0 with cleanup warnings:** the apply **committed** — config and runner hold the
  applied state; **never** restore its backup. Delete only the leftovers the warning names.
  If a marker remains, the next `apply` refuses (exit 2) and prints the recovery steps
  recorded in it (the dry run does not check the marker).
- **Runner `git_timeout` or `git_error` status** (git could not read the work tree): claim
  nothing about its state, and report the status line only. After that status, or once a CLI
  has run outside a git work tree, the runner tries no other CLI: nothing proves the first one
  wrote nothing. (It moves to the next runner in the prefer order only after a fallback status
  on a verified-clean tree, `no_change` for example.) **`tree=unknown`** on a run outside any git
  work tree means the CLI ran without the check: report that, and do not read it as a clean or
  dirty tree.
- **Effort sync** is not offered when the inventory points at a workstream config (gsd-core
  sync reads only the root config).

## Cross-AI execution

v2 `apply` sets `workflow.cross_ai_command` to the bare `node .planning/scripts/cross-ai.mjs` and
renders the runner from the bundled template (template 4); the runner reads its prefer order and
models from its own CONFIG. The hook names the runner, never a raw vendor CLI string.

**Permissions depend on which flow wrote the hook — say which one applies:**

- **v2 `apply` (this flow):** the bare hook passes no `--codex-sandbox`, so **every exec target,
  codex included, runs with full permissions** (codex with `--dangerously-bypass-approvals-and-sandbox`).
  It also passes no `--prepend-file`/`--no-preamble`: the runner's own preamble is the only
  guidance. Never describe a v2-configured codex target as sandboxed.
- **v1 `apply-execution`** and **`ai-kit-spec-execute-gsd`'s hook** name one runtime and model
  and add `--codex-sandbox workspace-write` for codex: writes stay inside the project dir plus
  `/tmp` and `$TMPDIR` (`.git` writability unverified). Every other exec target still runs with
  full permissions. Only `ai-kit-spec-execute-gsd`'s hook also adds `--no-preamble --prepend-file
  .planning/scripts/cross-ai-guidance.md`, whose write-only-inside-the-project sentence is prose,
  not a boundary.

After every external dispatch, print the `AIKIT-XAI status=…` line from stderr **verbatim**.

**Bare profile by default** (pi `--no-skills --no-extensions`, opencode with Claude-skill
loading off). The opencode bare profile is **partial**: `~/.agents/skills` and
`~/.config/opencode/skills` still load — say so.

**`.new` is not active:** a user-edited runner is never overwritten; apply writes
`cross-ai.mjs.new` and reports `script.active: false`. Never treat `.new` as live. **Read
[`references/runner.md`](references/runner.md) when** a runner upgrade, a `.new` merge,
`ensure-runner`, the template flags, the live timeout, or hand-edited CONFIG `extraArgs` comes up.

## Skills

- **Bare names** in the plan; apply writes `skills/<name>`, `global:<name>` or
  `global:<plugin>:<name>`. Plan, notes and report never name an uninstalled skill.
- **Not wired, with a note:** a project copy whose directory resolves outside the project,
  and a global skill outside the home directory that no configured trusted root covers.
- **Trusted-root approval** is one `needs_choice`. If the user **declined**, the skill stays
  wired and gsd-core skips it with a reported warning.
- Unknown installed skills get capped proposals (one per name, wireable only) — never
  auto-install or auto-wire them.
- **Jev session gate:** inventory detects the jev (System One) backend, `system_one_backend`, by a TCP
  reachability check of `JEV_API_URL` or by `JEV_API_KEY` being present (never a health
  check). A wiring that rests on reachability alone carries an `effect` flag. The agent
  session also needs `GSD_PATH_JEV=1` and `GSD_PATH_JEV_TIMEOUT_SECONDS`.
- **`ponytail_visibility`** lists the ponytail skills in each host's global skills root
  only; on claude they usually arrive as plugin rows in `skills`. Report what inventory says.
- **Limit:** skills kept only in a project's `.claude/skills` are **not** scanned.
- **Plugin skills** need install plus layered `enabledPlugins` (user, project, local).
  Per-key layering is **unverified**: entries that rely on it carry an `effect` flag.

## Limits (as of 2026-10-15)

| Topic | Limit |
|---|---|
| cursor / pi hosts | **not live-validated** |
| opencode providers | Providers defined only in a project's `opencode.json` are not candidates |
| effort sync | Skipped for workstream configs; `--config-dir <project>/<host dir>` value **unverified** |
| local gsd root | `.opencode/gsd-core` install root **unverified** |

## Subcommand reference

| Subcommand | Required flags | Role |
|---|---|---|
| `inventory` | `--project-dir` (`--host`, `--refresh` optional) | Snapshot to stdout; refreshes ai-kit caches, may go online |
| `recommend` | `--inventory`, `--profile`, `--rigor`, `--out` | Write `plan.json` |
| `plan-set` | `key`, `value`, `--plan` (`--inventory`, `--force` optional) | Decide a plan entry |
| `plan-unset` | `key`, `--plan` (`--inventory` optional) | Decline / remove a plan entry |
| `apply` | `--plan`, `--inventory`, `--project-dir` | Write config + runner (`--dry-run` previews) |
| `followups` | `--plan`, `--inventory`, `--project-dir` | List, or `--approve` the listed commands |
| `ensure-runner` | `--cwd` (`--guidance-file <path>` or `-` for stdin, optional) | Render or upgrade `.planning/scripts/cross-ai.mjs`; prints JSON `{ready, runner, guidance, notes}`, exit 0 ready, 1 not ready, 2 on error. Readiness is the `ready` field: an edited current-template runner is kept ready, an edited older or foreign one gets `.new` and is not ready |
| v1 | `--project-dir`, except the two `detect-*-candidate` (no flags) | See `references/v1-path.md` |

## NEVER

- **Never replace `gsd-settings` / `gsd-config`.** Power-user and integration knobs stay there;
  route tuning questions to `gsd-settings --advanced`.
- **In the v2 flow, never skip the plan review or the dry run, and never resolve a
  `needs_choice` yourself**, whatever the user says about speed or trust ("just apply it"):
  those two steps are where the user sees what changes and what is removed. The v1 path has
  neither; its approval rule is in `references/v1-path.md`.
- **Never hand-write `.planning/config.json` or `plan.json`.** Hand edits bypass gsd-core's
  schema check and the plan's own validation; use the subcommands.
- **Never run `inventory` on an untrusted checkout** — it executes that project's JavaScript.
- **Never pass `--force` to `plan-set` by habit.** It bypasses the candidate check, the
  trusted-root drop refusal and the full-permissions guard on every key gsd-core runs as a
  command (`workflow.cross_ai_command`, `plan_bounce_script`, `code_review_command`,
  `test_command`, `build_command`); use it only for a value the user explicitly chose.
- **Never run v1 `apply-execution`/`apply-review` on a project v2 `apply` configured.**
  `apply-execution` overwrites `workflow.cross_ai_command` with its own single-runtime
  runner command, dropping the prefer order and models v2 chose.
- **Never delete an apply marker** without following the recovery text apply prints.
- **Never treat `cross-ai.mjs.new` as active** before merging it and running `--print-argv`.

## Common mistakes

| Mistake | Why it fails | Fix |
|---|---|---|
| Not redirecting `inventory` to a file | It prints JSON to stdout only; every later step needs the file | `> "$WORK/inventory.json"` |
| `recommend --out <target>/.planning/plan.json` | Refused (exit 2): the plan must not sit in the config dir it describes | Use a scratch dir; keep `inventory.json` beside it |
| Copying example values into `recommend` | They become config writes the user never chose | Ask the four questions; pass the answers |
| `apply` while `needs_choice` remains | Apply refuses (exit 2) | `plan-set`/`plan-unset` until the dry run is clean |
| Stale inventory digest | The plan was built from another inventory | Re-run `inventory` and `recommend` |
| `plan-set agent_skills.<agent> ponytail` | A bare word is not a JSON list | `'["ponytail"]'`, keeping the agent's other skills |
| Restoring the backup after a committed apply with cleanup warnings | Config and runner already match the plan; the restore undoes it | Delete only the named leftovers |
| Dry run and real apply in one turn | The user approves rows they never saw, and a family summary hides which overrides go | Show every row by full key, end the turn, apply on the answer |
| `effort.agent_overrides.*` (was `high`) on a list of agents | The user cannot match a line to a dry-run row, so one dropped key goes unnoticed | One line per full dotted key and its value |
| Running `approve_with` without the entrypoint, or edited | It starts at the subcommand; the fingerprint binds it to the listed rows | `python3 "$ENTRYPOINT"` + the exact string |

## Reporting rule

Report each step as a short structured summary in conversation order — no separate report file,
and no full inventory/recommend/apply JSON pasted by default (the candidate catalog alone can
bury the decisions). The summary must still carry, verbatim: every warning, every open
`needs_choice` with its candidates, every **unverified** note or `effect` flag (never upgraded to
fact), every refusal or degraded reason, and the exact rows an approval is bound to (the
follow-up argv/cwd list and its fingerprint). Show the full JSON when the user asks, and keep the
files in `$WORK` so it stays available. For cross-AI dispatches, include the verbatim `AIKIT-XAI`
line.

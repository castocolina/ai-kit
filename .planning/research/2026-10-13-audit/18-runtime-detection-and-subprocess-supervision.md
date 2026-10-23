# 18: Runtime detection and subprocess supervision

Date: 2026-10-13. Scope: the user's two requirements for ai-kit's spec skills (review, fix, execute).
1. Simplify "native vs per-runtime model": detect the host, inventory each runtime's models, and use one rule to choose a native subagent or a CLI subprocess.
2. Supervise subprocesses so the orchestrator always knows whether a child is waiting for input, erroring, slow or finished.

Paths:
- `R/` = `scratchpad/review-v13/` (read-only v1.3 tree). `K/` = `R/skills/ai-kit-spec-review/ai_kit_spec/`.
- `S/` = `scratchpad/stall-probe/`. Logs: `S/logs/<label>.{stdout,stderr,samples.jsonl,result.json}`. Harness: `S/probe.py` (spawns under `timeout 60`, samples the process group every 2 s), `S/show.py` (sample viewer), `S/classify-check.mjs` (runs cross-ai.mjs's classifier on the captured errors; output in `S/logs/classify-check.txt`).
- Tags: **[L]** live here, **[H]** local help/source, **[D]** docs, **[R0x]** earlier report, **[I]** inference, **[U]** unverified.

Model spend: grok $0.038 + $0.054 (two runs that reached a model); cursor `auto`; opencode `opencode/big-pickle` (free); pi `router-env/my-coding` (one healthy run). The other 11 runs failed before inference.

---

## 0. Ranked findings

1. **None of the four CLIs blocks on a permission prompt when stdin is not a TTY. Three of them fail silently instead.** [L]
   - opencode without `--auto` auto-rejects the `ask` and exits **0** with empty stdout (`opencode-a-noauto`).
   - grok without `--always-approve` exits **0** with `stopReason:"cancelled"` and only the intention text, "I'll create `hello.txt`..." (`grok-a-noapprove`). cross-ai.mjs's grok parser does not treat `cancelled` as an error, so **it would report this run as a success** (`S/logs/classify-check.txt`).
   - pi given an empty prompt exits **0** with no stdout and no stderr (`pi-c-noprompt`).
   - Only cursor fails loudly: rc 1 and "Workspace Trust Required" in 2 s.
2. **The only real hang is an open stdin.** pi with an open, never-closed pipe on stdin printed nothing for 60 s until `timeout` killed it with rc 124 (`pi-a-openstdin`). It sat in `S`/`ep_poll` with zero TCP connections and almost flat CPU (+6 ticks). So the fix is an invariant, stdin always EOF. Detection is only a backstop.
3. **Output growth alone cannot tell "slow" from "stuck".** [L] A healthy grok run produced **0 bytes for 28 s** with flat CPU (+6 ticks) before printing its answer (`grok-d-healthy`). The stuck pi run looked the same on bytes and CPU. The one signal that separated them was **established TCP sockets in the process group**: 7 for healthy grok, 3–8 for healthy cursor, 1 for healthy pi, and 0 for stuck pi.
4. **Bad-model errors are worded differently by every CLI, and opencode's does not say "model" at all.** [L] opencode prints `UnknownError: Unexpected server error`. cross-ai.mjs classifies only grok's wording as fatal; cursor, opencode and pi come back `other`. Checking the model against the runtime's own list before spawning catches all four. That list costs 0.2–1.5 s and no model call.
5. **Both classifiers scan text the model wrote.** [L] cross-ai.mjs adds `stdout.slice(-4000)` to the text it matches, so a model answer containing `assert resp.status == 503` classifies as `transient` and triggers a resume-retry. That is the same bug as audit 04 #5 (Python matching the substring "quota"). The root-cause fix for both: classify only stderr plus the CLI's structured error field.
6. **`native_runtime` is written and validated but never read.** [H] Nothing routes on it, so a config saved under Claude Code (native `model = "opus"`) would be dispatched the same way from an opencode host. See §1.3.
7. **Host env signals verified live in a child shell** [L, `pi-d-healthy`, `cursor-d-healthy`, `grok-d-healthy`]:
   - pi sets `PI_CODING_AGENT` (the source sets it to `"true"`, plus `AI_AGENT="pi"`);
   - cursor sets `CURSOR_AGENT`;
   - grok sets `GROK_AGENT` and `GROK_SESSION_ID`.

   `detection.py` has no grok signal, and `KNOWN_CLIS` has no pi. Claude Code itself exports `AI_AGENT=claude-code_…`, which cursor and grok children inherit. cross-ai.mjs does not scrub it.

---

## 1. Detection today

### 1.1 What exists (fact inventory)

| Piece | Where | What it does | Who reads it |
|---|---|---|---|
| `KNOWN_CLIS` | `K/detection.py:19` | `claude, codex, opencode, grok, cursor-agent`; **no pi** | `detect_installed_clis`, `build_runtimes_snapshot` |
| `_RUNTIME_ENV_SIGNALS` + `detect_current_runtime` | `K/detection.py:50-105` | pi > opencode > cursor > codex > claude; **no grok**; labels `cursor` vs binary `cursor-agent` | only `cli.py:884` `detect-current-runtime`, which prints `{"native_runtime": …}` and is called by ai-kit-spec-config Step 2.7 |
| Model inventory | `detect_opencode_models`, `detect_cursor_agent_models`, `detect_codex_models`, `detect_opencode_image_input` | runs `<cli> models` / `codex debug models` | `runtimes.json` (30-day TTL) |
| claude ids | `CLAUDE_MODEL_ALIASES`, `CLAUDE_FALLBACK_MODEL_IDS` (dated 2026-09-23), `claude_runtime_fields`, `claude_runtime_is_current` | aliases plus full ids, from the catalog `_meta` or a dated fallback, with a catalog-freshness edge | runtimes cache and catalog discovery |
| `native_runtime` validation | `K/config_io.py:96-135` and `K/model_catalog.py:50-53,157-164` | two duplicate `_VALID_NATIVE_RUNTIME` sets ("must change together") | **validation only**. AGENTS.md:79-82 itself calls the catalog copy "forward-compatible-only (no live producer)" |
| Native candidate (`cli: None`) | `quota.py:13` `NO_CONFIG_FALLBACK`; review SKILL.md:219-237; superpowers `mode: "native_claude"` (`dispatch_injection.py:318`, 21 references) | "run in-process via the `Agent` tool with one of 4 aliases" | the orchestrator agent |
| GSD runtime | `ai_kit_spec_gsd/gsd_config.py:59` `resolve_active_runtime` (null → "claude"), `adapter.py:151` | GSD's own `runtime` key, not ai-kit's host detection | GSD adapter |
| pi / grok inventory | none in `detection.py` | — | — |

### 1.2 Inventory commands, live timing [L, `S/logs/inventory-*.txt`]

| Runtime | Command | rc | Time | Lines |
|---|---|---|---|---|
| pi 1.2.0 | `pi --list-models --offline` | 0 | 0.2 s | 30 (table; `router-env` rows included) |
| grok 1.0.52 | `grok models` | 0 | 0.7 s | 9 (`* id` lines) |
| opencode 1.18.35 | `opencode models` | 0 | 1.5 s | 86 |
| cursor 2026.10.01 | `cursor-agent models` | 0 | 1.4 s | 263 |

None of them makes a model call. Together they cost under 4 s, so the existing 30-day `runtimes.json` cache is more than enough.

### 1.3 Why the current shape is complex and still wrong

- **A native entry's meaning depends on the host, but nothing checks the host.** ai-kit-spec-config writes `model = "opus"` plus `native_runtime = "claude"`. review SKILL.md Step 1 then always uses the `Agent` tool with that alias. From an opencode or pi host the same entry still says "opus", and no code compares `native_runtime` with `detect_current_runtime()`.
- **The same runtime has two names**: `cursor` (host label) and `cursor-agent` (`KNOWN_CLIS`). A `target == host` comparison would never match for cursor.
- **The wording is host-specific**: `native_claude` in superpowers, plus "four Agent-tool aliases" written as the rule rather than as the Claude Code example (memory note `ai_kit_spec_native_and_model_categorization`).

---

## 2. The simplified model

### 2.1 Three facts plus one rule

1. **Host** = `detect_current_runtime()`, with one runtime-id vocabulary: `claude, codex, opencode, cursor, grok, pi`. Add `("grok", "GROK_AGENT")` [L]. Keep innermost-wins ordering.
2. **Inventory** = for each installed runtime, `{bin, models[]}` from its own list command (§1.2), cached in `runtimes.json`. For the host only, add its native selector set (Claude Code: the `Agent` aliases `sonnet/opus/haiku/fable`).
3. **A candidate is always `(runtime, model)`.** The one exception is the session default, meaning "the host, its default model" (today's `NO_CONFIG_FALLBACK`, `model == ""`).
4. **Rule**, decided at dispatch time and never stored:

```
if cand.runtime == host and host_can_select(cand.model):   # alias / native selector of THIS host
    native subagent (host mechanism; Claude Code = Agent tool)
elif cand.model in inventory[cand.runtime].models:
    subprocess via the supervised runner (cross-ai.mjs recipe, §4)
else:
    status=bad_model, skip candidate (never spawn)
```

- A same-host model the host cannot select natively (for example an opencode host asked for an opencode model that no agent definition pins) goes through the subprocess branch with the host signals scrubbed. That needs no special case.
- How each host spawns a native subagent with a chosen model: Claude Code `Agent(model=alias)` [H, SKILL.md]; opencode / cursor / grok / pi per-call model selection is **[U]**. Until it is verified, `host_can_select` returns true only for the session default on those hosts. The rule still works; it just uses the subprocess branch more often.

### 2.2 Delete or simplify (ponytail lens)

- **Delete `native_runtime`** from the config schema, config_io and model_catalog validation (the duplicated `_VALID_NATIVE_RUNTIME`), the AGENTS.md:73-82 paragraph, ai-kit-spec-config Step 2.7/3 prose, and the 34 test lines that mention it. Evidence: no routing reader (§1.1). Rename `detect-current-runtime`'s output key to `host`.
- **Replace `cli: None` + alias** with an explicit `runtime` on every pinned entry. Keep "cli omitted" only for the session default (empty `model`).
  - Migration: an old native entry with `native_runtime = X` becomes `runtime = X`.
  - An old entry marked `unknown` becomes the session default.
- **Rename `native_claude` → `native`** in superpowers (21 references). The payload carries `runtime` and `model`.
- **One id vocabulary**: map `cursor` ↔ binaries `cursor-agent`/`agent` in one table (cross-ai.mjs `RUNTIMES.cursor.bins` already does this). Add `pi` to `KNOWN_CLIS` with `pi --list-models` and `grok` with `grok models`.
- **Simplify the claude inventory (user decision)**: report-00 wave 2 says Claude is the host and never a cross-AI target. If that holds, `CLAUDE_FALLBACK_MODEL_IDS`, the `_meta.anthropic_model_ids` path and `claude_runtime_is_current` (25 references across detection.py, cli.py and tests) only serve a subprocess target that is out of scope. Keeping `CLAUDE_MODEL_ALIASES` as the host's native selector set is enough. Keep them if codex or opencode hosts should ever call `claude -p`.
- **Replace the quota pre-probe with the run's own classification.** `probe_reviewer_quota` spends a real prompt per ladder entry with `shell=True` (audit 04 #8, synthesis A4). With preflight (inventory) plus the error table in §4, the first real dispatch tells you the same thing at no extra cost. This is optional; it is a bigger cut.

---

## 3. Live probe results

Each run: a throwaway git repo `S/<cli>/`, `timeout 60`, `CLAUDECODE`/`CLAUDE_CODE_ENTRYPOINT` scrubbed, samples every 2 s. Elapsed times are rounded up to the 2 s sample slice. No probe repo was modified (`git status` clean for all four).

### 3.1 Outcomes (fact inventory)

| Label | Provocation | rc | Time | stdout / stderr | Signature |
|---|---|---|---|---|---|
| `cursor-a-notrust` | `-p` without `--trust/--force`, fresh dir | 1 | 2.0 s | 0 / 412 B | stderr `⚠ Workspace Trust Required … Pass --trust, --yolo, or -f` |
| `cursor-b-badmodel` | `--model no-such-model-zzz` | 1 | 4.0 s | 0 / 6141 B | stderr `Cannot use this model: no-such-model-zzz. Available models: …` |
| `cursor-c-noprompt` | stdin `/dev/null`, no prompt | 1 | 8.0 s | 0 / 41 B | `Error: No prompt provided for print mode` |
| `cursor-d-healthy` | full formula, `auto` | 0 | 18.1 s | 506 / 0 | 14 s at 0 B stdout, TCP 3–8 |
| `opencode-a-noauto` | `run` without `--auto`, write outside the dir | **0** | 10.1 s | **0** / 465 B | stderr `! permission requested: external_directory (…); auto-rejecting` then `Error: The user rejected permission to use this specific tool call.` |
| `opencode-b-badmodel` | `opencode/no-such-model-zzz` | 1 | 4.0 s | 218 / 0 | stdout JSON `{"type":"error","error":{"name":"UnknownError","data":{"message":"Unexpected server error. …"}}}`. **No mention of the model** |
| `opencode-c-noprompt` | stdin `/dev/null` | 1 | 2.0 s | 0 / 60 B | `Error: You must provide a message or a command` |
| `grok-a-noapprove` | `--permission-mode default`, no `--always-approve` | **0** | 6.0 s | 886 / 0 | JSON `stopReason:"cancelled"`, `text` = intention only, no file, $0.038 |
| `grok-b-badmodel` | `-m no-such-model-zzz` | 1 | 2.0 s | 278 / 126 B | `{"type":"error","message":"Couldn't set model …: Invalid params: \"unknown model id\"…"}` on stdout and the same text on stderr |
| `grok-c-noprompt` | `--prompt-file /dev/stdin` with `/dev/null` | 1 | 2.0 s | 0 / 37 B | `Error: '/dev/stdin': prompt is empty` |
| `grok-d-healthy` | full formula | 0 | 30.2 s | 926 / 0 | **28 s at 0 B**, CPU +6 ticks, TCP 7 throughout, `stopReason:"end_turn"`, $0.054 |
| `pi-a-openstdin` | stdin = open pipe, never closed | **124** | 60.3 s | 0 / 0 | killed by `timeout`. 30 samples: `pi` in `S`, wchan `ep_poll`, syscall 281 (`epoll_pwait`), fd0 `pipe:[…]`, TCP **0**, CPU 25→31 |
| `pi-b-badmodel` | `router-env/no-such-model-zzz` | 1 | 2.0 s | 0 / 333 B | `Warning: Model "…" not found for provider "router-env". Using custom model id.` then `400: {"message":"Unable to determine provider for model …","type":"invalid_request_error"}` |
| `pi-c-noprompt` | stdin `/dev/null`, no prompt | **0** | 2.0 s | **0 / 0** | silent no-op |
| `pi-d-healthy` | prompt piped, then EOF | 0 | 10.1 s | 27 / 0 | 8 s at 0 B, TCP 1 |

### 3.2 Process-state signatures (from `samples.jsonl`)

- **Event-loop CLIs never show a read on fd 0.** pi (node) blocked on stdin showed `ep_poll`/`epoll_pwait`, not `anon_pipe_read`. grok (Rust) shows `futex_do_wait` while it waits on the model. opencode (bun) and cursor (node) show `ep_poll`. So wchan or syscall alone cannot spot a stdin wait for these four.
- **A plain reader does show it.** In the harness self-test, `cat` on an open pipe showed wchan `anon_pipe_read` with syscall `0` on fd `0x0`. That makes the generic check useful for shell wrappers and simple tools, not for the agent CLIs.
- **CPU ticks do not discriminate**: +6 ticks over 28 s for healthy grok, +6 over 56 s for stuck pi.
- **Established TCP sockets do discriminate**: >0 in every healthy or working sample, 0 in all 30 stuck pi samples.
- **The CLIs spawn helpers into the process group**: opencode and cursor start extra `MainThread` processes, and cursor starts `pnpm` (MCP/LSP servers). Group-kill on exit is required, or they leak.

---

## 4. The supervision contract

One contract, implemented once. **Recommendation: the Python dispatchers call `node cross-ai.mjs --prefer <cli> --model-<cli> <m> --mode exec|review --status-file <path>` instead of keeping their own runner.**
- GSD already requires node.
- `commands.py`'s builders have drifted from the verified formulas: grok `--sandbox workspace`, cursor `--sandbox enabled`, `sh -c` quoting (audit 04 #2).
- Two Python runners already duplicate each other (audit 04 #13).
- If a node dependency in the review path is unwanted, the fallback is to share only the signature table as one JSON file read by both. That is more code, and it will drift.

### 4.1 Spawn invariants (prevent instead of detect)

- argv spawn, never a shell.
- **stdin is the prompt file or `/dev/null`, always followed by EOF.** Never inherited, never a TTY. This removes the only real hang seen (`pi-a-openstdin`).
- Refuse an empty or whitespace prompt before spawning (`status=bad_prompt`). pi would otherwise exit 0 silently.
- **Preflight the model**: `model ∈ inventory[runtime].models`, otherwise `status=bad_model` with no spawn. This is the only reliable bad-model check for opencode (`UnknownError`).
- Always pass explicit non-interactive flags (report 10 formulas):
  - cursor `--trust --force --sandbox disabled --approve-mcps`;
  - opencode `--auto`;
  - grok `--always-approve --permission-mode bypassPermissions`;
  - pi `--no-approve`.
- Run in its own process group and kill the **group** on every exit path, success included, so MCP and LSP helpers do not leak.
- Scrub host signals: `CLAUDECODE CLAUDE_CODE_ENTRYPOINT CLAUDE_CODE_SSE_PORT OPENCODE CURSOR_AGENT PI_CODING_AGENT CODEX_THREAD_ID CODEX_SANDBOX GROK_AGENT GROK_SESSION_ID` **plus `AI_AGENT`**, which is new.
- Write stdout and stderr to files, not pipes. Pass the caller a path, never the transcript (audit 04 #4).

### 4.2 Liveness, heartbeat and the two timeouts

Sample every 5 s:
- `bytes = size(stdout) + size(stderr)`;
- `tcp` = established TCP sockets across the group (`/proc/<pid>/fd` socket inodes ∩ state `01` in `/proc/net/tcp{,6}`);
- `stdin_reader` = any group member with `/proc/<pid>/syscall` = `0 0x0…` or wchan in `{anon_pipe_read, pipe_read, n_tty_read}`.

Derived state:
- `running`: `bytes` grew since the last sample.
- `waiting-on-model`: no growth and `tcp > 0`. This is normal: 28 s for grok, 14 s for cursor, 8 s for pi.
- `stalled-no-io`: no growth and `tcp == 0` for `idle_s`.
- `blocked-on-stdin`: `stdin_reader` true, or `stalled-no-io` while fd 0 is a TTY or a still-open pipe. The second form should never happen under §4.1; it means a supervisor bug.

Timeouts:
- **Wall timeout**: the inner deadline, `outer − min(30, outer/5)` (cross-ai.mjs `innerTimeoutS`, unchanged).
- **Idle timeout** (new): kill the group when `stalled-no-io` lasts `idle_s` (default **90 s**).
  - It never fires while the child holds an open connection to a provider. That keeps `dispatch_with_polling`'s rule, "a false stalled verdict on a slow model is worse than the wait" (`K/dispatch.py` docstring), for the slow case, while still catching the dead case.
  - `[I]`: 90 s is 1.5× the 60 s the stuck pi run was observed. No healthy sample ever had `tcp == 0` after startup.
- **Heartbeat**: every 30 s, one stderr line (§4.5) carrying the state, so `waiting-on-model 240s` is visible instead of silent.

### 4.3 Error classes

Match only **stderr plus the CLI's structured error field**, never the model's answer or the stdout tail:
- cursor JSON `is_error` and `result`;
- opencode `type:"error"` event `.error`;
- grok `type:"error"` `.message` and `stopReason`;
- codex `type:"error"|"turn.failed"`;
- pi stderr (since `-p`).

Check the classes in table order. The first match wins.

| Class | Signature (where) | Evidence | Action |
|---|---|---|---|
| `permission_blocked` | cursor stderr `Workspace Trust Required`; opencode stderr `permission requested: .*auto-rejecting\|user rejected permission`; grok `stopReason == "cancelled"`; cursor "only proposed" without `--force` [D] | [L] a-runs | never retry; it is a formula bug. Fall back only if the tree is clean, and always report it loudly |
| `input_wait` | `blocked-on-stdin` / `stalled-no-io` with fd 0 open | [L] `pi-a-openstdin` | kill the group; never retry with the same stdin; supervisor bug |
| `bad_prompt` | preflight; cursor `No prompt provided`; opencode `must provide a message`; grok `prompt is empty`; pi rc 0 with empty output | [L] c-runs | stop (caller bug) |
| `bad_model` | preflight miss; cursor `Cannot use this model`; grok `unknown model id`; pi `not found for provider\|Unable to determine provider`; opencode `UnknownError` **only right after spawn with zero tool events** [I] | [L] b-runs | skip the candidate and fall back (nothing ran) |
| `auth` | `401`, `token_expired`, `invalid_refresh_token`, `not logged in`, `log ?in required`, `ActionRequiredError`, `unauthori[sz]ed`, `invalid api key` | [R10] codex 401; `quota.py:23` cursor | fall back; tell the user to log in; never wait |
| `billing` | `402`, `spending limit`, `insufficient_quota`, `billing`, `credit`, `requires an opencode API key`, `pre-dispatch filters`, `credential gate` | [memory 2026-09-14] xai 403; [R08] 16-HANDOFF | fall back; never wait (waiting does not refill money) |
| `quota` | `usage limit`, `rate.?limit`, `429`, `too many requests`, `try again (at\|in)` | [memory] codex "You've hit your usage limit… try again at" | fall back now; mark the CLI for a later wake (CronCreate); no same-CLI retry |
| `capacity` | `temporarily unavailable`, `overloaded`, `cooling down`, `is locked`, `50[234]`, `service unavailable`, `ECONNRESET`, `ETIMEDOUT`, `socket hang up`, `stream (closed\|disconnected)` | [R08] router errors | resume-retry the same CLI ≤ 2 times within the deadline (existing cross-ai.mjs `RESUME_MSG`), then fall back |
| `timeout` / `idle_stall` | wall deadline / §4.2 idle | [L] | kill the group; fall back if the tree is clean, else stop |
| `empty_result` | rc 0 but no parsed final text | [L] opencode-a, pi-c | stop if the tree is dirty, else fall back |
| `crash` | other non-zero rc, or a signal | — | fall back if the tree is clean, else stop; never retry |

### 4.4 Exit codes (runner → caller)

The per-CLI exit codes are undocumented for cursor, opencode and grok [R10], and the runner no longer passes them through.

- `0` ok
- `1` crash / empty_result
- `2` usage, bad_prompt, or no model configured
- `69` (EX_UNAVAILABLE) permission_blocked, bad_model, auth, billing: fatal for this CLI
- `75` (EX_TEMPFAIL) quota, or capacity after retries
- `124` wall or idle timeout (GNU `timeout` / GSD `run-with-timeout` parity)
- `127` no preferred CLI installed
- `128+n` the runner itself was signalled

The CLI's own rc is kept in the status record.

### 4.5 What the orchestrator is told

- **Always**: one final stderr line and, with `--status-file`, the same fields as JSON. GSD keeps stdout as SUMMARY only.

```
AIKIT-XAI status=permission_blocked cli=grok model=grok-4.7-build-fast exit=69 cli_rc=0 elapsed=6s out=886B tree=clean action=fallback detail="stopReason=cancelled"
```

- **Heartbeat**, every 30 s:

```
AIKIT-XAI heartbeat cli=grok t=60s state=waiting-on-model out=0B err=0B tcp=7
```

- **SKILL.md rule** (review, execute-gsd, execute-superpowers): after every external dispatch, print the `AIKIT-XAI status=` line verbatim to the user. If it is not `status=ok`, do not mark the task done and do not re-dispatch the same CLI. Follow `action=` (`fallback`, `retry-later` or `stop`).
- `tree=clean|dirty` comes from the git-state compare cross-ai.mjs already does. It is what makes `fallback` safe.

### 4.6 Retry vs fall back vs stop

- **Retry the same CLI** only for `capacity`: ≤ 2 times, resume rather than re-run, inside the deadline.
- **Fall back to the next candidate**: `bad_model`, `auth`, `billing`, `quota`, `permission_blocked`, `timeout`, `idle_stall`, `crash` and `empty_result`, **only when `tree=clean`**.
- **Stop and surface**: any class with `tree=dirty`, plus `bad_prompt`, `input_wait` and usage errors.
- **Schedule a later wake**: only when at least one candidate failed with `quota` (the existing `any_quota_recoverable` gate). Never for billing or auth.

### 4.7 Small fixes this contract implies in cross-ai.mjs

- grok parser: treat `stopReason` not in `{end_turn}` as an error. Today `/error|abort|refus/` misses `cancelled` [L].
- `classify`: drop `r.stdout.slice(-4000)` from the blob and pass the structured error instead. Today `assert resp.status == 503` in the model's text classifies as `transient` [L `classify-check.txt`].
- Add `bad_model`, `permission_blocked`, `billing`, `auth` and `quota` as separate kinds; today they are `fatal|transient|other`.
- Add the idle watchdog (TCP-aware), `--status-file`, the `AIKIT-XAI` lines, and `AI_AGENT`/`GROK_SESSION_ID` in `SCRUB_ENV`.
- Add the preflight model check, reusing `<cli> models` output (or the cached `runtimes.json`).
- Self-test additions: replay every `S/logs/*-{a,b,c}-*` stderr/stdout pair through the classifier and assert the class. The cases are already captured.

---

## 5. Mapping onto the v1.3 phases

- **Phase 16.1 "Hardening"** (synthesis item A8). Classifier fix only, shared code first:
  - `classify_dispatch_failure` and `_unavailability_reason` (`dispatch_injection.py:197-219,360-379`) and `probe_reviewer_quota` (`quota.py:244-247`) match stderr only, with the §4.3 phrase sets: quota vs billing vs auth split, and "quota" alone is no longer a signal.
  - Plus one test reproducing audit 04 #5's `quota.py; 2 tests failed` case.
  - Add the `GROK_AGENT` signal and `pi` in `KNOWN_CLIS`, and mark the cursor/pi signals live-verified (this report).
- **Phase 18 (XAI-01/02, cross-ai.mjs)**: everything in §4 (the runner contract, status line, exit codes, idle watchdog, preflight, §4.7 fixes). Make the Python dispatchers call the runner, and delete `dispatch_with_heartbeat`/`dispatch_with_polling`. XAI-02's text "built by `build_execute_command`" changes to "the runner" (as synthesis §3 already proposes).
- **New phase (proposed "18.1 One runtime model")**, or fold it into 18. It touches config schema and skills, so it needs its own `/skill-judge` pass (memory `feedback_skill_judge_in_code_review`):
  - the §2 rule;
  - delete `native_runtime`, migrate `cli: None` entries to `runtime`, rename `native_claude`, and use one runtime-id table;
  - rewrite review SKILL.md Step 1 and config Step 2.7 so they are host-agnostic.
- **Phases 20–22 (live validation per host)**: rerun `S/probe.py` cases a–d from each host, to confirm the env signals and native per-call model selection (`host_can_select`, now [U]).

## 6. Not verified

- The TTY behaviour (a CLI started on a real TTY) was not tested, because the contract forbids it.
- How each non-Claude host spawns a native subagent with a chosen model.
- codex, and claude as a subprocess target.
- Whether opencode's `UnknownError` always means a bad model (it could also be a real server fault; preflight avoids relying on it).
- The 90 s idle default: n=1 stuck run.

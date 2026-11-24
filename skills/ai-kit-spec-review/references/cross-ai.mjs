#!/usr/bin/env node
// ai-kit-cross-ai generator=ai-kit-gsd-curated-config template=13 sha256=UNSTAMPED
/*
 * cross-ai.mjs: the GSD `workflow.cross_ai_command` dispatcher (template v13).
 *
 * tree=clean means this CLI run left HEAD and the tree unchanged; dirty changed them;
 * unknown means the cwd is not inside a git work tree (the CLI ran without the check) or git
 * failed. With no CLI run it is clean.
 * Gitignored files count by stat signature (mode, size, mtime, ctime), except inside a
 * fully ignored directory (a cache, an indexer's dir): edits there are not seen.
 *
 * GSD runs:  echo "$TASK_PROMPT" | gsd-tools run-with-timeout $T -- node .planning/scripts/cross-ai.mjs [flags]
 *   - The prompt arrives on stdin. stdout becomes the plan's SUMMARY candidate, and stderr is GSD's error log.
 *   - The cwd is the project root, and the command string is word-split with NO shell, so flags must not contain spaces.
 *
 * Every run-mode exit prints exactly one last stderr line:
 *   AIKIT-XAI status=... cli=... model=... exit=... cli_rc=... elapsed=...s out=... tree=... action=...
 *
 * Standard library only. Edit the CONFIG block and the RUNTIMES argv lines freely; the
 * generator will then refuse to overwrite this file silently (sha256 header above).
 *
 * Flags:
 *   --runtime <id>                           the one CLI this call runs; an id with no formula is refused unless --argv-file declares its command
 *   --prefer <list>                          alias: only the first entry runs (notice
 *                                            names the rest)
 *   --model <id>                             model for the selected runtime (wins over
 *                                            --model-<cli>)
 *   --model-<cli> <id>                       model per CLI, e.g. --model-cursor auto
 *   --route-<cli> router|unknown             confirmed route of that CLI (wins over CONFIG)
 *   --classify-only <path>                   classify a JSON case file and exit (no spawn,
 *                                            no write, stdin ignored; path relative to cwd)
 *   --role review|execute                    documented mode; --mode is an alias; disagreement is a usage error
 *   --mode exec|review                       exec = full permissions (default); review = read-only
 *   --effort <level>                         generic effort, shape ^[a-z][a-z0-9_-]{0,15}$
 *   --context <label>                        context label
 *   --escalate-runtime                       carried, never acted on
 *   --escalate-model                         carried, never acted on
 *   --session-id <id>                        session id
 *   --host auto|none                         hosting choice
 *   --idle-timeout <seconds|default>         idle watchdog: 0 to 86400 s (0 off) or default (900); beats CONFIG.idleTimeoutS
 *   --skill-path <dir>                       repeatable skill path
 *   --skill-name <name>                      repeatable skill name
 *   --mcp-config <file>                      MCP configuration path
 *   --argv-file <path>                       a JSON array: the command and its arguments for a runtime id with no formula
 *                                            (the file must lie inside the cwd tree; the command resolves through PATH;
 *                                            {model}, {effort}, {session} are the only placeholders;
 *                                            the prompt goes on stdin; a setting with no placeholder is reported no_slot)
 *   --describe                               describe runner capabilities
 *   --sweep                                  remove dead run directories, secrets and tabs and exit (no spawn, no lock)
 *   --tools-profile exec|review|none         named tool set from the runtime's table row
 *                                            (review accepts review or none)
 *   --timeout <s>                            inner deadline (lowers default; never above derived inner)
 *   --outer-timeout <s>                      outer deadline (replaces the GSD lookup and the
 *                                            CONFIG cap)
 *   --print-argv                             print the resolved command per CLI and exit (no model call)
 *   --no-preamble                            send the prompt unchanged
 *   --prepend-file <path>                    put this file before the prompt
 *                                            (path relative to the cwd)
 *   --codex-sandbox workspace-write          codex exec runs in Codex's workspace-write
 *                                            sandbox mode (by default the cwd plus /tmp
 *                                            and $TMPDIR; the owner's Codex config can
 *                                            add or exclude writable roots)
 *   --child-pgid-file <path>                 append spawn <pid> / exit <pid>
 *                                            per detached child, for a
 *                                            supervising caller's cleanup
 *   --codex-effort <level>                   alias of --effort (both given with different values: usage error)
 *   --codex-service-tier <id>                codex -c service_tier=
 *   --cursor-mode ask|plan                   review mode only (replaces cursor --mode)
 *   --self-test                              hermetic black-box checks (no real CLIs); its ceilings scale
 *                                            with load per CPU up to 4x, AIKIT_XAI_SELFTEST_LOAD overrides the reading
 *   --self-test-list                         print each self-test case as name<TAB>kind (logic or runtime);
 *                                            AIKIT_XAI_SELFTEST_CASES=a,b runs only the named cases
 *
 * CONFIG.effort.<runtime> is the baked default effort beneath the call's --effort, for every
 * runtime; --print-argv prints how each runtime takes it (cross-ai: setting effort=...).
 *
 * Live outer timeout reads workflow.cross_ai_timeout the way gsd-tools config-get does:
 * .planning[/$GSD_PROJECT][/workstreams/$GSD_WORKSTREAM]/config.json, then the root config
 * under GSD_WORKSTREAM, else 300.
 * Retry config reads [runner.retry] (and the active GSD scope's [runner.retry.scopes."<scope>"])
 * from the project .aikit/config.toml, then the user ${XDG_CONFIG_HOME:-~/.config}/ai-kit/config.toml,
 * then CONFIG.retry, per key. A legacy workflow.cross_ai_retry block in the GSD config and the user
 * cross-ai.json are migrated into those files once (migrateRetrySources). The error catalog is PATTERNS (generated from cross-ai-errors.json) plus the owner
 * overlay ${XDG_CONFIG_HOME:-~/.config}/ai-kit/cross-ai-errors.json.
 * Idle watchdog (opt-in, --idle-timeout or CONFIG.idleTimeoutS): a child that printed no byte for that long is ended like a timed-out attempt.
 */
import { spawn, spawnSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import vm from 'node:vm';
import os from 'node:os';
import path from 'node:path';
import { StringDecoder } from 'node:string_decoder';
import { fileURLToPath } from 'node:url';

// The runner's own file: the self-test harness copies it and is loaded from beside it (38-08).
const RUNNER_FILE = fileURLToPath(import.meta.url);

// <config>
const CONFIG = {
  "attemptTimeoutS": 0,
  "capS": 14400,
  "effort": {},
  "extraArgs": {},
  "heartbeatS": 30,
  "idleTimeoutS": 0,
  "models": {},
  "outerTimeoutS": 1800,
  "retry": {
    "base_s": 1,
    "factor": 1.5,
    "hard_every_s": 600,
    "hard_waits_s": [
      60,
      300
    ],
    "max_retries": 5,
    "session_resets": 1
  },
  "routerBacked": {},
  "runtime": "pi",
  "scrubEnv": [
    "AI_AGENT",
    "CLAUDECODE",
    "CLAUDE_CODE_ENTRYPOINT",
    "CLAUDE_CODE_SSE_PORT",
    "CODEX_SANDBOX",
    "CODEX_THREAD_ID",
    "CODEX_VERSION",
    "CURSOR_AGENT",
    "OPENCODE",
    "PI_CODING_AGENT"
  ]
};
// </config>
// gsd-core default when workflow.cross_ai_timeout is absent (execute-phase/detail/elaboration.md:74)
const GSD_DEFAULT_TIMEOUT_S = 300;
const TIMEOUT_MARGIN_S = 30;

const EXEC_PREAMBLE = `
<executor_rules>
You run unattended. No human will answer questions or approve anything: never stop to ask, decide and continue.
Do the work for real: edit files, run the plan's verify commands, and make the git commits the plan asks for.
Never run git push and never use --no-verify.
When done, reply with ONLY a SUMMARY.md-style markdown report: a "# " title line, a one-line outcome,
"## Accomplishments" bullets, "## Files Created/Modified" bullets, and the commit hashes. No prose before the title.
</executor_rules>
`;
const REVIEW_PREAMBLE = `
<reviewer_rules>
Read-only review. Do not modify files, do not commit, do not run commands that change state. Reply with the review only.
</reviewer_rules>
`;
const RESUME_MSG = 'You were interrupted by a provider error. Continue the same task from where you ' +
  'stopped: first inspect git status, git diff and git log, do not redo finished steps, finish the remaining ' +
  '(verify commands and commits included), then reply with the final report as originally asked.';

// Mirrors model_heuristics._ROUTER_NAME_HINTS; a Python test pins this line.
// A hint match is advisory only (route=router-inferred): it never enables the router-quota
// cycles, which need the flag or a confirmed CONFIG.routerBacked[cli] boolean.
const ROUTER_HINTS = ["router", "-env", "local-llm"];

// Pinned table order (vendor codes, then quota text, then auth, then capacity, then
// opencode type hints, then bare codes): pure-classify-order-mutation proves a reversal
// changes the class of a message that carries both billing and quota wording.
// <patterns>
const PATTERNS = [
  {
    "id": "router-model-cooldown",
    "tier": 0,
    "cli": "*",
    "route": "router",
    "provider": "*",
    "input": "any",
    "match": "model_cooldown",
    "class": "quota",
    "terminal": false,
    "label": "unverified",
    "evidence": "38.1 R4 D-22 (074cbcc): router client body 429 code model_cooldown with Retry-After and reset_seconds, read from the router source 2026-11-16; no body captured"
  },
  {
    "id": "router-all-targets-cooling-down",
    "tier": 0,
    "cli": "*",
    "route": "router",
    "provider": "*",
    "input": "any",
    "match": "all_targets_cooling_down",
    "class": "quota",
    "terminal": false,
    "label": "unverified",
    "evidence": "38.1 R4 D-22 (074cbcc): router client body 503 all_targets_cooling_down with Retry-After, read from the router source 2026-11-16; no body captured"
  },
  {
    "id": "omniroute-all-targets-skipped",
    "tier": 0,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "ALL_TARGETS_SKIPPED|all targets were skipped by pre-dispatch filters",
    "class": "quota",
    "terminal": false,
    "label": "verified",
    "evidence": "25.1-EVIDENCE.md captured bodies 2026-10-24 and 2026-10-25; supersedes Phase 25 text-pre-dispatch"
  },
  {
    "id": "omniroute-all-targets-cooling-down",
    "tier": 0,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "all_targets_cooling_down",
    "class": "transient",
    "terminal": false,
    "label": "unverified",
    "evidence": "CHANGELOG 0a1265ea8"
  },
  {
    "id": "omniroute-circuit-open",
    "tier": 0,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "circuit_open",
    "class": "transient",
    "terminal": false,
    "label": "unverified",
    "evidence": "CHANGELOG 0a1265ea8"
  },
  {
    "id": "omniroute-model-cooldown",
    "tier": 0,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "model_cooldown",
    "class": "transient",
    "terminal": false,
    "label": "verified",
    "evidence": "CHANGELOG 0a1265ea8; body seen in 45 cases from an older router image, logs read 2026-11-02 (v1.3-OWNER-FOLLOWUP.md section 1 and Evidence sources)"
  },
  {
    "id": "omniroute-endpoint-unavailable",
    "tier": 0,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "endpoint is unavailable",
    "class": "transient",
    "terminal": false,
    "label": "unverified",
    "evidence": "CHANGELOG 0a1265ea8"
  },
  {
    "id": "omniroute-model-unavailable",
    "tier": 0,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "\\bmodel \\S+ is unavailable\\b",
    "class": "transient",
    "terminal": false,
    "label": "verified",
    "evidence": "2026-10-24 capture"
  },
  {
    "id": "omniroute-no-executable-targets",
    "tier": 0,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "no_executable_targets|combo has no executable targets",
    "class": "bad_model",
    "terminal": false,
    "label": "verified",
    "evidence": "2026-10-25 capture"
  },
  {
    "id": "omniroute-model-not-in-catalog",
    "tier": 0,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "model_not_in_catalog",
    "class": "bad_model",
    "terminal": false,
    "label": "unverified",
    "evidence": "CHANGELOG 0a1265ea8"
  },
  {
    "id": "provider-not-configured",
    "tier": 0,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "\\bprovider_not_configured\\b",
    "class": "bad_model",
    "terminal": false,
    "label": "unverified",
    "evidence": "code name recorded in real runs (38.1 SPEC R2); body not captured"
  },
  {
    "id": "vendor-usage-limit-reached",
    "tier": 1,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "usage_limit_reached",
    "class": "quota",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.1 probe"
  },
  {
    "id": "vendor-insufficient-quota",
    "tier": 1,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "insufficient_quota",
    "class": "billing",
    "routerClass": "quota",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.1 probe"
  },
  {
    "id": "vendor-zhipu-1310",
    "tier": 1,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "\"code\"\\s*:\\s*\"1310\"",
    "class": "quota",
    "terminal": true,
    "label": "verified",
    "evidence": "the Zhipu GLM capture; weekly limit wording found in past runs (v1.3-OWNER-FOLLOWUP.md section 1)"
  },
  {
    "id": "vendor-data-inspection-failed",
    "tier": 1,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "\\bdata_inspection_failed\\b",
    "class": "bad_request",
    "terminal": true,
    "label": "unverified",
    "evidence": "code name recorded in real runs (38.1 SPEC Live facts 2026-11-16); body not captured"
  },
  {
    "id": "vendor-context-length-exceeded",
    "tier": 1,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "\\bcontext_length_exceeded\\b",
    "class": "bad_request",
    "terminal": true,
    "label": "unverified",
    "evidence": "code name recorded in real runs (38.1 SPEC Live facts 2026-11-16); body not captured"
  },
  {
    "id": "vendor-code-1311",
    "tier": 1,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "\"code\"\\s*:\\s*\"1311\"",
    "class": "billing",
    "routerClass": "quota",
    "terminal": true,
    "label": "unverified",
    "evidence": "vendor plan-not-open code recorded in real runs (38.1 SPEC Live facts 2026-11-16); body not captured"
  },
  {
    "id": "copilot-model-not-available",
    "tier": 1,
    "cli": "copilot",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "Model \"[^\"]+\" is not available",
    "class": "bad_model",
    "terminal": true,
    "label": "verified",
    "evidence": "captured headless 2026-11-16, copilot 1.0.112; fixture tests/fixtures/cross_ai_errors/copilot-bad-model.json"
  },
  {
    "id": "pi-model-not-found",
    "tier": 1,
    "cli": "pi",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "Model \"[^\"]+\" not found",
    "class": "bad_model",
    "terminal": true,
    "label": "verified",
    "evidence": "captured headless 2026-11-16, pi 1.5.2; fixture tests/fixtures/cross_ai_errors/pi-bad-model.json"
  },
  {
    "id": "opencode-model-unavailable",
    "tier": 1,
    "cli": "opencode",
    "route": "*",
    "provider": "*",
    "input": "event",
    "match": "^opencode-type:provider\\.no-route$",
    "class": "bad_model",
    "terminal": true,
    "label": "verified",
    "evidence": "captured headless 2026-11-16, opencode 2.3.0 provider.no-route event (message Model unavailable); fixture tests/fixtures/cross_ai_errors/opencode-bad-model.json"
  },
  {
    "id": "claude-selected-model",
    "tier": 1,
    "cli": "claude",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "issue with the selected model",
    "class": "bad_model",
    "terminal": true,
    "label": "verified",
    "evidence": "captured headless 2026-11-16, claude 2.1.325; fixture tests/fixtures/cross_ai_errors/claude-bad-model.json"
  },
  {
    "id": "codex-model-not-supported",
    "tier": 1,
    "cli": "codex",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "model is not supported when using",
    "class": "bad_model",
    "terminal": true,
    "label": "verified",
    "evidence": "captured headless 2026-11-16, codex 0.169.0; fixture tests/fixtures/cross_ai_errors/codex-bad-model.json"
  },
  {
    "id": "opencode-free-tier-error",
    "tier": 1,
    "cli": "opencode",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "FreeTierError",
    "class": "bad_request",
    "terminal": true,
    "label": "unverified",
    "evidence": "client rule reported in a pinned opencode maintainer post and issues; no body captured on this machine (38.1 D-27)"
  },
  {
    "id": "opencode-missing-session-id",
    "tier": 1,
    "cli": "opencode",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "MissingSessionID",
    "class": "bad_request",
    "terminal": true,
    "label": "unverified",
    "evidence": "client rule reported in a pinned opencode maintainer post and issues; no body captured on this machine (38.1 D-27)"
  },
  {
    "id": "opencode-free-tier-version-gate",
    "tier": 1,
    "cli": "opencode",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "or newer is required to use the free tier",
    "class": "bad_request",
    "terminal": true,
    "label": "unverified",
    "evidence": "client rule reported in a pinned opencode maintainer post and issues; no body captured on this machine (38.1 D-27)"
  },
  {
    "id": "text-billing",
    "tier": 2,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "(?<![/.])\\bbilling\\b(?![/.]\\w)",
    "class": "billing",
    "routerClass": "quota",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.1 probe"
  },
  {
    "id": "vendor-monthly-limit",
    "tier": 2,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "MonthlyLimitError",
    "class": "billing",
    "routerClass": "quota",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.2 CONTEXT; seen through direct calls in past runs (v1.3-OWNER-FOLLOWUP.md section 1, router limit texts)"
  },
  {
    "id": "text-spending-limit",
    "tier": 2,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "spending[ -]limit",
    "class": "billing",
    "routerClass": "quota",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.2 recorded hyphen"
  },
  {
    "id": "text-payment-required",
    "tier": 2,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "payment required",
    "class": "billing",
    "routerClass": "quota",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.1 probe format"
  },
  {
    "id": "text-free-tier",
    "tier": 2,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "free ?tier",
    "class": "billing",
    "routerClass": "quota",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.3 recorded"
  },
  {
    "id": "text-insufficient-funds",
    "tier": 2,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "insufficient (?:account )?funds",
    "class": "billing",
    "routerClass": "quota",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.2 Go wording; seen through direct calls in past runs (v1.3-OWNER-FOLLOWUP.md section 1, router limit texts)"
  },
  {
    "id": "text-run-out-credits",
    "tier": 2,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "run out of credits",
    "class": "billing",
    "routerClass": "quota",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.2 recorded"
  },
  {
    "id": "text-model-access-disabled",
    "tier": 2,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "model access is disabled",
    "class": "billing",
    "routerClass": "quota",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.2 Zen wording; seen through direct calls in past runs (v1.3-OWNER-FOLLOWUP.md section 1, router limit texts)"
  },
  {
    "id": "text-policy-budget-exceeded",
    "tier": 2,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "policy budget exceeded",
    "class": "billing",
    "routerClass": "quota",
    "terminal": true,
    "label": "unverified",
    "evidence": "name recorded in the 21.1 research and the 2026-10-11 todo; body not re-observed"
  },
  {
    "id": "text-account-budget-exceeded",
    "tier": 2,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "account budget exceeded",
    "class": "billing",
    "routerClass": "quota",
    "terminal": true,
    "label": "unverified",
    "evidence": "name recorded in the 21.1 research and the 2026-10-11 todo; body not re-observed"
  },
  {
    "id": "text-named-models",
    "tier": 2,
    "cli": "cursor",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "named models unavailable",
    "class": "billing",
    "routerClass": "quota",
    "terminal": true,
    "label": "unverified",
    "evidence": "25-RESEARCH 2.4"
  },
  {
    "id": "text-free-plan-auto",
    "tier": 2,
    "cli": "cursor",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "free plans can only use auto",
    "class": "billing",
    "routerClass": "quota",
    "terminal": true,
    "label": "unverified",
    "evidence": "25-RESEARCH 2.4"
  },
  {
    "id": "vendor-free-usage",
    "tier": 3,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "FreeUsageLimitError",
    "class": "quota",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.2 probe",
    "pool": "free"
  },
  {
    "id": "opencode-free-limit",
    "tier": 3,
    "cli": "opencode",
    "route": "*",
    "provider": "*",
    "input": "event",
    "match": "^opencode-type:provider\\.free-limit$",
    "class": "quota",
    "terminal": true,
    "label": "unverified",
    "evidence": "typed event shape from the opencode pull request text and a live probe on 2026-11-16 (429 with retryAfterMs); full body not stored (38.1 D-24)",
    "pool": "free"
  },
  {
    "id": "vendor-go-usage",
    "tier": 3,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "GoUsageLimitError",
    "class": "quota",
    "terminal": true,
    "label": "unverified",
    "evidence": "25-RESEARCH 2.3 cited list"
  },
  {
    "id": "cursor-action-usage-limit",
    "tier": 3,
    "cli": "cursor",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "actionrequirederror.*usage limit",
    "class": "quota",
    "terminal": true,
    "label": "unverified",
    "evidence": "25-RESEARCH 2.4 channel unverified"
  },
  {
    "id": "pi-chatgpt-usage-limit",
    "tier": 3,
    "cli": "pi",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "chatgpt usage limit",
    "class": "quota",
    "terminal": true,
    "label": "unverified",
    "evidence": "25-RESEARCH 2.3 cited bundle"
  },
  {
    "id": "claude-hit-your-limit",
    "tier": 3,
    "cli": "claude",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "hit your limit",
    "class": "quota",
    "terminal": true,
    "label": "unverified",
    "evidence": "25-RESEARCH 2.5 cited binary"
  },
  {
    "id": "claude-hit-your-limit-stdout",
    "tier": 3,
    "cli": "claude",
    "route": "*",
    "provider": "*",
    "input": "stdout",
    "match": "hit your (?:weekly )?limit",
    "class": "quota",
    "terminal": true,
    "label": "unverified",
    "evidence": "38.1 R3 D-07: claude limit sentence as plain stdout (run live, crash before this row); weekly form as the harness case evidence-claude-weekly"
  },
  {
    "id": "claude-selected-model-stdout",
    "tier": 3,
    "cli": "claude",
    "route": "*",
    "provider": "*",
    "input": "stdout",
    "match": "issue with the selected model",
    "class": "bad_model",
    "terminal": true,
    "label": "unverified",
    "evidence": "38.1 R3 D-04: claude model-missing sentence as plain stdout; the 2026-11-16 capture printed it inside the JSON result, the plain form is not captured"
  },
  {
    "id": "text-usage-limit",
    "tier": 3,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "usage limit",
    "class": "quota",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.1 probe"
  },
  {
    "id": "text-hit-your-limit",
    "tier": 3,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "hit your (?:\\w+ )?limit",
    "class": "quota",
    "terminal": true,
    "label": "unverified",
    "evidence": "25-RESEARCH 2.4 cursor wording"
  },
  {
    "id": "text-quota-exceeded",
    "tier": 3,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "quota exceeded",
    "class": "quota",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.1 probe"
  },
  {
    "id": "text-rate-limit",
    "tier": 3,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "rate.?limit",
    "class": "quota",
    "terminal": false,
    "label": "verified",
    "evidence": "25-RESEARCH 2.2 probe; not terminal (25-04)"
  },
  {
    "id": "text-too-many-requests",
    "tier": 3,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "too many requests",
    "class": "quota",
    "terminal": false,
    "label": "verified",
    "evidence": "25-RESEARCH 2.3 pi retries; not terminal (25-04)"
  },
  {
    "id": "text-requires-opencode-key",
    "tier": 4,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "requires an opencode api key",
    "class": "auth",
    "routerClass": "quota",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.2 probe"
  },
  {
    "id": "text-credential-gate",
    "tier": 4,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "credential gate",
    "class": "auth",
    "routerClass": "quota",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.2 recorded"
  },
  {
    "id": "text-unauthorized",
    "tier": 4,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "unauthori[sz]ed",
    "class": "auth",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.1 probe"
  },
  {
    "id": "text-token-expired",
    "tier": 4,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "token_expired",
    "class": "auth",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.1 recorded"
  },
  {
    "id": "text-invalid-refresh",
    "tier": 4,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "invalid_refresh_token",
    "class": "auth",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.1 recorded"
  },
  {
    "id": "text-refresh-reused",
    "tier": 4,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "refresh.token.(?:was already used|reused)",
    "class": "auth",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.1 recorded"
  },
  {
    "id": "text-could-not-refresh",
    "tier": 4,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "could not be refreshed",
    "class": "auth",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.1 recorded"
  },
  {
    "id": "text-not-logged-in",
    "tier": 4,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "not logged in",
    "class": "auth",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.1 recorded"
  },
  {
    "id": "text-login-required",
    "tier": 4,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "log ?in required",
    "class": "auth",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.1 recorded"
  },
  {
    "id": "text-please-sign-in",
    "tier": 4,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "please (?:log|sign) ?in",
    "class": "auth",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.1 recorded"
  },
  {
    "id": "text-invalid-api-key",
    "tier": 4,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "invalid api key",
    "class": "auth",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.4 live"
  },
  {
    "id": "text-incorrect-api-key",
    "tier": 4,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "incorrect api key",
    "class": "auth",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.2 probe"
  },
  {
    "id": "text-api-key-invalid",
    "tier": 4,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "api key is invalid",
    "class": "auth",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.4 live"
  },
  {
    "id": "text-permission-denied",
    "tier": 4,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "permission denied",
    "class": "permission_blocked",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.2 recorded"
  },
  {
    "id": "text-requires-approval",
    "tier": 4,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "requires approval",
    "class": "permission_blocked",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.2 recorded"
  },
  {
    "id": "text-approval-required",
    "tier": 4,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "approval required",
    "class": "permission_blocked",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.2 recorded"
  },
  {
    "id": "text-workspace-trust",
    "tier": 4,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "workspace trust required",
    "class": "permission_blocked",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.2 recorded"
  },
  {
    "id": "text-model-not-found",
    "tier": 4,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "model not found",
    "class": "bad_model",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.1 probe item"
  },
  {
    "id": "text-unknown-model",
    "tier": 4,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "unknown model",
    "class": "bad_model",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.1 probe item"
  },
  {
    "id": "text-invalid-model",
    "tier": 4,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "invalid model",
    "class": "bad_model",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.1 probe item"
  },
  {
    "id": "text-cannot-use-model",
    "tier": 4,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "cannot use this model",
    "class": "bad_model",
    "terminal": true,
    "label": "verified",
    "evidence": "25-RESEARCH 2.4 live"
  },
  {
    "id": "claude-overloaded",
    "tier": 5,
    "cli": "claude",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "overloaded",
    "class": "transient",
    "terminal": false,
    "label": "unverified",
    "evidence": "25-RESEARCH 2.5 CONTEXT"
  },
  {
    "id": "text-overloaded",
    "tier": 5,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "overloaded",
    "class": "transient",
    "terminal": false,
    "label": "verified",
    "evidence": "25-RESEARCH 2.2 probe"
  },
  {
    "id": "text-at-capacity",
    "tier": 5,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "at capacity",
    "class": "transient",
    "terminal": false,
    "label": "verified",
    "evidence": "25-RESEARCH 2.2 recorded"
  },
  {
    "id": "text-service-unavailable",
    "tier": 5,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "service (?:temporarily )?unavailable",
    "class": "transient",
    "terminal": false,
    "label": "verified",
    "evidence": "25-RESEARCH 2.2 recorded"
  },
  {
    "id": "text-resource-pressure",
    "tier": 5,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "resource pressure",
    "class": "transient",
    "terminal": false,
    "label": "verified",
    "evidence": "25-RESEARCH 2.2 recorded"
  },
  {
    "id": "text-admission-capacity",
    "tier": 5,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "admission capacity",
    "class": "transient",
    "terminal": false,
    "label": "verified",
    "evidence": "25-RESEARCH 2.2 recorded"
  },
  {
    "id": "text-event-400",
    "tier": 5,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "\\[400\\]: event: error",
    "class": "transient",
    "terminal": false,
    "label": "verified",
    "evidence": "25-CONTEXT transient upstream 400"
  },
  {
    "id": "text-temporarily-unavailable",
    "tier": 5,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "temporarily unavailable",
    "class": "transient",
    "terminal": false,
    "label": "verified",
    "evidence": "25-RESEARCH 2.2 recorded"
  },
  {
    "id": "router-accounts-cooling-down",
    "tier": 5,
    "cli": "*",
    "route": "router",
    "provider": "*",
    "input": "any",
    "match": "active accounts cooling down for model",
    "class": "quota",
    "terminal": false,
    "label": "unverified",
    "evidence": "38.1 R4 D-09: router log line (warning, tag AUTH), 34 episodes in the router's own log; never seen by the runner"
  },
  {
    "id": "router-all-models-failed",
    "tier": 5,
    "cli": "*",
    "route": "router",
    "provider": "*",
    "input": "any",
    "match": "All models failed \\|.*\\(reset after ",
    "class": "quota",
    "terminal": false,
    "label": "unverified",
    "evidence": "38.1 R4 D-09: router log wording with its reset text (the heading alone also prints for non-cooldown failures); never seen by the runner"
  },
  {
    "id": "router-persisted-cooldown",
    "tier": 5,
    "cli": "*",
    "route": "router",
    "provider": "*",
    "input": "any",
    "match": "has persisted cooldown until",
    "class": "quota",
    "terminal": false,
    "label": "unverified",
    "evidence": "38.1 R4 D-09: router log wording; never seen by the runner"
  },
  {
    "id": "text-cooling-down",
    "tier": 5,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "cooling down",
    "class": "transient",
    "terminal": false,
    "label": "verified",
    "evidence": "prior table"
  },
  {
    "id": "text-connection-capacity",
    "tier": 5,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "connection capacity reached",
    "class": "transient",
    "terminal": false,
    "label": "unverified",
    "evidence": "text recorded in real runs without a status code (38.1 SPEC Live facts 2026-11-16); body not captured"
  },
  {
    "id": "text-is-locked",
    "tier": 5,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "is locked",
    "class": "transient",
    "terminal": false,
    "label": "verified",
    "evidence": "prior table"
  },
  {
    "id": "text-econnreset",
    "tier": 5,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "ECONNRESET",
    "class": "transient",
    "terminal": false,
    "label": "verified",
    "evidence": "prior table"
  },
  {
    "id": "text-etimedout",
    "tier": 5,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "ETIMEDOUT",
    "class": "transient",
    "terminal": false,
    "label": "verified",
    "evidence": "prior table"
  },
  {
    "id": "text-socket-hangup",
    "tier": 5,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "socket hang up",
    "class": "transient",
    "terminal": false,
    "label": "verified",
    "evidence": "prior table"
  },
  {
    "id": "text-stream-cut",
    "tier": 5,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "stream (?:closed|disconnected)",
    "class": "transient",
    "terminal": false,
    "label": "verified",
    "evidence": "25-RESEARCH 2.1 recovered stream"
  },
  {
    "id": "opencode-type-quota",
    "tier": 5,
    "cli": "opencode",
    "route": "*",
    "provider": "*",
    "input": "event",
    "match": "opencode-type:provider\\.(?:quota|rate-limit)",
    "class": "quota",
    "terminal": false,
    "label": "verified",
    "evidence": "25-RESEARCH 2.2 probe"
  },
  {
    "id": "opencode-type-auth",
    "tier": 5,
    "cli": "opencode",
    "route": "*",
    "provider": "*",
    "input": "event",
    "match": "opencode-type:provider\\.auth",
    "class": "auth",
    "terminal": false,
    "label": "verified",
    "evidence": "25-RESEARCH 2.2 probe, weak hint"
  },
  {
    "id": "code-402",
    "tier": 6,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "\\b402\\b",
    "class": "billing",
    "routerClass": "quota",
    "terminal": false,
    "label": "verified",
    "evidence": "25-RESEARCH 2.1 probe; not terminal (25-04)"
  },
  {
    "id": "code-401-403",
    "tier": 6,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "(?<![:.\\d])\\b40[13]\\b(?!:\\d)",
    "class": "auth",
    "terminal": false,
    "label": "verified",
    "evidence": "25-RESEARCH 2.2 probe; not terminal (25-04)"
  },
  {
    "id": "router-usage-balance-exhausted",
    "tier": 6,
    "cli": "*",
    "route": "router",
    "provider": "*",
    "input": "any",
    "match": "usage balance exhausted",
    "class": "quota",
    "terminal": false,
    "label": "unverified",
    "evidence": "38.1 R4 D-09: router wording; a 402 body carrying it classifies by code-402 and a 401/403 by code-401-403 first, this row covers the form without a status code"
  },
  {
    "id": "code-429",
    "tier": 6,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "\\b429\\b",
    "class": "quota",
    "terminal": false,
    "label": "verified",
    "evidence": "25-CONTEXT kimi 429; not terminal (25-04)"
  },
  {
    "id": "code-5xx",
    "tier": 6,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "(?<![:.\\d])\\b50[0234]\\b(?!:\\d)",
    "class": "transient",
    "terminal": false,
    "label": "verified",
    "evidence": "25-RESEARCH 2.2 probe; not terminal (25-04)"
  },
  {
    "id": "code-529",
    "tier": 6,
    "cli": "*",
    "route": "*",
    "provider": "*",
    "input": "any",
    "match": "\\b529\\b",
    "class": "transient",
    "terminal": false,
    "label": "verified",
    "evidence": "25-RESEARCH 2.2 probe; not terminal (25-04)"
  }
];
// </patterns>

// Shipped rows, then the per-call table (overlay rows join it in main). Tier order is the
// match order for both live and post-hoc classification.
let TABLE = PATTERNS;
// 38-08: the self-test harness is another module and cannot assign an imported binding.
function setTable(value) { TABLE = value; }

const OVERLAY_MATCH_MS = 50;
const OVERLAY_CALL_BUDGET_MS = 200;
const ROW_CLASSES = ['quota', 'billing', 'auth', 'permission_blocked', 'bad_model', 'bad_request', 'transient'];
const ROW_ID_RE = /^[a-z0-9][a-z0-9-]{1,63}$/;
const PROVIDER_RE = /^[a-z0-9][a-z0-9._-]{0,63}$/;
let OVERLAY_IDS = new Set();
function setOverlayIds(value) { OVERLAY_IDS = value; }
let overlayDisabled = false;
let overlaySpentMs = 0;
let overlayScript = null;

function mergeCatalog(shipped, overlay) {
  overlayDisabled = false;
  overlaySpentMs = 0;
  overlayScript = null;
  return [...overlay, ...shipped]
    .map((row, index) => ({ row, index }))
    .sort((a, b) => (a.row.tier - b.row.tier) || (a.index - b.index))
    .map((item) => item.row);
}

function validateRow(row, known) {
  if (!row || typeof row !== 'object' || Array.isArray(row)) return 'row is not an object';
  for (const key of ['id', 'tier', 'cli', 'route', 'provider', 'input', 'match', 'class',
    'terminal', 'label', 'evidence']) {
    if (!Object.hasOwn(row, key)) return `missing ${key}`;
  }
  if (typeof row.id !== 'string' || !ROW_ID_RE.test(row.id)) return 'id is not a row id';
  if (!Number.isInteger(row.tier) || row.tier < 0 || row.tier > 6) return 'tier is not 0..6';
  if (row.cli !== '*' && !Object.hasOwn(known, row.cli)) return 'cli is not a known runtime';
  if (!['*', 'router', 'unknown'].includes(row.route)) return 'route is not *, router or unknown';
  if (row.provider !== '*' && (typeof row.provider !== 'string' || !PROVIDER_RE.test(row.provider))) {
    return 'provider is not * or a lowercase prefix';
  }
  if (!['stderr', 'event', 'stdout', 'any'].includes(row.input)) return 'input is not stderr, event, stdout or any';
  if (typeof row.match !== 'string' || row.match.length > 200) {
    return 'match is not a string of at most 200 characters';
  }
  try { new RegExp(row.match, 'i'); } catch { return 'match is not a regex'; }
  if (!ROW_CLASSES.includes(row.class)) return 'class is not a known class';
  if (row.routerClass !== undefined && row.routerClass !== 'quota') return 'routerClass is not quota';
  if (row.pool !== undefined && (typeof row.pool !== 'string' || !ROW_POOL_RE.test(row.pool))) return 'pool is not a pool tier';
  if (typeof row.terminal !== 'boolean') return 'terminal is not a boolean';
  if (row.label !== 'verified' && row.label !== 'unverified') return 'label is not verified or unverified';
  if (typeof row.evidence !== 'string' || !row.evidence) return 'evidence is empty';
  return null;
}

const STATUS_TABLE = {
  ok: { exit: 0 },
  no_change: { exit: 1 },
  empty_answer: { exit: 1 },
  crash: { exit: 1 },
  contract_violation: { exit: 1 },
  partial: { exit: 1 }, // SPEC R5: a blocking execute finding (D-15)
  usage: { exit: 2 },
  no_model: { exit: 2 },
  empty_stdin: { exit: 2 },
  permission_blocked: { exit: 69 },
  bad_model: { exit: 69 },
  bad_request: { exit: 69 }, // 38.1 D-01: the provider refused the request itself; retrying the same input never helps.
  auth: { exit: 69 },
  billing: { exit: 69 },
  quota: { exit: 75 },
  transient: { exit: 75 },
  locked: { exit: 75 }, // D-07: a bare 75; never retry_after_s (report or serialize).
  timeout: { exit: 124 },
  not_installed: { exit: 127 },
  signal: { exit: 128 },
  git_error: { exit: 1 },
  git_timeout: { exit: 1 },
};

const FINALIZE_CAP_MS = 10000;
const KILL_GRACE_MS = 2000;
// A child that prints a terminal limit and keeps running is stopped this long after the line.
const LIMIT_GRACE_MS = 1500;
const PIPE_DRAIN_MS = 2000;
// gsd-tools run-with-timeout SIGKILLs the runner 3 s after forwarding a signal, and the CLI
// runs in its own group, so the whole signal path (grace, kill, drain, tree) fits in 2.5 s.
const SIGNAL_BUDGET_MS = 2500;
const SIGNAL_GRACE_MS = 1000;
const SIGNAL_DRAIN_MS = 500;
const GIT_CAP_MS = 10000;
const LIST_CAP_MS = 15000;
const PI_RPC_ARGS = [
  '--mode', 'rpc', '--offline', '--no-session', '--no-extensions',
  '--no-skills', '--no-context-files', '--no-mcp',
];
const PI_RPC_REQUEST = '{"id":"1","type":"get_available_models"}\n';

let childPgidFile = null;
let childPgidBroken = false;
let runStartedMs = Date.now();
let liveFields = {
  cli: '-', model: '-', cli_rc: '-', out: 0, tree: 'clean',
  route: 'unknown', rule: '-', pattern: 'none',
};
// The settings report, session id and escalation flags the status line's 37 group prints (D-12); main fills it.
let liveSettings = { report: [], sessionId: null, escalation: { runtime: false, model: false } };
// SPEC R5: the execute check's coverage and findings for this call; finish prints them, main resets them.
let liveCheck = { coverage: '-', findings: [] };
let finished = false;
let finishedExit = 1;
let runDeadline = 0;
let finalizeBy = 0;
let current = null;
let currentFinalize = null;
let aborting = 0;
let signalBy = 0;
let backstop = null;
// The run lock this process created ({ file, runId, record }); only it is ever released (D-08).
let liveLock = null;
let lockUpdateFailed = false;
// SPEC R4: the effective baseline { head, tree, at, role, cli, model, source }, source flag|record|fresh; plans 38-16 and 38-18 read it.
let liveBaseline = null;
let baselineFile = null;
let baselineNoted = false;
const tempDirs = new Set();
// Tabs a hosted lane opened and has not confirmed closed; exitFlushed retries them (D-26).
const openTabs = new Map();
const sleepers = new Set();

function budgetMs(capMs, limit) {
  const end = aborting ? Math.min(limit, signalBy) : limit;
  return Math.max(0, Math.min(capMs, end - Date.now()));
}

function makeTemp(prefix) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), prefix));
  tempDirs.add(dir);
  return dir;
}
function dropTemp(dir) {
  fs.rmSync(dir, { recursive: true, force: true });
  tempDirs.delete(dir);
}

let stderrGone = false;
// A vanished reader must not crash the runner (that would orphan the CLI group): the run
// still finishes and is still supervised, only its output is lost.
process.stdout.on('error', () => { /* answer reader gone */ });
process.stderr.on('error', () => { stderrGone = true; });

let log = (text) => {
  if (finished || stderrGone) return;
  process.stderr.write(text.endsWith('\n') ? text : `${text}\n`);
};

// Every run that does not end ok reports once, immediately before its status line.
function reportAndFinish(status, fields, stopped) {
  const why = stopped || fields.stopped || 'class';
  if (status !== 'ok' && !fields.reportDone) {
    logReport(status, fields.cli ?? '-', fields.model ?? '-', fields.route, fields.attempts || 0,
      fields.cycles || 0, fields.firstFailureMs || 0, fields.lastFailureMs || 0, why,
      fields.dueAtMs || 0, fields.upstream || null, fields.check || '-');
    if (fields.upstream?.body) {
      const raw = fields.upstream.raw || '';
      const extra = redactedValues(normalizeInput(raw));
      log(redactSecrets(`cross-ai: upstream body=${JSON.stringify(fields.upstream.body)}`, extra));
      const values = fields.upstream.fields;
      const safe = values && Object.fromEntries(Object.entries(values).map(([key, value]) => [
        key, typeof value === 'string' ? replaceCopies(value, extra) : value,
      ]));
      log(redactSecrets(`cross-ai: upstream fields=${safe ? JSON.stringify(safe) : '-'}`, extra));
    }
  }
  return finish(status, fields);
}

// SPEC R5 closed list; this order is the print order (blocking first, then informational).
const FINDING_CODES = Object.freeze(['no_commit', 'task_uncovered', 'admits_skipped', 'forbidden_path', 'no_tree_change', 'outside_plan_files', 'uncommitted_edits', 'baseline_replaced', 'coverage_unchecked']);
const FINDING_ITEMS_MAX = 10;
function addFinding(code, detail) {
  if (!FINDING_CODES.includes(code)) throw new Error(`unknown finding code: ${code}`);
  liveCheck.findings.push({ code, detail });
}
// Redact, strip control characters and Unicode line separators, then redact again so one finding stays one line.
function findingText(value) {
  return redactSecrets(redactSecrets(String(value)).replace(/[\x00-\x1f\x7f-\x9f\u2028\u2029]/g, ''));
}
function findingDetail(detail) {
  if (Array.isArray(detail)) {
    const items = [...new Set(detail.map(findingText))].sort();
    const shown = items.slice(0, FINDING_ITEMS_MAX).join(', ');
    const text = items.length > FINDING_ITEMS_MAX ? `${shown} (+${items.length - FINDING_ITEMS_MAX} more)` : shown;
    return text || '-';
  }
  const text = findingText(detail ?? '');
  return text || '-';
}
function findingLines(check) {
  return FINDING_CODES.flatMap((code) => check.findings.filter((f) => f.code === code).map((f) => `cross-ai: finding reason=${code} detail=${findingDetail(f.detail)}`));
}
function checkGroup(check) {
  const coverage = /^(?:\d+\/\d+|n\/a|-)$/.test(String(check.coverage)) ? String(check.coverage) : '-';
  const codes = FINDING_CODES.filter((code) => check.findings.some((f) => f.code === code)).join(',') || '-';
  return `coverage=${coverage} findings=${codes}`;
}

function finish(status, fields) {
  if (finished) return finishedExit;
  // D-10: a finished task drops its baseline record; partial and every failure keep it.
  if (status === 'ok' && baselineFile) deleteCycleState(baselineFile);
  releaseLock(); // D-08: every status passes here.
  const row = STATUS_TABLE[status] || { exit: 1 };
  const tree = fields.tree ?? 'unknown';
  const exit = fields.exit ?? row.exit;
  const elapsed = fields.elapsed ?? Math.max(0, Math.round((Date.now() - runStartedMs) / 1000));
  const route = fields.route ?? 'unknown';
  const rule = fields.rule ?? '-';
  const pattern = fields.pattern ?? 'none';
  const attempts = fields.attempts ?? 0;
  const cycles = fields.cycles ?? 0;
  let line = `AIKIT-XAI status=${status} cli=${fields.cli ?? '-'} model=${fields.model ?? '-'} ` +
    `exit=${exit} cli_rc=${fields.cli_rc ?? '-'} elapsed=${elapsed}s out=${fields.out ?? 0} ` +
    `tree=${tree} action=stop route=${route} rule=${rule} pattern=${pattern}` +
    ` attempts=${attempts} cycles=${cycles}`;
  let group = 'session=- applied=- ignored=- unknown=- escalate=-';
  try { group = String(statusGroup(liveSettings.report, liveSettings.sessionId, liveSettings.escalation)).trim(); } catch { /* the one status line is printed whatever the group does (Pitfall 4) */ }
  line += ` ${group}`;
  let check = 'coverage=- findings=-';
  try { check = checkGroup(liveCheck); } catch { /* status codes do not depend on detail rendering */ }
  try { for (const text of findingLines(liveCheck)) log(text); } catch { /* always print the status line */ }
  line += ` ${check}`;
  if (fields.retryAfterS !== undefined && fields.retryAfterS !== null) {
    line += ` retry_after_s=${fields.retryAfterS} cycle=${fields.cycle ?? cycles}`;
  }
  if (!stderrGone) process.stderr.write(`${line}\n`);
  finished = true;
  finishedExit = exit;
  return exit;
}

// Declared above RUNTIMES: a row's modelId reads these at module load, and a later const
// would be in its temporal dead zone.
// SPEC R5 floor, the one model id refusal for every runtime: non-empty, no leading dash (read
// as a CLI option), no whitespace, no shell, control or non-ASCII character, one optional
// trailing [k=v,...] bracket. The per-runtime seed shapes below only advise (a note in main).
const MODEL_ID_FLOOR = /^[A-Za-z0-9][A-Za-z0-9._:/#@+-]*(?:\[[A-Za-z0-9._=,-]+\])?$/;
// Seed shapes (advisory only): no leading dash and no shell or space characters (U-4).
const MODEL_ID = /^[A-Za-z0-9][A-Za-z0-9._:/#@+-]*$/;
// Cursor only: one trailing [k=v,...] bracket (D-18). No space, quote, `$` or `;`.
const CURSOR_MODEL_ID = /^[A-Za-z0-9][A-Za-z0-9._:/#@+-]*(?:\[[A-Za-z0-9._=,-]+\])?$/;
// pi: provider/model. pi matches the whole id first and splits a trailing :<thinking> only
// when it is one of the seven levels (its model-resolver), so `:` inside the model part (a
// tag such as <name>:<tag>) is part of the id; modelSuffix strips only a known level.
const PI_MODEL_ID = /^[A-Za-z0-9][A-Za-z0-9._@+-]*\/[A-Za-z0-9][A-Za-z0-9._:\/@+-]*$/;
// opencode: provider/model (`:` stays inside the model part) and one trailing #variant.
const OPENCODE_MODEL_ID = /^[A-Za-z0-9][A-Za-z0-9._@+-]*\/[A-Za-z0-9][A-Za-z0-9._:\/@+-]*(?:#[A-Za-z0-9._-]+)?$/;

// process.exit drops writes still queued on a pipe, so exit only once both streams have
// flushed (a stalled reader gets a bounded wait, shorter on the signal path).
function exitFlushed(code) {
  if (backstop) clearTimeout(backstop);
  releaseLock();
  // Every exit drops the temp folders still registered (an early return skips its finally).
  // The catch keeps a failing rm from looping through the crash handler back to here.
  for (const [tab, dir] of [...openTabs]) {
    let closed = false;
    try { closed = closeTab(tab, 1000); } catch { /* retry failed */ }
    if (!closed) { dropSecrets(dir); keepRecordOnly(dir, tab); }
  }
  for (const dir of [...tempDirs]) { try { dropTemp(dir); } catch { tempDirs.delete(dir); } }
  process.exitCode = code;
  let pending = 2;
  const done = () => { if (--pending === 0) process.exit(code); };
  for (const s of [process.stdout, process.stderr]) {
    if (s.destroyed || s.writableEnded) done();
    else s.write('', done);
  }
  setTimeout(() => process.exit(code), aborting ? 300 : 5000).unref();
}

function setLog(fn) { log = fn; }
// 38-08: the self-test harness registers its abort routine here while it runs.
let selfTestHook = null;
function setSelfTestHook(fn) { selfTestHook = fn; }

process.on('uncaughtException', (e) => {
  if (selfTestHook) {
    process.stderr.write(`self-test: internal error: ${e && e.stack || e}\n`);
    selfTestHook(1);
    return;
  }
  if (current) killGroup(current, 'SIGKILL');
  log(`cross-ai: internal error: ${e && e.stack || e}`);
  exitFlushed(reportAndFinish(
        'crash', { ...liveFields, tree: 'unknown', exit: 1, cli_rc: '-' },
      ));
});

// D-08 backstop: a path that skips finish still drops this run's lock (synchronous).
process.on('exit', () => { releaseLock(); });

// SPEC R6: the live record of claude's permission flag (37-SPIKE.md Q3b); it labels only the flag.
const CLAUDE_EXEC_PROBE_RECORD = null;
// SPEC R6: the live record of the whole execute formula and its resume; null keeps it unverified, with a note on every execute call.
const CLAUDE_EXEC_FORMULA_RECORD = null;
const MCP_SERVER_RE = /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/;
const SKILL_PROSE = { label: { state: 'verified', source: 'runner: the SKILL.md text inlined before the prompt (stdin, or the copilot -p argument)' } };
function skillsNone(source) { return { name: { form: null, label: { state: 'unknown', source } }, path: { flag: null, label: { state: 'unknown', source } }, prose: SKILL_PROSE }; }
// SPEC R3 (D-02): what a final argv lets a lane do. tools: allow and deny flags, the tool names that are a shell or write files; facts: a flag run a recorded help line explains. Labels only quote tests/fixtures/cli_help/<host>/help.txt.
const CODEX_SANDBOX_LABEL = { state: 'verified', source: 'codex 0.170.0 --help 2026-11-21: "-s, --sandbox <SANDBOX_MODE> Select the sandbox policy to use when executing model-generated shell commands [possible values: read-only, workspace-write, danger-full-access]"' };
const CODEX_BYPASS_LABEL = { state: 'verified', source: 'codex 0.170.0 --help 2026-11-21: "--dangerously-bypass-approvals-and-sandbox Skip all confirmation prompts and execute commands without sandboxing"' };
const RUNTIMES = {
  cursor: {
    bins: ['cursor-agent', 'agent'],
    list: { argv: ['models'], parse: parseCursorListingIds },
    exec: (m, c) => ['-p', '--output-format', 'json', '--model', m, '--trust', '--force', '--sandbox', 'disabled', '--approve-mcps', '--workspace', c.cwd],
    review: (m, c) => ['-p', '--output-format', 'json', '--model', m, '--mode', c.cursorMode || 'ask', '--trust', '--workspace', c.cwd],
    resume: (m, c, sid, mode) => [...RUNTIMES.cursor[mode](m, c), '--resume', sid],
    // Cursor bracket ids (effort, fast); the listing has the bare id.
    modelSuffix: /\[[^\]]*\]$/,
    parse: (out) => {
      const ev = lastJson(out, (j) => j.type === 'result');
      if (!ev) return { text: '', sessionId: null, error: 'no result event in cursor output' };
      return { text: ev.result || '', sessionId: ev.session_id || null, error: ev.is_error ? (ev.result || 'is_error') : null };
    },
    modelId: CURSOR_MODEL_ID,
    profiles: null,
    reviewExtras: [],
    env: {},
    forms: {
      mcp: null,
      skills: skillsNone('cursor-agent 2026.11.13 help 2026-11-21: no skill form'),
      context: { kind: 'bracket', key: 'context', valueKind: 'label', label: { state: 'verified', source: 'cursor-agent 2026.11.13 --help 2026-11-21: "--model <model>" with the bracket example "[context=1m,effort=high,fast=false]"; meaning per model unverified' } },
      session: { style: 'minted', resumeFlag: '--resume', label: { state: 'unverified', source: 'cursor-agent 2026.11.13 --help 2026-11-21: "--resume [chatId] Select a session to resume"; resume not live-probed' } },
      capabilities: { tools: null, facts: [{ run: ['--mode', 'ask'], field: 'write', value: 'none', label: { state: 'verified', source: 'cursor-agent 2026.11.13 --help 2026-11-21: "ask: Q&A style for explanations and questions (read-only)"' } }, { run: ['--mode', 'plan'], field: 'write', value: 'none', label: { state: 'verified', source: 'cursor-agent 2026.11.13 --help 2026-11-21: "plan: read-only/planning (analyze, propose plans, no edits)"' } }, { run: ['--force'], field: 'shell', value: 'yes', label: { state: 'verified', source: 'cursor-agent 2026.11.13 --help 2026-11-21: "-f, --force Force allow commands unless explicitly denied"' } }], label: { state: 'verified', source: 'cursor-agent 2026.11.13 --help 2026-11-21 (tests/fixtures/cli_help/cursor/)' } },
      effort: { kind: 'id-bracket', key: 'effort', label: { state: 'verified', source: 'cursor-agent 2026.11.13 --help 2026-11-21: "--model <model>" with the bracket example "[context=1m,effort=high,fast=false]"' } },
      provider: { kind: 'none', label: { state: 'unknown', source: 'no provider part in the model id form' } },
    },
  },
  // opencode 2.3.2 run --help formulas (recorded: tests/fixtures/cli_help/opencode/); partial bare profile: opencode still loads
  // ~/.agents/skills and ~/.config/opencode/skills (opencode docs). --standalone (a global flag) runs a headless run
  // on a private server, never inside the user's long-lived managed service. listModels (`opencode models`) also
  // accepts --standalone and --server; the runner does not pass them, so the listing reads the shared service, read-only.
  opencode: {
    bins: ['opencode'],
    list: { argv: ['models'], parse: parseOpencodeListingIds },
    exec: (m) => ['run', '--model', m, '--auto', '--format', 'json', '--standalone'],
    review: (m) => ['run', '--model', m, '--agent', 'plan', '--format', 'json', '--standalone'],
    resume: (m, c, sid, mode) => [...RUNTIMES.opencode[mode](m, c), '--session', sid],
    parse: parseOpencode,
    modelSuffix: /#[^#/]+$/, // provider/model#variant; the listing prints no variants, the model API lists them (variants[].id)
    modelId: OPENCODE_MODEL_ID,
    profiles: null,
    reviewExtras: [],
    env: { OPENCODE_DISABLE_AUTOUPDATE: '1', OPENCODE_DISABLE_CLAUDE_CODE_SKILLS: '1' },
    forms: {
      mcp: null,
      skills: skillsNone('opencode 2.3.2 help 2026-11-21: no skill form'),
      context: { kind: 'none', valueKind: null, label: { state: 'unknown', source: 'opencode 2.3.2 run --help 2026-11-21: no context form' } },
      session: { style: 'minted', resumeFlag: '--session', label: { state: 'unverified', source: 'opencode 2.3.2 run --help 2026-11-21: "Session ID to continue, or to create if it does not exist"; caller-chosen id shapes unverified (a ses_ id was accepted live on 2026-11-16)' } },
      capabilities: { tools: null, facts: [], label: { state: 'unknown', source: 'opencode 2.3.2 help 2026-11-21: no recorded help line states the write reach, a shell tool or MCP for the run flags' } },
      effort: { kind: 'id-suffix', key: '#', label: { state: 'verified', source: 'opencode 2.3.2 run --help 2026-11-21: "Model to use in the format provider/model#variant"' } },
      provider: { kind: 'id-prefix', label: { state: 'verified', source: 'opencode 2.3.2 run --help 2026-11-21: "Model to use in the format provider/model#variant"' } },
    },
  },
  pi: {
    bins: ['pi'],
    list: { argv: PI_RPC_ARGS, input: PI_RPC_REQUEST, parse: parsePiListingIds },
    exec: (m, c) => ['-p', '--model', m, ...(c.adds?.effort || []), '--session-id', c.sid, '--no-skills', '--no-extensions', '--no-approve', '--offline',
      ...(c.profileFlags || []), ...(c.adds?.skills || [])],
    review: (m, c) => ['-p', '--model', m, ...(c.adds?.effort || []), '--session-id', c.sid, '--no-skills', '--no-extensions', '--no-approve', '--offline',
      ...(c.profileFlags || []), ...(c.adds?.skills || [])],
    resume: (m, c, sid, mode) => RUNTIMES.pi[mode](m, c),
    parse: (out) => ({ text: out, sessionId: null, error: null }),
    // pi documents its model flag as provider/id[:thinking]; the listing has bare ids.
    modelSuffix: /:(?:off|minimal|low|medium|high|xhigh|max)$/,
    modelId: PI_MODEL_ID,
    // Tool sets live here, not in the formulas, so a profile can only narrow review.
    profiles: {
      exec: [],
      review: ['--tools', 'read,grep,find,ls', '--no-mcp', '--no-context-files'],
      none: ['--no-tools', '--no-mcp', '--no-context-files'],
    },
    reviewExtras: ['--skill'],
    env: {},
    forms: {
      mcp: null,
      skills: { name: { form: null, reason: 'mode_forbids', label: { state: 'unknown', source: 'pi 1.5.2 help 2026-11-21: no load-by-name form; the formulas pass --no-skills' } }, path: { flag: '--skill', label: { state: 'verified', source: 'pi 1.5.2 help 2026-11-21: "--skill <path> Load a skill file or directory (can be used multiple times)"' } }, prose: SKILL_PROSE },
      context: { kind: 'none', valueKind: null, label: { state: 'unknown', source: 'pi 1.5.2 --help 2026-11-21: no context form' } },
      session: { style: 'chosen', flag: '--session-id', label: { state: 'unverified', source: 'pi 1.5.2 --help 2026-11-21: "--session-id <id> Use the current directory existing session with the ID, creating it otherwise"; resume not live-probed' } },
      capabilities: { tools: { allow: ['--tools'], deny: ['--exclude-tools'], shell: ['bash'], write: ['edit', 'write'], label: { state: 'verified', source: 'pi 1.5.2 --help 2026-11-21: "--tools, -t <tools> Comma-separated allowlist of tool names or patterns (*) to enable" and "Only +name/-name entries add to or remove from the defaults"' } }, facts: [{ run: ['--no-mcp'], field: 'mcp', value: 'none', label: { state: 'verified', source: 'pi 1.5.2 --help 2026-11-21: "--no-mcp Disable built-in MCP support: no servers connect and no MCP tools"' } }, { run: ['--no-skills'], field: 'skills', value: 'none', label: { state: 'verified', source: 'pi 1.5.2 --help 2026-11-21: "--no-skills, -ns Disable skills discovery and loading"' } }, { run: ['--no-tools'], field: 'shell', value: 'no', label: { state: 'verified', source: 'pi 1.5.2 --help 2026-11-21: "--no-tools, -nt Disable all tools by default (built-in and extension)"' } }, { run: ['--no-tools'], field: 'write', value: 'none', label: { state: 'verified', source: 'pi 1.5.2 --help 2026-11-21: "--no-tools, -nt Disable all tools by default (built-in and extension)"' } }], label: { state: 'verified', source: 'pi 1.5.2 --help 2026-11-21 (tests/fixtures/cli_help/pi/)' } },
      effort: { kind: 'flag', flag: '--thinking', label: { state: 'verified', source: 'pi 1.5.2 --help 2026-11-21: "--thinking <level> Set thinking level: off, minimal, low, medium, high, xhigh, max"' } },
      provider: { kind: 'id-prefix', label: { state: 'verified', source: 'pi 1.5.2 --help 2026-11-21: "--model <pattern> Model pattern or ID (supports provider/id and optional :<thinking>)"' } },
    },
  },
  // unverified (outside the default prefer)
  codex: {
    bins: ['codex'],
    list: { argv: ['debug', 'models'], parse: parseCodexListingIds },
    exec: (m, c) => withCodexKnobs(codexExecArgv(m, c), c),
    review: (m, c) => withCodexKnobs(['exec', '--sandbox', 'read-only', '--skip-git-repo-check', '-C', c.cwd, '-m', m, '--json', '-o', c.outFile, '-'], c),
    resume: (m, c, sid, mode) => withCodexKnobs(['exec', 'resume', ...(mode === 'exec' ? ['--dangerously-bypass-approvals-and-sandbox'] : []),
      '--skip-git-repo-check', '-m', m, '--json', '-o', c.outFile, sid, '-'], c),
    parse: (out, c) => {
      let sid = null, error = null;
      // shortcut: assumes codex emits `error` for stream retries it recovers from and ends a
      // good turn with turn.completed (not live-verified); turn.failed always counts.
      for (const j of jsonLines(out)) {
        if (j.type === 'thread.started') sid = j.thread_id || sid;
        if (j.type === 'error' || j.type === 'turn.failed') error = JSON.stringify(j).slice(0, 400);
        if (j.type === 'turn.completed') error = null;
      }
      let text = '';
      try { text = fs.readFileSync(c.outFile, 'utf8'); } catch { /* no answer written */ }
      return { text, sessionId: sid, error };
    },
    modelId: MODEL_ID,
    profiles: null,
    reviewExtras: [],
    env: {},
    forms: {
      mcp: { flag: null, prefix: '', after: [], label: { state: 'unverified', source: 'codex 0.170.0 help 2026-11-21: a generic -c key=value override whose help names no MCP key; it would put server values on argv' } },
      skills: skillsNone('codex 0.170.0 help 2026-11-21: no skill form'),
      context: { kind: 'config', key: 'model_context_window', valueKind: 'tokens', label: { state: 'verified', source: 'codex 0.170.0 exec --help 2026-11-21: "-c, --config <key=value>"; a zero-token config parse rejected a non-integer model_context_window as "expected i64" (2026-11-16); its effect on a model window is unverified' } },
      session: { style: 'minted', resumeFlag: null, noResume: ['review', 'sandbox'], label: { state: 'unverified', source: 'codex 0.170.0 exec --help 2026-11-21: "resume Resume a previous session by id"; exec resume has no read-only sandbox form; resume not live-probed' } },
      capabilities: { tools: null, facts: [{ run: ['--sandbox', 'read-only'], field: 'write', value: 'none', label: CODEX_SANDBOX_LABEL }, { run: ['--sandbox', 'workspace-write'], field: 'write', value: 'workspace', label: CODEX_SANDBOX_LABEL }, { run: ['--sandbox', 'danger-full-access'], field: 'write', value: 'full', label: CODEX_SANDBOX_LABEL }, { run: ['--dangerously-bypass-approvals-and-sandbox'], field: 'write', value: 'full', label: CODEX_BYPASS_LABEL }, { run: ['--dangerously-bypass-approvals-and-sandbox'], field: 'shell', value: 'yes', label: CODEX_BYPASS_LABEL }], label: { state: 'verified', source: 'codex 0.170.0 --help 2026-11-21 (tests/fixtures/cli_help/codex/)' } },
      effort: { kind: 'config', key: 'model_reasoning_effort', label: { state: 'verified', source: 'codex 0.170.0 exec --help 2026-11-21: "-c, --config <key=value>"; model_reasoning_effort is the runner\'s existing codex effort key' } },
      provider: { kind: 'none', label: { state: 'unknown', source: 'no provider part in the model id form' } },
    },
  },
  // read-only enforcement not live-verified
  // execute formula: full permissions like every other execute runtime; labelled by execLabel until a live record of the exact formula and its resume exists (SPEC R6).
  claude: {
    bins: ['claude'],
    list: null,
    exec: (m, c) => ['-p', '--model', m, '--output-format', 'json', '--permission-mode', 'bypassPermissions', ...(c.adds?.effort || []), ...(c.adds?.skills || []), ...(c.adds?.mcp || [])],
    review: (m, c) => ['-p', '--model', m, '--output-format', 'json', '--permission-mode', 'plan', ...(c.adds?.effort || []), ...(c.adds?.skills || []), ...(c.adds?.mcp || [])],
    resume: (m, c, sid, mode) => [...RUNTIMES.claude[mode](m, c), '--resume', sid],
    permissionLabel: CLAUDE_EXEC_PROBE_RECORD === null ? { state: 'unverified', source: 'claude permission flag: no live probe record (37-SPIKE.md Q3b)' } : { state: 'verified', source: CLAUDE_EXEC_PROBE_RECORD },
    execLabel: CLAUDE_EXEC_FORMULA_RECORD === null ? { state: 'unverified', source: 'claude execute formula: no live record of the exact formula and its resume (37-SPIKE.md Q3)' } : { state: 'verified', source: CLAUDE_EXEC_FORMULA_RECORD },
    parse: (out) => {
      const j = parseJson((out || '').trim());
      if (!j || typeof j !== 'object') return { text: '', sessionId: null, error: 'no claude json' };
      return {
        text: j.result || '', sessionId: j.session_id || null,
        error: j.is_error ? (j.result || 'is_error') : null,
      };
    },
    modelId: MODEL_ID,
    profiles: null,
    reviewExtras: [],
    env: {},
    forms: {
      mcp: { flag: '--mcp-config', prefix: '', after: ['--strict-mcp-config'], label: { state: 'verified', source: 'claude 2.1.330 help 2026-11-21: "--mcp-config <configs...> Load MCP servers from JSON files or strings" and "--strict-mcp-config Only use MCP servers from --mcp-config"' } },
      skills: { name: { form: '/<name>', label: { state: 'unverified', source: 'claude 2.1.330 help 2026-11-21: "Skills still resolve via /skill-name" appears only in the bare-mode text' } }, path: { flag: '--add-dir', label: { state: 'unverified', source: 'claude 2.1.330 help 2026-11-21: "--add-dir <directories...> More directories Claude can access" names no skill loading' } }, prose: SKILL_PROSE },
      context: { kind: 'id-suffix', valueKind: null, label: { state: 'unverified', source: 'claude 2.1.330 --help 2026-11-21: no model-context flag; the [1m] model suffix is not in the help' } },
      session: { style: 'minted', resumeFlag: '--resume', label: { state: 'unverified', source: 'claude 2.1.330 --help 2026-11-21: "-r, --resume [value] Resume a conversation by session ID or name"; resume not live-probed' } },
      capabilities: { tools: { allow: ['--tools'], deny: ['--disallowedTools', '--disallowed-tools'], variadic: true, shell: ['Bash'], write: ['Edit', 'Write', 'NotebookEdit'], label: { state: 'verified', source: 'claude 2.1.330 --help 2026-11-21: "--tools <tools...> Built-in tools to make available: "" for none, "default" for the default set, or tool names (e.g. "Bash,Edit,Read")" and "--disallowedTools, --disallowed-tools <tools...> Comma or space-separated list of tool names to deny"' } }, facts: [], label: { state: 'verified', source: 'claude 2.1.330 --help 2026-11-21 (tests/fixtures/cli_help/claude/); --permission-mode lists plan and bypassPermissions without saying what they allow' } },
      effort: { kind: 'flag', flag: '--effort', label: { state: 'verified', source: 'claude 2.1.330 --help 2026-11-21: "--effort <level> Effort level for the current session (low, medium, high, xhigh, max)"' } },
      provider: { kind: 'none', label: { state: 'unknown', source: 'no provider part in the model id form' } },
    },
  },
  // Flags documented in copilot 1.0.103 `--help` and `help permissions`; error, quota and
  // exit-code shapes unverified (no real copilot run in this phase).
  copilot: {
    bins: ['copilot'],
    list: null,
    argvPrompt: true,
    errorsUnverified: true,
    modelId: MODEL_ID,
    exec: (m, c) => ['-p', c.promptArg, '-s', '--no-ask-user', '--model', m, ...(c.adds?.effort || []), ...(c.adds?.context || []), '--session-id', c.sid, ...(c.profileFlags || []), ...(c.adds?.skills || []), ...(c.adds?.mcp || [])],
    review: (m, c) => ['-p', c.promptArg, '-s', '--no-ask-user', '--model', m, ...(c.adds?.effort || []), ...(c.adds?.context || []), '--session-id', c.sid, ...(c.profileFlags || []), ...(c.adds?.skills || []), ...(c.adds?.mcp || [])],
    resume: null,
    parse: (out) => ({ text: out, sessionId: null, error: null }),
    modelSuffix: null,
    env: { COPILOT_ALLOW_ALL: '' },
    profiles: {
      exec: ['--allow-all-tools'],
      review: ['--allow-all-tools', '--available-tools=view,grep,glob',
        '--excluded-tools=bash,create,edit,apply_patch', '--deny-tool=shell', '--deny-tool=write',
        '--disable-builtin-mcps'],
    },
    reviewExtras: [],
    forms: {
      mcp: { flag: '--additional-mcp-config', prefix: '@', after: [], label: { state: 'verified', source: 'copilot 1.0.112 help 2026-11-21: "--additional-mcp-config <json> Additional MCP servers configuration as JSON string or file path (prefix with @)"; augments the user servers, no strict form' } },
      skills: { name: { form: null, label: { state: 'unverified', source: 'copilot 1.0.112 skill help 2026-11-21: discovery roots only, no load-by-name form' } }, path: { flag: '--add-dir', root: '.github/skills', label: { state: 'unverified', source: 'copilot 1.0.112 help 2026-11-21: "--add-dir <directory> Allow file access to a directory and load its .github/skills" as trusted configuration; layout effect untested' } }, prose: SKILL_PROSE },
      context: { kind: 'flag', flag: '--context', valueKind: 'enum', values: ['default', 'long_context'], label: { state: 'verified', source: 'copilot 1.0.112 --help 2026-11-21: "--context <tier> Set the context window tier (overrides persisted setting) [possible values: default, long_context]"' } },
      session: { style: 'chosen', flag: '--session-id', label: { state: 'unverified', source: 'copilot 1.0.112 --help 2026-11-21: "--session-id <id> Resume an existing session or task by ID, or set the UUID for a new session"; resume not live-probed' } },
      capabilities: { tools: { allow: ['--available-tools'], deny: ['--excluded-tools', '--deny-tool'], variadic: true, shell: ['bash', 'shell'], write: ['create', 'edit', 'apply_patch', 'write'], label: { state: 'verified', source: 'copilot 1.0.112 --help 2026-11-21: "--available-tools [<tools>...] Only these tools will be available to the model", "--excluded-tools [<tools>...] These tools will not be available to the model" and "--deny-tool [<tools>...] Tools the CLI does not have permission to use"' } }, facts: [], label: { state: 'verified', source: 'copilot 1.0.112 --help 2026-11-21 (tests/fixtures/cli_help/copilot/)' } },
      effort: { kind: 'flag', flag: '--reasoning-effort', label: { state: 'verified', source: 'copilot 1.0.112 --help 2026-11-21: "--reasoning-effort <level> Set the reasoning effort level; supported levels depend on the model"' } },
      provider: { kind: 'none', label: { state: 'unknown', source: 'no provider part in the model id form' } },
    },
  },
};

// R9: provenance of each formula and listing, from the recorded help under tests/fixtures/cli_help (labels only; nothing decides on them).
const FORMULA_LABELS = Object.fromEntries([
  ['claude', '2.1.330', '2026-11-21', ['exec', 'review', 'resume']],
  ['codex', '0.170.0', '2026-11-21', ['exec', 'review', 'resume', 'listing']],
  ['copilot', '1.0.112', '2026-11-21', ['exec', 'review']],
  ['cursor', '2026.11.13', '2026-11-21', ['exec', 'review', 'resume', 'listing']],
  ['opencode', '2.3.2', '2026-11-20', ['exec', 'review', 'resume', 'listing']],
  ['pi', '1.5.2', '2026-11-21', ['exec', 'review', 'resume', 'listing']],
].map(([id, version, recorded, facts]) => [id, Object.fromEntries(facts.map((fact) => [fact, {
  state: 'verified', source: `verified: ${id} ${version} help recorded ${recorded} (tests/fixtures/cli_help/${id}/)`,
}]))]));

// SPEC R4: the only placeholders a declared argv file may hold; the prompt always goes on stdin.
const ARGV_FILE_PLACEHOLDERS = ['{model}', '{effort}', '{session}'];
const ARGV_FILE_NO_FORM = Object.freeze({ kind: 'none', style: 'none', flag: null, key: null, valueKind: null, label: Object.freeze({ state: 'unknown', source: 'declared by --argv-file' }) });

// Settings planner (D-11, D-14): rows carry forms as data; one pure planSettings decides argv additions and the report.
const SETTING_REASONS = ['no_form', 'id_carries', 'unverified_form', 'mode_forbids', 'no_slot', 'recorded_only', 'no_provider_form', 'bad_value', 'no_herdr', 'host_failed'];
const SETTING_NAMES = ['model', 'provider', 'role', 'effort', 'context', 'session', 'escalate_runtime', 'escalate_model', 'host', 'skill', 'mcp'];
const SETTING_STATES = ['applied', 'ignored', 'unknown'];

function bracketValue(model, key) {
  const match = model.match(/\[([^\]]*)\]$/);
  if (!match) return null;
  for (const item of match[1].split(',')) {
    const at = item.indexOf('=');
    if (at >= 0 && item.slice(0, at) === key) return item.slice(at + 1);
  }
  return null;
}

function mergeBracket(model, key, value) {
  const match = model.match(/\[([^\]]*)\]$/);
  if (!match) return `${model}[${key}=${value}]`;
  return `${model.slice(0, match.index)}[${match[1] ? `${match[1]},` : ''}${key}=${value}]`;
}

function contextTokens(label) {
  // Decimal k and m, accepted assumption A1.
  const match = /^([1-9][0-9]*)([km]?)$/.exec(label);
  if (!match) return null;
  const value = Number(match[1]) * (match[2] === 'k' ? 1000 : match[2] === 'm' ? 1000000 : 1);
  return Number.isSafeInteger(value) && value >= 1 && value <= 1000000000 ? value : null;
}

function cleanSettingValue(name, value) {
  const text = String(value ?? '-').replace(/[\x00-\x1f\x7f-\x9f]/g, '');
  // BROAD_RES redacts every UUID, and a session id must stay reusable.
  return name === 'session' ? redactKeyShapes(text) : redactSecrets(text);
}

const SETTING_HANDLERS = {
  model: (plan, row, role, call) => {
    plan.report.push({ name: 'model', value: call.model, state: 'applied', proof: 'model' });
  },
  provider: (plan, row, role, call) => {
    const slash = call.model.indexOf('/');
    if (slash <= 0) return;
    const prefix = call.model.slice(0, slash);
    if (row.forms?.provider?.kind === 'id-prefix') {
      plan.provider = prefix;
      plan.report.push({ name: 'provider', value: prefix, state: 'applied', proof: { slotPrefix: `${prefix}/` } });
    } else {
      plan.report.push({ name: 'provider', value: prefix, state: 'unknown', reason: 'no_provider_form' });
    }
  },
  role: (plan, row, role) => {
    plan.report.push({ name: 'role', value: role === 'exec' ? 'execute' : 'review', state: 'applied', proof: { mode: role } });
  },
  effort: (plan, row, role, call) => {
    const level = call.effort ?? call.configEffort ?? null;
    if (level === null) return;
    const form = row.forms?.effort || { kind: 'none' };
    let reason = null;
    if (form.kind === 'none') reason = 'no_form';
    else if (form.label?.state !== 'verified') reason = 'unverified_form';
    else if (!LEVEL_RE.test(String(level))) reason = 'bad_value';
    else if (form.kind === 'id-bracket' ? bracketValue(plan.model, form.key) !== null : Boolean(row.modelSuffix && row.modelSuffix.test(plan.model))) reason = 'id_carries';
    if (reason) {
      plan.report.push({ name: 'effort', value: level, state: 'ignored', reason });
      return;
    }
    let proof = 'model';
    if (form.kind === 'flag') proof = plan.adds.effort = [form.flag, level];
    else if (form.kind === 'config') proof = plan.adds.effort = ['-c', `${form.key}=${level}`];
    else if (form.kind === 'id-bracket') plan.model = mergeBracket(plan.model, form.key, level);
    else if (form.kind === 'id-suffix') plan.model = `${plan.model}${form.key}${level}`;
    plan.report.push({ name: 'effort', value: level, state: 'applied', proof });
  },
  context: (plan, row, role, call) => {
    const label = call.context ?? null;
    if (label === null) return;
    const form = row.forms?.context || { kind: 'none' };
    let reason = null;
    if (form.kind === 'none') reason = 'no_form';
    else if (form.label?.state !== 'verified') reason = 'unverified_form';
    else if (form.valueKind === 'enum' && !(form.values || []).includes(label)) reason = 'bad_value';
    else if (form.valueKind === 'tokens' && contextTokens(label) === null) reason = 'bad_value';
    else if (form.kind === 'bracket' && bracketValue(plan.model, form.key) !== null) reason = 'id_carries';
    if (reason) { plan.report.push({ name: 'context', value: label, state: 'ignored', reason }); return; }
    let proof = 'model';
    if (form.kind === 'flag') proof = plan.adds.context = [form.flag, label];
    else if (form.kind === 'config') proof = plan.adds.context = ['-c', `${form.key}=${form.valueKind === 'tokens' ? String(contextTokens(label)) : label}`];
    else if (form.kind === 'bracket') plan.model = mergeBracket(plan.model, form.key, label);
    else { plan.report.push({ name: 'context', value: label, state: 'ignored', reason: 'no_form' }); return; }
    plan.report.push({ name: 'context', value: label, state: 'applied', proof });
  },
  session: (plan, row, role, call) => {
    const form = row.forms?.session || { style: 'none' };
    const id = call.sessionId ?? null;
    if (form.style === 'chosen') plan.sessionId = id ?? call.newSessionId ?? null;
    if (id === null) return;
    // SPEC R7 requires resume; D-17 labels evidence rather than refusing it.
    let reason = null;
    if (form.style === 'none') reason = 'no_form';
    else if (form.style === 'chosen') { plan.report.push({ name: 'session', value: id, state: 'applied', proof: [form.flag, id] }); return; }
    else if (typeof row.resume !== 'function') reason = 'no_form';
    else if ((form.noResume || []).some((k) => (k === 'review' && role === 'review') || (k === 'sandbox' && call.sandbox))) reason = 'mode_forbids';
    if (reason) { plan.report.push({ name: 'session', value: id, state: 'ignored', reason }); return; }
    plan.sessionId = id;
    plan.resume = true;
    const proof = form.resumeFlag ? [form.resumeFlag, id] : { runs: [['exec', 'resume'], [id, '-']] };
    plan.report.push({ name: 'session', value: id, state: 'applied', proof });
  },
  escalate_runtime: (plan, row, role, call) => {
    if (call.escalateRuntime) plan.report.push({ name: 'escalate_runtime', value: 'true', state: 'ignored', reason: 'recorded_only' });
  },
  escalate_model: (plan, row, role, call) => {
    if (call.escalateModel) plan.report.push({ name: 'escalate_model', value: 'true', state: 'ignored', reason: 'recorded_only' });
  },
  host: (plan, row, role, call) => {
    const setting = call.hostSetting;
    if (!setting || setting.value === null) return;
    if (setting.value === 'none' || (setting.value === 'auto' && setting.available)) {
      plan.report.push({ name: 'host', value: setting.value === 'none' ? 'none' : 'herdr', state: 'applied', proof: { unprovable: 'transport (D-28)' } });
    } else if (setting.value === 'auto') plan.report.push({ name: 'host', value: 'auto', state: 'ignored', reason: 'no_herdr' });
  },
  skill: (plan, row, role, call) => {
    if (call.skillPlan) { plan.adds.skills.push(...call.skillPlan.adds); plan.report.push(...call.skillPlan.report); }
  },
  mcp: (plan, row, role, call) => {
    const mp = planMcp(row, role, call.mcp);
    plan.adds.mcp.push(...mp.adds); plan.report.push(...mp.report);
  },
};

function fillArgvFile(list, model, ctx) {
  const s = (ctx && ctx.adds && ctx.adds.slots) || {};
  return list.map((el) => el.replaceAll('{model}', () => model).replaceAll('{effort}', () => s.effort ?? '').replaceAll('{session}', () => s.session ?? ''));
}

function argvFileAllowed(row, mode) { return !row || typeof row[mode] !== 'function'; }

function argvFileRow(declared) {
  const formula = (m, c) => fillArgvFile(declared.argv.slice(1), m, c);
  const forms = Object.fromEntries(Object.keys(RUNTIMES.claude.forms || {}).map((k) => [k, ARGV_FILE_NO_FORM]));
  forms.skills = { ...skillsNone('argv file lane: no skill slot'), name: { form: null, reason: 'no_slot', label: { state: 'unknown', source: 'argv file lane: no skill slot' } } };
  forms.mcp = { flag: null, prefix: '', after: [], reason: 'no_slot', label: { state: 'unknown', source: 'argv file lane: no MCP slot' } };
  return { argvFile: true, slots: declared.slots, argvRest: declared.argv.slice(1), bins: [declared.argv[0]], list: null, exec: formula, review: formula, resume: null, parse: (out) => ({ text: out, sessionId: null, error: null }), modelSuffix: null, modelId: null, profiles: null, reviewExtras: [], env: {}, errorsUnverified: true, forms };
}

function planArgvFile(plan, row) {
  const slots = row.slots;
  const effortEntry = plan.report.find((e) => e.name === 'effort');
  const sessionEntry = plan.report.find((e) => e.name === 'session');
  if (slots.effort && !effortEntry) return { ...plan, error: '--argv-file holds {effort} and the call names no effort (pass --effort)' };
  if (slots.session && !sessionEntry) return { ...plan, error: '--argv-file holds {session} and the call names no session id (pass --session-id)' };
  const values = { effort: effortEntry?.value ?? null, session: sessionEntry?.value ?? null };
  const slotElement = (name) => fillArgvFile([row.argvRest.find((el) => el.includes(`{${name}}`))], plan.model, { adds: { slots: values } })[0];
  const report = plan.report.map((entry) => {
    if (entry.name === 'provider') {
      const { reason, proof, ...rest } = entry;
      return { ...rest, value: '-', state: 'unknown' };
    }
    if (['model', 'effort', 'session', 'context'].includes(entry.name)) {
      const { reason, proof, ...rest } = entry;
      return slots[entry.name] ? { ...rest, state: 'applied', proof: [slotElement(entry.name)] } : { ...rest, state: 'ignored', reason: 'no_slot' };
    }
    return entry;
  });
  return { ...plan, report, resume: false, sessionId: slots.session ? sessionEntry.value : null, adds: { ...plan.adds, slots: { effort: slots.effort ? effortEntry.value : null, session: slots.session ? sessionEntry.value : null } } };
}

// Pure: no fs, env, spawn or clock. role is 'review' | 'exec'. Returns an object so later members (capabilities) fit.
function planSettings(row, role, call) {
  if (row.argvFile) return planArgvFile(planSettings({ ...row, argvFile: false }, role, call), row);
  const plan = { model: call.model, adds: { session: [], effort: [], context: [], skills: [], mcp: [] }, sessionId: null, resume: false, report: [], provider: null, promptPrefix: call.skillPlan?.promptPrefix ?? '' };
  for (const name of SETTING_NAMES) SETTING_HANDLERS[name]?.(plan, row, role, call);
  for (const entry of plan.report) if (entry.proof === 'model') entry.proof = { slot: plan.model };
  return plan;
}

// SPEC R3 (D-02): pure; no fs, env, spawn or clock. A fact the final argv does not show stays unknown; role is the D-02 signature's (the argv already reflects the mode).
const CAP_UNKNOWN = Object.freeze({ value: 'unknown', label: Object.freeze({ state: 'unknown', source: 'not shown by the final argv' }) });
// The wire label is a fresh {state, source} object, the shape of the row forms' labels (39-07 validates exactly that).
function capLabel(label) { return { state: label.state, source: label.source }; }
// value null: a missing or dash-led operand, a malformed use (never an empty list); operand: the index the separate value occupies, never read as a flag.
function flagUses(argv, flag) { const out = []; argv.forEach((el, i) => { if (el.startsWith(`${flag}=`)) out.push({ value: el.slice(flag.length + 1), joined: true }); else if (el === flag) { const next = argv[i + 1]; out.push({ value: next === undefined || next.startsWith('-') ? null : next, joined: false, operand: next === undefined ? undefined : i + 1 }); } }); return out; }
// SPEC R3 encoding edge: --flag=value matches the two-element run; an element that is a tool flag's operand is not a flag. shortcut: an option outside the row's tool flags whose operand spells a fact flag is read as that flag; the formulas never produce one (paths are absolute, argvPromptElement keeps a prompt off a leading dash), only CONFIG.extraArgs could; upgrade if a row gains such an option.
function factAt(argv, run, operands) { return argv.some((el, i) => !operands.has(i) && ((run.length === 2 && el === `${run[0]}=${run[1]}`) || run.every((v, j) => argv[i + j] === v))); }
function toolListCaps(tools, uses) {
  const used = [...new Set(uses.map((u) => u.flag))];
  if (!used.length) return null;
  const known = { state: tools.label.state, source: `from argv ${used.join(' ')}: ${tools.label.source}` };
  const out = (v) => (v === null ? null : { value: v, label: v === 'unknown' ? { state: 'unknown', source: `from argv ${used.join(' ')}: the tool list does not decide this (a missing operand, a repeated, variadic, pattern, default or +/- entry)` } : capLabel(known) });
  if (uses.some((u) => u.value === null) || (tools.variadic && uses.some((u) => !u.joined))) return { shell: out('unknown'), write: out('unknown') };
  const split = (v) => v.split(/[\s,]+/).filter((e) => e !== '');
  const allowValues = [...new Set(uses.filter((u) => tools.allow.includes(u.flag)).map((u) => u.value))];
  const denied = uses.filter((u) => tools.deny.includes(u.flag)).flatMap((u) => split(u.value));
  const left = (names) => names.filter((n) => tools.shell.includes(n) && !denied.includes(n));
  let shell = null, write = null;
  if (allowValues.length > 1) shell = 'unknown';
  else if (allowValues.length === 1) { const entries = split(allowValues[0]);
    if (entries.some((e) => /^[+-]/.test(e) || e === 'default')) shell = 'unknown';
    else if (entries.includes('*')) shell = left(tools.shell).length ? 'yes' : 'no';
    else if (entries.some((e) => e.includes('*'))) shell = 'unknown';
    else { shell = left(entries).length ? 'yes' : 'no'; if (shell === 'no' && !entries.some((e) => tools.write.includes(e) && !denied.includes(e))) write = 'none'; } }
  else if (!left(tools.shell).length) shell = 'no';
  if (shell === 'no' && write === null && tools.write.every((w) => denied.includes(w))) write = 'none';
  return { shell: out(shell), write: out(write) };
}
function laneCapabilities(row, role, argv, report) {
  const prompt = row && row.argvPrompt ? { channel: 'argv', max_bytes: ARGV_PROMPT_MAX - Buffer.byteLength(`${RESUME_MSG}\n\n`) } : { channel: 'stdin', max_bytes: null };
  const caps = { write: CAP_UNKNOWN, shell: CAP_UNKNOWN, skills: CAP_UNKNOWN, mcp: CAP_UNKNOWN };
  if (!row || row.argvFile) { for (const k of Object.keys(caps)) caps[k] = { value: 'unknown', label: { state: 'unknown', source: 'argv file lane: declared by --argv-file' } }; return { ...caps, prompt }; }
  const form = row.forms?.capabilities || { tools: null, facts: [] };
  const uses = form.tools ? [...form.tools.allow, ...form.tools.deny].flatMap((f) => flagUses(argv, f).map((u) => ({ ...u, flag: f }))) : [];
  const operands = new Set(uses.filter((u) => u.operand !== undefined).map((u) => u.operand));
  const set = {};
  for (const f of form.facts || []) { if (!factAt(argv, f.run, operands)) continue; const prev = set[f.field];
    if (!prev) set[f.field] = { value: f.value, label: capLabel(f.label), flag: f.run[0] };
    else if (prev.value !== f.value) set[f.field] = { value: 'unknown', label: { state: 'unknown', source: `${prev.flag} and ${f.run[0]} disagree in the final argv; no recorded help says which wins` }, flag: prev.flag }; }
  for (const [k, v] of Object.entries(set)) caps[k] = { value: v.value, label: v.label };
  const listed = form.tools ? toolListCaps(form.tools, uses) : null;
  for (const k of ['shell', 'write']) { if (!listed?.[k]) continue;
    caps[k] = set[k] && set[k].value !== listed[k].value ? { value: 'unknown', label: { state: 'unknown', source: 'a mode flag and the tool list disagree in the final argv; no recorded help says which wins' } } : listed[k]; }
  const applied = (name, f) => (report || []).some((e) => e.name === name && e.state === 'applied' && (f === undefined || e.form === f));
  if (applied('skill', 'path')) caps.skills = { value: 'path', label: capLabel({ state: row.forms.skills.path.label.state, source: `from argv ${row.forms.skills.path.flag}: applied skill setting form=path` }) };
  else if (applied('skill', 'name')) caps.skills = { value: 'discovery', label: capLabel({ state: row.forms.skills.name.label.state, source: 'from argv: applied skill setting form=name' }) };
  if (applied('mcp')) caps.mcp = { value: 'call_file', label: capLabel({ state: row.forms.mcp.label.state, source: `from argv ${row.forms.mcp.flag}: applied mcp setting` }) };
  return { ...caps, prompt };
}

const MODEL_SLOT_FLAGS = ['--model', '-m'];

// The state comes from the built argv, never from the request (SPEC R13/R14 prohibition).
function confirmReport(report, argv, promptPrefix = '', builtMode = null) {
  const hasRun = (run) => argv.some((_, i) => run.every((value, j) => argv[i + j] === value));
  const index = argv.findIndex((value) => MODEL_SLOT_FLAGS.includes(value));
  for (const e of report) {
    if (e.state !== 'applied') continue;
    const p = e.proof;
    let ok;
    if (Array.isArray(p)) ok = hasRun(p);
    else if (p && Array.isArray(p.runs)) ok = p.runs.every(hasRun);
    else if (p && 'slot' in p) ok = index >= 0 && argv[index + 1] === p.slot;
    else if (p && 'slotPrefix' in p) ok = index >= 0 && (argv[index + 1] || '').startsWith(p.slotPrefix);
    else if (p && 'mode' in p) ok = p.mode === builtMode;
    else if (p && typeof p.unprovable === 'string' && p.unprovable) ok = true;
    else if (typeof e.proofPrompt === 'string') ok = promptPrefix.includes(e.proofPrompt);
    else throw new Error(`settings report entry ${e.name} has no proof`);
    if (!ok) throw new Error(`settings report claims ${e.name}=${e.value} applied but the built argv does not carry it`);
  }
  return report;
}

function statusGroup(report, sessionId, escalation) {
  const group = (state) => report.filter((e) => e.state === state).map((e) =>
    ['skill', 'mcp'].includes(e.name) ? `${e.name}:${redactKeyShapes(String(e.value))}` : e.name).join(',') || '-';
  const session = typeof sessionId === 'string' && SESSION_ID_RE.test(sessionId) ? redactKeyShapes(sessionId) : '-';
  const flags = [escalation.runtime && 'runtime', escalation.model && 'model'].filter(Boolean).join(',') || '-';
  return `session=${session} applied=${group('applied')} ignored=${group('ignored')} unknown=${group('unknown')} escalate=${flags}`;
}

function reportLines(report) {
  return report.map((e) => `cross-ai: setting ${e.name}=${cleanSettingValue(e.name, e.value)} ${e.state}${e.reason ? ` reason=${e.reason}` : ''}${e.form ? ` form=${e.form}` : ''}`);
}

function withCodexKnobs(argv, ctx) {
  const out = [...argv];
  out.push(...(ctx.adds?.effort || []));
  if (ctx.adds) out.push(...ctx.adds.context);
  if (ctx.codexServiceTier) out.push('-c', `service_tier=${ctx.codexServiceTier}`);
  return out;
}

// --codex-sandbox workspace-write selects Codex's workspace-write sandbox mode, not a fixed path
// list (by default the cwd plus /tmp and $TMPDIR; the owner's Codex config can change the writable
// roots). Without the flag the bypass formula is unchanged.
function codexExecArgv(model, ctx) {
  const gate = ctx.codexSandbox
    ? ['--sandbox', 'workspace-write']
    : ['--dangerously-bypass-approvals-and-sandbox'];
  return [
    'exec', ...gate, '--skip-git-repo-check', '-C', ctx.cwd, '-m', model,
    '--json', '-o', ctx.outFile, '-',
  ];
}

function parseJson(s) { try { return JSON.parse(s); } catch { return null; } }
function* jsonLines(s) { for (const l of s.split('\n')) { const j = l.trim().startsWith('{') ? parseJson(l) : null; if (j) yield j; } }
function lastJson(s, pred) { let hit = null; for (const j of jsonLines(s)) if (pred(j)) hit = j; return hit; }

function parseOpencode(out) {
  let sessionId = null, error = null, lateError = null, turnDone = false, endMsg = null, endReason = null;
  const msgs = new Map();
  for (const ev of jsonLines(out)) {
    sessionId = sessionId || ev.sessionID || null;
    if (!turnDone && ev.type === 'text' && ev.part && typeof ev.part.text === 'string') {
      if (!msgs.has(ev.part.messageID)) msgs.set(ev.part.messageID, new Map());
      msgs.get(ev.part.messageID).set(ev.part.id, ev.part.text);
    }
    // Our turn ends at the first step finishing for a reason other than tool-calls/unknown; later steps answer injected turns (2.3.0 plan-mode reminder). opencode's run rule is "idle with no pending background job", so a background_wait after a stop means the agent continues: reopen the turn.
    if (ev.type === 'background_wait') { turnDone = false; endMsg = null; endReason = null; }
    if (!turnDone && ev.type === 'step_finish' && typeof ev.part?.reason === 'string' && !['tool-calls', 'unknown'].includes(ev.part.reason)) {
      turnDone = true;
      endMsg = ev.part.messageID ?? null;
      endReason = ev.part.reason;
    }
    if (ev.type === 'error') {
      const msg = JSON.stringify(ev.error || ev).slice(0, 400);
      if (turnDone) lateError = msg; else error = msg;
    }
  }
  // A turn cut short (length, content-filter, error) is not a complete answer.
  if (!error && ['length', 'content-filter', 'error'].includes(endReason)) error = `opencode step finished: ${endReason}`;
  // The message that ended the turn is the answer; the last message only when no step_finish was seen (older opencode).
  const parts = endMsg != null ? msgs.get(endMsg) : [...msgs.values()].pop();
  return { text: parts ? [...parts.values()].join('') : '', sessionId, error, lateError };
}

function normalize(text) {
  return text.replace(/\x1B\[[0-9;?]*[A-Za-z]/g, '').replace(/([.!?:])(#{1,6} \S)/g, '$1\n\n$2').trim() + '\n';
}

const INPUT_CAP = 65536;
// CSI color and cursor codes, and OSC sequences such as terminal hyperlinks (BEL or ST end).
const ANSI_RE = /\x1B\[[0-9;?]*[A-Za-z]|\x1B\][^\x07\x1B]*(?:\x07|\x1B\\)/g;
// Child text can echo credentials and identifiers. Key rules preserve the key and replace
// only its complete quoted or delimited value.
// Distinctive key shapes as one JSON line, kept equal to the shared Python table by a test.
const KEY_SHAPES = [["github_token","(?:(?<![A-Za-z0-9_])|(?<=\\\\[nrt])|(?<=%[0-9A-Fa-f]{2}))gh[pousr]_[A-Za-z0-9]{20,}"],["github_pat","(?:(?<![A-Za-z0-9_])|(?<=\\\\[nrt])|(?<=%[0-9A-Fa-f]{2}))github_pat_[A-Za-z0-9_]{20,}"],["google_api_key","(?:(?<![A-Za-z0-9_])|(?<=\\\\[nrt])|(?<=%[0-9A-Fa-f]{2}))AIza[0-9A-Za-z_-]{20,}"],["slack_token","(?:(?<![A-Za-z0-9_])|(?<=\\\\[nrt])|(?<=%[0-9A-Fa-f]{2}))(?:xox[abposre]|xapp|xwfp)-[A-Za-z0-9_-]{12,}"],["pem_private_key","-----BEGIN [A-Z0-9 ]+-----(?:[\\s\\S]{0,16384}?-----END [A-Z0-9 ]+-----|[A-Za-z0-9+/=\\r\\n]{0,16384})?"],["aws_access_key_id","(?:(?<![A-Za-z0-9_])|(?<=\\\\[nrt])|(?<=%[0-9A-Fa-f]{2}))(?:AKIA|ASIA|ABIA|ACCA)[A-Z0-9]{16}"],["gitlab_token","(?:(?<![A-Za-z0-9_])|(?<=\\\\[nrt])|(?<=%[0-9A-Fa-f]{2}))(?:glpat|gloas|gldt|glrtr?|glcbt|glptt|glft|glimt|glagent|glwt|glsoat|glffct)-[A-Za-z0-9_-]{16,}"],["xai_api_key","(?:(?<![A-Za-z0-9_])|(?<=\\\\[nrt])|(?<=%[0-9A-Fa-f]{2}))xai-[A-Za-z0-9]{16,}"],["jwt","(?:(?<![A-Za-z0-9_-])|(?<=\\\\[nrt])|(?<=%[0-9A-Fa-f]{2}))eyJ[A-Za-z0-9_-]{10,}\\.eyJ[A-Za-z0-9_-]{10,}\\.[A-Za-z0-9_-]{10,}"],["stripe_key","(?:(?<![A-Za-z0-9_])|(?<=\\\\[nrt])|(?<=%[0-9A-Fa-f]{2}))(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}"],["huggingface_token","(?:(?<![A-Za-z0-9_])|(?<=\\\\[nrt])|(?<=%[0-9A-Fa-f]{2}))hf_[A-Za-z0-9]{30,}"],["npm_token","(?:(?<![A-Za-z0-9_])|(?<=\\\\[nrt])|(?<=%[0-9A-Fa-f]{2}))npm_[A-Za-z0-9]{36,}"],["groq_key","(?:(?<![A-Za-z0-9_])|(?<=\\\\[nrt])|(?<=%[0-9A-Fa-f]{2}))gsk_[A-Za-z0-9]{20,}"],["sk_rk_key","(?:(?<![A-Za-z0-9_])|(?<=\\\\[nrt])|(?<=%[0-9A-Fa-f]{2}))(?:sk|rk)-[A-Za-z0-9_-]{8,}"]];
const SECRET_RES = KEY_SHAPES.map(([, source]) => new RegExp(source, 'g'));
// Bearer and Basic values go before the key shapes, so a key-shaped run inside one cannot
// stop the rule early; the other broad rules go after them.
const BEARER_BASIC_RES = [
  /(?<=\bBearer )[A-Za-z0-9._~+/=-]{8,}/gi,
  /(?<=\bBasic )[A-Za-z0-9+/=]{8,}/gi,
];
const BROAD_RES = [
  /conn:[0-9a-f]{8,}/gi,
  /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/gi,
];

// Every key shape is matched on the same text and overlapping matches merge into one span,
// so no row cuts into a token another row matches; text outside the spans is kept.
function redactKeyShapes(text) {
  const spans = SECRET_RES.flatMap((re) => [...text.matchAll(re)])
    .map((m) => [m.index, m.index + m[0].length])
    .sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const merged = [];
  for (const [start, end] of spans) {
    const lastEnd = merged.length ? merged[merged.length - 1][1] : -1;
    if (start < lastEnd) merged[merged.length - 1][1] = Math.max(lastEnd, end);
    else merged.push([start, end]);
  }
  let out = '';
  let pos = 0;
  for (const [start, end] of merged) {
    out += text.slice(pos, start) + '<redacted>';
    pos = end;
  }
  return out + text.slice(pos);
}

const KEY_VALUE_RE = /((?:\\?["']?)(?:api[_-]?key|token|secret|password|passwd|(?<=[?&])key)(?:\\?["']?)\s*(?:=>|[:=])\s*)(?:\\?"(?:\\\\.|[^"\\])*\\?"|\\?'(?:\\\\.|[^'\\])*\\?'|[^\s,"'\]}\];&]+)/gi;
const ID_VALUE_RE = /((?:\\?["']?)(?:account|connection|conn|org|organization|user|request|session|key)[_-]?id(?:\\?["']?)\s*(?:=>|[:=])\s*)(?:\\?"(?:\\\\.|[^"\\])*\\?"|\\?'(?:\\\\.|[^'\\])*\\?'|[^\s,"'\]}\];&]+)/gi;

function redactedValues(text) {
  const values = [];
  for (const re of [KEY_VALUE_RE, ID_VALUE_RE]) {
    re.lastIndex = 0;
    let match;
    while ((match = re.exec(String(text)))) {
      const removed = match[0].slice(match[1].length).replace(/^\\?["']|\\?["']$/g, '');
      if (removed) values.push(removed);
    }
  }
  return [...new Set(values)];
}

function replaceCopies(text, values) {
  let out = text;
  for (const value of values) {
    if (!value) continue;
    const escaped = value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    out = out.replace(new RegExp(`(?<![A-Za-z0-9])${escaped}(?![A-Za-z0-9])`, 'g'), '<redacted>');
  }
  return out;
}

function decodeUtf8(text) {
  if (typeof text !== 'string') return '';
  return Buffer.from(text, 'utf8').toString('utf8');
}

function cleanInput(text) { return decodeUtf8(text).replace(ANSI_RE, '').replace(/\u2019/g, "'"); }

function normalizeInput(text) {
  const decoded = cleanInput(text);
  return decoded.length > INPUT_CAP ? decoded.slice(-INPUT_CAP) : decoded;
}

function redactSecrets(line, extra = []) {
  let out = String(line);
  const copies = [...redactedValues(out), ...extra];
  // Key rules keep their key and quote; a shape rule has no capture group (the callback's second
  // argument is then the match offset, never a prefix), so it replaces the whole match.
  for (const re of [KEY_VALUE_RE, ID_VALUE_RE]) {
    re.lastIndex = 0;
    out = out.replace(re, (match, prefix) => {
      const value = match.slice(prefix.length);
      const quote = value.match(/^\\?["']/)?.[0] || '';
      return quote ? `${prefix}${quote}<redacted>${quote}` : `${prefix}<redacted>`;
    });
  }
  for (const re of BEARER_BASIC_RES) {
    re.lastIndex = 0;
    out = out.replace(re, '<redacted>');
  }
  out = redactKeyShapes(out);
  for (const re of BROAD_RES) {
    re.lastIndex = 0;
    out = out.replace(re, '<redacted>');
  }
  return replaceCopies(out, copies);
}

// One bounded line splitter per stream. The live watcher hooks this same buffer: one cap,
// one flush. `onLine` sees each complete line; `onPartial` sees the buffer before a trim,
// so an unterminated terminal line is recorded before a newline-free flood drops its head.
// D-17: each relayed line is normalized (ANSI stripped, decoded) before it is redacted, and
// `seen` (shared by a run's stdout and stderr relays) keeps every value redacted so far, so a
// later copy of it is redacted too. The live watcher still sees the raw line.
const SEEN_MIN_CHARS = 8;
// shortcut: the per-run set stops growing at 256 values; a flood of distinct keys past that
// relays later copies of the newer values per line only. Raise it if a capture needs more.
const SEEN_MAX = 256;
function makeLineRelay(hooks = {}) {
  let pending = '';
  const onLine = hooks.onLine || (() => {});
  const onPartial = hooks.onPartial || (() => {});
  const seen = hooks.seen || new Set();
  const emit = (line) => {
    onLine(line);
    const clean = normalizeInput(line);
    // A short value (`"token":"1"`) would turn every later `1` into <redacted>: per line only.
    for (const value of redactedValues(clean)) {
      if (value.length >= SEEN_MIN_CHARS && seen.size < SEEN_MAX) seen.add(value);
    }
    if (!hooks.quiet) log(redactSecrets(clean, [...seen]));
  };
  return {
    push(chunk) {
      pending += chunk;
      let nl = pending.indexOf('\n');
      while (nl >= 0) {
        emit(pending.slice(0, nl));
        pending = pending.slice(nl + 1);
        nl = pending.indexOf('\n');
      }
      if (pending.length > INPUT_CAP) {
        onPartial(pending);
        emit(pending.slice(0, INPUT_CAP));
        pending = '';
      }
    },
    flush() {
      if (!pending) return;
      emit(pending);
      pending = '';
    },
    partial() { return pending; },
  };
}

const NO_MATCH = { status: 'crash', rule: '-', label: 'none', source: null, line: null, raw: null };
const compiledRows = new Map();

function rowRegex(row) {
  let re = compiledRows.get(row);
  if (!re) {
    re = new RegExp(row.match, 'i');
    compiledRows.set(row, re);
  }
  return re;
}

// SPEC R3 (D-07): plain stdout is read only by rows that opt in with input: stdout; any keeps stderr and events.
function rowAdmits(row, source) {
  if (row.input === 'any') return source !== 'stdout';
  return row.input === source;
}

// `router` is the confirmed lane only. `unknown` is every other route (including
// router-inferred). `*` admits all.
function routeAdmits(row, route) {
  const want = row.route || '*';
  if (want === '*') return true;
  if (want === 'router') return route === 'router';
  if (want === 'unknown') return route !== 'router';
  return false;
}

// A provider prefix filters non-router lanes by model id. On a confirmed router lane the
// member is only in the body, so the column is informational and the row still admits.
function providerAdmits(row, route, model) {
  const provider = row.provider || '*';
  if (provider === '*') return true;
  if (route === 'router') return true;
  return String(model || '').toLowerCase().startsWith(provider);
}

function overlayHits(text) {
  if (!OVERLAY_IDS.size || overlayDisabled) return new Set();
  if (!overlayScript) {
    overlayScript = new vm.Script(
      'const found = [];\n' +
      'for (const row of rows) { if (new RegExp(row.match, "i").test(text)) found.push(row.id); }\n' +
      'found;',
    );
  }
  const rows = TABLE.filter((row) => OVERLAY_IDS.has(row.id))
    .map((row) => ({ id: row.id, match: row.match }));
  const started = performance.now();
  let found;
  try {
    found = overlayScript.runInContext(vm.createContext({ rows, text }), { timeout: OVERLAY_MATCH_MS });
  } catch (err) {
    overlaySpentMs += performance.now() - started;
    overlayDisabled = true;
    if (err && err.code === 'ERR_SCRIPT_EXECUTION_TIMEOUT') {
      log(`cross-ai: overlay disabled: match exceeded ${OVERLAY_MATCH_MS} ms`);
    } else {
      log(`cross-ai: overlay disabled: match failed (${err && err.message})`);
    }
    return new Set();
  }
  overlaySpentMs += performance.now() - started;
  if (overlaySpentMs >= OVERLAY_CALL_BUDGET_MS) {
    overlayDisabled = true;
    const spent = Math.round(overlaySpentMs);
    log(`cross-ai: overlay disabled: matching used ${spent} ms this call ` +
      `(budget ${OVERLAY_CALL_BUDGET_MS} ms)`);
  }
  return new Set(Array.isArray(found) ? found : []);
}

// SPEC R3: the plain lines of a failed attempt's stdout. JSON is decided per complete, uncapped line (any JSON value is dropped), then the INPUT_CAP tail is taken and the partial line the cap cut is dropped, so a clipped JSON answer never becomes plain text.
function plainStdoutText(stdout) {
  const kept = cleanInput(stdout || '').split('\n').filter((line) => line.trim() !== '' && parseJson(line.trim()) === null);
  const text = kept.join('\n');
  if (text.length <= INPUT_CAP) return text;
  const tail = text.slice(-INPUT_CAP);
  const cut = tail.indexOf('\n');
  return cut < 0 ? '' : tail.slice(cut + 1);
}

function classifyStop({ cli, routerLane, route, model, stderr, events, eventRaw, stdout }, table = TABLE) {
  const callRoute = route ?? (routerLane ? 'router' : 'unknown');
  const lane = routerLane ?? (callRoute === 'router');
  const callModel = model || '';
  const normalizedStderr = normalizeInput(stderr || '');
  const sources = [['stderr', normalizedStderr, null]];
  for (let i = 0; i < (events || []).length; i += 1) {
    sources.push(['event', normalizeInput(events[i] || ''), eventRaw?.[i] ?? null]);
  }
  const plain = plainStdoutText(stdout); if (plain) sources.push(['stdout', plain, null]);
  const overlayByText = new Map();
  for (const row of table) {
    if (row.cli !== '*' && row.cli !== cli) continue;
    if (!routeAdmits(row, callRoute) || !providerAdmits(row, callRoute, callModel)) continue;
    const overlayRow = OVERLAY_IDS.has(row.id);
    for (const [source, text, raw] of sources) {
      if (!text || !rowAdmits(row, source)) continue;
      let match = null;
      if (overlayRow) {
        let hits = overlayByText.get(text);
        if (!hits) {
          hits = overlayHits(text);
          overlayByText.set(text, hits);
        }
        if (!hits.has(row.id)) continue;
        match = { index: text.search(rowRegex(row)) };
      } else {
        const re = rowRegex(row);
        re.lastIndex = 0;
        match = re.exec(text);
        if (!match) continue;
      }
      const start = text.lastIndexOf('\n', match.index) + 1;
      const end = text.indexOf('\n', match.index);
      const line = source === 'stderr' || source === 'stdout' ? text.slice(start, end < 0 ? undefined : end) : text;
      const status = lane && row.routerClass === 'quota' ? 'quota' : row.class;
      return { status, rule: row.id, label: row.label, source, line, raw: raw || line };
    }
  }
  return { ...NO_MATCH };
}

function pushStr(out, value) {
  if (typeof value === 'string' && value) out.push(value);
  else if (typeof value === 'number') out.push(String(value));
}

function nestedBodyFields(raw) {
  const out = [];
  if (typeof raw !== 'string' || !raw) return out;
  out.push(raw);
  const body = parseJson(raw);
  if (!body || typeof body !== 'object') return out;
  const inner = body.error && typeof body.error === 'object' ? body.error : null;
  for (const obj of [inner, body]) {
    if (!obj) continue;
    pushStr(out, obj.type);
    pushStr(out, obj.code);
    pushStr(out, obj.message);
  }
  return out;
}

function opencodeEventStrings(ev) {
  const out = [];
  const err = ev.error && typeof ev.error === 'object' ? ev.error : {};
  pushStr(out, err.message);
  if (err.status !== undefined && err.status !== null) out.push(`status ${err.status}`);
  if (typeof err.type === 'string' && err.type) out.push(`opencode-type:${err.type}`);
  const response = err.response && typeof err.response === 'object' ? err.response : null;
  if (response) out.push(...nestedBodyFields(response.body));
  pushStr(out, err.name);
  const data = err.data && typeof err.data === 'object' ? err.data : null;
  if (data) {
    pushStr(out, data.message);
    if (data.statusCode !== undefined && data.statusCode !== null) {
      out.push(`status ${data.statusCode}`);
    }
  }
  return out;
}

function codexEventStrings(ev) {
  const out = [];
  if (ev.type === 'error') pushStr(out, ev.message);
  if (ev.type === 'turn.failed') {
    const err = ev.error && typeof ev.error === 'object' ? ev.error : null;
    pushStr(out, err ? err.message : null);
  }
  return out;
}

// 38.1 D-08: claude's structured fields feed the bare status-code rows, as opencode's error status does; cursor has no such capture, so only claude asks for them.
function resultEventString(out, withFields = false) {
  const ev = lastJson(out, (j) => j.type === 'result');
  if (!ev || !ev.is_error) return [];
  const found = typeof ev.result === 'string' && ev.result ? [ev.result] : [];
  if (withFields) {
    const code = ev.api_error_status;
    if (Number.isInteger(code) && code >= 100 && code <= 599) found.push(`status ${code}`);
    if (typeof ev.api_error_type === 'string' && ev.api_error_type) found.push(ev.api_error_type);
  }
  return found;
}

function eventIsTerminal(cli, ev) {
  if (cli === 'opencode') return ev.type === 'error';
  if (cli === 'codex') return ev.type === 'turn.failed';
  if (cli === 'cursor' || cli === 'claude') return ev.type === 'result' && Boolean(ev.is_error);
  return false;
}

// terminalOnly (25-04): live watching keeps only terminal events. A bare codex `error` is
// recorded after the fact, never a live kill (ruling Q1); only `turn.failed` kills.
function extractEvents(cli, stdout, terminalOnly = false) {
  const out = [];
  const text = typeof stdout === 'string' ? stdout : '';
  if (cli === 'opencode') {
    for (const ev of jsonLines(text)) {
      if (ev.type !== 'error') continue;
      if (terminalOnly && !eventIsTerminal(cli, ev)) continue;
      out.push(...opencodeEventStrings(ev));
    }
  } else if (cli === 'codex') {
    for (const ev of jsonLines(text)) {
      if (terminalOnly && !eventIsTerminal(cli, ev)) continue;
      out.push(...codexEventStrings(ev));
    }
  } else if (cli === 'cursor' || cli === 'claude') {
    if (terminalOnly) {
      const ev = lastJson(text, (j) => j.type === 'result');
      if (ev && eventIsTerminal(cli, ev)) out.push(...resultEventString(text));
    } else {
      out.push(...resultEventString(text, cli === 'claude'));
    }
  }
  return out;
}

function eventsWithRaw(cli, stdout, terminalOnly = false) {
  const events = [];
  const eventRaw = [];
  for (const raw of String(stdout || '').split('\n')) {
    const extracted = extractEvents(cli, raw, terminalOnly);
    for (const event of extracted) {
      events.push(event);
      eventRaw.push(raw);
    }
  }
  return { events, eventRaw };
}

// SPEC R4 (D-09): whole seconds from the router's "(reset after <n>h <n>m <n>s)"; parts add up in any order, a repeated unit or any other form is absent (null). Shown as an upstream field; statedResetS reads it once for the reset check (R5), never as a wait by itself.
function resetAfterSeconds(text) {
  const m = /\(reset after ([^)]*)\)/i.exec(String(text || ''));
  if (!m) return null;
  const seen = new Set();
  let total = 0;
  for (const part of m[1].trim().split(/\s+/)) {
    const p = /^(\d{1,6})([hms])$/.exec(part);
    if (!p || seen.has(p[2])) return null;
    seen.add(p[2]);
    total += Number(p[1]) * { h: 3600, m: 60, s: 1 }[p[2]];
  }
  return total;
}

function upstreamFields(raw) {
  const text = String(raw || '');
  const start = text.indexOf('{');
  // shortcut: one parse from the first object opener; captures with a prose brace prefix
  // require a dedicated fixture before broadening this bounded parser.
  const outer = start < 0 ? null : parseJson(text.slice(start));
  const result = {};
  if (outer && typeof outer === 'object' && !Array.isArray(outer)) {
    const body = outer.error?.response?.body;
    const nested = typeof body === 'string' ? parseJson(body) : null;
    const objects = [outer, outer.error, nested, nested?.error, outer.recovery_hint];
    const keys = ['retry_after', 'reset_at', 'retry_after_seconds', 'resetsAt', 'reset_seconds', 'retryAfterMs'];
    for (const key of keys) {
      for (const object of objects) {
        if (!object || typeof object !== 'object' || !Object.hasOwn(object, key)) continue;
        const value = object[key];
        if (value === null || ['string', 'number', 'boolean'].includes(typeof value)) {
          result[key] = value;
          break;
        }
      }
    }
  }
  const reset = resetAfterSeconds(text);
  if (reset !== null) result.reset_after_s = reset;
  return Object.keys(result).length ? result : null;
}

function capCodePoints(text, n) { return Array.from(String(text)).slice(0, n).join(''); }

function upstreamOf(cls, r, cli) {
  let raw = r.liveHit?.raw || cls?.raw || '';
  if (!raw) {
    const stderr = String(r.stderr || '').split('\n').filter((line) => line.trim());
    raw = stderr.at(-1) || '';
  }
  if (!raw) {
    const terminal = eventsWithRaw(cli, r.stdout || '', true);
    raw = terminal.eventRaw.at(-1) || '';
  }
  if (!raw) return null;
  const extras = [...new Set([...redactedValues(normalizeInput(raw)), ...(r.redacted || [])])];
  const fields = upstreamFields(raw);
  const safeFields = fields && Object.fromEntries(Object.entries(fields).map(([key, value]) => [
    key, typeof value === 'string' ? redactSecrets(replaceCopies(value, extras), extras) : value,
  ]));
  return {
    raw,
    body: capCodePoints(redactSecrets(normalizeInput(raw), extras), 2000),
    fields: safeFields,
  };
}

// Flag, then an explicit CONFIG boolean, then the name heuristic, else unknown (D-05).
// Only `router` is a confirmed lane: an inferred route stays advisory.
function routeOf(cli, model, routes) {
  const flagged = routes && Object.hasOwn(routes, cli) ? routes[cli] : undefined;
  if (flagged === 'router' || flagged === 'unknown') return flagged;
  const baked = ownValue(CONFIG.routerBacked, cli);
  // routerBacked is per CLI and was confirmed for its pinned model: another model on that CLI
  // is not the confirmed lane (ponytail review, 25).
  const pinned = ownValue(CONFIG.models, cli);
  if (baked === true) return pinned && pinned !== model ? 'unknown' : 'router';
  if (baked === false) return 'unknown';
  const id = String(model || '').toLowerCase();
  if (ROUTER_HINTS.some((hint) => id.includes(hint))) return 'router-inferred';
  return 'unknown';
}

function confirmedRoute(route) {
  return route === 'router';
}

function which(bin, envPath = process.env.PATH || '') {
  if (bin.includes('/')) return isExec(bin) ? path.resolve(bin) : null;
  return pathHits(bin, envPath).next().value ?? null;
}
function* pathHits(bin, envPath = process.env.PATH || '') {
  for (const dir of envPath.split(path.delimiter)) {
    // An empty segment is the cwd, as POSIX shells resolve it (U-5, informational).
    const p = path.resolve(dir || '.', bin);
    if (isExec(p)) yield p;
  }
}
function isExec(p) { try { fs.accessSync(p, fs.constants.X_OK); return fs.statSync(p).isFile(); } catch { return false; } }

// A bare `agent` is cursor only when it really is cursor-agent (D-02). Anything else
// (another CLI that ships the same name) is not acceptable; a realpath error is the same.
// D-09: every PATH entry is scanned for the guarded name; another CLI's agent earlier on PATH no longer hides cursor's.
function resolveBin(rt, envPath) {
  for (const b of rt.bins) {
    if (b !== 'agent') {
      const found = which(b, envPath);
      if (found) return found;
      continue;
    }
    for (const found of pathHits(b, envPath)) {
      let base = '';
      try { base = path.basename(fs.realpathSync(found)); } catch { base = ''; }
      if (base === 'cursor-agent') return found;
    }
  }
  return null;
}

function ownTimeout(cfgPath) {
  // No root: the timeout read keeps following a symlinked config.json (gsd-tools config-get
  // parity). A malformed file still reads as absent.
  return workflowValue(cfgPath, 'cross_ai_timeout').value;
}
// Same ladder as gsd-core readScopedConfigValue (planning-workspace.cjs), which config-get
// follows: the scoped config's own key, then the root key only under GSD_WORKSTREAM; a
// GSD_PROJECT/GSD_WORKSTREAM with a path separator or `..` reads as absent.
// shortcut: the stored active-workstream pointer is not read (only the env), upgrade when
// GSD starts running cross_ai_command without exporting GSD_WORKSTREAM.
function scopedConfigPaths(cwd, env) {
  const ws = (env.GSD_WORKSTREAM || '').trim();
  const project = (env.GSD_PROJECT || '').trim();
  if (/[/\\]|\.\./.test(ws) || /[/\\]|\.\./.test(project)) return [];
  const root = path.join(cwd, '.planning');
  const scoped = path.join(root, project, ws ? path.join('workstreams', ws) : '');
  const paths = [path.join(scoped, 'config.json')];
  if (ws) paths.push(path.join(root, 'config.json'));
  return paths;
}
// The active scope key (D-26): the scoped config folder's path under .planning/ with '/'
// separators, the same rule as scopedConfigPaths, so a scope may hold [ ] " or spaces; the
// quote-aware header constants read such a scope table back (C2-2). No scope means no table.
function retryScope(cwd, env) {
  const ws = (env.GSD_WORKSTREAM || '').trim();
  const project = (env.GSD_PROJECT || '').trim();
  if (/[/\\]|\.\./.test(ws) || /[/\\]|\.\./.test(project)) return '';
  const parts = [];
  if (project) parts.push(project);
  if (ws) parts.push('workstreams', ws);
  return parts.join('/');
}
function liveOuterTimeoutS(cwd, env) {
  const paths = scopedConfigPaths(cwd, env);
  let t = paths.length ? ownTimeout(paths[0]) : undefined;
  if (t === undefined && paths.length > 1) t = ownTimeout(paths[1]);
  const n = Number(t);
  return t !== undefined && t !== null && Number.isFinite(n) && n > 0 ? n : GSD_DEFAULT_TIMEOUT_S;
}
// A missing file is silent and is tested before realpathSync, which throws ENOENT when
// .planning itself is absent (the common case). With rootDir, the file's real path must stay
// inside the root's real path: a stow-style symlink out of it is refused by name.
function confinementError(file, rootDir) {
  let realFile;
  let realRoot;
  try {
    realFile = fs.realpathSync(file);
    realRoot = fs.realpathSync(rootDir);
  } catch (e) {
    return `unreadable (${e.code || e.message})`;
  }
  const rel = path.relative(realRoot, realFile);
  if (rel.startsWith('..') || path.isAbsolute(rel)) {
    return `resolves outside ${rootDir} (retry config reads are confined; a symlink out of ` +
      'it is not followed)';
  }
  return null;
}

// A config read never blocks or fills memory before the deadlines exist.
const CONFIG_READ_MAX = 1024 * 1024;

// A config read refuses invalid UTF-8 rather than replace bytes (Python's ConfigError does the
// same). Existence, confinement, file type and size are checked here once, for JSON and TOML.
function readConfigText(file, rootDir = null) {
  if (!fs.existsSync(file)) return { text: null };
  if (rootDir != null) {
    const error = confinementError(file, rootDir);
    if (error) return { error };
  }
  let stat;
  try { stat = fs.statSync(file); } catch (e) { return { error: `unreadable (${e.code || e.message})` }; }
  if (!stat.isFile()) return { error: 'not a regular file' };
  if (stat.size > CONFIG_READ_MAX) return { error: `larger than ${CONFIG_READ_MAX} bytes` };
  let bytes;
  try { bytes = fs.readFileSync(file); } catch (e) { return { error: `unreadable (${e.code || e.message})` }; }
  try {
    return { text: new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bytes) };
  } catch {
    return { error: 'not valid UTF-8' };
  }
}
function readJsonObject(file, rootDir = null) {
  const read = readConfigText(file, rootDir);
  if (read.error) return { error: read.error };
  if (read.text === null) return { obj: null };
  const parsed = parseJson(read.text);
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return { error: 'not a JSON object' };
  return { obj: parsed };
}

// The TOML subset reader (D-07). Header names are quote-aware (C2-2): a double-quoted segment may
// hold [ ] # or an escaped quote. The line splicer of Plan 04 matches headers through these names.
const TOML_ARRAY_HEADER_RE = /^\s*\[\[((?:[^\[\]"]|"(?:[^"\\]|\\.)*")+)\]\]\s*(#.*)?$/;
const TOML_TABLE_HEADER_RE = /^\s*\[((?:[^\[\]"]|"(?:[^"\\]|\\.)*")+)\]\s*(#.*)?$/;
const TOML_NUMBER_RE = /^[+-]?(0|[1-9]\d*)(\.\d+)?([eE][+-]?\d+)?/;
const TOML_TAIL_RE = /^\s*(#.*)?$/;
const TOML_ESCAPES = Object.freeze({ '"': '"', '\\': '\\', n: '\n', t: '\t', r: '\r', b: '\b', f: '\f' });

// A TOML basic string whose opening quote is s[i]: { value, end } with end just past the closing
// quote, or null for an unknown escape, a bad \u or \U code point, a raw control character or no
// closing quote.
function scanBasicString(s, i) {
  let out = '';
  let j = i + 1;
  while (j < s.length) {
    const c = s[j];
    if (c === '"') return { value: out, end: j + 1 };
    if (c === '\\') {
      const e = s[j + 1];
      if (e === 'u' || e === 'U') {
        const width = e === 'u' ? 4 : 8;
        const hex = s.slice(j + 2, j + 2 + width);
        if (!new RegExp(`^[0-9A-Fa-f]{${width}}$`).test(hex)) return null;
        const code = parseInt(hex, 16);
        if (code > 0x10ffff || (code >= 0xd800 && code <= 0xdfff)) return null;
        out += String.fromCodePoint(code);
        j += 2 + width;
      } else if (Object.hasOwn(TOML_ESCAPES, e)) {
        out += TOML_ESCAPES[e];
        j += 2;
      } else {
        return null;
      }
      continue;
    }
    const code = c.charCodeAt(0);
    if ((code < 0x20 && c !== '\t') || code === 0x7f) return null;
    out += c;
    j += 1;
  }
  return null;
}

// A dotted header name split into its keys: a quoted segment is decoded by scanBasicString, a bare
// segment must be a key, and any other segment (empty, a literal 'quoted' name) makes it null.
function splitTomlName(name) {
  const pieces = [];
  let cur = '';
  let quoted = false;
  for (let i = 0; i < name.length; i += 1) {
    const c = name[i];
    if (quoted && c === '\\') { cur += c + (name[i + 1] ?? ''); i += 1; continue; }
    if (c === '"') quoted = !quoted;
    if (c === '.' && !quoted) { pieces.push(cur); cur = ''; continue; }
    cur += c;
  }
  pieces.push(cur);
  const out = [];
  for (const piece of pieces) {
    const seg = piece.trim();
    if (seg.startsWith('"')) {
      const got = scanBasicString(seg, 0);
      if (!got || got.end !== seg.length) return null;
      out.push(got.value);
    } else if (/^[A-Za-z0-9_-]+$/.test(seg)) {
      out.push(seg);
    } else {
      return null;
    }
  }
  return out;
}

function isPlainObject(v) {
  return v !== null && typeof v === 'object' && !Array.isArray(v);
}

// A one-line array of basic strings and numbers, closed on the same line; a trailing comma is
// allowed. { value, end } or null (nested arrays, inline tables, literal strings, a missing bracket).
function scanTomlArray(s) {
  const items = [];
  let i = 1;
  const skip = () => { while (s[i] === ' ' || s[i] === '\t') i += 1; };
  skip();
  if (s[i] === ']') return { value: items, end: i + 1 };
  for (;;) {
    skip();
    if (s[i] === '"') {
      const got = scanBasicString(s, i);
      if (!got) return null;
      items.push(got.value);
      i = got.end;
    } else {
      const num = TOML_NUMBER_RE.exec(s.slice(i));
      if (!num) return null;
      items.push(Number(num[0]));
      i += num[0].length;
    }
    skip();
    if (s[i] === ',') {
      i += 1;
      skip();
      if (s[i] === ']') return { value: items, end: i + 1 };
    } else if (s[i] === ']') {
      return { value: items, end: i + 1 };
    } else {
      return null;
    }
  }
}

// One value after `=`: a basic string, true or false, a number or a one-line array of strings and
// numbers, then only spaces and an optional comment. Anything else (a date, an inline table, a
// literal string, a multi-line string) is an error.
function scanTomlValue(text) {
  const s = text.replace(/^\s+/, '');
  if (s.startsWith('"""')) return { error: 'multi-line string' };
  let value;
  let end;
  if (s.startsWith('"')) {
    const got = scanBasicString(s, 0);
    if (!got) return { error: 'unsupported value' };
    ({ value, end } = got);
  } else if (s.startsWith('[')) {
    const got = scanTomlArray(s);
    if (!got) return { error: 'unsupported value' };
    ({ value, end } = got);
  } else {
    const bool = /^(true|false)(?![A-Za-z0-9_])/.exec(s);
    const num = bool ? null : TOML_NUMBER_RE.exec(s);
    if (bool) {
      value = bool[1] === 'true';
      end = bool[0].length;
    } else if (num) {
      value = Number(num[0]);
      end = num[0].length;
    } else {
      return { error: 'unsupported value' };
    }
  }
  return TOML_TAIL_RE.test(s.slice(end)) ? { value } : { error: 'unsupported value' };
}

// Table or key names that would reach Object.prototype through a plain object (IN-51).
const TOML_RESERVED_NAMES = new Set(['__proto__', 'constructor', 'prototype']);

// The multi-line string delimiter ('"""' or "'''") still open at the end of an opaque line, or
// null: `open` is the delimiter already open at its start. A comment and one-line strings are
// skipped, so a `'''` inside either does not count (WR-51).
function tomlOpenDelimiter(line, open) {
  let delim = open;
  let i = 0;
  while (i < line.length) {
    const c = line[i];
    if (delim) {
      if (delim === '"""' && c === '\\') i += 2;
      else if (line.startsWith(delim, i)) { delim = null; i += 3; } else i += 1;
    } else if (c === '#') {
      break;
    } else if (line.startsWith('"""', i) || line.startsWith("'''", i)) {
      delim = line.slice(i, i + 3);
      i += 3;
    } else if (c === '"' || c === "'") {
      i += 1;
      while (i < line.length && line[i] !== c) i += c === '"' && line[i] === '\\' ? 2 : 1;
      i += 1;
    } else {
      i += 1;
    }
  }
  return delim;
}

// Parses the TOML subset (D-07) and keeps only the runner subtree: { obj: { runner: {...} } }, or
// { error: 'line N: <reason>' } for anything outside the subset or any table/value collision in
// either order. [[lanes.*]] and every other table are opaque: their lines are skipped, and a
// multi-line string inside [lanes] is skipped until its delimiter closes (elsewhere it is refused).
function parseTomlSubset(text) {
  const obj = {};
  const defined = new Set();
  let table = null;
  let tableName = '';
  let seenHeader = false;
  let inLanes = false;
  let openString = null;
  const lines = text.split(/\r?\n/);
  for (let idx = 0; idx < lines.length; idx += 1) {
    const n = idx + 1;
    const line = lines[idx];
    if (openString) {
      openString = tomlOpenDelimiter(line, openString);
      continue;
    }
    const trimmed = line.trim();
    if (trimmed === '' || trimmed.startsWith('#')) continue;
    const arr = TOML_ARRAY_HEADER_RE.exec(line);
    const hdr = arr || TOML_TABLE_HEADER_RE.exec(line);
    if (hdr) {
      const segs = splitTomlName(hdr[1]);
      if (!segs) return { error: `line ${n}: unsupported table name` };
      if (arr && segs[0] !== 'lanes') return { error: `line ${n}: array of tables outside [lanes]` };
      table = null;
      seenHeader = true;
      inLanes = segs[0] === 'lanes';
      if (arr || segs[0] !== 'runner') continue;
      if (segs.some((s) => TOML_RESERVED_NAMES.has(s))) return { error: `line ${n}: reserved table name` };
      const name = segs.join('.');
      if (defined.has(name)) return { error: `line ${n}: duplicate table ${name}` };
      defined.add(name);
      let node = obj;
      for (let k = 0; k < segs.length; k += 1) {
        if (!Object.hasOwn(node, segs[k])) {
          node[segs[k]] = {};
        } else if (!isPlainObject(node[segs[k]])) {
          return { error: `line ${n}: table ${name} conflicts with key ${segs.slice(0, k + 1).join('.')}` };
        }
        node = node[segs[k]];
      }
      table = node;
      tableName = name;
      continue;
    }
    if (table === null) {
      // A root-level `runner.x = 1` or `runner = { }` names the runner subtree outside a header
      // (CR-51): refuse it, so it is never ignored and a migration never appends a second table.
      if (!seenHeader && /^\s*(?:runner|"runner"|'runner')\s*[.=]/.test(line)) {
        return { error: `line ${n}: runner keys outside a [runner] table` };
      }
      openString = tomlOpenDelimiter(line, null);
      if (openString && !inLanes) return { error: `line ${n}: multi-line string` };
      continue;
    }
    const kv = /^\s*([A-Za-z0-9_-]+)\s*=\s*(.*)$/.exec(line);
    if (!kv) return { error: `line ${n}: not a key = value line` };
    const key = kv[1];
    if (TOML_RESERVED_NAMES.has(key)) return { error: `line ${n}: reserved key ${key}` };
    if (Object.hasOwn(table, key)) {
      if (isPlainObject(table[key])) return { error: `line ${n}: key ${key} conflicts with table ${tableName}.${key}` };
      return { error: `line ${n}: duplicate key ${key}` };
    }
    const got = scanTomlValue(kv[2]);
    if (got.error) return { error: `line ${n}: ${got.error}` };
    table[key] = got.value;
  }
  if (openString) return { error: `line ${lines.length}: multi-line string not closed` };
  return { obj };
}

function readTomlSubset(file, rootDir = null) {
  const read = readConfigText(file, rootDir);
  if (read.error) return { error: read.error };
  if (read.text === null) return { obj: null };
  return parseTomlSubset(read.text);
}

// ${XDG_CONFIG_HOME}/ai-kit or ${HOME}/.config/ai-kit: the one user-dir rule (D-19, D-27; SPEC
// R10), shared with config_io, local_secrets, jev_review and tools/common_config. An absolute
// XDG_CONFIG_HOME (surrounding whitespace removed) is used; a relative or blank one is ignored,
// then HOME must be absolute. Otherwise there is no user dir (null). No ambient home lookup, so
// every copy gives the same answer for an unset or empty HOME.
function aiKitConfigDir(env) {
  const xdg = (env.XDG_CONFIG_HOME || '').trim();
  if (xdg && path.isAbsolute(xdg)) return path.join(xdg, 'ai-kit');
  const home = env.HOME || '';
  return path.isAbsolute(home) ? path.join(home, '.config', 'ai-kit') : null;
}

function loadOverlay(env) {
  const root = aiKitConfigDir(env);
  if (root === null) {
    log('cross-ai: no absolute home directory; the user overlay is skipped');
    return [];
  }
  const file = path.join(root, 'cross-ai-errors.json');
  if (!fs.existsSync(file)) return [];
  // Confinement, file type and size are checked before any byte is read: a FIFO or a huge file
  // must never block or fill memory before the deadlines exist.
  const confined = confinementError(file, root);
  if (confined) {
    log(`cross-ai: overlay ignored (${file}): ${confined}`);
    return [];
  }
  let stat;
  try { stat = fs.statSync(file); } catch (e) {
    log(`cross-ai: overlay ignored (${file}): unreadable (${e.code || e.message})`);
    return [];
  }
  if (!stat.isFile()) {
    log(`cross-ai: overlay ignored (${file}): not a regular file`);
    return [];
  }
  if (stat.size > 65536) {
    log(`cross-ai: overlay ignored (${file}): larger than 65536 bytes`);
    return [];
  }
  const parsed = parseJson(readOr(file, ''));
  if (!Array.isArray(parsed)) {
    log(`cross-ai: overlay ignored (${file}): not a JSON array`);
    return [];
  }
  const seen = new Set(PATTERNS.map((row) => row.id));
  const accepted = [];
  parsed.forEach((row, index) => {
    const id = row && typeof row.id === 'string' ? row.id : `#${index}`;
    const reason = validateRow(row, RUNTIMES);
    if (reason) {
      log(`cross-ai: overlay row ${id} refused (${file}): ${reason}`);
      return;
    }
    if (seen.has(row.id)) {
      log(`cross-ai: overlay row ${row.id} refused (${file}): id already used`);
      return;
    }
    seen.add(row.id);
    accepted.push(row);
  });
  OVERLAY_IDS = new Set(accepted.map((row) => row.id));
  if (accepted.length) log(`cross-ai: overlay ${accepted.length} rows`);
  return accepted;
}
function workflowValue(cfgPath, key, rootDir = null) {
  const read = readJsonObject(cfgPath, rootDir);
  if (read.error) return { value: undefined, error: read.error };
  const cfg = read.obj;
  const wf = cfg && typeof cfg === 'object' && !Array.isArray(cfg) ? cfg.workflow : null;
  if (!wf || typeof wf !== 'object' || Array.isArray(wf) || !Object.hasOwn(wf, key)) {
    return { value: undefined };
  }
  return { value: wf[key] };
}
function innerTimeoutS(outer) {
  // D-29: inner deadline sits strictly below outer (margin floor at least 1s).
  return outer - Math.max(1, Math.min(TIMEOUT_MARGIN_S, Math.floor(outer / 5)));
}
function resolveDeadline(cwd, env, o) {
  // D-18: an explicit outer deadline replaces both the GSD lookup and the CONFIG cap.
  const outer = o.outerTimeout != null
    ? o.outerTimeout
    : Math.min(CONFIG.outerTimeoutS, liveOuterTimeoutS(cwd, env));
  if (outer < 2) return { error: 'cross-ai: outer timeout must be at least 2s' };
  const innerDefault = innerTimeoutS(outer);
  const inner = o.timeout != null ? Math.min(innerDefault, o.timeout) : innerDefault;
  return { outer, inner, innerDefault };
}
function logDeadline(cwd, env, o) {
  const d = resolveDeadline(cwd, env, o);
  if (d.error) return d;
  log(`cross-ai: deadline ${d.inner}s (outer ${d.outer}s)`);
  return d;
}

// Kept on purpose (38 R10): clampAttemptTimeout (read by attemptCapMs), clampCapS (the 4-hour bound, T-25-13),
// liveMatch and armLimit (the live limit watcher, CR-01) are live code, not Phase 25 leftovers.
// A per-attempt cap is 0 (none) or 10..1800 s.
function clampAttemptTimeout(value) {
  const n = Math.trunc(Number(value));
  if (!Number.isFinite(n) || n <= 0) return 0;
  return Math.min(1800, Math.max(10, n));
}
// SPEC 4-hour prohibition: the cap never exceeds 14400 s, and the cooldown never exceeds it.
function clampCapS(value) {
  const n = Math.trunc(Number(value));
  if (!Number.isFinite(n) || n < 0) return 0;
  return Math.min(14400, n);
}
// judged (D-03): healthy review lanes took 288 to 579 s in total, observed stalls printed nothing for 1800 s, and GSD asks the owner after 10 minutes without commits.
const IDLE_DEFAULT_S = 900;
const IDLE_MAX_S = 86400;
// SPEC R1 cannot-fire note; compared in ms by the callers, shown in whole seconds (plan 38-11 prints it against the live attempt cap).
function idleBudgetNote(idleS, budgetMs) { return `cross-ai: note: idle timeout ${idleS}s is not below the attempt budget of ${Math.floor(budgetMs / 1000)}s; it cannot fire before the deadline`; }
// SPEC R1 / D-01: pure; the call wins over CONFIG, 0 is off; checkS is the execute tree-poll interval (R2), not the output clock.
function planIdle(call, config, role) {
  const notices = [];
  let idleS = 0;
  if (call.idleTimeout !== null && call.idleTimeout !== undefined) {
    idleS = call.idleTimeout === 'default' ? IDLE_DEFAULT_S : call.idleTimeout;
  } else {
    const baked = config.idleTimeoutS ?? 0;
    if (Number.isInteger(baked) && baked >= 0 && baked <= IDLE_MAX_S) idleS = baked;
    else notices.push('cross-ai: note: CONFIG.idleTimeoutS is not an integer from 0 to 86400; the idle watchdog is off');
  }
  if (idleS === 0) return { idleS: 0, checkS: 0, pollTree: false, notices };
  if (idleS < 60) notices.push(`cross-ai: note: idle timeout ${idleS}s is under 60s; a slow, quiet model may be ended`);
  if (Number.isFinite(call.budgetMs) && idleS * 1000 >= call.budgetMs) notices.push(idleBudgetNote(idleS, call.budgetMs));
  return { idleS, checkS: Math.min(60, Math.max(1, Math.floor(idleS / 10))), pollTree: role === 'execute', notices };
}
// Last source of the retry cascade. Never validated and never refused: a cap below a default
// hard wait stops the hard tier first (25.1-03 hardWaitFor), it does not drop a key.
const RETRY_DEFAULTS = Object.freeze({
  base_s: 1, factor: 1.5, max_retries: 5, session_resets: 1,
  hard_waits_s: Object.freeze([60, 300]), hard_every_s: 600,
});
const RETRY_KEYS = ['base_s', 'factor', 'max_retries', 'session_resets', 'hard_waits_s', 'hard_every_s'];

function validateRetryKey(key, value, capS) {
  if (!RETRY_KEYS.includes(key)) return 'unknown key';
  const finite = typeof value === 'number' && Number.isFinite(value);
  if (key === 'base_s') {
    if (!finite) return 'wrong type';
    if (value < 0 || value > 60) return 'out of bounds (0..60)';
    return null;
  }
  if (key === 'factor') {
    if (!finite) return 'wrong type';
    if (value < 1 || value > 3) return 'out of bounds (1.0..3.0)';
    return null;
  }
  if (key === 'max_retries' || key === 'session_resets') {
    const hi = key === 'max_retries' ? 10 : 3;
    if (!Number.isInteger(value)) return typeof value === 'number' ? 'not an integer' : 'wrong type';
    if (value < 0 || value > hi) return `out of bounds (0..${hi})`;
    return null;
  }
  if (key === 'hard_every_s') {
    if (!Number.isInteger(value)) return typeof value === 'number' ? 'not an integer' : 'wrong type';
    if (value !== 0 && (value < 60 || value > capS)) return `out of bounds (0 or 60..${capS})`;
    return null;
  }
  if (!Array.isArray(value)) return 'wrong type';
  if (value.length < 1 || value.length > 6) return 'out of bounds (1..6 entries)';
  for (const entry of value) {
    if (!Number.isInteger(entry)) return 'non-integer entry';
    if (entry < 0 || entry > capS) return `entry out of bounds (0..${capS})`;
  }
  return null;
}

// Read once per call from ai-kit's config.toml layers (D-13): project .aikit/config.toml, then the
// user config.toml, then CONFIG.retry, then RETRY_DEFAULTS, per key. Each key falls through the
// sources on its own; a refusal names the key and the source and the next source fills it in.
// The one-time legacy migration (migrateRetrySources) runs before this read.
function resolveRetry(cwd, env) {
  const rawCap = CONFIG.capS;
  const capS = clampCapS(rawCap);
  if (typeof rawCap === 'number' && rawCap > 14400) {
    log(`cross-ai: config capS ${rawCap} refused (CONFIG): above 14400; using 14400`);
  }
  const scope = retryScope(cwd, env);
  const layers = [{
    label: '.aikit/config.toml',
    file: path.join(cwd, '.aikit', 'config.toml'),
    root: path.join(cwd, '.aikit'),
  }];
  const userDir = aiKitConfigDir(env);
  if (userDir === null) {
    log('cross-ai: no absolute home directory; the user config layer is skipped');
  } else {
    layers.push({
      label: `user ${path.join(userDir, 'config.toml')}`,
      file: path.join(userDir, 'config.toml'),
      root: userDir,
    });
  }
  const sources = [];
  for (const layer of layers) {
    const got = readTomlSubset(layer.file, layer.root);
    if (got.error) {
      log(`cross-ai: config ${layer.label} ${got.error}; retry keys from the next source`);
      continue;
    }
    const table = got.obj && got.obj.runner && got.obj.runner.retry;
    if (!isPlainObject(table)) continue;
    if (scope && isPlainObject(table.scopes) && isPlainObject(table.scopes[scope])) {
      sources.push({
        label: `${layer.label} [runner.retry.scopes."${scope}"]`,
        value: table.scopes[scope],
      });
    }
    const { scopes: _scopes, ...top } = table;
    sources.push({ label: `${layer.label} [runner.retry]`, value: top });
  }
  sources.push({ label: 'CONFIG', value: CONFIG.retry, config: true });
  const usable = [];
  for (const src of sources) {
    const named = src.config ? 'retry' : 'runner.retry';
    if (!src.value || typeof src.value !== 'object' || Array.isArray(src.value)) {
      log(`cross-ai: config ${src.label} ${named} is not an object; retry keys from the next source`);
      continue;
    }
    for (const extra of Object.keys(src.value)) {
      if (!RETRY_KEYS.includes(extra)) {
        log(`cross-ai: config ${named}.${extra} refused (${src.label}): unknown key`);
      }
    }
    usable.push(src);
  }
  const retry = {};
  for (const key of RETRY_KEYS) {
    for (const src of usable) {
      if (!Object.hasOwn(src.value, key)) continue;
      const reason = validateRetryKey(key, src.value[key], capS);
      if (reason) {
        const named = src.config ? 'retry' : 'runner.retry';
        log(`cross-ai: config ${named}.${key} refused (${src.label}): ${reason}`);
        continue;
      }
      retry[key] = src.value[key];
      break;
    }
    if (!Object.hasOwn(retry, key)) retry[key] = RETRY_DEFAULTS[key];
  }
  const waits = retry.hard_waits_s.join(',');
  log(`cross-ai: retry base_s=${retry.base_s} factor=${retry.factor} max_retries=${retry.max_retries} ` +
    `session_resets=${retry.session_resets} hard_waits_s=${waits} hard_every_s=${retry.hard_every_s} cap_s=${capS}`);
  return { retry, capS };
}

// Publishes text through a temp file beside the real path (D-13): the temp is fsynced and renamed
// over the target, so a symlinked config stays a link and its mode is kept. The folder is fsynced
// best effort after the rename.
function writeFileAtomic(file, text) {
  const exists = fs.existsSync(file);
  const target = exists ? fs.realpathSync(file) : file;
  const dir = path.dirname(target);
  fs.mkdirSync(dir, { recursive: true });
  const mode = exists ? fs.statSync(target).mode & 0o777 : 0o600;
  const tmp = path.join(dir, `.${path.basename(target)}.${process.pid}.${crypto.randomUUID()}.tmp`);
  let fd = null;
  try {
    fd = fs.openSync(tmp, 'wx', mode);
    fs.writeFileSync(fd, text);
    fs.fsyncSync(fd);
    fs.closeSync(fd);
    fd = null;
    fs.chmodSync(tmp, mode);
    fs.renameSync(tmp, target);
  } catch (e) {
    if (fd !== null) {
      try { fs.closeSync(fd); } catch { /* already closed */ }
    }
    try { fs.unlinkSync(tmp); } catch { /* never created, or already renamed */ }
    throw e;
  }
  try {
    const dirFd = fs.openSync(dir, 'r');
    try { fs.fsyncSync(dirFd); } finally { fs.closeSync(dirFd); }
  } catch { /* best effort: some filesystems refuse a folder fsync */ }
}

// The GSD block removal (D-13) uses a span scanner over plain JSON: strings are skipped with their
// backslash escapes and objects and arrays nest by their brackets. The model is
// tools/config_doctor_appliers.py _find_top_level_key_span, ported here (never imported).
function jsonSkipWs(text, i) {
  let j = i;
  while (j < text.length && /\s/.test(text[j])) j += 1;
  return j;
}

function jsonStringEnd(text, i) {
  for (let j = i + 1; j < text.length; j += 1) {
    if (text[j] === '\\') j += 1;
    else if (text[j] === '"') return j + 1;
  }
  return -1;
}

// The end (exclusive) of the JSON value that starts at text[i], or -1.
function jsonValueEnd(text, i) {
  if (text[i] === '"') return jsonStringEnd(text, i);
  if (text[i] !== '{' && text[i] !== '[') {
    let j = i;
    while (j < text.length && !/[\s,\]}]/.test(text[j])) j += 1;
    return j > i ? j : -1;
  }
  const closers = [];
  for (let j = i; j < text.length; j += 1) {
    const c = text[j];
    if (c === '"') {
      const end = jsonStringEnd(text, j);
      if (end < 0) return -1;
      j = end - 1;
    } else if (c === '{' || c === '[') {
      closers.push(c === '{' ? '}' : ']');
    } else if (c === '}' || c === ']') {
      if (closers.pop() !== c) return -1;
      if (closers.length === 0) return j + 1;
    }
  }
  return -1;
}

// The span of `key` among the members of the object that opens at text[objStart]:
// { keyStart, valueStart, valueEnd } (valueEnd exclusive), or null.
function findJsonKeySpan(text, objStart, key) {
  let i = jsonSkipWs(text, objStart + 1);
  while (text[i] === '"') {
    const keyEnd = jsonStringEnd(text, i);
    if (keyEnd < 0) return null;
    let name;
    try { name = JSON.parse(text.slice(i, keyEnd)); } catch { return null; }
    const colon = jsonSkipWs(text, keyEnd);
    if (text[colon] !== ':') return null;
    const valueStart = jsonSkipWs(text, colon + 1);
    const valueEnd = jsonValueEnd(text, valueStart);
    if (valueEnd < 0) return null;
    if (name === key) return { keyStart: i, valueStart, valueEnd };
    const next = jsonSkipWs(text, valueEnd);
    if (text[next] !== ',') return null;
    i = jsonSkipWs(text, next + 1);
  }
  return null;
}

// The GSD block removal (D-13, C1-6): the workflow.cross_ai_retry member goes with its own line
// (or with its comma and the spaces after it), every other byte stays. { text: null } when there is
// no block; the result is kept only when it parses to the original object without the block.
function removeRetryBlock(text) {
  const parsed = parseJson(text);
  if (!isPlainObject(parsed) || !isPlainObject(parsed.workflow)
    || !Object.hasOwn(parsed.workflow, 'cross_ai_retry')) {
    return { text: null };
  }
  const notVerified = { error: 'the block removal did not verify' };
  const top = jsonSkipWs(text, 0);
  const workflow = text[top] === '{' ? findJsonKeySpan(text, top, 'workflow') : null;
  if (!workflow || text[workflow.valueStart] !== '{') return notVerified;
  const block = findJsonKeySpan(text, workflow.valueStart, 'cross_ai_retry');
  if (!block) return notVerified;
  const s = block.keyStart;
  let k = block.valueEnd;
  while (text[k] === ' ' || text[k] === '\t') k += 1;
  const comma = text[k] === ',';
  const e2 = comma ? k + 1 : block.valueEnd;
  const lineStart = text.lastIndexOf('\n', s - 1) + 1;
  let lineEnd = e2;
  while (text[lineEnd] === ' ' || text[lineEnd] === '\t') lineEnd += 1;
  let eol = -1;
  if (lineEnd === text.length) eol = lineEnd;
  else if (text.startsWith('\r\n', lineEnd)) eol = lineEnd + 2;
  else if (text[lineEnd] === '\n') eol = lineEnd + 1;
  let from = s;
  let to = e2;
  if (/^[ \t]*$/.test(text.slice(lineStart, s)) && eol >= 0) {
    from = lineStart;
    to = eol;
  } else {
    while (text[to] === ' ' || text[to] === '\t') to += 1;
  }
  // A block with no comma after it is the last member, so the comma before it goes too.
  let commaAt = -1;
  if (!comma) {
    let p = from - 1;
    while (p >= 0 && /\s/.test(text[p])) p -= 1;
    if (p >= 0 && text[p] === ',') commaAt = p;
  }
  const out = commaAt < 0
    ? text.slice(0, from) + text.slice(to)
    : text.slice(0, commaAt) + text.slice(commaAt + 1, from) + text.slice(to);
  const want = JSON.parse(text);
  delete want.workflow.cross_ai_retry;
  let got;
  try { got = JSON.parse(out); } catch { return notVerified; }
  return JSON.stringify(got) === JSON.stringify(want) ? { text: out } : notVerified;
}

// A plain JS value as one TOML value on one line, or null when the subset cannot hold it (D-07).
// String(number) is valid TOML for every finite number: an integer, or a float with '.' or 'e'.
function tomlValueText(v) {
  if (typeof v === 'number') return Number.isFinite(v) ? String(v) : null;
  if (typeof v === 'string') return JSON.stringify(v);
  if (typeof v === 'boolean') return v ? 'true' : 'false';
  if (Array.isArray(v) && v.every((x) => (typeof x === 'number' && Number.isFinite(x)) || typeof x === 'string')) {
    return `[${v.map((x) => tomlValueText(x)).join(', ')}]`;
  }
  return null;
}

// Splices entries into one table of a TOML text, found by segment identity (C1-7): a header is the
// table when the parser's own names (splitTomlName) equal `segments`, so ["runner"."retry"] and
// [runner.retry] are one table. An existing key is replaced only when replaceKeys names it, else it
// is kept (listed in kept); a new key goes after the table's last key line; a missing table is
// appended. Lines keep their endings. JSON.stringify emits only escapes scanBasicString decodes, so
// a quoted segment reads back the same (C2-2); a name the reader still refuses fails the caller's
// pre-publish check and nothing is written.
function upsertTomlKeys(text, segments, entries, replaceKeys = []) {
  const nl = text.includes('\r\n') ? '\r\n' : '\n';
  const lines = text.match(/[^\n]*\n|[^\n]+$/g) ?? [];
  const bareOf = (line) => line.replace(/\r?\n$/, '');
  const isHeader = (line) => TOML_ARRAY_HEADER_RE.test(bareOf(line)) || TOML_TABLE_HEADER_RE.test(bareOf(line));
  const isTarget = (name) => {
    const segs = splitTomlName(name);
    return segs !== null && segs.length === segments.length && segs.every((seg, i) => seg === segments[i]);
  };
  let hdr = -1;
  for (let i = 0; i < lines.length && hdr < 0; i += 1) {
    if (TOML_ARRAY_HEADER_RE.test(bareOf(lines[i]))) continue;
    const m = TOML_TABLE_HEADER_RE.exec(bareOf(lines[i]));
    if (m && isTarget(m[1])) hdr = i;
  }
  let end = lines.length;
  if (hdr >= 0) {
    for (let i = hdr + 1; i < lines.length; i += 1) {
      if (isHeader(lines[i])) {
        end = i;
        break;
      }
    }
  }
  const kept = [];
  const pending = [];
  for (const [key, value] of entries) {
    const valueText = tomlValueText(value);
    if (valueText === null) continue;
    const line = `${key} = ${valueText}${nl}`;
    if (hdr < 0) {
      pending.push(line);
      continue;
    }
    const escapedKey = key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const keyLine = new RegExp(`^\\s*${escapedKey}\\s*=`);
    const found = lines.findIndex((l, i) => i > hdr && i < end && keyLine.test(l));
    if (found >= 0) {
      if (replaceKeys.includes(key)) lines[found] = line;
      else kept.push(key);
      continue;
    }
    let at = hdr + 1;
    for (let i = hdr + 1; i < end; i += 1) {
      if (/^\s*[A-Za-z0-9_-]+\s*=/.test(lines[i])) at = i + 1;
    }
    if (!lines[at - 1].endsWith('\n')) lines[at - 1] += nl;
    lines.splice(at, 0, line);
    end += 1;
  }
  let out = lines.join('');
  if (hdr < 0 && pending.length > 0) {
    if (out !== '') {
      if (!out.endsWith('\n')) out += nl;
      out += nl;
    }
    const name = segments.map((seg) => (/^[A-Za-z0-9_-]+$/.test(seg) ? seg : JSON.stringify(seg))).join('.');
    out += `[${name}]${nl}${pending.join('')}`;
  }
  return { text: out, kept };
}

// The one merge every migration write uses (D-25, C1-5): read the target, splice the entries with
// upsertTomlKeys, verify with parseTomlSubset, re-read right before publishing (a changed file
// rebuilds from the fresh text, at most two attempts), publish atomically, then re-read and confirm
// the merged values, so a source is retired only after its values are in the target. `entries` may
// be a function of the current table (the list is rebuilt from the fresh read). Returns { kept,
// before } or { error }.
function mergeTomlTable(target, root, segments, entries, replaceKeys = []) {
  const tableAt = (obj) => {
    let node = obj;
    for (const seg of segments) {
      if (!isPlainObject(node) || !Object.hasOwn(node, seg)) return {};
      node = node[seg];
    }
    return isPlainObject(node) ? node : {};
  };
  const holds = (text, list, kept) => {
    const parsed = parseTomlSubset(text);
    if (parsed.error) return false;
    const table = tableAt(parsed.obj);
    return list.every(([key, value]) => kept.includes(key) || JSON.stringify(table[key]) === JSON.stringify(value));
  };
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const base = readConfigText(target, root);
    if (base.error) return { error: base.error };
    const text0 = base.text ?? '';
    const p0 = parseTomlSubset(text0);
    if (p0.error) return { error: p0.error };
    const before = tableAt(p0.obj);
    const list = typeof entries === 'function' ? entries(before) : entries;
    const up = upsertTomlKeys(text0, segments, list, replaceKeys);
    if (!holds(up.text, list, up.kept)) return { error: 'merge did not verify' };
    const again = readConfigText(target, root);
    if (again.error || (again.text ?? '') !== text0) continue;
    if (up.text !== text0) writeFileAtomic(target, up.text);
    const after = readConfigText(target, root);
    if (after.error || !holds(after.text ?? '', list, up.kept)) {
      return { error: 'changed after the merge; the next run retries' };
    }
    return { kept: up.kept, before };
  }
  return { error: 'changed during the migration; the next run retries' };
}

// A legacy retry block split into the entries the TOML subset can hold and one notice line per
// entry it cannot (WR-52): a key that is not bare or is a reserved name, or a value outside the
// subset. A refused entry is named with its value, so nothing is dropped silently.
function splitRetryEntries(block) {
  const ok = [];
  const refused = [];
  for (const [key, value] of Object.entries(block)) {
    if (!/^[A-Za-z0-9_-]+$/.test(key) || TOML_RESERVED_NAMES.has(key)) {
      refused.push(`retry key ${JSON.stringify(key)} not migrated: not a usable key (value ${JSON.stringify(value)})`);
    } else if (tomlValueText(value) === null) {
      refused.push(`retry key ${key} not migrated: a value outside the TOML subset (${JSON.stringify(value)})`);
    } else {
      ok.push([key, value]);
    }
  }
  return { ok, refused };
}

// The project .aikit folder as a link, or as the user's own config folder, would send a project
// migration into the user layer (SEC-W1): a reason string, or null when it is a plain folder.
function aikitFolderUnsafe(aikitRoot, env) {
  try {
    if (fs.lstatSync(aikitRoot).isSymbolicLink()) return 'is a link';
    const userDir = aiKitConfigDir(env);
    if (userDir !== null && fs.realpathSync(aikitRoot) === fs.realpathSync(userDir)) return 'is the user config folder';
  } catch { /* absent: nothing to migrate into yet */ }
  return null;
}

// The one-time migration of the legacy retry sources (D-13, D-14, D-15, D-25, D-26). Each source is
// merged into its config.toml first (its own keys win; a conflict is named), retired second (only
// while it still equals the snapshot that was merged, C1-6) and recorded in [runner] migrated_from
// last. Every migration read goes through readConfigText (C1-8). A migration error is logged and
// never stops the dispatch.
function migrateRetrySources(cwd, env) {
  const say = (line) => log(`cross-ai: ${line}`);
  try {
    const aikitRoot = path.join(cwd, '.aikit');
    const target = path.join(aikitRoot, 'config.toml');
    const planningRoot = path.join(cwd, '.planning');
    const unsafe = aikitFolderUnsafe(aikitRoot, env);
    if (unsafe) say(`workflow.cross_ai_retry not migrated: .aikit ${unsafe}; the project migration is refused`);
    for (const file of unsafe ? [] : scopedConfigPaths(cwd, env)) {
      const rel = path.relative(cwd, file).split(path.sep).join('/');
      const read = readTomlSubset(target, aikitRoot);
      if (read.error) {
        say(`${rel} workflow.cross_ai_retry not migrated: .aikit/config.toml ${read.error}`);
        break;
      }
      const marks = read.obj?.runner?.migrated_from;
      const recorded = Array.isArray(marks) && marks.every((s) => typeof s === 'string') ? marks : [];
      if (recorded.includes(rel)) {
        const again = readJsonObject(file, planningRoot);
        if (isPlainObject(again.obj?.workflow) && Object.hasOwn(again.obj.workflow, 'cross_ai_retry')) {
          say(`${rel} holds workflow.cross_ai_retry again; ignored (already migrated to .aikit/config.toml)`);
        }
        continue;
      }
      const snap = readConfigText(file, planningRoot);
      if (snap.error) {
        say(`${rel} workflow.cross_ai_retry not migrated: ${snap.error}`);
        continue;
      }
      if (snap.text === null) continue;
      const doc = parseJson(snap.text);
      if (!isPlainObject(doc)) {
        say(`${rel} workflow.cross_ai_retry not migrated: not a JSON object`);
        continue;
      }
      if (!isPlainObject(doc.workflow) || !Object.hasOwn(doc.workflow, 'cross_ai_retry')) continue;
      const block = doc.workflow.cross_ai_retry;
      if (!isPlainObject(block)) {
        say(`${rel} workflow.cross_ai_retry not migrated: not an object`);
        continue;
      }
      const split = splitRetryEntries(block);
      for (const line of split.refused) say(`${rel} ${line}`);
      const scope = path.relative(planningRoot, path.dirname(file)).split(path.sep).join('/');
      const segments = scope === '' ? ['runner', 'retry'] : ['runner', 'retry', 'scopes', scope];
      const tableName = scope === '' ? 'runner.retry' : `runner.retry.scopes."${scope}"`;
      const merged = mergeTomlTable(target, aikitRoot, segments, split.ok);
      if (merged.error) {
        say(`${rel} workflow.cross_ai_retry not migrated: .aikit/config.toml ${merged.error}`);
        continue;
      }
      for (const key of merged.kept) {
        if (JSON.stringify(merged.before[key]) !== JSON.stringify(block[key])) {
          say(`${rel} retry key ${key} not migrated: .aikit/config.toml already sets it`);
        }
      }
      const now = readConfigText(file, planningRoot);
      if (now.text === null) continue;
      if (now.error || now.text !== snap.text) {
        say(`${rel} workflow.cross_ai_retry not migrated: the file changed during the migration; the next run retries`);
        continue;
      }
      const removed = removeRetryBlock(snap.text);
      if (typeof removed.text !== 'string') {
        say(`${rel} workflow.cross_ai_retry not migrated: ${removed.error ?? 'the block removal did not verify'}`);
        continue;
      }
      writeFileAtomic(file, removed.text);
      const marked = mergeTomlTable(target, aikitRoot, ['runner'], (table) => [[
        'migrated_from',
        [...(Array.isArray(table.migrated_from) ? table.migrated_from.filter((s) => typeof s === 'string' && s !== rel) : []), rel],
      ]], ['migrated_from']);
      if (marked.error) {
        say(`${rel} workflow.cross_ai_retry not migrated: .aikit/config.toml ${marked.error}`);
        continue;
      }
      say(`migrated workflow.cross_ai_retry from ${rel} to .aikit/config.toml [${tableName}] ` +
        '(the project file is per checkout and may be git-ignored)');
    }
    const userDir = aiKitConfigDir(env);
    const userJson = userDir === null ? null : path.join(userDir, 'cross-ai.json');
    if (userJson !== null && fs.existsSync(userJson)) {
      const userToml = path.join(userDir, 'config.toml');
      const read2 = readTomlSubset(userToml, userDir);
      if (read2.error) {
        say(`${userJson} cross_ai_retry not migrated: ${userToml} ${read2.error}`);
        return;
      }
      const userMarks = read2.obj?.runner?.migrated_from;
      if (Array.isArray(userMarks) && userMarks.includes('cross-ai.json')) {
        say(`${userJson} is back; ignored (already migrated to ${userToml})`);
        return;
      }
      const snap2 = readConfigText(userJson, userDir);
      if (snap2.error) {
        say(`${userJson} cross_ai_retry not migrated: ${snap2.error}`);
        return;
      }
      if (snap2.text === null) return;
      const doc2 = parseJson(snap2.text);
      if (!isPlainObject(doc2)) {
        say(`${userJson} cross_ai_retry not migrated: not a JSON object`);
        return;
      }
      const has = Object.hasOwn(doc2, 'cross_ai_retry');
      if (has && !isPlainObject(doc2.cross_ai_retry)) {
        say(`${userJson} cross_ai_retry not migrated: not an object`);
        return;
      }
      const block2 = has ? doc2.cross_ai_retry : {};
      const split2 = splitRetryEntries(block2);
      for (const line of split2.refused) say(`${userJson} ${line}`);
      const merged2 = mergeTomlTable(userToml, userDir, ['runner', 'retry'], split2.ok);
      if (merged2.error) {
        say(`${userJson} cross_ai_retry not migrated: ${userToml} ${merged2.error}`);
        return;
      }
      for (const key of merged2.kept) {
        if (JSON.stringify(merged2.before[key]) !== JSON.stringify(block2[key])) {
          say(`${userJson} retry key ${key} not migrated: ${userToml} already sets it`);
        }
      }
      const now2 = readConfigText(userJson, userDir);
      if (now2.text === null) return;
      if (now2.error || now2.text !== snap2.text) {
        say(`${userJson} cross_ai_retry not migrated: the file changed during the migration; the next run retries`);
        return;
      }
      let retired = `${userJson}.migrated`;
      for (let n = 1; fs.existsSync(retired); n += 1) retired = `${userJson}.migrated.${n}`;
      fs.renameSync(userJson, retired);
      const marked2 = mergeTomlTable(userToml, userDir, ['runner'], (table) => [[
        'migrated_from',
        [...(Array.isArray(table.migrated_from) ? table.migrated_from.filter((s) => typeof s === 'string' && s !== 'cross-ai.json') : []), 'cross-ai.json'],
      ]], ['migrated_from']);
      if (marked2.error) {
        say(`${userJson} cross_ai_retry not migrated: ${userToml} ${marked2.error}`);
        return;
      }
      say(`migrated ${userJson} to ${userToml} [runner.retry]; the old file is now ${retired}`);
    }
  } catch (e) {
    say(`retry migration skipped (${e && e.message ? e.message : String(e)})`);
  }
}

// Nominal wait k is base_s x factor^(k-1), in ms, jittered by at most +-10% and rounded to the
// nearest millisecond. The floor only lifts a wait that jitter pushed more than 10% under its
// predecessor, so jitter never makes wait k more than 10% shorter than wait k-1.
function softWaitMs(retry, k, rand = Math.random, prevMs = 0) {
  const nominal = retry.base_s * 1000 * retry.factor ** (k - 1);
  const jittered = Math.round(nominal * (1 + (rand() * 2 - 1) * 0.1));
  return Math.max(jittered, Math.ceil(0.9 * prevMs));
}
// Pure step of the soft series. Table-free: the caller decides the class. `st = {retry,
// resets, canResume, firstMs, cycle}`, `lim = {maxRetries, sessionResets, deadlineMs, waitMs,
// capMs}`. A CLI that cannot resume still walks the same-session retries, each as a new
// session (D-10). Once the series and its resets are spent both soft classes hand the call to
// the one hard handler, which can admit a short in-call wait. The admission checks apply to both
// soft classes: one shared episode cap (D-07).
function ladderNext(st, cls, nowMs, lim) {
  if (cls !== 'transient' && cls !== 'quota') return { next: 'stop', why: 'class' };
  let next = 'hard';
  let why = 'soft-spent';
  if (st.retry < lim.maxRetries) {
    next = st.canResume ? 'same' : 'new';
    why = 'soft-retry';
  } else if (st.canResume && st.resets < lim.sessionResets) {
    next = 'reset';
    why = 'session-reset';
  }
  if (next === 'hard') return { next, why };
  if (nowMs + (lim.waitMs || 0) + 60000 > lim.deadlineMs) {
    return { next: 'stop', why: 'deadline' };
  }
  if (st.firstMs && nowMs + 60000 > st.firstMs + lim.capMs) {
    return { next: 'stop', why: 'cap' };
  }
  return { next, why };
}

// The caller's hard tier (SPEC R5, D-10): cycle n waits hard_waits_s[n], then hard_every_s
// after the list; 0 ends at the list's end (stopped=hard-waits),
// and a wait past the episode cap left is the cap stop. capLeftS is the seconds still allowed.
function hardWaitFor(cycle, waits, capLeftS, everyS = 0) {
  if (cycle >= waits.length && !everyS) return { stop: 'hard-waits' };
  const wait = cycle < waits.length ? waits[cycle] : everyS;
  if (wait > capLeftS) return { stop: 'cap' };
  return { retryAfterS: Math.trunc(wait), cycle };
}

// SPEC R5, D-11: a stated reset is untrusted data; it can only add one check, 60 s ahead at the earliest and before the cap's end.
const RESET_RELATIVE_KEYS = ['retry_after', 'retry_after_seconds', 'reset_seconds', 'reset_after_s'];
const RESET_ABSOLUTE_KEYS = ['reset_at', 'resetsAt'];
// A window clears about 2 minutes after its stated reset (v1.3 recovery notes).
const RESET_MARGIN_S = 120;

// Whole seconds until the earliest stated reset that is not in the past, else null; relative fields are seconds, absolute ones epoch seconds, epoch ms or an ISO time.
function statedResetS(fields, nowMs) {
  if (!fields || typeof fields !== 'object') return null;
  const num = (v) => {
    if (typeof v === 'number') return Number.isFinite(v) ? v : null;
    return typeof v === 'string' && /^\d+(\.\d+)?$/.test(v) ? Number(v) : null;
  };
  const iso = (v) => {
    if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,3})?Z$/.test(v)) return null;
    const t = Date.parse(v);
    return Number.isFinite(t) && new Date(t).toISOString().slice(0, 19) === v.slice(0, 19) ? t : null;
  };
  const found = [];
  const ahead = (ms) => { if (ms !== null && ms - nowMs >= 0) found.push(Math.trunc((ms - nowMs) / 1000)); };
  for (const key of RESET_RELATIVE_KEYS) {
    const v = fields[key];
    const n = num(v);
    if (n !== null) { if (n >= 0) found.push(Math.trunc(n)); }
    else if (key === 'retry_after' && typeof v === 'string') ahead(iso(v));
  }
  for (const key of RESET_ABSOLUTE_KEYS) {
    const v = fields[key];
    const n = num(v);
    let ms = null;
    if (n !== null) ms = n >= 1e12 ? n : (n >= 1e9 ? n * 1000 : null);
    else if (typeof v === 'string') ms = iso(v);
    ahead(ms);
  }
  return found.length ? Math.min(...found) : null;
}

// The extra check's wait: stated + 120 s, only when at least 60 s, before the cap's end and earlier than the next check.
function resetCheckS(statedS, nextWaitS, capLeftS) {
  if (!Number.isInteger(statedS) || statedS < 0) return null;
  const at = statedS + RESET_MARGIN_S;
  return at >= 60 && at < capLeftS && at < nextWaitS ? at : null;
}

// A short hard wait, including zero, runs in the call only with a 60 second reserve.
function shortHardWait(waitS, atMs, deadlineMs) {
  if (!(waitS >= 0 && waitS < 60)) return { waitS, inCall: false };
  return atMs + waitS * 1000 + 60000 <= deadlineMs ? { waitS, inCall: true } : { waitS: 60, inCall: false };
}

// Rung 1 continues the captured session. Null when no session can be continued: no id,
// no resume formula, a sandboxed codex exec, or codex review (its resume argv has no
// read-only sandbox).
// An id is printed or passed back only inside the session charset and when no key shape matches it (SPEC R7; redactSecrets would also hide a UUID).
function sessionShown(id) { return typeof id === 'string' && SESSION_ID_RE.test(id) && redactKeyShapes(id) === id; }

function sameSessionArgv(name, rt, model, ctx, sid, mode, input = RESUME_MSG) {
  if (!sid || !rt.resume) return null;
  if (name === 'codex' && (mode === 'review' || ctx.codexSandbox)) return null;
  return { argv: withExtra(name, rt.resume(model, ctx, sid, mode)), input };
}

// Rung 2 is a fresh argv on the same CLI and model; every chosen row (pi, copilot) gets a new session id.
function newSessionArgv(name, rt, model, ctx, mode, prompt, keepSid = false) {
  if (!keepSid && rt.forms?.session?.style === 'chosen') ctx.sid = crypto.randomUUID();
  if (rt.argvPrompt) {
    ctx.promptArg = argvPromptElement(prompt);
    return { argv: withExtra(name, rt[mode](model, ctx)), input: null };
  }
  return { argv: withExtra(name, rt[mode](model, ctx)), input: prompt };
}

// An argv prompt is one element. ARGV_PROMPT_MAX covers that element plus the resume text a
// fresh-session retry can prepend, so no retry argv can pass the limit either.
const ARGV_PROMPT_MAX = 102400;

// shortcut: the option parser's handling of a leading dash is unverified, so a prompt that
// starts with `-` is prefixed with a newline and never reads as another flag.
function argvPromptElement(prompt) {
  const text = String(prompt ?? '');
  return text.startsWith('-') ? `\n${text}` : text;
}

function argvPromptProblem(prompt) {
  const element = Buffer.byteLength(argvPromptElement(prompt));
  const reserve = Buffer.byteLength(`${RESUME_MSG}\n\n`);
  const bytes = element + reserve;
  return bytes > ARGV_PROMPT_MAX ? { bytes } : null;
}

function displayArgv(argv, promptEl) {
  if (promptEl === undefined) return argv;
  return argv.map((el) => (el === promptEl ? '<prompt>' : el));
}
// 37 R4: an argv file is caller-written and may carry a key; the printed copy is redacted, the spawned argv stays raw.
function shownArgv(rt, argv) {
  return rt?.argvFile ? argv.map((el) => redactSecrets(el)) : argv;
}
function readOr(p, dflt) { try { return fs.readFileSync(p, 'utf8'); } catch { return dflt; } }

// Quota cycles span calls. The file is keyed by lane and model under the XDG state dir
// (the home fallback is ~/.local/state, so a scratch HOME never reaches the real one).
const QUOTA_KEEP = new Set(['quota', 'transient', 'timeout']);

function stateHome() {
  const named = (process.env.XDG_STATE_HOME || '').trim();
  if (named) return named;
  return path.join(process.env.HOME || os.homedir(), '.local', 'state');
}

function sha16(text) {
  return crypto.createHash('sha256').update(String(text)).digest('hex').slice(0, 16);
}

function taskDigest(prompt) {
  // The preamble is appended after a blank line and carries its own objective block, which
  // would make every task hash the same. The caller's prompt is the part before it.
  const text = String(prompt || '');
  const cut = text.lastIndexOf('\n\n<');
  const body = cut > 0 ? text.slice(0, cut) : text;
  const m = /<objective>([\s\S]*?)<\/objective>/.exec(body);
  return sha16(m ? m[1] : body);
}

// The route kind is part of the file name (orchestrator decision 2026-10-25): a confirmed
// router lane and every other route on the same CLI and model keep separate records, so an
// unconfirmed call can never read, delete or overwrite a router-quota record. Nothing has
// shipped under the Phase 25 single-file name, so there is no migration.
function cycleFilePath(cli, model, kind, cwd = process.cwd(), home = stateHome()) {
  let root = cwd;
  try { root = fs.realpathSync(root); } catch { /* the cwd itself is the key */ }
  const dir = path.join(home, 'ai-kit', 'spec', 'cycles', sha16(root));
  return path.join(dir, `${cli}-${kind}-${sha16(model)}.json`);
}

function readCycleState(file) {
  const parsed = parseJson(readOr(file, ''));
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return null;
  if (typeof parsed.first_seen !== 'number' || typeof parsed.cycle !== 'number') return null;
  // A record without the class of the attempt that reached the hard handler is not a record
  // this runner wrote; treat it as absent rather than guess (25.1-03 route-keyed files).
  if (parsed.class !== 'transient' && parsed.class !== 'quota') return null;
  return parsed;
}

function writeCycleState(file, data) {
  fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
  try { fs.chmodSync(path.dirname(file), 0o700); } catch { /* best effort */ }
  const tmp = path.join(path.dirname(file),
    `.${path.basename(file)}.${process.pid}.${crypto.randomUUID()}.tmp`);
  const fd = fs.openSync(tmp, 'wx', 0o600);
  try {
    fs.writeFileSync(fd, JSON.stringify(data));
  } finally {
    fs.closeSync(fd);
  }
  fs.renameSync(tmp, file);
  try { fs.chmodSync(file, 0o600); } catch { /* the create mode already is 0600 */ }
}

// 38.1 R11 (D-23..D-25): a usage-limited pool's blocked-until record; the runner never acts on it.
// Mirrors Phase 36's POOL_RX (lane_settings.py) so a caller's --pool equals the recorded string.
const BLOCKED_POOL_RE = /^[A-Za-z0-9._-]{1,64}:[a-z]{1,16}$/;
// The tier part of BLOCKED_POOL_RE, so a row tier that validates always forms a pool key.
const ROW_POOL_RE = /^[a-z]{1,16}$/;
const BLOCKED_DAY_S = 86400;
const BLOCKED_MARGIN_S = 120;
function blockedIso(s) { return new Date(s * 1000).toISOString().replace(/\.\d{3}Z$/, 'Z'); }
function blockedStatedS(fields) {
  const ms = fields ? fields.retryAfterMs : undefined;
  return typeof ms === 'number' && Number.isInteger(ms) && ms > 0 ? Math.min(Math.trunc(ms / 1000), BLOCKED_DAY_S) : null;
}
function blockedNext(prev, nowS, statedS) {
  const base = statedS === null ? BLOCKED_DAY_S : statedS + BLOCKED_MARGIN_S;
  const basis = statedS === null ? 'default_24h' : 'retry_after_ms';
  if (!prev) return { untilS: nowS + base, failures: 1, basis };
  if (nowS < prev.untilS) return { untilS: Math.max(prev.untilS, nowS + base), failures: prev.failures, basis: nowS + base > prev.untilS ? basis : prev.basis };
  const failures = prev.failures + 1;
  return { untilS: nowS + Math.max(base, BLOCKED_DAY_S), failures, basis: base >= BLOCKED_DAY_S ? basis : 'floor_24h' };
}
function blockedPoolKey(poolOpt, row, model) {
  if (poolOpt) return poolOpt;
  if (!row || !row.pool) return null;
  const cut = String(model || '').indexOf('/');
  if (cut <= 0) return null;
  const key = `${model.slice(0, cut)}:${row.pool}`;
  return BLOCKED_POOL_RE.test(key) ? key : null;
}
function blockedFilePath(pool, home = stateHome()) { return path.join(home, 'ai-kit', 'spec', 'blocked', `${encodeURIComponent(pool)}.json`); }
const BLOCKED_BASES = new Set(['retry_after_ms', 'default_24h', 'floor_24h']);
const BLOCKED_MAX_BYTES = 4096;
function readBlocked(pool, home = stateHome()) {
  let rec;
  try {
    const file = blockedFilePath(pool, home);
    const st = fs.lstatSync(file);
    if (!st.isFile() || st.size > BLOCKED_MAX_BYTES) return null;
    rec = parseJson(fs.readFileSync(file, 'utf8'));
  } catch { return null; }
  if (!rec || typeof rec !== 'object' || Array.isArray(rec) || rec.pool !== pool || typeof rec.blocked_until !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(rec.blocked_until) || !Number.isFinite(Date.parse(rec.blocked_until)) || !Number.isInteger(rec.failures) || rec.failures < 1 || !BLOCKED_BASES.has(rec.basis) || typeof rec.rule !== 'string' || (rec.rule !== '-' && !ROW_ID_RE.test(rec.rule))) return null;
  return { pool, untilS: Date.parse(rec.blocked_until) / 1000, failures: rec.failures, basis: rec.basis, rule: rec.rule };
}
const BLOCKED_WAIT = new Int32Array(new SharedArrayBuffer(4));
const BLOCKED_LOCK_ROUNDS = 40;
// A writer publishes only while it holds the pool lock; a busy lock skips the write (R11: the later blocked_until wins).
function blockedWithLock(file, fn, rounds = BLOCKED_LOCK_ROUNDS) {
  const lock = `${file}.lock`;
  const record = { version: LOCK_RECORD_VERSION, run_id: crypto.randomUUID(), pid: process.pid, pid_start: lockStartTime(process.pid), host_name: os.hostname(), started_ms: Date.now(), child_pgid: null, child_start: null };
  for (let round = 0; round < rounds; round += 1) {
    if (createLockFile(lock, record)) {
      try { return { done: true, value: fn() }; } finally {
        const mine = readLockOnce(lock);
        if (mine.rec && mine.rec.run_id === record.run_id) fs.rmSync(lock, { force: true });
      }
    }
    const seen = readLockOnce(lock);
    if (seen.gone) continue;
    if (!seen.bad && lockVerdict(seen.rec, lockProbe()) === 'stale') { clearStaleLock(lock, seen); continue; }
    if (round + 1 < rounds) Atomics.wait(BLOCKED_WAIT, 0, 0, 25);
  }
  return { done: false };
}
// The live watcher keeps the first terminal string (an opencode message comes before its type), so a pool row may match a later string of the same raw text.
function blockedPoolRow(r, model) {
  const hit = TABLE.find((item) => item.id === r.rule) || null;
  if (hit && hit.pool) return hit;
  const raw = String(r.upstream?.raw || '');
  const { events, eventRaw } = eventsWithRaw(r.cli, raw, true);
  const cls = classifyStop({ cli: r.cli, route: r.route || 'unknown', model, stderr: raw, events, eventRaw }, TABLE.filter((item) => item.pool));
  return cls.status !== 'crash' ? TABLE.find((item) => item.id === cls.rule) || hit : hit;
}
function blockedAfterStop(poolOpt, model, r, nowMs = Date.now(), home = stateHome(), rounds = BLOCKED_LOCK_ROUNDS) {
  if (!r || r.status !== 'quota' || confirmedRoute(r.route || 'unknown')) return null;
  const row = blockedPoolRow(r, model);
  const key = blockedPoolKey(poolOpt, row, model);
  if (!key) return null;
  try {
    const nowS = Math.floor(nowMs / 1000);
    const file = blockedFilePath(key, home);
    const res = blockedWithLock(file, () => {
      const prev = readBlocked(key, home);
      const next = blockedNext(prev, nowS, blockedStatedS(r.upstream?.fields));
      if (prev && prev.untilS > next.untilS) next.untilS = prev.untilS;
      writeCycleState(file, { pool: key, blocked_until: blockedIso(next.untilS), failures: next.failures, basis: next.basis, rule: row && ROW_ID_RE.test(row.id) ? row.id : '-', written_at: blockedIso(nowS) });
      return next;
    }, rounds);
    if (!res.done) { log('cross-ai: blocked-until write skipped (pool lock busy)'); return null; }
    const next = res.value;
    log(`cross-ai: blocked-until pool=${key} until=${blockedIso(next.untilS)} failures=${next.failures} basis=${next.basis}`);
    return next;
  } catch (e) { log(`cross-ai: blocked-until write failed (${e && e.code || 'error'})`); return null; }
}
// An ok attempt clears only a pool the caller named: a paid lane of the same provider is not in the pool.
function blockedClearAfterOk(poolOpt, home = stateHome()) {
  if (!poolOpt) return;
  const done = blockedClear(poolOpt, home);
  if (done !== 'cleared' && done !== 'absent') log(`cross-ai: blocked-until clear failed (${done})`);
}

function blockedStatusLine(pool, home = stateHome()) {
  const rec = readBlocked(pool, home);
  return `blocked_until=${rec ? blockedIso(rec.untilS) : '-'} failures=${rec ? rec.failures : 0}`;
}

function blockedClear(pool, home = stateHome()) {
  try { fs.unlinkSync(blockedFilePath(pool, home)); } catch (e) { return e && e.code === 'ENOENT' ? 'absent' : String(e && e.code || 'error'); }
  log(`cross-ai: blocked-until cleared pool=${pool}`);
  return 'cleared';
}

function deleteCycleState(file) {
  try { fs.rmSync(file, { force: true }); } catch { /* already gone */ }
}

// D-06 to D-09: the per-checkout run lock of an execute run (SPEC R3).
const LOCK_RECORD_VERSION = 1;
// SPEC R3: an unparseable record is re-read until it is this old, then refused and kept.
const LOCK_REREAD_MS = 2000;
const LOCK_MAX_BYTES = 65536;
// A .clearing mutex older than this was abandoned by a killed clearer.
const LOCK_CLEAR_STALE_MS = 10000;
function lockPath(root, home = path.resolve(stateHome())) {
  return path.join(home, 'ai-kit', 'spec', 'locks', sha16(root) + '.json');
}
function checkoutRoot(cwd) {
  let real = cwd;
  try { real = fs.realpathSync(cwd); } catch { /* the cwd itself is the key */ }
  // shortcut: under GIT_DIR the work tree is not found by a walk; the cwd's real path is the key.
  if ((process.env.GIT_DIR || '').trim()) return real;
  const ceiling = (process.env.GIT_CEILING_DIRECTORIES || '').split(path.delimiter).filter(Boolean).map((d) => path.resolve(d));
  let dir = real;
  for (;;) {
    if (ceiling.includes(dir)) return real;
    if (fs.existsSync(path.join(dir, '.git'))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) return real;
    dir = parent;
  }
}
function lockText(value) {
  return redactSecrets(redactSecrets(String(value ?? '-')).replace(/[\x00-\x1f\x7f-\x9f]/g, ''));
}
function procReadable() {
  try { fs.readFileSync('/proc/self/stat', 'utf8'); return true; } catch { return false; }
}
// D-06/D-32: /proc start ticks where /proc reads; ps lstart (whole seconds, LC_ALL=C) only where it does not; '-' when neither.
function lockStartTime(pid, procOk = procReadable(), env = process.env) {
  if (procOk) return procStartTime(pid);
  const r = spawnSync('ps', ['-o', 'lstart=', '-p', String(pid)], { encoding: 'utf8', timeout: 2000, stdio: ['ignore', 'pipe', 'ignore'], env: { ...env, LC_ALL: 'C' } });
  const text = String(r.stdout || '').trim().replace(/\s+/g, ' ');
  return r.status === 0 && text && !/[\x00-\x1f]/.test(text) ? text : '-';
}
function lockPidAlive(pid) {
  try { process.kill(pid, 0); } catch (e) { return e.code === 'EPERM'; }
  return pidAlive(pid);
}
function lockRecordValid(rec) {
  return Boolean(rec) && typeof rec === 'object' && !Array.isArray(rec) && rec.version === LOCK_RECORD_VERSION && typeof rec.run_id === 'string' && rec.run_id !== '' && Number.isInteger(rec.pid) && rec.pid > 0 && typeof rec.pid_start === 'string' && typeof rec.host_name === 'string' && rec.host_name !== '' && (rec.child_pgid === null || Number.isInteger(rec.child_pgid)) && (rec.child_start === null || typeof rec.child_start === 'string');
}
function lockGroupAlive(pgid, start, procOk = procReadable()) {
  if (!Number.isInteger(pgid) || pgid <= 1) return false;
  // A detached child leads its own group and session; a leader whose start changed is a reused pid.
  if (procOk) return groupMembers(pgid, pgid).some((m) => m !== pgid || !start || start === '-' || procStartTime(pgid) === start);
  try { process.kill(-pgid, 0); return true; } catch (e) { return e.code === 'EPERM'; }
}
function lockVerdict(rec, probe, ownRunId = null) {
  if (ownRunId && rec.run_id === ownRunId) return 'own';
  if (rec.host_name !== probe.host) return 'foreign';
  const now = Number.isInteger(rec.pid) && probe.alive(rec.pid) ? probe.start(rec.pid) : null;
  const runnerAlive = now !== null && (typeof rec.pid_start !== 'string' || rec.pid_start === '-' || now === '-' || now === rec.pid_start);
  if (runnerAlive) return 'held';
  if (probe.groupAlive(rec.child_pgid, rec.child_start)) return 'orphan';
  if ((Number.isInteger(rec.launcher_pgid) || typeof rec.token === 'string') && probe.launcherAlive && probe.launcherAlive(rec)) return 'orphan';
  return 'stale';
}
function lockProbe() {
  return { host: os.hostname(), alive: lockPidAlive, start: (pid) => lockStartTime(pid), groupAlive: (pgid, start) => lockGroupAlive(pgid, start), launcherAlive: (rec) => hostedLaunchAlive(rec) };
}
function lockSince(rec) {
  return Number.isFinite(rec?.started_ms) && Math.abs(rec.started_ms) <= 8.64e15 ? new Date(rec.started_ms).toISOString() : '-';
}
function lockHeldLine(rec) {
  const r = rec && typeof rec === 'object' ? rec : {};
  return `cross-ai: run lock held by pid ${lockText(r.pid)} (lane ${lockText(r.cli)}/${lockText(r.model)}, since ${lockSince(r)}); not starting`;
}
// 38 D-26: a refusal names a hosted holder's launcher group and tab (never the tab as liveness).
function lockHostedLine(rec) {
  if (!rec || (!Number.isInteger(rec.launcher_pgid) && typeof rec.token !== 'string')) return null;
  return redactSecrets(redactSecrets(`cross-ai: lock: held by a hosted lane, launcher group ${lockText(rec.launcher_pgid ?? '-')}, herdr tab ${lockText(rec.tab_id ?? '-')}`).replace(/[\x00-\x1f\x7f-\x9f]/g, ''));
}
// A launcher that wrote its pid file before its runner adopted it (no launcher_pgid recorded yet).
function pidFileLauncherAlive(pidText) {
  return /^\d+\n?$/.test(pidText) && lockPidAlive(Number(pidText)) && procGroup(Number(pidText)) === Number(pidText);
}
function hostedLaunchAlive(rec) {
  if (Number.isInteger(rec.launcher_pgid)) return lockGroupAlive(rec.launcher_pgid, rec.launcher_start);
  if (typeof rec.token !== 'string' || !/^[0-9a-f]{12}$/.test(rec.token)) return false;
  const pidText = readOr(path.join(hostRunDir(path.resolve(stateHome()), rec.token), HOST_FILES.pid), '');
  if (/^\d+\n?$/.test(pidText)) return pidFileLauncherAlive(pidText);
  return !pidText && Number.isFinite(rec.host_ms) && Date.now() - rec.host_ms < HOST_PID_GRACE_MS;
}
function lockForeignLine(rec) {
  return `cross-ai: run lock held by pid ${lockText(rec.pid)} on host ${lockText(rec.host_name)} (lane ${lockText(rec.cli)}/${lockText(rec.model)}, since ${lockSince(rec)}); this host cannot probe it; not starting`;
}
function readLockOnce(file) {
  let st;
  try { st = fs.lstatSync(file); } catch (e) { return e.code === 'ENOENT' ? { gone: true } : { bad: true, mtimeMs: null }; }
  if (!st.isFile() || st.size > LOCK_MAX_BYTES || st.mtimeMs > Date.now() + 1000) return { bad: true, mtimeMs: st.mtimeMs };
  try {
    const fd = fs.openSync(file, 'r');
    let raw, fst;
    try { raw = fs.readFileSync(fd, 'utf8'); fst = fs.fstatSync(fd); } finally { fs.closeSync(fd); }
    const rec = parseJson(raw);
    return lockRecordValid(rec) ? { rec, raw, dev: fst.dev, ino: fst.ino } : { bad: true, mtimeMs: st.mtimeMs };
  } catch (e) { return e.code === 'ENOENT' ? { gone: true } : { bad: true, mtimeMs: st.mtimeMs }; }
}
async function readLockRecord(file) {
  const t0 = Date.now();
  for (;;) {
    const seen = readLockOnce(file);
    if (!seen.bad) return seen;
    if (Date.now() - t0 >= LOCK_REREAD_MS) return { unreadable: true, ageS: seen.mtimeMs === null ? '-' : Math.max(0, Math.round((Date.now() - seen.mtimeMs) / 1000)) };
    await sleep(100);
  }
}
function createLockFile(file, record) {
  let created = false;
  try {
    fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
    try { fs.chmodSync(path.dirname(file), 0o700); } catch { /* best effort */ }
    const fd = fs.openSync(file, 'wx', 0o600);
    created = true;
    try { fs.writeFileSync(fd, JSON.stringify(record)); } finally { fs.closeSync(fd); }
    return true;
  } catch (e) {
    if (e.code === 'EEXIST') return false;
    if (created) { try { fs.rmSync(file, { force: true }); } catch { /* best effort */ } }
    throw e;
  }
}
function clearStaleLock(file, seen) {
  const mutex = file + '.clearing';
  try { fs.mkdirSync(mutex, { mode: 0o700 }); } catch (e) {
    if (e.code !== 'EEXIST') return false;
    try {
      if (Date.now() - fs.statSync(mutex).mtimeMs <= LOCK_CLEAR_STALE_MS) return false;
      fs.rmdirSync(mutex);
      fs.mkdirSync(mutex, { mode: 0o700 });
    } catch { return false; }
  }
  try {
    let fd;
    try { fd = fs.openSync(file, 'r'); } catch { return false; }
    let fst, raw;
    try { fst = fs.fstatSync(fd); raw = fs.readFileSync(fd, 'utf8'); } finally { fs.closeSync(fd); }
    if (fst.dev !== seen.dev || fst.ino !== seen.ino || raw !== seen.raw) return false;
    const moved = file + '.stale-' + process.pid + '-' + crypto.randomUUID();
    fs.renameSync(file, moved);
    fs.rmSync(moved, { force: true });
    return true;
  } catch { return false; } finally { try { fs.rmdirSync(mutex); } catch { /* best effort */ } }
}
async function acquireLock(root, lane) {
  const file = lockPath(root);
  // baseline is plan 38-15's; launcher_pgid, token and tab_id are a hosted lane's (38-21).
  const record = { version: LOCK_RECORD_VERSION, run_id: crypto.randomUUID(), pid: process.pid,
    pid_start: lockStartTime(process.pid), host_name: os.hostname(), started_ms: Date.now(),
    cli: lane.cli, model: lane.model, role: 'execute', root, child_pgid: null, child_start: null,
    baseline: null, launcher_pgid: null, token: null, tab_id: null };
  for (let round = 0; round < 3; round++) {
    try {
      if (createLockFile(file, record)) {
        liveLock = { file, runId: record.run_id, record };
        return { ok: true };
      }
    } catch (e) {
      log(`cross-ai: run lock not taken (${e.code || e.message}); running without a lock`);
      return { ok: true };
    }
    const seen = await readLockRecord(file);
    if (seen.gone) continue;
    if (seen.unreadable) return { ok: false, line: `cross-ai: run lock record ${lockText(file)} is unreadable (age ${seen.ageS}s); not cleared; not starting` };
    const verdict = lockVerdict(seen.rec, lockProbe(), record.run_id);
    if (verdict === 'own') { liveLock = { file, runId: record.run_id, record: seen.rec }; return { ok: true }; }
    if (verdict === 'held') return { ok: false, line: lockHeldLine(seen.rec), hosted: lockHostedLine(seen.rec) };
    if (verdict === 'foreign') return { ok: false, line: lockForeignLine(seen.rec) };
    if (verdict === 'orphan') {
      if (typeof seen.rec.token === 'string') return { ok: false, line: lockHostedLine(seen.rec) };
      return { ok: false, line: `cross-ai: run lock: pid ${lockText(seen.rec.pid)} is gone but its child group ${lockText(seen.rec.child_pgid)} still runs; not starting` };
    }
    if (clearStaleLock(file, seen)) {
      log(`cross-ai: stale run lock from pid ${lockText(seen.rec.pid)} (since ${lockSince(seen.rec)}) cleared`);
      if (typeof seen.rec.token === 'string') await sweepRuns({ explicit: false, hostingOff: Boolean(lane.hostingOff), onlyToken: seen.rec.token });
    }
  }
  return { ok: false, line: lockHeldLine(parseJson(readOr(file, ''))) };
}
function lockUpdate(fields, lock = liveLock) {
  if (!lock) return;
  lock.record = { ...lock.record, ...fields };
  try { writeCycleState(lock.file, lock.record); } catch (e) {
    if (!lockUpdateFailed) {
      lockUpdateFailed = true;
      log(`cross-ai: note: run lock record not updated (${e.code || e.message})`);
    }
  }
}
function releaseLock() {
  if (!liveLock) return;
  const { file, runId } = liveLock;
  liveLock = null;
  try {
    const rec = parseJson(readOr(file, ''));
    if (rec && rec.run_id === runId) fs.rmSync(file, { force: true });
  } catch { /* best effort */ }
}
function lockSeen(root) {
  // D-09: a review notes a live, orphaned or unprobeable lock and never waits, clears or rewrites one.
  const rec = parseJson(readOr(lockPath(root), ''));
  if (!rec || typeof rec !== 'object' || Array.isArray(rec)) return false;
  const v = lockVerdict(rec, lockProbe());
  return v === 'held' || v === 'orphan' || v === 'foreign';
}

// D-10: the start-of-run baseline of an execute run (SPEC R4).
const BASELINE_RECORD_VERSION = 1;
const BASELINE_SHA_RE = /^[0-9a-f]{40}(?:[0-9a-f]{24})?$/;
function baselineVerdict(rec, nowMs, capS, descends) {
  if (!rec || typeof rec !== 'object' || Array.isArray(rec) || rec.version !== BASELINE_RECORD_VERSION || typeof rec.tree !== 'string' || !BASELINE_SHA_RE.test(rec.tree.split('\t')[0]) || !(rec.head === null || (typeof rec.head === 'string' && BASELINE_SHA_RE.test(rec.head))) || !Number.isInteger(rec.at)) return { reason: 'invalid: the record does not parse' };
  if (rec.at > nowMs) return { reason: 'future: the record time is ahead of the clock' };
  const age = nowMs - rec.at;
  if (age >= capS * 1000) return { reason: `expired: age ${Math.floor(age / 1000)}s is not under the cap ${capS}s` };
  if (descends === false) return { reason: `rebased: HEAD does not descend from ${String(rec.head).slice(0, 12)}` };
  return { reuse: true };
}
async function baselineGit(cwd, argv) {
  const git = which('git', process.env.PATH || '');
  if (!git) return 'unknown';
  const r = await runChild(git, argv, { cwd, capMs: GIT_CAP_MS, limit: runDeadline });
  if (r.timedOut || r.spawnErr) return 'unknown';
  return r.code === 0 ? 'yes' : r.code === 1 || r.code === 128 ? 'no' : 'unknown';
}
async function headDescends(cwd, base, head) {
  if (base === null) return 'yes'; // An unborn baseline: every commit counts.
  if (base === head) return 'yes';
  if (head === null) return 'no';
  return baselineGit(cwd, ['merge-base', '--is-ancestor', base, head]);
}
async function baselineObjectsExist(cwd, rec) {
  for (const obj of [rec.head, rec.tree.split('\t')[0]].filter((x) => x !== null)) {
    const got = await baselineGit(cwd, ['cat-file', '-e', obj]);
    if (got !== 'yes') return got;
  }
  return 'yes';
}
function baselinePath(root, digest, home = path.resolve(stateHome())) {
  return path.join(home, 'ai-kit', 'spec', 'baselines', sha16(root), digest + '.json');
}
function baselineNote(text) {
  if (!baselineNoted) {
    baselineNoted = true;
    log(`cross-ai: note: ${text}; this call keeps its baseline in memory`);
  }
}
async function resolveBaseline(root, before, prompt, lane, flag, capS) {
  baselineFile = baselinePath(root, taskDigest(prompt));
  const fresh = { head: before.head, tree: before.tree, at: Date.now(), role: 'execute', cli: lane.cli, model: lane.model };
  let base = flag ? { ...fresh, head: flag.head, tree: [flag.treeId, ...before.tree.split('\t').slice(1)].join('\t'), source: 'flag' } : null;
  let keep = false;
  if (!flag) {
    let text = null;
    try { text = fs.readFileSync(baselineFile, 'utf8'); } catch (e) {
      if (e.code !== 'ENOENT') baselineNote(`baseline record not read (${e.code || e.message})`);
    }
    if (text !== null) {
      const rec = parseJson(text); const now = Date.now();
      let verdict = baselineVerdict(rec, now, capS, true);
      if (verdict.reuse) {
        const objects = await baselineObjectsExist(process.cwd(), rec);
        if (objects === 'no') verdict = { reason: `missing: ${String(rec.head ?? rec.tree.split('\t')[0]).slice(0, 12)} is not in this repository` };
        else if (objects === 'unknown') { keep = true; baselineNote('baseline record not checked (git unavailable)'); }
        else {
          const d = await headDescends(process.cwd(), rec.head, before.head);
          if (d === 'unknown') { keep = true; baselineNote('baseline ancestry not readable (git unavailable)'); }
          else verdict = baselineVerdict(rec, now, capS, d === 'yes');
        }
      }
      if (!keep && verdict.reuse) base = { head: rec.head, tree: rec.tree, at: rec.at, role: 'execute', cli: typeof rec.cli === 'string' ? rec.cli : lane.cli, model: typeof rec.model === 'string' ? rec.model : lane.model, source: 'record' };
      if (!keep && !verdict.reuse) addFinding('baseline_replaced', verdict.reason);
    }
  }
  if (!base) base = { ...fresh, source: 'fresh' };
  if (base.source !== 'record' && !keep && !baselineNoted) {
    try {
      writeCycleState(baselineFile, { version: BASELINE_RECORD_VERSION, head: base.head, tree: base.tree, at: base.at, role: base.role, cli: base.cli, model: base.model });
    } catch (e) { baselineNote(`baseline record not written (${e.code || e.message})`); }
  }
  if (keep) baselineFile = null; // An unchecked record must survive even a successful call.
  liveBaseline = base;
  lockUpdate({ baseline: { head: base.head, tree: base.tree, at: base.at, role: base.role, cli: base.cli, model: base.model } });
}

function stateSig(st) {
  if (!st) return null;
  return `${st.head ?? ''}\t${st.tree ?? ''}`;
}

function treeLabel(before, after) {
  if (!before || !after) return 'unknown';
  return stateSig(before) === stateSig(after) ? 'clean' : 'dirty';
}

// Bookkeeping for a supervisor that may have to reap a runner which can no longer run its
// own signal handler. A write error logs once and never fails the run; later writes skip.
function noteChildPgid(kind, pid) {
  if (!childPgidFile || childPgidBroken || !pid) return;
  try {
    fs.appendFileSync(childPgidFile, `${kind} ${pid}\n`);
  } catch {
    childPgidBroken = true;
    log(`cross-ai: --child-pgid-file unwritable: ${childPgidFile}`);
  }
}

function killGroup(child, sig) {
  if (!child || !child.pid) return;
  try { process.kill(-child.pid, sig); } catch { try { child.kill(sig); } catch { /* gone */ } }
}

function waitForExit(child, ms) {
  return new Promise((resolve) => {
    if (!child || child.exitCode !== null) return resolve(true);
    const t = setTimeout(() => resolve(false), ms);
    child.once('exit', () => { clearTimeout(t); resolve(true); });
  });
}

function drainStream(stream, ms) {
  return new Promise((resolve) => {
    if (!stream || stream.readableEnded) return resolve();
    const t = setTimeout(resolve, ms);
    stream.on('end', () => { clearTimeout(t); resolve(); });
    stream.on('close', () => { clearTimeout(t); resolve(); });
    stream.resume();
  });
}

function captureMaxBytes(text) {
  const max = 32 * 1024 * 1024;
  const s = String(text ?? '');
  if (!/^\d{1,9}$/.test(s)) return max;
  const n = Number(s);
  return n >= 65536 && n <= max ? n : max;
}
// A noisy child must not exhaust memory before the status line: keep only the newest bytes per stream.
const CAPTURE_MAX_BYTES = 32 * 1024 * 1024;
// Test-only knob (38-19): lowers only the lane captures of runOnce, never a git or listing read.
const LANE_CAPTURE_MAX_BYTES = captureMaxBytes(process.env.AIKIT_XAI_CAPTURE_MAX_BYTES);

function pushCapped(buf, d, max = CAPTURE_MAX_BYTES) {
  buf.chunks.push(d);
  buf.bytes += d.length;
  while (buf.bytes > max) {
    const over = buf.bytes - max;
    const first = buf.chunks[0];
    if (first.length <= over) { buf.chunks.shift(); buf.bytes -= first.length; }
    else { buf.chunks[0] = first.subarray(over); buf.bytes -= over; }
    buf.dropped = true;
  }
}

function runChild(bin, argv, opts = {}) {
  const capMs = opts.capMs ?? Number.POSITIVE_INFINITY;
  const limit = opts.limit ?? finalizeBy;
  const spawnMs = budgetMs(capMs, limit);
  if (spawnMs <= 0) {
    return Promise.resolve({ code: null, signal: null, timedOut: true, spawnErr: null, stdout: '', stderr: '' });
  }
  return new Promise((resolve) => {
    let settled = false;
    let child = null;
    let timer = null;
    let timedOut = false;
    let limited = false;
    let spawnErr = null;
    let idle = false;
    let idleTimer = null;
    let lastByteMs = 0;
    let code = null;
    let signal = null;
    const out = { chunks: [], bytes: 0, dropped: false };
    const err = { chunks: [], bytes: 0, dropped: false };

    // Caps are read when each wait starts, so a signal mid-finalize shortens what is left.
    const finalize = async (reason) => {
      if (settled) return;
      settled = true;
      opts.bg?.stops.delete(finalize);
      if (timer) clearTimeout(timer);
      if (idleTimer) clearTimeout(idleTimer);
      if (currentFinalize === finalize) currentFinalize = null;
      if (child) {
        killGroup(child, 'SIGTERM');
        if (reason === 'limit') limited = true;
        if (child.exitCode === null && reason !== 'exit') {
          await waitForExit(child, budgetMs(aborting ? SIGNAL_GRACE_MS : KILL_GRACE_MS, finalizeBy));
        }
        killGroup(child, 'SIGKILL');
        const drainMs = budgetMs(aborting ? SIGNAL_DRAIN_MS : PIPE_DRAIN_MS, finalizeBy);
        await Promise.all([drainStream(child.stdout, drainMs), drainStream(child.stderr, drainMs)]);
        child.stdout?.removeAllListeners('data');
        child.stderr?.removeAllListeners('data');
        child.stdin?.destroy();
        child.stdout?.destroy();
        child.stderr?.destroy();
        noteChildPgid('exit', child.pid);
      }
      if (current === child) current = null;
      for (const [label, buf] of [['stdout', out], ['stderr', err]]) {
        if (buf.dropped) log(`cross-ai: child ${label} passed ${opts.captureMax ?? CAPTURE_MAX_BYTES} bytes; kept the newest ${buf.bytes}`);
      }
      resolve({
        code, signal, timedOut, limited, idle, spawnErr,
        stdoutDropped: out.dropped,
        stdout: Buffer.concat(out.chunks).toString('utf8'),
        stderr: Buffer.concat(err.chunks).toString('utf8'),
      });
    };

    timer = setTimeout(() => { timedOut = true; finalize('timeout'); }, spawnMs);
    try {
      // An argv prompt carries its text on argv, so stdin is closed off (`ignore`) and never
      // inherited from the runner.
      const stdinMode = opts.input === null ? 'ignore' : 'pipe';
      child = spawn(bin, argv, {
        cwd: opts.cwd, env: opts.env, stdio: [stdinMode, 'pipe', 'pipe'], detached: true,
      });
    } catch (e) {
      spawnErr = e;
      finalize('spawn');
      return;
    }
    noteChildPgid('spawn', child.pid);
    // Only runOnce passes onSpawn: git snapshot and listing children never reach the lock record.
    opts.onSpawn?.(child.pid);
    // Background reads must not replace the lane for signal or limit handling.
    if (!opts.bg) current = child;
    // SPEC R1 / D-01: opt-in (runOnce only); any child byte resets the clock, the runner's own lines never do; finalize settles once.
    if (opts.idleMs > 0) {
      lastByteMs = performance.now();
      const idleQuiet = () => performance.now() - lastByteMs;
      const idleCheck = () => {
        idleTimer = null;
        if (settled || aborting) return;
        if (idleQuiet() < opts.idleMs) {
          idleTimer = setTimeout(idleCheck, opts.idleMs - idleQuiet());
          return;
        }
        // The setImmediate turn lets a data event already queued at the boundary reset the clock first: activity wins the tie.
        setImmediate(() => {
          if (settled || aborting || idleTimer) return;
          if (idleQuiet() < opts.idleMs) {
            idleTimer = setTimeout(idleCheck, opts.idleMs - idleQuiet());
            return;
          }
          if (opts.onIdle && opts.onIdle() === false) {
            idleTimer = setTimeout(idleCheck, opts.idleMs);
            return;
          }
          idle = true;
          timedOut = true;
          finalize('idle');
        });
      };
      idleTimer = setTimeout(idleCheck, opts.idleMs);
      // Seam for plan 38-16: reset() counts as a child byte (a changed tree read); recheck() re-runs the idle decision once a deferred read is in; onIdle returning false defers an expiry.
      opts.idleResetter?.({ reset: () => { if (!settled) lastByteMs = performance.now(); }, recheck: () => { if (settled) return; if (idleTimer) { clearTimeout(idleTimer); idleTimer = null; } idleCheck(); } });
    }
    if (opts.bg) opts.bg.stops.add(finalize); else currentFinalize = finalize;
    if (opts.input === null) {
      // stdin is `ignore`: there is no stream to write or end.
    } else if (opts.input !== undefined) {
      child.stdin.on('error', () => { /* closed early */ });
      child.stdin.end(opts.input);
    } else {
      child.stdin.end();
    }
    child.stdout.on('data', (d) => {
      if (opts.idleMs > 0) lastByteMs = performance.now();
      pushCapped(out, d, opts.captureMax);
      opts.onStdout?.(d);
    });
    child.stderr.on('data', (d) => {
      if (opts.idleMs > 0) lastByteMs = performance.now();
      pushCapped(err, d, opts.captureMax);
      opts.onStderr?.(d);
    });
    child.on('error', (e) => { spawnErr = e; finalize('error'); });
    child.on('exit', (c, s) => { code = c; signal = s; finalize('exit'); });
  });
}

// Hosted lane (SPEC R12, D-22 to D-28): herdr is called only by the transport in this block.
const HERDR_BIN = 'herdr';
// D-23/D-28: availability is HERDR_ENV=1 plus a herdr on PATH, read without calling herdr.
function hostAvailable(env, whichFn = which) {
  return env.HERDR_ENV === '1' && Boolean(env.PATH) && Boolean(whichFn(HERDR_BIN, env.PATH));
}

// D-22 / 0b-6 / 38 D-27: the only herdr commands the runner runs; tab list is read by the sweep only.
const HERDR_VERBS = Object.freeze(['tab create', 'pane run', 'tab close', 'tab list']);
const HERDR_TIMEOUT_MS = 5000;

// The one herdr spawn site (arch rule): a verb outside HERDR_VERBS throws.
function herdrCall(verb, args, timeoutMs = HERDR_TIMEOUT_MS) {
  if (!HERDR_VERBS.includes(verb)) throw new Error(`herdr verb ${verb} is not one of ${HERDR_VERBS.join(', ')}`);
  const r = spawnSync(HERDR_BIN, [...verb.split(' '), ...args], { encoding: 'utf8', timeout: Math.max(1, timeoutMs), killSignal: 'SIGKILL', stdio: ['ignore', 'pipe', 'pipe'], env: process.env });
  let detail = null;
  if (r.error) detail = r.error.code === 'ETIMEDOUT' ? 'timeout' : `spawn ${r.error.code || r.error.message}`;
  else if (r.signal) detail = `signal ${r.signal}`;
  else if (r.status !== 0) detail = `exit ${r.status}`;
  // herdr prints a server error as one JSON line on stderr: {"error":{"code":...}} (live 2026-11-16).
  // JSON.parse inline: the protocol test extracts herdrCall without other helpers.
  let code = null;
  if (detail !== null) { try { const parsed = JSON.parse(String(r.stderr || '').trim()); if (typeof parsed?.error?.code === 'string') code = parsed.error.code; } catch { /* not a herdr JSON error */ } }
  return { ok: detail === null, stdout: r.stdout || '', stderr: r.stderr || '', detail, code };
}

// SPEC R12 precision: one integer 0-255 or a signal name; anything else is a crash, never coerced.
function parseRc(text) {
  const body = String(text ?? '').replace(/\n$/, '');
  if (body === '') return null;
  if (/^(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)$/.test(body)) return { code: Number(body), signal: null };
  if (/^SIG[A-Z0-9]{2,8}$/.test(body)) return { code: null, signal: body };
  return { code: null, signal: null, bad: body.split('\n')[0].replace(/[\x00-\x1f\x7f-\x9f]/g, '').slice(0, 80) };
}

function hostStartProblem(dir) {
  if (!HOST_PATH_SAFE.test(dir)) return 'state home path holds a character outside [A-Za-z0-9._/-]';
  const tool = HOST_TOOLS.find((item) => !isExec(item));
  return tool ? `${tool} is not executable` : null;
}

// D-24 to D-27: the hosted-lane protocol (pinned by tests/fixtures/runner_host_protocol.json).
const HOST_LABEL_PREFIX = 'aikit';
const HOST_PATH_SAFE = /^[A-Za-z0-9._\/-]+$/;
const HOST_FILES = Object.freeze({ run: 'run.json', launcher: 'launch.sh', env: 'env', prompt: 'prompt', out: 'out', err: 'err', pid: 'pid', rc: 'rc' });
const HOST_TOOLS = Object.freeze(['/bin/sh', '/usr/bin/env', '/bin/rm', '/bin/mv', '/bin/cat']);
const HOST_SETSID = '/usr/bin/setsid';
const RUN_RECORD_VERSION = 1;

// Run time and self-test both use it (moved from the self-test helpers for the hosted lane).
function pidAlive(pid) {
  try { process.kill(pid, 0); } catch { return false; }
  try { return !/^\d+ \(.*\) Z/.test(fs.readFileSync(`/proc/${pid}/stat`, 'utf8')); } catch { return true; }
}

function shQuote(value) {
  const text = String(value);
  if (text.includes('\0')) throw new Error('argv element holds a NUL byte');
  return "'" + text.replace(/'/g, "'\\''") + "'";
}

function hostToken() {
  return crypto.randomBytes(6).toString('hex');
}

function hostLabel(role, runtime, token) {
  return `${HOST_LABEL_PREFIX}:${role}:${runtime}:${token}`;
}

function hostRunDir(home, token) {
  return path.join(home, 'ai-kit', 'spec', 'host', token);
}

function writePrivate(file, text) {
  const fd = fs.openSync(file, 'wx', 0o600);
  try { fs.writeFileSync(fd, text); } finally { fs.closeSync(fd); }
}

// Field 22 (start ticks), parsed after the last ')' so a command name with spaces cannot shift it (0b-3).
function procStartTime(pid) {
  try {
    const stat = fs.readFileSync(`/proc/${pid}/stat`, 'utf8');
    const fields = stat.slice(stat.lastIndexOf(')') + 1).trim().split(/\s+/);
    return /^\d+$/.test(fields[19]) ? fields[19] : '-';
  } catch { return '-'; }
}

function procGroup(pid) {
  try {
    const stat = fs.readFileSync(`/proc/${pid}/stat`, 'utf8');
    const fields = stat.slice(stat.lastIndexOf(')') + 1).trim().split(/\s+/);
    return /^\d+$/.test(fields[2]) ? Number(fields[2]) : null;
  } catch { return null; }
}

// Field 6 (session id), parsed after the last ')' like procGroup.
function procSession(pid) {
  try {
    const stat = fs.readFileSync(`/proc/${pid}/stat`, 'utf8');
    const fields = stat.slice(stat.lastIndexOf(')') + 1).trim().split(/\s+/);
    return /^\d+$/.test(fields[3]) ? Number(fields[3]) : null;
  } catch { return null; }
}

// Live members of process group `pgid` inside session `sid`. Neither id is reused while a member
// lives, so a signal to -pgid then reaches only that group.
function groupMembers(pgid, sid) {
  if (!Number.isInteger(pgid) || pgid <= 1 || !Number.isInteger(sid)) return [];
  let names;
  try { names = fs.readdirSync('/proc'); } catch { return []; }
  const members = [];
  for (const name of names) {
    if (!/^\d+$/.test(name)) continue;
    let stat;
    try { stat = fs.readFileSync(`/proc/${name}/stat`, 'utf8'); } catch { continue; }
    const fields = stat.slice(stat.lastIndexOf(')') + 1).trim().split(/\s+/);
    if (fields[0] !== 'Z' && Number(fields[2]) === pgid && Number(fields[3]) === sid) members.push(Number(name));
  }
  return members;
}

function hostTypedLine(files) {
  return 'sh ' + files.launcher;
}

function hostEnvText(env) {
  const lines = [];
  let skipped = 0;
  for (const [name, value] of Object.entries(env)) {
    if (/^[A-Za-z_][A-Za-z0-9_]*$/.test(name)) lines.push(`export ${name}=${shQuote(value)}`);
    else skipped++;
  }
  return { text: lines.join('\n') + '\n', skipped };
}

// 0b-2: clean environment in its own group, env file, prompt fd or variable, delete both, pid; rc is renamed into place after out and err close.
function buildLauncher(lane, files, token) {
  const stdinPrompt = lane.input !== null;
  const argvPrompt = lane.promptArg !== undefined && lane.promptArg !== null;
  const at = argvPrompt ? lane.argv.indexOf(lane.promptArg) : -1;
  if (argvPrompt && at < 0) throw new Error('argv prompt element not found');
  const q = shQuote;
  const quotedArgv = lane.argv.map(q);
  const command = [q(lane.bin), ...quotedArgv.map((el, i) => (i === at ? '"$aikit_prompt"' : el))].join(' ');
  const lines = [
    '#!/bin/sh',
    `[ "\${AIKIT_HOST_CLEAN:-}" = ${q(token)} ] || { [ -x /usr/bin/setsid ] && exec /usr/bin/env -i AIKIT_HOST_CLEAN=${q(token)} /usr/bin/setsid /bin/sh "$0"; exec /usr/bin/env -i AIKIT_HOST_CLEAN=${q(token)} /bin/sh "$0"; }`,
    'unset AIKIT_HOST_CLEAN',
    `. ${q(files.env)}`,
  ];
  if (stdinPrompt) lines.push(`exec 3< ${q(files.prompt)}`);
  if (argvPrompt) lines.push(`aikit_prompt=$(/bin/cat ${q(files.prompt)}; printf x); aikit_prompt=\${aikit_prompt%x}`);
  lines.push(`/bin/rm -f ${q(files.env)}${stdinPrompt || argvPrompt ? ' ' + q(files.prompt) : ''}`);
  lines.push(`printf '%s\\n' "$$" > ${q(files.pid + '.tmp')} && /bin/mv ${q(files.pid + '.tmp')} ${q(files.pid)}`);
  lines.push(`printf 'AIKIT-HOST-START %s\\n' ${q(token)}`);
  lines.push(`cd ${q(lane.cwd)} && ${command}${stdinPrompt ? ' <&3 3<&-' : ' < /dev/null'} >> ${q(files.out)} 2>> ${q(files.err)}`);
  lines.push('rc=$?');
  if (stdinPrompt) lines.push('exec 3<&-');
  if (argvPrompt) lines.push('unset aikit_prompt');
  lines.push('if [ "$rc" -gt 128 ] && sig=$(kill -l "$rc" 2>/dev/null); then rc="SIG$sig"; fi');
  lines.push(`printf '%s\\n' "$rc" > ${q(files.rc + '.tmp')} && /bin/mv ${q(files.rc + '.tmp')} ${q(files.rc)}`);
  lines.push(`printf 'AIKIT-HOST-DONE %s rc=%s\\n' ${q(token)} "$rc"`);
  return lines.join('\n') + '\n';
}

// 0b-3: run.json first, then env and prompt; the tab comes after (plan 37-20).
function writeRunDir(home, token, lane) {
  const dir = hostRunDir(home, token);
  const files = Object.fromEntries(Object.entries(HOST_FILES).map(([key, name]) => [key, path.join(dir, name)]));
  const label = hostLabel(lane.role, lane.runtime, token);
  const launcher = buildLauncher(lane, files, token);
  let checkout;
  try { checkout = fs.realpathSync(lane.cwd); } catch { checkout = lane.cwd; }
  const record = { version: RUN_RECORD_VERSION, token, runner_pid: process.pid, runner_start: procStartTime(process.pid), host_name: os.hostname(), checkout_root: checkout, role: lane.role, runtime: lane.runtime, label, tab_id: null, pane_id: null, launcher_pid: null, launcher_pgid: null, launcher_start: null, created_ms: Date.now() };
  writeCycleState(files.run, record);
  const envText = hostEnvText(lane.env || {});
  writePrivate(files.env, envText.text);
  const prompted = lane.input !== null || (lane.promptArg !== undefined && lane.promptArg !== null);
  if (lane.input !== null) writePrivate(files.prompt, String(lane.input ?? ''));
  else if (prompted) writePrivate(files.prompt, String(lane.promptArg));
  writePrivate(files.launcher, launcher);
  writePrivate(files.out, '');
  writePrivate(files.err, '');
  return { dir, files, label, record, prompted, envSkipped: envText.skipped };
}

// D-23: none from the flag or AIKIT_HOST wins; auto from either asks for hosting; anything else is ignored with a note.
function hostSettingValue(flag, envValue) {
  const env = typeof envValue === 'string' ? envValue.trim() : '';
  const safe = redactSecrets(redactSecrets(env).replace(/[\x00-\x1f\x7f-\x9f]/g, '')).slice(0, 40);
  const note = env && env !== 'auto' && env !== 'none' ? `cross-ai: AIKIT_HOST=${safe} is not auto or none; ignored` : null;
  if (flag === 'none' || env === 'none') return { value: 'none', note };
  if (flag === 'auto' || env === 'auto') return { value: 'auto', note };
  return { value: null, note };
}

// 0b-4: 250 ms measured 0.08 % of a core.
const HOST_POLL_MS = 250;
const HOST_ID_RX = /^[A-Za-z0-9._:-]{1,64}$/;
const HOST_ADMIT_GRACE_MS = 1000;
// Review c1: a pane shell may take seconds to start the typed line; no pid by then means not started or dead.
const HOST_PID_GRACE_MS = 5000;

function closeTab(tabId, timeoutMs = HERDR_TIMEOUT_MS) {
  const r = herdrCall('tab close', [tabId], timeoutMs);
  // 38 D-27: tab_not_found means the tab is already gone (closed by hand or by herdr), not a failure.
  if (r.ok || r.code === 'tab_not_found') { openTabs.delete(tabId); return true; }
  log(`cross-ai: host: tab close ${tabId} failed (${r.detail})`);
  return false;
}
function dropSecrets(dir) {
  for (const name of [HOST_FILES.env, HOST_FILES.prompt]) {
    try { fs.rmSync(path.join(dir, name), { force: true }); } catch { /* best effort */ }
  }
}
function keepRecordOnly(dir, tabId) {
  try { for (const name of fs.readdirSync(dir)) if (name !== HOST_FILES.run) fs.rmSync(path.join(dir, name), { force: true }); } catch { /* best effort */ }
  tempDirs.delete(dir);
  log(`cross-ai: host: kept ${dir}/run.json for tab ${tabId ?? '-'} (close not confirmed)`);
}
async function waitDead(pid, ms) {
  const end = Date.now() + ms;
  while (pidAlive(pid) && Date.now() < end) await sleep(50);
}
async function waitForFile(file, ms) {
  const end = Date.now() + ms;
  while (!fs.existsSync(file) && Date.now() < end) await sleep(100);
  return fs.existsSync(file);
}
// Review c1: signal only a verified group leader with an unchanged start time; anything unreadable means no signal.
function launcherVerified(pid, recordedStart, currentStart, currentGroup) {
  return recordedStart !== '-' && currentStart === recordedStart && currentGroup === pid;
}
async function hostedChild(bin, argv, opts) {
  const capMs = opts.capMs ?? Number.POSITIVE_INFINITY;
  const limit = opts.limit ?? finalizeBy;
  const none = { code: null, signal: null, timedOut: false, limited: false, spawnErr: null, stdout: '', stderr: '' };
  if (budgetMs(capMs, limit) <= 0) return { ...none, timedOut: true };
  const home = path.resolve(stateHome());
  const token = hostToken();
  const dir = hostRunDir(home, token);
  const problem = hostStartProblem(dir);
  if (problem) return { hostFailed: problem, rerun: true };
  const laneCwd = opts.cwd || process.cwd();
  let made;
  try {
    made = writeRunDir(home, token, { role: opts.host.role, runtime: opts.host.runtime, cwd: laneCwd, bin, argv, env: opts.env || process.env, input: opts.input === undefined ? '' : opts.input, promptArg: opts.promptArg });
  } catch (e) {
    try { fs.rmSync(dir, { recursive: true, force: true }); } catch { /* best effort */ }
    return { hostFailed: `run directory not written (${e.code || e.message})`, rerun: true };
  }
  tempDirs.add(dir);
  if (made.envSkipped) log(`cross-ai: host: ${made.envSkipped} environment names are not shell names and are not passed`);
  let tabId = null;
  let stop = null;
  let typedSent = false;
  const startupFinalize = (reason) => { stop = reason; };
  currentFinalize = startupFinalize;
  const startupEnd = (result) => {
    dropSecrets(dir);
    if (tabId !== null && !closeTab(tabId, Math.max(500, budgetMs(HERDR_TIMEOUT_MS, finalizeBy)))) keepRecordOnly(dir, tabId);
    else dropTemp(dir);
    if (currentFinalize === startupFinalize) currentFinalize = null;
    return result;
  };
  let record;
  try {
    const created = herdrCall('tab create', ['--label', made.label, '--no-focus', '--cwd', laneCwd]);
    const answer = created.ok ? parseJson(created.stdout.trim()) : null;
    const id = answer?.result?.tab?.tab_id;
    const paneId = answer?.result?.root_pane?.pane_id;
    if (!HOST_ID_RX.test(id || '')) {
      if (!created.ok && String(created.detail).startsWith('exit ')) return startupEnd({ hostFailed: `tab create failed (${created.detail})`, rerun: true });
      dropSecrets(dir);
      keepRecordOnly(dir, null);
      if (currentFinalize === startupFinalize) currentFinalize = null;
      return { hostFailed: `tab create answer lost (${created.detail || 'no tab id in its answer'}); kept the run record for the sweep`, rerun: true };
    }
    tabId = id;
    openTabs.set(tabId, dir);
    if (aborting || stop) return startupEnd(none);
    if (!HOST_ID_RX.test(paneId || '')) return startupEnd({ hostFailed: 'tab create failed (no pane id in its answer)', rerun: true });
    record = { ...made.record, tab_id: tabId, pane_id: paneId };
    writeCycleState(made.files.run, record);
    lockUpdate({ token: made.record.token, tab_id: tabId, host_ms: Date.now() });
    log(`cross-ai: host herdr tab=${tabId} label=${made.label}`);
    typedSent = true;
    const typed = herdrCall('pane run', [paneId, hostTypedLine(made.files)]);
    if (aborting || stop) return startupEnd(none);
    if (!typed.ok) {
      const definite = String(typed.detail).startsWith('exit ');
      const started = await waitForFile(made.files.pid, definite ? HOST_ADMIT_GRACE_MS : HOST_PID_GRACE_MS);
      if (aborting || stop) return startupEnd(none);
      if (!started) return startupEnd({ hostFailed: definite ? `pane run failed (${typed.detail})` : `pane run answer unclear (${typed.detail})`, rerun: definite });
    }
  } catch (e) { return startupEnd({ hostFailed: `startup failed (${e.code || e.message})`, rerun: !typedSent }); }
  return new Promise((resolve) => {
    let settled = false, timer = null, poller = null, timedOut = false, limited = false;
    let idle = false, idleTimer = null, lastByteMs = 0;
    const out = { chunks: [], bytes: 0, dropped: false }, err = { chunks: [], bytes: 0, dropped: false };
    const pos = { out: 0, err: 0 };
    const cutFailed = { out: false, err: false };
    const cap = opts.captureMax ?? CAPTURE_MAX_BYTES;
    const fds = { out: fs.openSync(made.files.out, 'r+'), err: fs.openSync(made.files.err, 'r+') };
    let launcherPid = null, launcherStart = null, launcherSid = null, verified = false, pseudo = null;
    const pidDeadline = Date.now() + HOST_PID_GRACE_MS;
    const readNew = (key) => {
      const buf = Buffer.alloc(65536);
      let n;
      while ((n = fs.readSync(fds[key], buf, 0, buf.length, pos[key])) > 0) {
        pos[key] += n;
        if (opts.idleMs > 0) lastByteMs = performance.now();
        const d = Buffer.from(buf.subarray(0, n));
        pushCapped(key === 'out' ? out : err, d, cap);
        if (key === 'out') opts.onStdout?.(d); else opts.onStderr?.(d);
        // Cut the same inode after twice the cap and resume at offset zero next poll.
        // A failed cut keeps the offset (the file then grows): rereading it would relay old bytes and feed the idle clock.
        if (pos[key] > 2 * cap && !cutFailed[key]) {
          try { fs.ftruncateSync(fds[key], 0); pos[key] = 0; break; } catch (e) {
            cutFailed[key] = true; log(`cross-ai: host: could not cut ${key} (${e.code || e.message})`);
          }
        }
      }
    };
    // One path for the poll and for a finalize that runs before the first poll saw the pid: the
    // group is registered and run.json names the launcher, so a kept record can still be swept.
    const leaderAlive = () => launcherVerified(launcherPid, launcherStart, procStartTime(launcherPid), procGroup(launcherPid));
    // R12: the lane's group ends on every exit, like the headless kill. A live verified leader, or a
    // member left in the leader's group and session, keeps the group id in use. A launcher already gone
    // when its pid was first read cannot be verified; then only members of the session it made itself
    // (session id = group id = its pid, from setsid) are signalled.
    const groupAlive = () => launcherPid !== null && ((verified && leaderAlive()) || groupMembers(launcherPid, verified ? launcherSid : launcherPid).length > 0);
    const signalGroup = (sig) => { try { process.kill(-launcherPid, sig); } catch { /* gone */ } };
    const adoptPid = () => {
      const pidText = readOr(made.files.pid, '');
      if (launcherPid !== null || !/^\d+\n?$/.test(pidText)) return;
      launcherPid = Number(pidText); launcherStart = procStartTime(launcherPid);
      const group = procGroup(launcherPid);
      verified = launcherVerified(launcherPid, launcherStart, launcherStart, group);
      if (verified) { launcherSid = procSession(launcherPid); pseudo = { pid: launcherPid, kill: (sig) => { try { if (leaderAlive()) process.kill(launcherPid, sig); } catch { /* gone */ } } }; current = pseudo; }
      else log(`cross-ai: host: launcher ${launcherPid} is not a verified group leader; not signalled`);
      noteChildPgid('spawn', launcherPid);
      record = { ...record, launcher_pid: launcherPid, launcher_pgid: group, launcher_start: launcherStart };
      writeCycleState(made.files.run, record);
      // 38 D-26: the lock record names the hosted lane's token, tab and launcher group (a review lane holds no lock: no-op).
      lockUpdate({ token: made.record.token, tab_id: record.tab_id, launcher_pid: launcherPid, launcher_pgid: group, launcher_start: launcherStart });
    };
    const finalize = async (reason, rc = null) => {
      if (settled) return;
      settled = true;
      clearInterval(poller); clearTimeout(timer); clearTimeout(idleTimer);
      if (currentFinalize === finalize) currentFinalize = null;
      if (reason === 'limit') limited = true;
      // A signal can arrive after the launcher starts but before the first poll.
      adoptPid();
      if (groupAlive()) {
        signalGroup('SIGTERM');
        if (!['exit', 'dead', 'nopid'].includes(reason)) await waitDead(launcherPid, budgetMs(aborting ? SIGNAL_GRACE_MS : KILL_GRACE_MS, finalizeBy));
        if (groupAlive()) signalGroup('SIGKILL');
      }
      readNew('out'); readNew('err');
      fs.closeSync(fds.out); fs.closeSync(fds.err);
      dropSecrets(dir);
      const closed = closeTab(tabId, Math.max(500, budgetMs(HERDR_TIMEOUT_MS, finalizeBy)));
      if (closed) dropTemp(dir); else keepRecordOnly(dir, tabId);
      if (launcherPid !== null) noteChildPgid('exit', launcherPid);
      if (current === pseudo) current = null;
      for (const [label, buf] of [['stdout', out], ['stderr', err]]) {
        if (buf.dropped) log(`cross-ai: child ${label} passed ${cap} bytes; kept the newest ${buf.bytes}`);
      }
      let code = null, signal = null;
      if (rc?.bad) log(redactSecrets(`cross-ai: host: rc file is not an exit code: ${rc.bad}`));
      else if (rc) { code = rc.code; signal = rc.signal; }
      // shortcut: the launcher died without writing rc; the real signal is unknown, reported as SIGKILL.
      else if (reason === 'dead') signal = 'SIGKILL';
      else if (reason === 'nopid') log(`cross-ai: host: the launcher wrote no pid within ${HOST_PID_GRACE_MS} ms; not rerun`);
      else if (launcherPid !== null) signal = 'SIGTERM';
      resolve({ code, signal, timedOut, limited, idle, spawnErr: null, stdout: Buffer.concat(out.chunks).toString('utf8'), stderr: Buffer.concat(err.chunks).toString('utf8') });
    };
    const tick = () => {
      if (settled) return;
      try {
        readNew('out'); readNew('err');
        adoptPid();
        const rc = parseRc(readOr(made.files.rc, ''));
        if (rc !== null) { finalize('exit', rc); return; }
        if (launcherPid !== null && !pidAlive(launcherPid)) { const late = parseRc(readOr(made.files.rc, '')); finalize(late ? 'exit' : 'dead', late); }
        else if (launcherPid === null && Date.now() > pidDeadline) finalize('nopid');
      } catch (e) { log(`cross-ai: host: poll failed (${e.code || e.message})`); finalize('dead'); }
    };
    currentFinalize = finalize;
    timer = setTimeout(() => { timedOut = true; finalize('timeout'); }, budgetMs(capMs, limit));
    poller = setInterval(tick, HOST_POLL_MS);
    // 38 D-28: the hosted idle clock counts bytes read from the output files.
    if (opts.idleMs > 0) {
      lastByteMs = performance.now();
      const idleQuiet = () => performance.now() - lastByteMs;
      const idleCheck = () => {
        idleTimer = null;
        if (settled || aborting) return;
        if (idleQuiet() < opts.idleMs) { idleTimer = setTimeout(idleCheck, opts.idleMs - idleQuiet()); return; }
        setImmediate(() => {
          if (settled || aborting || idleTimer) return;
          tick();
          if (settled) return;
          if (idleQuiet() < opts.idleMs) { idleTimer = setTimeout(idleCheck, opts.idleMs - idleQuiet()); return; }
          if (opts.onIdle && opts.onIdle() === false) { idleTimer = setTimeout(idleCheck, opts.idleMs); return; }
          idle = true; timedOut = true; finalize('idle');
        });
      };
      idleTimer = setTimeout(idleCheck, opts.idleMs);
      opts.idleResetter?.({ reset: () => { if (!settled) lastByteMs = performance.now(); }, recheck: () => { if (settled) return; if (idleTimer) { clearTimeout(idleTimer); idleTimer = null; } idleCheck(); } });
    }
  });
}
function hostFailedNote(host, reason, rerun) {
  log(`cross-ai: host: ${reason}; ${rerun ? 'the lane runs headless' : 'the lane may have started, so it is not rerun'}`);
  host.failed = true; host.entry.state = 'ignored'; host.entry.reason = 'host_failed';
  for (const line of reportLines([host.entry])) log(line);
}

const SWEEP_HERDR_TIMEOUT_MS = 2000;
const SWEEP_BUDGET_MS = 4000;
const SWEEP_REREAD_MS = 2000;
const RUN_RECORD_MAX_BYTES = 65536;
const SWEEP_DIR_RX = /^([0-9a-f]{12})(?:\.sweep-(\d+)-(\d+|-))?$/;
const SWEEP_REASONS = Object.freeze(['unreadable', 'other host', 'live launcher', 'hosting off', 'herdr unreachable', 'tab unproven', 'close failed', 'cleanup failed']);

function runnerAlive(rec) {
  if (!lockPidAlive(rec.runner_pid)) return false;
  const now = lockStartTime(rec.runner_pid);
  return rec.runner_start === '-' || now === '-' || now === rec.runner_start;
}
function launcherGroupAlive(rec) {
  return Number.isInteger(rec.launcher_pgid) && lockGroupAlive(rec.launcher_pgid, rec.launcher_start);
}
function readRunRecord(dir, token) {
  const file = path.join(dir, HOST_FILES.run);
  try {
    const st = fs.lstatSync(file);
    if (!st.isFile() || st.size > RUN_RECORD_MAX_BYTES) return null;
    const fd = fs.openSync(file, fs.constants.O_RDONLY | (fs.constants.O_NOFOLLOW || 0));
    let raw;
    try {
      const fst = fs.fstatSync(fd);
      if (!fst.isFile() || fst.size > RUN_RECORD_MAX_BYTES || fst.ino !== st.ino || fst.dev !== st.dev) return null;
      raw = fs.readFileSync(fd, 'utf8');
      if (Buffer.byteLength(raw) > RUN_RECORD_MAX_BYTES) return null;
    } finally { fs.closeSync(fd); }
    const rec = parseJson(raw);
    return rec && typeof rec === 'object' && rec.version === RUN_RECORD_VERSION && rec.token === token &&
      ['review', 'execute'].includes(rec.role) && typeof rec.runtime === 'string' &&
      rec.label === hostLabel(rec.role, rec.runtime, token) && rec.label.length <= 63 &&
      Number.isInteger(rec.runner_pid) && rec.runner_pid > 0 && typeof rec.runner_start === 'string' &&
      typeof rec.host_name === 'string' && rec.host_name !== '' &&
      (rec.tab_id === null || (typeof rec.tab_id === 'string' && HOST_ID_RX.test(rec.tab_id))) &&
      (rec.launcher_pgid === null || (Number.isInteger(rec.launcher_pgid) && rec.launcher_pgid > 1)) &&
      (rec.launcher_start === null || typeof rec.launcher_start === 'string') ? rec : null;
  } catch { return null; }
}

// Claim dead runs, remove secrets, and close only a tab proven by the complete label.
async function sweepRuns({ explicit, hostingOff, onlyToken = null }) {
  const root = path.join(path.resolve(stateHome()), 'ai-kit', 'spec', 'host');
  let names = [];
  try { names = fs.readdirSync(root).sort(); } catch { /* nothing to sweep */ }
  const counts = Object.fromEntries(SWEEP_REASONS.map((r) => [r, 0]));
  let closed = 0, removed = 0, tabs;
  const me = `${process.pid}-${procStartTime(process.pid)}`;
  const safe = (s) => redactSecrets(redactSecrets(String(s)).replace(/[\x00-\x1f\x7f-\x9f]/g, ''));
  const budgetStart = performance.now();
  const timeout = () => Math.min(SWEEP_HERDR_TIMEOUT_MS, Math.max(0, Math.floor(SWEEP_BUDGET_MS - (performance.now() - budgetStart))));
  for (const name of names) {
    const m = SWEEP_DIR_RX.exec(name);
    if (!m) continue;
    const [, token, claimPid, claimStart] = m;
    if (onlyToken !== null && token !== onlyToken) continue;
    if (claimPid !== undefined) {
      const pid = Number(claimPid);
      if (lockPidAlive(pid)) { const start = lockStartTime(pid); if (claimStart === '-' || start === '-' || start === claimStart) continue; }
    }
    const dir = path.join(root, name);
    try { if (!fs.lstatSync(dir).isDirectory()) continue; } catch { continue; }
    let rec = readRunRecord(dir, token), mtime;
    const t0 = performance.now();
    try { mtime = fs.lstatSync(dir).mtimeMs; } catch { continue; }
    while (!rec && Date.now() - mtime < SWEEP_REREAD_MS && performance.now() - t0 < SWEEP_REREAD_MS) {
      await sleep(100);
      rec = readRunRecord(dir, token);
      try { mtime = fs.lstatSync(dir).mtimeMs; } catch { mtime = null; break; }
    }
    if (mtime === null) continue;
    if (!rec) {
      counts.unreadable++;
      log(safe(`cross-ai: sweep: unreadable record ${name} age ${Math.max(0, Math.floor((Date.now() - mtime) / 1000))}s; left alone`));
      continue;
    }
    if (rec.host_name !== os.hostname()) { counts['other host']++; continue; }
    if (runnerAlive(rec)) continue;
    // A runner killed before it adopted the launcher left only the pid file: never claim (and delete) a live one.
    if (launcherGroupAlive(rec) || (rec.launcher_pgid === null && pidFileLauncherAlive(readOr(path.join(dir, HOST_FILES.pid), '')))) { counts['live launcher']++; continue; }
    const claimed = path.join(root, `${token}.sweep-${me}`);
    if (claimed !== dir) { try { fs.renameSync(dir, claimed); } catch { continue; } }
    dropSecrets(claimed);
    try { for (const f of fs.readdirSync(claimed)) if (f !== HOST_FILES.run) fs.rmSync(path.join(claimed, f), { recursive: true, force: true }); } catch { /* checked below */ }
    let keep = null;
    try { if (fs.readdirSync(claimed).some((f) => f !== HOST_FILES.run)) keep = 'cleanup failed'; } catch { keep = 'cleanup failed'; }
    if (!keep && !explicit && hostingOff) keep = 'hosting off';
    else if (!keep && !hostAvailable(process.env)) keep = 'herdr unreachable';
    else if (!keep) {
      if (tabs === undefined) {
        const ms = timeout();
        const r = ms ? herdrCall('tab list', [], ms) : null;
        const listed = r?.ok ? parseJson(r.stdout.trim())?.result?.tabs : null;
        tabs = Array.isArray(listed) && listed.every((t) => t && typeof t === 'object' && typeof t.tab_id === 'string' && typeof t.label === 'string') ? listed : null;
      }
      if (tabs === null) keep = 'herdr unreachable';
      else {
        const matches = tabs.filter((t) => t.label === rec.label && (rec.tab_id === null || t.tab_id === rec.tab_id));
        if (rec.tab_id === null && matches.length > 1) keep = 'tab unproven';
        else if (matches.length && HOST_ID_RX.test(matches[0].tab_id)) {
          const ms = timeout();
          const r = ms ? herdrCall('tab close', [matches[0].tab_id], ms) : null;
          if (r?.ok) closed++;
          else if (!r || r.code === 'server_not_running' || r.detail === 'timeout') { tabs = null; keep = 'herdr unreachable'; }
          else if (r.code !== 'tab_not_found') keep = 'close failed';
        } else if (matches.length) keep = 'tab unproven';
      }
    }
    if (!keep) { try { fs.rmSync(claimed, { recursive: true, force: true }); removed++; } catch { keep = 'cleanup failed'; } }
    if (keep) {
      counts[keep]++;
      try { fs.renameSync(claimed, path.join(root, token)); } catch { /* retain claim for a later sweep */ }
    }
  }
  const kept = SWEEP_REASONS.reduce((n, r) => n + counts[r], 0);
  if (explicit || closed || removed || kept) {
    const reasons = kept ? SWEEP_REASONS.filter((r) => counts[r]).map((r) => `${r} ${counts[r]}`).join(', ') : '-';
    log(safe(`cross-ai: sweep: closed ${closed} tab(s), removed ${removed} run director(ies), kept ${kept} (${reasons})`));
  }
  return { closed, removed, kept };
}

function parsePiListingIds(stdout) {
  if (typeof stdout !== 'string') return null;
  let envelope = null;
  for (const line of stdout.split('\n')) {
    const t = line.trim();
    if (!t) continue;
    const parsed = parseJson(t);
    if (parsed && parsed.command === 'get_available_models') { envelope = parsed; break; }
  }
  if (!envelope || envelope.success !== true) return null;
  const modelsRaw = envelope.data && envelope.data.models;
  if (!Array.isArray(modelsRaw)) return null;
  const ids = [];
  const seen = new Set();
  for (const item of modelsRaw) {
    if (!item || typeof item !== 'object') continue;
    const bareId = item.id;
    const provider = item.provider;
    if (typeof bareId !== 'string' || !bareId.trim()) continue;
    if (typeof provider !== 'string' || !provider.trim()) continue;
    const full = `${provider}/${bareId}`;
    if (seen.has(full)) continue;
    seen.add(full);
    ids.push(full);
  }
  return ids;
}

function parseOpencodeListingIds(stdout) {
  if (typeof stdout !== 'string') return null;
  const ids = stdout.split('\n').map((l) => l.trim()).filter(Boolean);
  return ids;
}

// Mirrors detection.parse_cursor_models (D-10), which a parity test runs on the same fixtures:
// ANSI stripped, Python splitlines()/strip() rules, ASCII ids, and a nameless
// `id (current, default)` line counts only after the header. null = unrecognized output.
function parseCursorListingIds(stdout) {
  if (typeof stdout !== 'string') return null;
  const line = /^([A-Za-z0-9._-]+)(?: - .*| \((?:current|default|current, default)\))?$/;
  const space = '[\\t\\n\\v\\f\\r\\x1c-\\x20\\x85\\xa0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000]+';
  const strip = new RegExp(`^${space}|${space}$`, 'g');
  const ids = [];
  let header = false;
  let unrecognized = false;
  for (const raw of stdout.replace(/\x1B\[[0-9;?]*[A-Za-z]/g, '').split(/\r\n|[\n\r\v\f\x1c-\x1e\x85\u2028\u2029]/)) {
    const ln = raw.replace(strip, '');
    if (ln === 'Available models') { header = true; continue; }
    if (!ln || ln.startsWith('Tip:') || ln === 'No models available for this account.') continue;
    const m = line.exec(ln);
    if (m && (header || ln.includes(' - '))) ids.push(m[1]);
    else unrecognized = true;
  }
  return ids.length || !unrecognized ? ids : null;
}

function parseCodexListingIds(stdout) {
  if (typeof stdout !== 'string') return null;
  const data = parseJson(stdout);
  if (!data || !Array.isArray(data.models)) return null;
  const ids = [];
  const seen = new Set();
  for (const item of data.models) {
    if (!item || typeof item !== 'object') continue;
    const slug = item.slug;
    if (typeof slug !== 'string' || !slug.trim() || item.visibility !== 'list') continue;
    if (seen.has(slug)) continue;
    seen.add(slug);
    ids.push(slug);
  }
  return ids;
}

async function listModels(rt, binPath, env, limit) {
  if (!rt.list) return { ok: false, ids: [], reason: 'no listing' };
  const { argv, input, parse } = rt.list;
  const r = await runChild(binPath, argv, { cwd: process.cwd(), env, input, capMs: LIST_CAP_MS, limit });
  if (r.timedOut) return { ok: false, ids: [], reason: 'timeout' };
  if (r.spawnErr) return { ok: false, ids: [], reason: 'spawn error' };
  if (r.code !== 0) return { ok: false, ids: [], reason: `exit ${r.code}` };
  const ids = parse(r.stdout);
  if (ids === null) return { ok: false, ids: [], reason: 'unparseable' };
  if (ids.length === 0) return { ok: false, ids: [], reason: 'no ids' };
  return { ok: true, ids, reason: '' };
}

const MAX_NESTED_REPOS = 8;
// Set by treeState before every null return: { kind: 'timeout'|'error', what }.
let gitFailure = null;
// The non-git polling note prints once per run.
let treePollNoted = false;
// The no_tree_change finding and the failed-read note are once per run, not once per ladder attempt.
let noTreeChangeNoted = false;
let pollFailNoted = false;

function gitFailed(result, what) {
  gitFailure = { kind: result.timedOut ? 'timeout' : 'error', what };
}

// One private-index tree read and its commit count form a single poll.
async function pollTreeRead(cwd, limit, baseHead, bg) {
  const st = await treeState(cwd, limit, 0, bg);
  if (st === null || bg.cancelled) return null;
  if (!st.head) return { ...st, commits: 0 };
  const git = which('git', process.env.PATH || '');
  const range = baseHead ? `${baseHead}..${st.head}` : st.head;
  const r = await runChild(git, ['rev-list', '--count', range], { cwd, capMs: GIT_CAP_MS, limit, bg });
  if (bg.cancelled) return null;
  if (r.timedOut || r.spawnErr || r.code !== 0) { gitFailed(r, 'rev-list'); return null; }
  return { ...st, commits: Number(r.stdout.trim()) || 0 };
}

function gitFailStatus() {
  const f = gitFailure || { kind: 'error', what: 'unknown' };
  const verb = f.kind === 'timeout' ? 'timed out' : 'failed';
  log(`cross-ai: git ${f.what} ${verb} reading the work tree (fail closed)`);
  return f.kind === 'timeout' ? 'git_timeout' : 'git_error';
}

// Filesystem only, so it cannot hang and ignores locale. A repo git refuses to read (dubious
// ownership, for example) still counts: it fails closed below.
function inGitTree(cwd) {
  if ((process.env.GIT_DIR || '').trim()) return true;
  const ceiling = (process.env.GIT_CEILING_DIRECTORIES || '').split(path.delimiter).filter(Boolean)
    .map((d) => path.resolve(d));
  let dir = path.resolve(cwd);
  for (;;) {
    if (ceiling.includes(dir)) return false;
    if (fs.existsSync(path.join(dir, '.git'))) return true;
    const parent = path.dirname(dir);
    if (parent === dir) return false;
    dir = parent;
  }
}

// 38 D-29: exclude only the runner's own state subtree, even when state home is the checkout.
// Anchored at the checkout top (the lock's root), so a start in a subdirectory excludes it too:
// `pathspec` for git add, `local` (relative to cwd, as ls-files prints) for the ignored listing.
function stateExclude(cwd) {
  let here;
  try { here = fs.realpathSync(cwd); } catch { return null; }
  const base = checkoutRoot(here);
  let probe = path.join(path.resolve(stateHome()), 'ai-kit', 'spec');
  let rest = '', real = null;
  while (real === null) {
    try { real = path.join(fs.realpathSync(probe), rest); } catch {
      const parent = path.dirname(probe);
      if (parent === probe) return null;
      rest = path.join(path.basename(probe), rest);
      probe = parent;
    }
  }
  const rel = path.relative(base, real);
  if (rel === '' || rel === '..' || rel.startsWith('..' + path.sep) || path.isAbsolute(rel)) return null;
  const posix = (p) => p.split(path.sep).join('/');
  return { pathspec: `:(top,exclude,literal)${posix(rel)}`, local: posix(path.relative(here, real)) };
}

async function treeState(cwd, limit, depth = 0, bg = null) {
  const git = which('git', process.env.PATH || '');
  if (!git) { gitFailure = { kind: 'error', what: 'not found' }; return null; }
  // --verify -q: exit 1 with no message on an unborn HEAD, in any locale; 128 outside a repo.
  // A cancelled background read starts no further git step.
  const headR = await runChild(git, ['rev-parse', '--verify', '-q', 'HEAD'], { cwd, capMs: GIT_CAP_MS, limit, bg });
  if (bg?.cancelled) return null;
  if (headR.timedOut || headR.spawnErr || (headR.code !== 0 && headR.code !== 1)) {
    gitFailed(headR, 'rev-parse'); return null;
  }
  const head = headR.code === 0 ? headR.stdout.trim() : null;
  const idxDir = makeTemp('xai-idx-');
  const env = { ...process.env, GIT_INDEX_FILE: path.join(idxDir, 'index') };
  try {
    const ex = stateExclude(cwd);
    const addR = await runChild(git, ex ? ['add', '-A', '--', ex.pathspec] : ['add', '-A'],{ cwd, env, capMs: GIT_CAP_MS, limit, bg });
    if (bg?.cancelled) return null;
    if (addR.timedOut || addR.spawnErr || addR.code !== 0) {
      gitFailed(addR, 'add -A'); return null;
    }
    const wtR = await runChild(git, ['write-tree'], { cwd, env, capMs: GIT_CAP_MS, limit, bg });
    if (bg?.cancelled) return null;
    if (wtR.timedOut || wtR.spawnErr || wtR.code !== 0) {
      gitFailed(wtR, 'write-tree'); return null;
    }
    // git add -A skips ignored files, so fold in a stat signature of each one (U-3): hashing
    // contents would be too slow for node_modules-sized trees, and a write changes ctime.
    // Fully ignored dirs list as one 'dir/' entry and are skipped, so a background cache or
    // indexer (graphify-out/, node_modules/) cannot read as an agent edit.
    const ignR = await runChild(git, ['ls-files', '-z', '-o', '-i', '--exclude-standard', '--directory'], { cwd, env, capMs: GIT_CAP_MS, limit, bg });
    if (bg?.cancelled) return null;
    if (ignR.timedOut || ignR.spawnErr || ignR.code !== 0) {
      gitFailed(ignR, 'ls-files'); return null;
    }
    const ignHash = crypto.createHash('sha256');
    for (const rel of ignR.stdout.split('\0').filter((r) => r && !r.endsWith('/') && !(ex && (r === ex.local || r.startsWith(ex.local + '/')))).sort()) {
      let sig = 'gone';
      try {
        const st = fs.lstatSync(path.join(cwd, rel));
        sig = `${st.mode}:${st.size}:${st.mtimeMs}:${st.ctimeMs}`;
      } catch { /* removed since the listing */ }
      ignHash.update(`${rel}\0${sig}\0`);
    }
    // git add records a submodule (or any nested repo) as its HEAD only, so snapshot each
    // checked-out one too: edits inside it must count.
    const lsR = await runChild(git, ['ls-files', '-s', '-z'], { cwd, env, capMs: GIT_CAP_MS, limit, bg });
    if (bg?.cancelled) return null;
    if (lsR.timedOut || lsR.spawnErr || lsR.code !== 0) { gitFailed(lsR, 'ls-files'); return null; }
    let nested = '';
    for (const entry of lsR.stdout.split('\0')) {
      if (!entry.startsWith('160000 ')) continue;
      const rel = entry.slice(entry.indexOf('\t') + 1);
      if (!fs.existsSync(path.join(cwd, rel, '.git'))) continue; // not checked out: the gitlink is all there is
      if (depth >= MAX_NESTED_REPOS) {
        gitFailure = { kind: 'error', what: 'nested repos' }; return null;
      }
      const sub = await treeState(path.join(cwd, rel), limit, depth + 1, bg);
      if (sub === null) return null;
      nested += `\t${rel}=${stateSig(sub)}`;
    }
    return { head, tree: `${wtR.stdout.trim()}\tignored=${ignHash.digest('hex')}${nested}` };
  } finally {
    dropTemp(idxDir);
  }
}

function childEnv(extra, baseEnv) {
  const env = { ...baseEnv, ...extra };
  for (const k of CONFIG.scrubEnv) if (!(k in extra)) delete env[k];
  for (const [k, v] of Object.entries(extra)) if (v === '') delete env[k];
  env.AI_KIT_CROSS_AI_CHILD = '1'; // the session wake refuses to arm in a runner child (26 D-24)
  return env;
}

function withExtra(cli, argv) {
  const extra = ownValue(CONFIG.extraArgs, cli);
  return extra && extra.length ? [...argv, ...extra] : argv;
}

// A review argv may only extend its bare formula with the runtime's allowlist: a listed flag
// (compared before any `=`) or the one non-flag value right after it. Anything else, an
// alias, a config override or a re-enabling flag, is a reason naming the element.
function reviewArgvProblem(argv, baseArgv, allowed) {
  const base = baseArgv || [];
  for (let i = 0; i < base.length; i++) {
    if (argv[i] !== base[i]) return argv[i] === undefined ? '(missing)' : argv[i];
  }
  const ok = new Set(allowed || []);
  for (let i = base.length; i < argv.length; i++) {
    const el = argv[i];
    const flag = String(el).split('=')[0];
    if (ok.has(flag)) {
      if (!String(el).includes('=')) {
        const value = argv[i + 1];
        if (value === undefined || String(value).startsWith('-')) return el;
        i += 1;
      }
      continue;
    }
    return el;
  }
  return null;
}

for (const [sig, n] of [['SIGTERM', 15], ['SIGINT', 2], ['SIGHUP', 1]]) {
  process.on(sig, () => {
    if (selfTestHook) { selfTestHook(128 + n); return; }
    if (aborting) {
      // A second signal skips what is left of the grace period.
      if (current) killGroup(current, 'SIGKILL');
      return;
    }
    // main() owns the outcome: every wait below is now capped by signalBy, the CLI gets its
    // grace and SIGKILL, the tree is read once more and main prints status=signal.
    aborting = n;
    signalBy = Date.now() + SIGNAL_BUDGET_MS;
    for (const wake of [...sleepers]) wake();
    if (currentFinalize) currentFinalize('signal');
    backstop = setTimeout(() => {
      if (current) killGroup(current, 'SIGKILL');
      const fields = { ...liveFields, exit: 128 + n, tree: 'unknown' };
      exitFlushed(reportAndFinish('signal', fields, 'signal'));
    }, SIGNAL_BUDGET_MS + 200);
  });
}

// Live matching uses the same tier order as post-hoc matching. The first admitted row wins;
// the kill is armed only when that row is terminal and, for an event, not transient. A later
// terminal row never wins over an earlier non-terminal one.
function liveMatch(cli, source, text, raw = text, route = 'unknown', model = '') {
  const events = source === 'event' ? [text] : [];
  const stderr = source === 'stderr' ? text : '';
  const cls = classifyStop({
    cli, route, model, stderr, events, eventRaw: source === 'event' ? [raw] : [],
  });
  if (cls.status === 'crash') return null;
  const row = TABLE.find((item) => item.id === cls.rule);
  if (!row || !row.terminal) return null;
  if (source === 'event' && row.class === 'transient') return null;
  return cls;
}

function armLimit(state, cls) {
  if (state.liveHit || !cls) return;
  state.liveHit = { status: cls.status, rule: cls.rule, label: cls.label,
    source: cls.source, line: cls.line, raw: cls.raw };
  const child = current;
  state.limitTimer = setTimeout(() => {
    if (current === child && currentFinalize) currentFinalize('limit');
  }, LIMIT_GRACE_MS);
}

function watchChunk(relay, chunk) {
  relay.push(chunk);
}

async function runOnce(bin, argv, input, env, cwd, label, opts = {}) {
  let outBytes = 0;
  let lastBytes = 0;
  const started = Date.now();
  let idleCtl = null;
  let activeSinceTick = false;
  let pollGate = null;
  let errTail = '';
  const state = { liveHit: null, limitTimer: null };
  const cli = label;
  const route = opts.route || 'unknown';
  const model = opts.model || '';
  const noteLine = (source) => (line) => {
    if (source === 'stderr') {
      armLimit(state, liveMatch(cli, 'stderr', line, line, route, model));
      return;
    }
    const extracted = eventsWithRaw(cli, line, true);
    for (let i = 0; i < extracted.events.length; i += 1) {
      armLimit(state, liveMatch(cli, 'event', extracted.events[i], extracted.eventRaw[i], route, model));
    }
  };
  const notePartial = (source) => (buf) => {
    if (source !== 'stderr' || state.liveHit) return;
    armLimit(state, liveMatch(cli, 'stderr', buf, buf, route, model));
  };
  // The answer goes to stdout only: the stdout relay feeds the live watcher, never the log.
  // Both relays share one set of redacted values (D-17), which also feeds upstreamOf.
  const seen = new Set();
  const outRelay = makeLineRelay({
    onLine: noteLine('stdout'), onPartial: notePartial('stdout'), quiet: true, seen,
  });
  const errRelay = makeLineRelay({
    onLine: noteLine('stderr'), onPartial: notePartial('stderr'), seen,
  });
  const childLimit = opts.limit ?? runDeadline;
  // One decoder per stream: a multi-byte character split across two chunks decodes whole.
  const outDecoder = new StringDecoder('utf8');
  const errDecoder = new StringDecoder('utf8');
  const onErrText = (text) => {
    if (!text) return;
    watchChunk(errRelay, text);
    errTail = (errTail + text).slice(-INPUT_CAP);
  };
  const childOpts = {
    cwd, env, input, capMs: budgetMs(opts.capMs ?? Number.POSITIVE_INFINITY, childLimit),
    limit: childLimit,
    captureMax: LANE_CAPTURE_MAX_BYTES,
    onStdout: (d) => {
      activeSinceTick = true;
      poll.allowIdle = false;
      outBytes += d.length;
      watchChunk(outRelay, outDecoder.write(d));
    },
    onStderr: (d) => { activeSinceTick = true; poll.allowIdle = false; onErrText(errDecoder.write(d)); },
    // D-08: a detached child leads its own group and session (pgid = sid = pid).
    onSpawn: (pid) => lockUpdate({ child_pgid: pid, child_start: procStartTime(pid) }),
    idleMs: (opts.idleS || 0) * 1000,
    idleResetter: (ctl) => { idleCtl = ctl; },
    onIdle: () => { if (state.liveHit) return false; if (pollGate && !pollGate()) return false; log(redactSecrets(`cross-ai: idle watchdog: ${cli} printed nothing for ${opts.idleS}s; ending its process group`)); return true; },
  };
  const idlePlan = opts.idlePlan || null;
  if (idlePlan?.pollTree && !inGitTree(cwd) && !treePollNoted) {
    treePollNoted = true;
    log('cross-ai: tree polling off: not inside a git work tree; the idle clock reads output only');
  }
  const polling = Boolean(idlePlan?.pollTree) && liveBaseline !== null && inGitTree(cwd);
  const pollStart = performance.now();
  // The first previous read is the baseline's own value.
  const poll = { bg: { stops: new Set(), cancelled: false }, inFlight: null, stopped: false,
    prev: { head: liveBaseline?.head ?? null, tree: liveBaseline?.tree ?? null }, commits: 0,
    treeChanged: false, lastChangeMs: pollStart, lastReadMs: pollStart, lastDoneMs: 0,
    lastNoticeMs: 0, idleDue: false, allowIdle: false };
  const pollFailed = (text) => { if (!pollFailNoted) { pollFailNoted = true; log(text); } };
  // Changed trees reset the clock; unchanged or failed reads release deferred idle.
  const onRead = (read, quiet) => {
    poll.inFlight = null;
    poll.lastDoneMs = performance.now();
    if (poll.stopped) return;
    if (read === null) {
      const f = gitFailure || { kind: 'error', what: 'unknown' };
      pollFailed(`cross-ai: tree poll: git ${f.what} ${f.kind === 'timeout' ? 'timed out' : 'failed'}; no signal from this read`);
    } else {
      const changed = read.head !== poll.prev.head || read.tree !== poll.prev.tree;
      poll.prev = { head: read.head, tree: read.tree };
      poll.commits = read.commits;
      poll.treeChanged = read.tree !== liveBaseline.tree;
      if (changed) { poll.lastChangeMs = performance.now(); poll.idleDue = false; poll.allowIdle = false; if (idleCtl) idleCtl.reset(); return; }
      const still = performance.now() - poll.lastChangeMs;
      if (!quiet && still >= idlePlan.idleS * 1000 && performance.now() - poll.lastNoticeMs >= idlePlan.idleS * 1000) {
        poll.lastNoticeMs = performance.now();
        const n = Math.round(still / 1000);
        log(`cross-ai: ${label} printed output but changed nothing in the checkout for ${n}s`);
        if (!noTreeChangeNoted) { noTreeChangeNoted = true; addFinding('no_tree_change', `${label} printed output but changed nothing for ${n}s`); }
      }
    }
    if (poll.idleDue) { poll.idleDue = false; poll.allowIdle = true; if (idleCtl) idleCtl.recheck(); }
  };
  const startRead = (quiet) => {
    poll.lastReadMs = performance.now();
    poll.inFlight = pollTreeRead(cwd, childLimit, liveBaseline.head, poll.bg).then(
      (read) => onRead(read, quiet),
      (e) => { pollFailed(`cross-ai: tree poll: read failed (${e && (e.code || e.message)}); no signal from this read`); onRead(null, quiet); },
    ).catch((e) => { poll.inFlight = null; pollFailed(`cross-ai: tree poll: read failed (${e && (e.code || e.message)}); no signal from this read`); });
  };
  // One read in flight; quiet ticks read, and output permits one read per idle period.
  const pollTick = () => {
    if (poll.stopped || poll.inFlight) return;
    const quiet = !activeSinceTick;
    activeSinceTick = false;
    if (!quiet && performance.now() - poll.lastReadMs < idlePlan.idleS * 1000) return;
    startRead(quiet);
  };
  // Idle expiry waits for an in-flight or fresh read before ending the lane.
  if (polling) pollGate = () => {
    if (poll.allowIdle) { poll.allowIdle = false; return true; }
    if (!poll.inFlight && performance.now() - poll.lastDoneMs < idlePlan.checkS * 1000) return true;
    poll.idleDue = true;
    if (!poll.inFlight) startRead(true);
    return false;
  };
  const pollTimer = polling ? setInterval(pollTick, idlePlan.checkS * 1000) : null;
  const hb = setInterval(() => {
    const secs = Math.round((Date.now() - started) / 1000);
    log(`cross-ai: ${label} running ${secs}s, stdout +${outBytes - lastBytes} bytes${polling ? `, commits +${poll.commits} since the baseline, tree ${poll.treeChanged ? 'changed' : 'unchanged'}` : ''}`);
    lastBytes = outBytes;
  }, CONFIG.heartbeatS * 1000);
  let r = null;
  if (opts.host && !opts.host.failed) {
    const hosted = await hostedChild(bin, argv, { ...childOpts, host: opts.host, promptArg: opts.promptArg });
    if (hosted.hostFailed) {
      hostFailedNote(opts.host, hosted.hostFailed, hosted.rerun);
      // The headless rerun is the lane now: the lock must not name the abandoned tab.
      if (hosted.rerun) lockUpdate({ token: null, tab_id: null, host_ms: null });
      if (!hosted.rerun) r ={ code: null, signal: null, timedOut: false, limited: false, spawnErr: null, stdout: '', stderr: '' };
    } else r = hosted;
  }
  if (!r) r = await runChild(bin, argv, childOpts);
  // Stop and join the whole background read before the next tree read.
  if (pollTimer) clearInterval(pollTimer);
  poll.stopped = true;
  poll.bg.cancelled = true;
  for (const stop of [...poll.bg.stops]) stop('stop');
  if (poll.inFlight) await poll.inFlight;
  clearInterval(hb);
  if (state.limitTimer) clearTimeout(state.limitTimer);
  const outRest = outDecoder.end();
  if (outRest) outRelay.push(outRest);
  onErrText(errDecoder.end());
  outRelay.flush();
  errRelay.flush();
  return {
    ...r, stderr: errTail || r.stderr, outBytes, liveHit: state.liveHit,
    partialOut: outRelay.partial(), partialErr: errRelay.partial(), redacted: [...seen],
  };
}

// A signal wakes every sleeper so the backoff never outlives the signal budget.
const sleep = (ms) => new Promise((resolve) => {
  const wake = () => { clearTimeout(t); sleepers.delete(wake); resolve(); };
  const t = setTimeout(wake, ms);
  sleepers.add(wake);
});

// The child timer keeps 60 s in hand for the next rung when the deadline has it.
// A deadline shorter than that still runs this attempt (the ladder then admits nothing).
// A router-quota cycle also clamps the timer to the absolute cap minus the same reserve, so
// an attempt admitted near the cap cannot run past it.
function attemptCapMs(opts, nowMs, quotaEndMs = 0, deadlineMs = runDeadline) {
  const remaining = Math.max(0, deadlineMs - nowMs);
  // Reserve 60 s for the next rung only when the attempt keeps at least as much: no 1 s cliff.
  let budget = remaining >= 120000 ? remaining - 60000 : remaining;
  if (quotaEndMs > 0) {
    // The cap itself is the hard stop: the reserve guards admission, not the child's length.
    const capLeft = Math.max(0, quotaEndMs - nowMs);
    budget = Math.min(budget, capLeft);
  }
  const cap = clampAttemptTimeout(opts.attemptTimeoutS ?? CONFIG.attemptTimeoutS);
  if (cap > 0) return Math.min(cap * 1000, budget);
  return budget;
}

// A quota or rate-limit match wins over a plain timeout; anything else on a timed-out
// attempt is a transient rung (owner list), and a real failure class is itself.
function ladderClass(timedOut, hit) {
  if (!timedOut) return hit === 'transient' ? 'transient' : 'stop';
  if (hit && hit !== 'transient') return 'stop';
  return 'transient';
}

// A rungs stop that started as a timeout still reports transient (owner rung 4): Python
// re-runs a timeout status once per tier. timeout/124 is only the no-budget stop before any
// rung was admitted. A transient failure that cannot start a rung stays transient.
function ladderStop(step, timedOut, admitted, fallback) {
  if (step.why === 'class') return { status: fallback, timedOut: false };
  if (step.why === 'deadline' && !admitted && timedOut) {
    return { status: 'timeout', timedOut: true };
  }
  return { status: 'transient', timedOut: false };
}

// One evidence line per failed attempt. Values are ids, labels and times only.
function logAttempt(n, rung, cycle, sid, status, rule, pattern, startedMs) {
  const took = Math.max(0, Math.round((Date.now() - startedMs) / 1000));
  const at = new Date(startedMs).toISOString();
  log(`cross-ai: attempt n=${n} rung=${rung} cycle=${cycle} session=${sid || '-'} ` +
    `status=${status} rule=${rule || '-'} pattern=${pattern || '-'} at=${at} took=${took}s`);
}

// One report line before the status line of every run that does not end ok. due_at is the
// ISO-8601 UTC time (seconds) of a hint exit's wait end, `-` on every other stop.
function logReport(status, cli, model, route, attempts, cycles, firstMs, lastMs, stopped, dueMs = 0, upstream = null, check = '-') {
  const iso = (ms) => (ms ? new Date(ms).toISOString() : '-');
  const dueIso = (ms) => (ms ? new Date(ms).toISOString().replace(/\.\d{3}Z$/, 'Z') : '-');
  log(`cross-ai: report status=${status} lane=${cli}/${model} route=${route || 'unknown'} ` +
    `attempts=${attempts} cycles=${cycles} first_failure=${iso(firstMs)} ` +
    `last_failure=${iso(lastMs)} due_at=${dueIso(dueMs)} stopped=${stopped} ` +
    `upstream=${upstream?.body ? 'present' : '-'} check=${check}`);
}

function stoppedWhy(step, dirty) {
  if (dirty) return 'dirty-tree';
  if (step && step.why === 'deadline') return 'deadline';
  if (step && step.why === 'cap') return 'cap';
  if (step && step.why === 'soft-spent') return 'rungs';
  return 'class';
}

async function runCli(name, rt, binPath, model, mode, prompt, opts = {}) {
  // The preamble is the runner's own rules, appended after a blank line. The dirty-tree gate
  // judges edits against the caller's prompt only: the preamble names files the plan never did.
  const preambleAt = prompt.lastIndexOf('\n\n<');
  const userPrompt = preambleAt > 0 ? prompt.slice(0, preambleAt) : prompt;
  const retryCfg = opts.retry || RETRY_DEFAULTS;
  const beforeSig = opts.beforeSig ?? null;
  const capS = clampCapS(opts.capS ?? CONFIG.capS);
  const tmp = makeTemp('cross-ai-');
  const ctx = {
    cwd: process.cwd(), sid: crypto.randomUUID(), outFile: path.join(tmp, 'last-message.md'),
    adds: opts.adds, codexServiceTier: opts.codexServiceTier,
    cursorMode: opts.cursorMode,
    codexSandbox: opts.codexSandbox,
    profileFlags: opts.profileFlags || [],
    promptArg: '<prompt>',
  };
  if (opts.sessionId) ctx.sid = opts.sessionId;
  // An explicit id the planner applied is pinned: retries keep it and no rung starts a fresh session (SPEC R7).
  const pinned = opts.pinSession ? opts.sessionId : null;
  const chosen = rt.forms?.session?.style === 'chosen';
  // A pinned chosen row continues through its create-or-continue form with the same id.
  const sameArgv = (sid, input) => sameSessionArgv(name, rt, model, ctx, sid, mode, input) || (pinned && chosen && sid === pinned ? newSessionArgv(name, rt, model, ctx, mode, input, true) : null);
  const env = childEnv(rt.env, process.env);
  // A resume argv is checked against the runtime's own resume formula, so its session flag is
  // trusted and only extras beyond the formula count as a widening.
  const reviewProblem = (argv, sid = null) => {
    if (mode !== 'review') return null;
    const base = sid && rt.resume ? rt.resume(model, ctx, sid, mode) : rt.review(model, ctx);
    return reviewArgvProblem(argv, base, rt.reviewExtras || []);
  };
  const refuseReview = (problem) => {
    const allowed = (rt.reviewExtras || []).join(', ') || 'none';
    log(`cross-ai: review argv for ${name} holds ${problem}; review extras allowed for ${name}: ${allowed}; refused`);
    return { ok: false, status: 'usage', exit: 2, cli_rc: '-', outBytes: 0 };
  };
  if (rt.argvPrompt) ctx.promptArg = argvPromptElement(prompt);
  // The first attempt spawns the argv the settings report was confirmed against (SPEC R2, R7).
  const first = opts.resume && opts.sessionId ? sameSessionArgv(name, rt, model, ctx, opts.sessionId, mode, prompt) : null;
  let argv = first ? first.argv : withExtra(name, rt[mode](model, ctx));
  // SPEC R12 encoding: no argv element may hold a NUL byte, hosted or headless (a spawn would throw).
  if (argv.some((el) => String(el).includes('\0'))) {
    log(`cross-ai: argv for ${name} holds a NUL byte; refused`);
    return { ok: false, status: 'usage', exit: 2, cli_rc: '-', outBytes: 0 };
  }
  const initialProblem = reviewProblem(argv, first ? opts.sessionId : null);
  if (initialProblem) return refuseReview(initialProblem);
  let input = first ? first.input : (rt.argvPrompt ? null : prompt);
  let attemptSid = rt.argvFile ? (opts.sessionId ?? null) : (first ? opts.sessionId : (argv.includes(ctx.sid) ? ctx.sid : null));
  let unshownNoted = false;
  // The dirty-tree gate runs once, when a fresh series opens, and its input covers every
  // call of that series. Re-running it mid-series would see the series' own edits.
  let seriesInput = prompt;
  let gated = false;
  // A re-entry repeats the task, so its same-session retries send the prompt, not the note.
  let continued = false;
  // seenSig is the tree before the attempt in flight, seriesSig the tree before the current
  // series. A fresh series is judged against the previous series' end, never its own edits.
  let seenSig = beforeSig;
  let seriesSig = beforeSig;
  const ladder = {
    retry: 0, resets: 0, canResume: false, firstMs: 0, cycle: 0, prevWaitMs: 0,
  };
  let admitted = false;
  // Every lane owns its own state file; the route kind keys the name, so a confirmed router
  // lane and an unconfirmed call on the same CLI and model never share a record.
  const routerLane = confirmedRoute(opts.route || 'unknown');
  const stateFile = cycleFilePath(name, model, routerLane ? 'router' : 'other');
  const digest = taskDigest(prompt);
  const loaded = readCycleState(stateFile);
  const now0 = Date.now();
  const capMs = capS * 1000;
  let cycleCount = 0;
  let priorAttempts = 0;
  let persisted = null;
  // One state line per run, at the first action on the file (a save, a delete or a refusal
  // read): the caller's evidence for where the lane's record lives.
  let stateLogged = false;
  const logState = () => {
    if (stateLogged) return;
    stateLogged = true;
    log(`cross-ai: state ${stateFile}`);
  };
  const dropStateFile = () => {
    if (!fs.existsSync(stateFile)) return;
    deleteCycleState(stateFile);
    logState();
  };
  if (loaded && typeof loaded.last_attempt_at === 'number') {
    if (now0 - loaded.last_attempt_at > capMs) {
      // Stale, stopped or not: the episode is long over, so the record is dropped and the
      // lane starts a fresh episode at cycle 0 (the owner's other reset is time itself).
      deleteCycleState(stateFile);
      logState();
      log('cross-ai: stale-state-fresh-start');
    } else if (loaded.stopped) {
      // A terminal stop holds the lane (D-08): every call is refused without a model call
      // until the record goes stale or the owner deletes the file to start a new episode.
      logState();
      // A hand-edited record may lack the stop time; the stop itself still holds (25.1 IN-01).
      const stoppedAt = Number.isFinite(loaded.stopped_at)
        ? new Date(loaded.stopped_at).toISOString() : '-';
      log(`cross-ai: lane stopped=${loaded.stopped} at ${stoppedAt}; ` +
        `delete ${stateFile} to start a new episode`);
      return {
        ok: false, status: loaded.class, code: 69, exit: 69, outBytes: 0, cli_rc: '-',
        route: opts.route || 'unknown', rule: '-', pattern: 'none',
        attempts: loaded.attempts || 0, cycles: loaded.cycle || 0,
        stopped: loaded.stopped,
      };
    } else if (now0 - loaded.first_seen > capMs) {
      // The episode ended while the lane waited: persist the cap stop (D-09) so a later
      // session or Phase 26's wake can surface it, then refuse without a model call. A write
      // failure never changes the stop (the notice is the trace, the exit stays 69).
      try {
        writeCycleState(stateFile, {
          ...loaded, last_attempt_at: now0, retry_after_s: null, due_at: null,
          stopped: 'cap', stopped_at: now0,
        });
      } catch (e) {
        log(`cross-ai: cycle state unwritable: ${stateFile} (${e.code || e.message})`);
      }
      logState();
      return {
        ok: false, status: loaded.class, code: 69, exit: 69, outBytes: 0, cli_rc: '-',
        route: opts.route || 'unknown', rule: '-', pattern: 'none',
        attempts: loaded.attempts || 0, cycles: loaded.cycle || 0, stopped: 'cap',
        
      };
    } else if (typeof loaded.due_at === 'number' && now0 < loaded.due_at) {
      const left = Math.max(0, Math.round((loaded.due_at - now0) / 1000));
      logState();
      return {
        ok: false, status: loaded.class, outBytes: 0, cli_rc: '-',
        route: opts.route || 'unknown', rule: '-', pattern: 'none',
        attempts: loaded.attempts || 0, cycles: loaded.cycle || 0,
        retryAfterS: left, cycle: loaded.cycle || 0, stopped: 'rungs',
        dueAtMs: loaded.due_at,
        check: ['first', 'periodic', 'reset'].includes(loaded.check) ? loaded.check : '-',
      };
    } else {
      cycleCount = (loaded.cycle || 0) + 1;
      priorAttempts = loaded.attempts || 0;
      persisted = loaded;
      ladder.firstMs = loaded.first_seen;
      ladder.cycle = cycleCount;
    }
  }
  let firstFailureMs = persisted ? persisted.first_seen : 0;
  // One reset check per episode (D-11); every save carries it, because saveCycle rebuilds the record.
  let resetCheck = persisted && Number.isFinite(persisted.reset_check) ? persisted.reset_check : null;
  let lastFailureMs = 0;
  let attempts = priorAttempts;
  // The label of the step that produced the attempt about to run: a reset starts a fresh
  // session, a same-session retry resumes, and a no-resume retry is a new session.
  let rungLabel = 'first';
  const rungOf = () => rungLabel;
  // One episode clock for both soft classes: the first soft failure of the call, or a loaded
  // record's first_seen. 0 before any soft failure, so the cap never bites a first attempt.
  const episodeEnd = () => (ladder.firstMs ? ladder.firstMs + capMs : 0);
  const counts = () => ({
    attempts, cycles: ladder.cycle,
    firstFailureMs, lastFailureMs,
  });
  const dropState = (status) => {
    if (!QUOTA_KEEP.has(status)) {
      dropStateFile();
    }
  };
  // An unwritable state file never leaves a hint the runner cannot track: the wait or stop
  // stays its class, but the exit is a bare one (no retry_after_s=) so no caller loop runs
  // untracked (25.1-03, kept from Phase 25's quota rule).
  let stateWritable = true;
  const saveCycle = (sid, at, record) => {
    try {
      writeCycleState(stateFile, {
        first_seen: ladder.firstMs, last_attempt_at: at, cycle: ladder.cycle,
        attempts, last_sid: sid || null, task_digest: digest,
        ...(resetCheck === null ? {} : { reset_check: resetCheck }), ...record,
      });
      logState();
    } catch (e) {
      stateWritable = false;
      log(`cross-ai: cycle state unwritable: ${stateFile} (${e.code || e.message})`);
    }
  };
  // One hard handler for both soft classes (D-07). A short wait may run in the call;
  // otherwise the next list or periodic wait is an exit-75 hint. When the list is spent
  // with no periodic wait, or the cap would pass the wait, the call persists a stop (D-09).
  // A soft step refused for `cap` is already past the episode end, so it stops at once.
  const hardHandler = (r, evidence, why, sid, cls) => {
    const at = Date.now();
    const stopped = why === 'deadline' ? 'deadline' : 'rungs';
    const step = why === 'cap'
      ? { stop: 'cap' }
      : hardWaitFor(ladder.cycle, retryCfg.hard_waits_s,
          ladder.firstMs ? (ladder.firstMs + capMs - at) / 1000 : -1,
          retryCfg.hard_every_s ?? RETRY_DEFAULTS.hard_every_s);
    if (step.stop) {
      saveCycle(sid, at, {
        class: cls, stopped: step.stop, stopped_at: at, retry_after_s: null, due_at: null,
      });
      return {
        ok: false, status: cls, timedOut: false,
        outBytes: r.outBytes, cli_rc: r.code ?? '-', ...evidence, ...counts(),
        cycle: ladder.cycle, exit: 69, stopped: step.stop, check: '-',
      };
    }
    const plan = shortHardWait(step.retryAfterS, at, why === 'soft-spent' ? runDeadline : 0);
    let waitS = plan.waitS;
    const capLeftS = ladder.firstMs ? (ladder.firstMs + capMs - at) / 1000 : -1;
    if (waitS > capLeftS) {
      saveCycle(sid, at, { class: cls, stopped: 'cap', stopped_at: at, retry_after_s: null, due_at: null });
      return { ok: false, status: cls, timedOut: false, outBytes: r.outBytes, cli_rc: r.code ?? '-', ...evidence, ...counts(), cycle: ladder.cycle, exit: 69, stopped: 'cap', check: '-' };
    }
    let check = step.cycle < retryCfg.hard_waits_s.length ? 'first' : 'periodic';
    if (resetCheck === null && !plan.inCall) {
      const extra = resetCheckS(statedResetS(evidence.upstream?.fields, at), waitS, capLeftS);
      if (extra !== null) { waitS = extra; check = 'reset'; resetCheck = at + extra * 1000; }
    }
    const dueAtMs = at + waitS * 1000;
    const record = { class: cls, retry_after_s: waitS, due_at: dueAtMs, check };
    // The loop writes this only after its tree checks pass.
    if (plan.inCall) return { inCallS: waitS, cycle: step.cycle, at, record };
    saveCycle(sid, at, record);
    return {
      ok: false, status: cls, timedOut: false,
      outBytes: r.outBytes, cli_rc: r.code ?? '-', ...evidence, ...counts(),
      retryAfterS: stateWritable ? waitS : undefined,
      dueAtMs: stateWritable ? dueAtMs : undefined,
      cycle: step.cycle, exit: 75, stopped, check: stateWritable ? check : '-',
    };
  };
  try {
    if (!opts.callSessionId && persisted && persisted.task_digest === digest && persisted.last_sid) {
      if (!sessionShown(persisted.last_sid)) {
        log('cross-ai: note: the quota record\'s session id is outside [A-Za-z0-9._:-] or shaped like a key; it is not reused');
      } else {
        ctx.sid = persisted.last_sid;
        // A re-entry repeats the task on the saved session, so the session gets the prompt
        // itself; the resume note would hide it.
        const retry = sameSessionArgv(name, rt, model, ctx, persisted.last_sid, mode, prompt);
        if (retry) {
          argv = retry.argv;
          input = retry.input;
          seriesInput = prompt;
          continued = true;
          ladder.canResume = true;
          attemptSid = persisted.last_sid;
        }
      }
    }
    liveSettings.sessionId = sessionShown(attemptSid) ? attemptSid : null;
    let idleNoteShown = false;
    for (let attempt = 0; ; attempt++) {
      // Before the child runs: the snapshot after it would race the next attempt's edits.
      if (mode === 'exec' && seenSig !== null) {
        const seen = await treeState(ctx.cwd, runDeadline);
        if (seen) seenSig = stateSig(seen);
      }
      const startedMs = Date.now();
      const childCap = attemptCapMs(opts, startedMs, episodeEnd());
      // SPEC R1: the cannot-fire note against the live attempt cap, once per call (plan 38-10's idleBudgetNote; compared in ms).
      if ((opts.idleS || 0) > 0 && !idleNoteShown && opts.idleS * 1000 >= childCap) { idleNoteShown = true; log(idleBudgetNote(opts.idleS, childCap)); }
      const left = Math.max(0, Math.round(childCap / 1000));
      log(`cross-ai: cli=${name} bin=${binPath} mode=${mode} attempt=${attempt + 1} timeout=${left}s`);
      log(`cross-ai: argv=${JSON.stringify(shownArgv(rt, displayArgv(argv, rt.argvPrompt ? ctx.promptArg : undefined)))}`);
      const childLimit = episodeEnd() ? Math.min(runDeadline, episodeEnd()) : runDeadline;
      const route = opts.route || 'unknown';
      const r = await runOnce(binPath, argv, input, env, ctx.cwd, name,
        { capMs: childCap, limit: childLimit, route, model, host: opts.host, promptArg: rt.argvPrompt ? ctx.promptArg : undefined, idleS: opts.idleS || 0, idlePlan: opts.idlePlan || null });
      // Self-test fakes only (FAKE_CALLS): a fake child stalls the post-run git snapshot only
      // while it is alive. A real run never touches the caller's home.
      if (process.env.FAKE_CALLS) {
        try { fs.rmSync(path.join(env.HOME || '', '.fake-git-hang')); } catch { /* not set */ }
      }
      if (aborting) return { ok: false, code: 128 + aborting, outBytes: r.outBytes, cli_rc: r.code };
      const lane = confirmedRoute(route);
      const evidenceOf = (cls) => {
        const rule = cls && cls.rule ? cls.rule : '-';
        // 38.1 D-05: see patternFor.
        const pattern = patternFor(rt, name, mode, cls);
        return { route, rule, pattern, upstream: upstreamOf(cls, r, name) };
      };
      if (r.spawnErr) {
        // ENOENT at spawn (the binary or its interpreter is gone) is not_installed/127, as when
        // the CLI is missing from PATH; any other spawn error stays a crash.
        const missing = r.spawnErr.code === 'ENOENT';
        log(`cross-ai: ${name} did not start (${r.spawnErr.code || r.spawnErr.message}); ` +
          'no other CLI runs (no automatic fallback)');
        return {
          ok: false, status: missing ? 'not_installed' : 'crash', exit: missing ? 127 : 1,
          error: String(r.spawnErr), outBytes: 0, cli_rc: '-', ...counts(), stopped: 'class',
        };
      }
      const p = rt.parse(r.stdout, ctx);
      const hostSid = sessionShown(p.sessionId) ? p.sessionId : null;
      if (p.sessionId && !hostSid && !unshownNoted) {
        unshownNoted = true;
        log(`cross-ai: note: ${name} printed a session id outside [A-Za-z0-9._:-] or shaped like a key; session=- and it is not passed back`);
      }
      const usedSid = hostSid || attemptSid;
      liveSettings.sessionId = sessionShown(usedSid) ? usedSid : null;
      // A live hit wins only when it ended the child: one that finished on its own with exit 0
      // and an answer succeeded, whatever it printed on stderr on the way.
      // A late error (after our turn ended) does not discard a complete answer.
      const lateOk = !r.timedOut && !p.error && Boolean(p.lateError) && Boolean(p.text.trim());
      const finished = !r.timedOut && (r.code === 0 || lateOk) && !p.error && Boolean(p.text.trim());
      if (r.liveHit && !r.limited && finished) r.liveHit = null;
      // A live terminal signal is the attempt's class; no second pass (D-09).
      let hit = null;
      let evidence = evidenceOf(null);
      // A non-retryable class ends the call here; both class checks below share it.
      const classStop = () => {
        attempts += 1;
        logAttempt(attempts, rungOf(), ladder.cycle, usedSid, hit, evidence.rule,
          evidence.pattern, startedMs);
        lastFailureMs = Date.now();
        if (!firstFailureMs) firstFailureMs = startedMs;
        dropState(hit);
        return {
          ok: false, status: hit, outBytes: r.outBytes, cli_rc: r.code ?? '-', ...evidence,
          ...counts(), stopped: 'class',
        };
      };
      if (r.liveHit) {
        // liveMatch classified with this call's route, so the router-quota mapping is applied.
        hit = r.liveHit.status;
        evidence = evidenceOf(r.liveHit);
      } else if (r.timedOut) {
        // Post-hoc over everything it printed, terminal and non-terminal rows alike.
        const captured = [r.stderr || '', r.partialErr || '', r.partialOut || ''].join('\n');
        const { events, eventRaw } = eventsWithRaw(name, r.stdout);
        const cls = classifyStop({ cli: name, route, model, stderr: captured, events, eventRaw, stdout: r.stdout });
        if (cls.status !== 'crash') {
          hit = cls.status;
          evidence = evidenceOf(cls);
        }
      } else {
        const failed = (r.code !== 0 && !lateOk) || Boolean(p.error);
        const { events, eventRaw } = eventsWithRaw(name, r.stdout);
        const cls = classifyStop({ cli: name, route, model, stderr: r.stderr, events, eventRaw, stdout: failed ? r.stdout : '' });
        if (cls.status !== 'crash') {
          hit = cls.status;
          evidence = evidenceOf(cls);
        }
        if (!failed && p.text.trim()) {
          if (p.lateError) log(`cross-ai: ${name} failed after the answer (${p.lateError})`);
          attempts += 1;
          dropStateFile();
          return {
            ok: true, text: normalize(p.text), outBytes: Buffer.byteLength(r.stdout, 'utf8'),
            cli_rc: 0, ...counts(),
          };
        }
        if (hit && hit !== 'transient' && !(hit === 'quota' && lane)) return classStop();
        if (!failed) {
          return {
            ok: false, status: 'empty_answer', outBytes: r.outBytes, cli_rc: 0,
            ...counts(), stopped: 'class',
          };
        }
      }
      if (hit && hit !== 'transient' && !r.timedOut && !(hit === 'quota' && lane)) return classStop();
      const cls0 = ladderClass(Boolean(r.timedOut), hit);
      const quotaLane = cls0 === 'stop' && hit === 'quota' && lane;
      const cls = quotaLane ? 'quota' : cls0;
      attempts += 1;
      lastFailureMs = Date.now();
      if (!firstFailureMs) firstFailureMs = startedMs;
      const sid = usedSid;
      const rung = rungOf();
      logAttempt(attempts, rung, ladder.cycle, sid, hit || (r.timedOut ? 'timeout' : 'crash'),
        r.idle ? 'idle-watchdog' : (hit ? evidence.rule : '-'), hit ? evidence.pattern : '-', startedMs);
      const soft = cls === 'transient' || cls === 'quota';
      if (soft && !ladder.firstMs) ladder.firstMs = Date.now();
      const sig = r.signal ? ' ' + r.signal : '';
      log(`cross-ai: ${name} failed (exit ${r.code}${sig}, rule=${hit ? evidence.rule : '-' })`);
      ladder.canResume = Boolean(sameArgv(sid));
      // k restarts at 1 with every series, so the reset and the first retry after it both wait
      // about base_s, and the ordering floor applies within one series only.
      const k = ladder.retry < retryCfg.max_retries ? ladder.retry + 1 : 1;
      const prevMs = k === 1 ? 0 : ladder.prevWaitMs;
      const nominal = softWaitMs(retryCfg, k, Math.random, prevMs);
      const end = episodeEnd();
      let step = ladderNext(ladder, cls, Date.now(), {
        maxRetries: retryCfg.max_retries, sessionResets: pinned ? 0 : retryCfg.session_resets,
        deadlineMs: runDeadline, waitMs: nominal, capMs,
      });
      let wait = end ? Math.min(nominal, Math.max(0, end - Date.now())) : nominal;
      log(`cross-ai: ladder ${name} next=${step.next} why=${step.why}`);
      let inCallHard = null;
      if (step.next === 'hard') {
        inCallHard = hardHandler(r, evidence, step.why, sid, cls);
        if (inCallHard.inCallS === undefined) return inCallHard;
        step = { next: ladder.canResume ? 'same' : 'new', why: 'hard-in-call' };
        wait = inCallHard.inCallS * 1000;
      }
      if (pinned && (step.next === 'new' || step.next === 'reset')) {
        log(`cross-ai: --session-id was given; no fresh session is started (next=${step.next} refused)`);
        dropState(hit || 'crash');
        return { ok: false, status: hit || 'crash', outBytes: r.outBytes, cli_rc: r.code ?? '-', ...evidence, ...counts(), stopped: 'class' };
      }
      if (step.next === 'stop') {
        // A no-budget timeout, the first attempt stopped before any retry was admitted, stays
        // timeout/124 (ladderStop). Any other soft deadline or cap stop is the hard handler's.
        const noBudget = step.why === 'deadline' && !admitted && r.timedOut && attempt === 0;
        if (soft && (step.why === 'deadline' || step.why === 'cap') && !noBudget) {
          return hardHandler(r, evidence, step.why, sid, cls);
        }
        const stop = ladderStop(step, Boolean(r.timedOut), admitted, hit || 'crash');
        dropState(stop.status);
        return {
          ok: false, status: stop.status, timedOut: stop.timedOut,
          code: stop.status === 'timeout' ? 124 : undefined,
          outBytes: r.outBytes, cli_rc: r.code ?? '-', ...evidence,
          ...counts(), stopped: stoppedWhy(step, false),
        };
      }
      if (mode === 'review' && beforeSig !== null) {
        const mid = await treeState(ctx.cwd, runDeadline);
        if (mid === null) {
          const status = gitFailStatus();
          return {
            ok: false, status, outBytes: r.outBytes, cli_rc: r.code ?? '-',
            ...counts(), stopped: 'class',
          };
        }
        if (stateSig(mid) !== beforeSig) {
          return {
            ok: false, status: 'contract_violation', outBytes: r.outBytes, cli_rc: r.code ?? '-',
            ...counts(), stopped: 'class',
          };
        }
      }
      // The first series is spent, so whatever follows continues the task.
      if (ladder.retry >= retryCfg.max_retries) gated = true;
      const opensSeries = !continued && (step.next === 'reset' || (step.next === 'new' && !gated));
      // Every fresh session is gated, not only the one that opens a series: a later failed
      // attempt's own out-of-scope edit must stop the next fresh start too.
      const fresh = step.next === 'reset' || step.next === 'new';
      if (fresh && mode === 'exec') {
        const base = step.next === 'reset' ? seriesSig : seenSig;
        // The tree now, after the failed attempt: its own edits are what the gate must judge.
        const now = await treeState(ctx.cwd, runDeadline);
        const nowSig = now ? stateSig(now) : null;
        const gate = await rung2Gate(ctx.cwd, base, userPrompt, nowSig);
        if (gate.stop) {
          log(`cross-ai: ladder ${name} stop why=dirty-tree`);
          const stopped = cls === 'quota' ? 'quota' : gate.status;
          return {
            ok: false, status: stopped, outBytes: r.outBytes, cli_rc: r.code ?? '-',
            ...evidence, ...counts(), stopped: 'dirty-tree',
          };
        }
        if (opensSeries) {
          seriesInput = gate.input;
          gated = true;
          seriesSig = nowSig;
        }
      }
      // A later series of one call continues the task, so it carries the resume note. The
      // gate's own text wins when the tree changed.
      if (gated && (seriesInput === prompt || seriesInput === userPrompt)) {
        seriesInput = `${RESUME_MSG}\n\n${prompt}`;
      }
      const nextInput = seriesInput;
      if (inCallHard) {
        saveCycle(sid, inCallHard.at, inCallHard.record);
        if (!stateWritable) return { ok: false, status: cls, timedOut: false, outBytes: r.outBytes, cli_rc: r.code ?? '-', ...evidence, ...counts(), cycle: inCallHard.cycle, exit: 75, stopped: 'rungs' };
        log(`cross-ai: hard wait in call s=${inCallHard.inCallS} cycle=${inCallHard.cycle}`);
        ladder.cycle = inCallHard.cycle + 1;
      }
      log(`cross-ai: wait ms=${wait} next=${step.next} retry=${k}`);
      await sleep(budgetMs(wait, runDeadline));
      if (aborting) return { ok: false, outBytes: r.outBytes, cli_rc: r.code ?? '-', ...counts() };
      admitted = true;
      ladder.prevWaitMs = wait;
      if (step.next === 'same') {
        ladder.retry += 1;
        rungLabel = 'same';
        // A fresh series opened over a dirty tree keeps the gate's resume text; every other
        // same-session retry gets the plain resume note.
        const resumed = gated ? seriesInput : RESUME_MSG;
        const retry = sameArgv(sid, resumed);
        const resumeProblem = reviewProblem(retry.argv, sid);
        if (resumeProblem) return refuseReview(resumeProblem);
        argv = retry.argv;
        attemptSid = sid;
        input = retry.input;
      } else if (step.next === 'reset') {
        ladder.resets += 1;
        ladder.retry = 0;
        rungLabel = 'reset';
        const retry = newSessionArgv(name, rt, model, ctx, mode, nextInput);
        argv = retry.argv;
        attemptSid = rt.argvFile ? (opts.sessionId ?? null) : (argv.includes(ctx.sid) ? ctx.sid : null);
        input = retry.input;
      } else {
        ladder.retry += 1;
        rungLabel = 'new';
        // A new session with nothing to resume gets the task itself. The resume note is for a
        // session that already ran, or for a reset continuing one.
        const fresh = gated ? nextInput : prompt;
        const retry = newSessionArgv(name, rt, model, ctx, mode, fresh);
        argv = retry.argv;
        // An argv-file row rebuilds the same filled argv, so its explicit id (maybe embedded, such as --session=<id>) stays.
        attemptSid = rt.argvFile ? (opts.sessionId ?? null) : (argv.includes(ctx.sid) ? ctx.sid : null);
        input = retry.input;
      }
    }
  } finally {
    dropTemp(tmp);
  }
}

// Every <files> body in the prompt, split on commas. Backticks, quotes and a leading `./`
// are presentation, not part of the path. The union of every block is the plan's own scope
// (assumption A6: the GSD prompt carries the whole plan).
function promptFiles(prompt) {
  const out = new Set();
  const re = /<files>([\s\S]*?)<\/files>/g;
  let m;
  while ((m = re.exec(String(prompt || '')))) {
    for (let raw of m[1].split(',')) {
      raw = raw.trim().replace(/^[`'"]+|[`'"]+$/g, '').replace(/^\.\//, '').trim();
      if (raw) out.add(raw);
    }
  }
  return out;
}

// D-13 seed, label judged: lowercase substrings after 999.15-LESSONS 1.3 (a 26-03 report admitted
// unimplemented plan cases); recall unverified (the original report text is not in the repository).
// CONFIG.admissionPhrases replaces it; the matched phrase is printed.
const ADMISSION_PHRASES_SEED = Object.freeze(['not implemented', 'not completed', 'did not implement', 'did not complete', "didn't implement", "didn't complete", 'left unimplemented', 'left for later', 'deferred to a later', 'deferred to a follow-up', 'could not finish', 'could not complete', 'could not implement', 'unable to complete', 'unable to implement', 'remaining work', 'skipped the task', 'skipped task']);
// D-14 seed, source: GSD execute-phase/detail/elaboration.md step 4 (the orchestrator writes STATE
// and ROADMAP after an external lane) plus REQUIREMENTS from the 999.15 list, verified 2026-11-16.
// CONFIG.forbiddenPaths replaces it; a path the prompt's <files> names is exempt.
const FORBIDDEN_PATHS_SEED = Object.freeze(['.planning/STATE.md', '.planning/ROADMAP.md', '.planning/REQUIREMENTS.md']);
const PLAN_ID_RE = /^[0-9]+(\.[0-9]+)*-[0-9]+[A-Za-z0-9.-]*$/;

// SPEC R5 / D-12: directory paths cover descendants on whole components.
function pathCovers(listed, changed) { return changed === listed || (listed.endsWith('/') && changed.startsWith(listed)); }

// Scan task blocks once; unclosed planned tasks cannot be checked.
function parseTasks(text) {
  const src = String(text || ''); const tasks = []; const re = /<task(\s[^>]*)?>|<\/task>/g;
  let open = null; let m;
  const planned = (attrs) => { const type = (/\btype\s*=\s*["']([^"']*)["']/.exec(attrs) || [])[1]; return type === undefined || !type.startsWith('checkpoint'); };
  const unclosed = (o) => { if (planned(o.attrs)) tasks.push({ name: `task ${tasks.length + 1} (unclosed)`, files: [], checkable: false }); };
  while ((m = re.exec(src))) {
    if (m[0].startsWith('</')) {
      if (open && planned(open.attrs)) {
        const body = src.slice(open.end, m.index); const named = /<name>([\s\S]*?)<\/name>/.exec(body);
        const name = (named ? named[1] : '').replace(/[\x00-\x1f\x7f-\x9f]+/g, ' ').trim() || `task ${tasks.length + 1}`;
        const files = [...promptFiles(body)];
        tasks.push({ name, files, checkable: files.some((f) => !/[*?[\]{}]/.test(f)) });
      }
      open = null;
    } else { if (open) unclosed(open); open = { attrs: m[1] || '', end: m.index + m[0].length }; }
  }
  if (open) unclosed(open);
  return tasks;
}

// Orchestrator decision 4: port of gsd-core gate-evaluation-scope.cjs:113-119, :126-134 and :145-148
// (zero padding only in the leading integer of each half; the rest literal).
function planSubjectRe(id) {
  const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const padded = (v) => { const m = /^(\d+)(.*)$/.exec(v); return m ? `0*${esc(m[1].replace(/^0+(?=\d)/, ''))}${esc(m[2])}` : esc(v); };
  const dash = id.indexOf('-'); const phase = dash > 0 ? id.slice(0, dash) : ''; const plan = dash > 0 ? id.slice(dash + 1) : '';
  const fragment = /^[0-9A-Za-z.]+$/.test(phase) && /^[0-9A-Za-z.]+$/.test(plan) ? `${padded(phase)}-${padded(plan)}` : esc(id);
  return new RegExp(`^[a-z]+\\(${fragment}\\)!?:`);
}

function coverageOf(tasks, commits, planId = null) {
  const subjectRe = planId ? planSubjectRe(planId) : null; const touched = commits.flatMap((c) => c.paths);
  const covered = []; const uncovered = []; const unchecked = [];
  for (const t of tasks) {
    if (!t.checkable) unchecked.push(t.name);
    else if (t.files.filter((f) => !/[*?[\]{}]/.test(f)).some((f) => touched.some((p) => pathCovers(f, p)))) covered.push(t.name);
    else uncovered.push(t.name);
  }
  const planIdCount = subjectRe ? commits.filter((c) => subjectRe.test(c.subject || '')).length : null;
  return { covered: covered.length, checkable: covered.length + uncovered.length, uncovered, unchecked, planned: tasks.length, planIdCount, planIdShort: planIdCount !== null && planIdCount < tasks.length };
}

// Strip fenced and inline code before matching admissions.
function stripCode(text) {
  const out = []; let fence = null;
  for (const line of String(text || '').split('\n')) {
    const m = /^ {0,3}(`{3,}|~{3,})/.exec(line);
    if (fence) { if (m && m[1][0] === fence[0] && m[1].length >= fence.length && /^ {0,3}(`+|~+)\s*$/.test(line)) fence = null; continue; }
    if (m) { fence = m[1]; continue; }
    out.push(line);
  }
  return out.join('\n').replace(/(?<!`)(`+)(?!`)[\s\S]*?(?<!`)\1(?!`)/g, ' ');
}
function admissionHits(answer, phrases) {
  const prose = stripCode(answer).toLowerCase();
  return [...new Set(phrases.map((p) => String(p).toLowerCase()).filter((p) => p && prose.includes(p)))];
}
function forbiddenHits(changed, forbidden, named) {
  const names = [...named];
  return [...new Set(changed)].filter((p) => forbidden.some((f) => pathCovers(f, p)) && !names.some((n) => pathCovers(n, p))).sort();
}
// SPEC R12 / D-24: the runner supervision flags (not lane settings), sorted; --describe lists them.
const SUPERVISION_FLAGS = Object.freeze(['--baseline', '--blocked-clear', '--blocked-status', '--forbid', '--idle-timeout', '--plan-id', '--pool', '--sweep']);
// SPEC R5: the result of each blocking finding code; every other code of FINDING_CODES is informational.
const FINDING_RESULTS = Object.freeze({ no_commit: 'partial', task_uncovered: 'partial', admits_skipped: 'partial', forbidden_path: 'contract_violation' });

function planFindings(input) {
  const cov = coverageOf(input.tasks, input.commits, input.planId); const out = [];
  if (input.answered && input.tasks.length > 0 && input.commits.length === 0) out.push({ code: 'no_commit', detail: `no commit since the baseline for ${input.tasks.length} planned task${input.tasks.length === 1 ? '' : 's'}` });
  else if (cov.uncovered.length || cov.planIdShort) out.push({ code: 'task_uncovered', detail: [cov.uncovered.length ? findingDetail(cov.uncovered) : '', cov.planIdShort ? `plan-id ${input.planId}: ${cov.planIdCount} commits for ${cov.planned} tasks` : ''].filter(Boolean).join('; ') });
  const hits = admissionHits(input.answer, input.phrases);
  if (hits.length) out.push({ code: 'admits_skipped', detail: findingDetail(hits.map((p) => `phrase "${p}"`)) });
  const bad = forbiddenHits(input.changed, input.forbidden, input.named);
  if (bad.length) out.push({ code: 'forbidden_path', detail: findingDetail(bad) });
  const names = [...input.named]; const outside = names.length === 0 ? [] : [...new Set(input.changed)].filter((p) => !names.some((n) => pathCovers(n, p))).sort();
  if (outside.length) out.push({ code: 'outside_plan_files', detail: `${outside.length} path${outside.length === 1 ? '' : 's'}: ${findingDetail(outside)}` });
  if (input.uncommitted.length) out.push({ code: 'uncommitted_edits', detail: findingDetail(input.uncommitted) });
  if (cov.unchecked.length) out.push({ code: 'coverage_unchecked', detail: findingDetail(cov.unchecked) });
  const codes = out.map((f) => f.code);
  const results = codes.map((c) => FINDING_RESULTS[c]).filter(Boolean);
  const blocking = results.includes('contract_violation') ? 'contract_violation' : (results.includes('partial') ? 'partial' : null);
  return { coverage: input.tasks.length === 0 ? 'n/a' : `${cov.covered}/${cov.checkable}`, findings: out, blocking };
}

// Sorted paths that differ between two tree-ish ids; null when git fails, times out or overflows.
async function diffNames(a, b, cwd, limit = runDeadline) {
  const git = which('git', process.env.PATH || '');
  if (!git || !a || !b) return null;
  const diff = await runChild(git, ['-c', 'core.quotepath=off', 'diff-tree', '-r', '--no-renames', '--name-only', '-z', a, b], { cwd, capMs: GIT_CAP_MS, limit });
  if (diff.timedOut || diff.spawnErr || diff.code !== 0 || diff.stdoutDropped) { gitFailed(diff, 'diff-tree'); return null; }
  return diff.stdout.split('\0').filter((p) => p.length > 0).sort();
}

// D-11: port of gsd-core gate-evaluation-scope.cjs:787-803 (parseLog): records end in \x1e, fields
// are split on \x1f, a record without a hex sha is skipped.
function parseCommitLog(text) {
  const commits = [];
  for (const record of String(text || '').split('\x1e')) {
    const trimmed = record.replace(/^\n+/, '');
    if (!trimmed) continue;
    const [sha, parents, subject] = trimmed.split('\x1f');
    if (!sha || !/^[0-9a-f]{40}([0-9a-f]{24})?$/.test(sha)) continue;
    commits.push({ sha, parents: (parents ?? '').split(' ').filter(Boolean), subject: subject ?? '', paths: [] });
  }
  return commits;
}

// D-11: port of gsd-core gate-evaluation-scope.cjs:760-768 (commitFiles): a non-merge contributes
// what it changed, a two-parent merge only what the merge itself changed (--remerge-diff), an
// octopus merge or a git without --remerge-diff nothing; null when the read fails.
async function commitPaths(git, sha, parents, cwd, limit) {
  const merge = parents.length > 1;
  if (merge && parents.length !== 2) return [];
  const args = ['-c', 'core.quotepath=off', 'show', merge ? '--remerge-diff' : '--first-parent', '--pretty=format:', '--name-only', '-z', sha];
  const r = await runChild(git, args, { cwd, capMs: GIT_CAP_MS, limit });
  if (merge && !r.timedOut && !r.spawnErr && r.code !== 0) return [];
  if (r.timedOut || r.spawnErr || r.code !== 0 || r.stdoutDropped) { gitFailed(r, 'show'); return null; }
  return r.stdout.split('\0').filter((p) => p.length > 0);
}

// D-11: read commits since the baseline and their paths; null on failure.
async function commitsSince(baseHead, endHead, cwd, limit) {
  if (!endHead) return [];
  const git = which('git', process.env.PATH || '');
  if (!git) { gitFailure = { kind: 'error', what: 'not found' }; return null; }
  const range = baseHead ? `${baseHead}..${endHead}` : endHead;
  const r = await runChild(git, ['log', '--format=%H%x1f%P%x1f%s%x1e', range], { cwd, capMs: GIT_CAP_MS, limit });
  if (r.timedOut || r.spawnErr || r.code !== 0 || r.stdoutDropped) { gitFailed(r, 'log'); return null; }
  const commits = parseCommitLog(r.stdout);
  for (const c of commits) {
    const paths = await commitPaths(git, c.sha, c.parents, cwd, limit);
    if (paths === null) return null;
    c.paths = paths;
  }
  return commits;
}

// An owner's CONFIG list replaces a seed only as a list of strings; anything else keeps the seed with a note.
function configList(name, seed) {
  const value = CONFIG[name];
  if (value === undefined || value === null) return seed;
  if (Array.isArray(value) && value.every((s) => typeof s === 'string')) return value;
  log(`cross-ai: note: CONFIG.${name} is not a list of strings; the seed list is used`);
  return seed;
}

// SPEC R5: check spawned execute runs against the baseline; fail closed on missing git evidence.
async function executeFindings(prompt, r, end, cwd, o, noTree) {
  const common = { answer: r.ok ? (r.text || '') : '', answered: Boolean(r.ok), phrases: configList('admissionPhrases', ADMISSION_PHRASES_SEED), forbidden: [...configList('forbiddenPaths', FORBIDDEN_PATHS_SEED), ...(o.forbid || [])], named: promptFiles(prompt), planId: o.planId ?? null };
  let result;
  if (noTree) result = planFindings({ ...common, tasks: [], commits: [], changed: [], uncommitted: [] });
  else {
    const b = liveBaseline; const limit = finalizeBy;
    const commits = await commitsSince(b.head, end.head, cwd, limit);
    if (commits === null) return { gitFailed: true };
    const baseTree = String(b.tree).split('\t')[0]; const endTree = String(end.tree).split('\t')[0];
    const changed = await diffNames(baseTree, endTree, cwd, limit);
    if (changed === null) return { gitFailed: true };
    let uncommitted = [];
    if (b.head && end.head) {
      const endDirty = await diffNames(end.head, endTree, cwd, limit);
      const baseDirty = await diffNames(b.head, baseTree, cwd, limit);
      if (endDirty === null || baseDirty === null) return { gitFailed: true };
      uncommitted = endDirty.filter((p) => !baseDirty.includes(p));
    }
    result = planFindings({ ...common, tasks: parseTasks(prompt), commits, changed, uncommitted });
  }
  for (const f of result.findings) addFinding(f.code, f.detail);
  liveCheck.coverage = result.coverage;
  return result;
}

// Null when the ignored or nested parts differ, or git fails: those changes have no path to
// account for. Otherwise the sorted paths that differ between the two write-tree ids.
async function changedPaths(before, mid, cwd) {
  const beforeParts = String(before || '').split('\t');
  const midParts = String(mid || '').split('\t');
  if (beforeParts.slice(1).join('\t') !== midParts.slice(1).join('\t')) return null;
  const git = which('git', process.env.PATH || '');
  if (!git || !beforeParts[0] || !midParts[0]) return null;
  return diffNames(beforeParts[0], midParts[0], cwd);
}

// Rung 2 runs over an unchanged tree with the original prompt, or over a changed tree only
// when every changed path is one the prompt lists (the resume message goes before it then).
// A non-git cwd, a git failure or any other change stops the ladder.
async function rung2Gate(cwd, beforeSig, prompt, midSig) {
  const stop = (status) => ({ stop: true, status });
  if (!inGitTree(cwd) || beforeSig === null) return stop('transient');
  const beforeTree = String(beforeSig).split('\t').slice(1).join('\t');
  // The caller's snapshot when it has one, taken after the failed attempt and before the next.
  const mid = midSig !== undefined ? midSig : await (async () => {
    const read = await treeState(cwd, runDeadline);
    return read === null ? null : stateSig(read);
  })();
  if (mid === null) return stop(gitFailStatus());
  if (mid === beforeSig) return { stop: false, input: prompt };
  const midTree = String(mid).split('\t').slice(1).join('\t');
  const changed = await changedPaths(beforeTree, midTree, cwd);
  const allowed = promptFiles(prompt);
  if (!changed || !changed.length || changed.some((p) => !allowed.has(p))) return stop('transient');
  return { stop: false, input: `${RESUME_MSG}\n\n${prompt}` };
}

// One cap for every file a call names (argv file, SKILL.md body, MCP file); equals INPUT_CAP (SPEC R4, R13, R14).
const FILE_READ_MAX = 65536;

// Strict reader for files a call names: read once, non-blocking open, same file as checked, regular file, size-capped, strict UTF-8, no BOM.
function readCallFile(flag, relPath, opts = {}) {
  const { cwdOnly = false, mode = 0, cwd = process.cwd() } = opts;
  const unreadable = () => new Error(`${flag} unreadable: ${relPath}`);
  let abs, pre, fd;
  try { abs = fs.realpathSync(path.resolve(cwd, relPath)); } catch { throw unreadable(); }
  if (cwdOnly) {
    let rel;
    try { rel = path.relative(fs.realpathSync(cwd), abs); } catch { throw unreadable(); }
    if (rel === '' || rel.startsWith('..') || path.isAbsolute(rel)) throw new Error(`${flag} must name a file inside the working directory: ${relPath}`);
  }
  try { pre = fs.statSync(abs); } catch { throw unreadable(); }
  try { fd = fs.openSync(abs, fs.constants.O_RDONLY | fs.constants.O_NONBLOCK); } catch { throw unreadable(); }
  try {
    const st = fs.fstatSync(fd);
    if (st.dev !== pre.dev || st.ino !== pre.ino) throw new Error(`${flag} changed while it was opened: ${relPath}`);
    if (!st.isFile()) throw new Error(`${flag} must name a regular file: ${relPath}`);
    if (mode && (st.mode & mode)) throw new Error(`${flag} must not be accessible by group or others (mode ${(st.mode & 0o777).toString(8).padStart(3, '0')}): ${relPath}`);
    const buf = Buffer.alloc(FILE_READ_MAX + 1);
    let n = 0;
    while (n < buf.length) { const count = fs.readSync(fd, buf, n, buf.length - n, null); if (!count) break; n += count; }
    if (n > FILE_READ_MAX) throw new Error(`${flag} is over ${FILE_READ_MAX} bytes: ${relPath}`);
    const bytes = buf.subarray(0, n);
    let text;
    try { text = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bytes); } catch { throw new Error(`${flag} is not valid UTF-8: ${relPath}`); }
    if (text.startsWith('\uFEFF')) throw new Error(`${flag} starts with a byte-order mark: ${relPath}`);
    return { abs, bytes, text };
  } finally { fs.closeSync(fd); }
}

function loadMcpConfig(o) {
  if (o.mcpConfig === null) return null;
  const { abs, text } = readCallFile('--mcp-config', o.mcpConfig, { mode: 0o077 });
  const shown = redactSecrets(redactSecrets(o.mcpConfig).replace(/[\x00-\x1f\x7f-\x9f]/g, ''));
  let doc;
  try { doc = strictJson(text); } catch (e) {
    throw new Error(e.message.startsWith('duplicate key') ? `--mcp-config holds a duplicate key (key not shown): ${shown}` : `--mcp-config is not valid JSON (content not shown): ${shown}`);
  }
  const isObj = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);
  if (!isObj(doc)) throw new Error('--mcp-config: the top level must be a JSON object');
  const names = isObj(doc.mcpServers) ? jsonKeys(doc.mcpServers) : [];
  if (!names.length) throw new Error('--mcp-config: mcpServers must be a non-empty object');
  for (const [i, name] of names.entries()) if (!MCP_SERVER_RE.test(name)) throw new Error(`--mcp-config: server name ${i + 1} (in file order) must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$`);
  return { file: abs, servers: names };
}

function planMcp(row, role, mcp) {
  if (!mcp) return { adds: [], report: [] };
  const form = row.forms?.mcp ?? null;
  let reason = null;
  if ((row.profiles?.[role] || []).includes('--no-mcp')) reason = 'mode_forbids';
  else if (!form || form.label.state === 'unknown') reason = form?.reason || 'no_form';
  else if (form.label.state === 'unverified') reason = form.reason || 'unverified_form';
  const adds = reason ? [] : [form.flag, `${form.prefix || ''}${mcp.file}`, ...(form.after || [])];
  const report = mcp.servers.map((value) => reason ? { name: 'mcp', value, state: 'ignored', reason } : { name: 'mcp', value, state: 'applied', proof: adds });
  return { adds, report };
}

function skillFrontmatterName(text) {
  const front = /^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/.exec(text);
  return front ? (/^name:[ \t]*["']?([^"'\r\n]*?)["']?[ \t]*$/m.exec(front[1])?.[1] ?? null) : null;
}

function loadSkills(o) {
  const skills = [];
  for (const [at, item] of o.skillArgs.entries()) {
    if (item.flag !== '--skill-path') continue;
    const shown = redactSecrets(item.value.replace(/[\x00-\x1f\x7f-\x9f]/g, ''));
    if (PROMPT_CONTROL_RE.test(item.value)) throw new Error('--skill-path: the path holds a control character');
    let dir;
    try { dir = fs.realpathSync(path.resolve(process.cwd(), item.value)); if (!fs.statSync(dir).isDirectory()) throw new Error(); }
    catch { throw new Error(`--skill-path ${shown}: no such directory`); }
    if (PROMPT_CONTROL_RE.test(dir)) throw new Error('--skill-path: the path holds a control character');
    if (skills.some((s) => s.path === dir)) continue;
    const file = path.join(dir, 'SKILL.md');
    if (!fs.existsSync(file)) throw new Error(`--skill-path ${shown}: no SKILL.md in the directory`);
    const { bytes, text } = readCallFile('--skill-path', file);
    if (text === '') throw new Error(`--skill-path ${shown}: SKILL.md is empty`);
    const dirName = path.basename(dir), fmName = skillFrontmatterName(text);
    const name = fmName && SKILL_NAME_RE.test(fmName) ? fmName : SKILL_NAME_RE.test(dirName) ? dirName : null;
    if (!name) throw new Error(`--skill-path ${shown}: the skill needs a name of shape ^[a-z0-9][a-z0-9-]{0,63}$ (frontmatter name or directory name)`);
    skills.push({ name, path: dir, dirName, fmName, sha256: crypto.createHash('sha256').update(bytes).digest('hex'), body: text, byName: false, at });
  }
  for (const [at, item] of o.skillArgs.entries()) {
    if (item.flag !== '--skill-name') continue;
    const s = skills.find((v) => v.path && (v.dirName === item.value || v.fmName === item.value));
    if (s) { s.byName = true; s.name = item.value; s.at = Math.min(s.at, at); }
    else if (!skills.some((v) => !v.path && v.name === item.value)) skills.push({ name: item.value, path: null, dirName: null, fmName: null, sha256: null, body: null, byName: true, at });
  }
  return skills.sort((a, b) => a.at - b.at);
}

function skillPathArg(form, s) {
  if (!form.flag || form.label.state !== 'verified') return null;
  if (!form.root) return s.path;
  const tail = path.sep + form.root.split('/').join(path.sep) + path.sep + s.dirName;
  return s.path.endsWith(tail) ? s.path.slice(0, -tail.length) : null;
}
function skillBlock(s) { return `<skill name="${s.name}" path="${s.path}" sha256="${s.sha256}">\n${s.body}\n</skill>\n`; }
function planSkills(row, skills) {
  const forms = row.forms?.skills || skillsNone('no recorded skill form');
  const adds = [], report = []; let promptPrefix = '';
  for (const s of skills) {
    const entry = { name: 'skill', value: s.name };
    if (s.byName && forms.name.form && forms.name.label.state === 'verified') {
      const text = forms.name.form.replace('<name>', s.name) + '\n';
      promptPrefix += text; report.push({ ...entry, state: 'applied', form: 'name', proofPrompt: text });
    } else if (s.path && skillPathArg(forms.path, s) !== null) {
      const frag = [forms.path.flag, skillPathArg(forms.path, s)];
      adds.push(...frag); report.push({ ...entry, state: 'applied', form: 'path', proof: frag });
    } else if (s.path && forms.prose.label.state === 'verified') {
      const text = skillBlock(s); promptPrefix += text;
      report.push({ ...entry, state: 'applied', form: 'prose', proofPrompt: text, sha256: s.sha256 });
    } else {
      const why = s.byName ? forms.name : forms.path;
      report.push({ ...entry, state: 'ignored', reason: why.reason || (why.label.state === 'unverified' ? 'unverified_form' : 'no_form') });
    }
  }
  return { adds, promptPrefix, report };
}
function skillBlockLines(report) { return report.filter((e) => e.name === 'skill' && e.form === 'prose').map((e) => `cross-ai: skill-block ${e.value} bytes=${Buffer.byteLength(e.proofPrompt)} sha256=${e.sha256}`); }
function composePrompt(prefix, prepended, raw, preamble) { return prefix + (prepended === null ? raw : `${prepended.replace(/^(?:<!--[^\n]*-->\r?\n)+/, '')}\n\n${raw}`) + preamble; }

const JSON_KEY_ORDER = new WeakMap();
function jsonKeys(obj) { return JSON_KEY_ORDER.get(obj) || Object.keys(obj); }

// JSON.parse keeps the last duplicate key; a call file must not hold one (SPEC R14 adjacency).
function strictJson(text) {
  const value = JSON.parse(text);
  const stack = [], records = [];
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (c === '"') {
      const start = i++;
      while (text[i] !== '"') { if (text[i] === '\\') i++; i++; }
      const frame = stack[stack.length - 1];
      if (frame && frame.wantKey) {
        const key = JSON.parse(text.slice(start, i + 1));
        if (frame.keys.has(key)) throw new SyntaxError(`duplicate key ${JSON.stringify(key)}`);
        frame.keys.add(key); frame.order.push(key); frame.key = key; frame.wantKey = false;
      }
    } else if (c === '{') {
      const parent = stack[stack.length - 1];
      const objectPath = stack.length === 0 ? [] : parent?.path != null ? [...parent.path, parent.key] : null;
      stack.push({ keys: new Set(), wantKey: true, order: [], path: objectPath, key: null });
    } else if (c === '[') stack.push(null);
    else if (c === '}' || c === ']') {
      const frame = stack.pop();
      if (frame && frame.path !== null) records.push([frame.path, frame.order]);
    } else if (c === ',') { const frame = stack[stack.length - 1]; if (frame) frame.wantKey = true; }
  }
  for (const [objectPath, order] of records) {
    let target = value;
    for (const key of objectPath) target = target == null ? undefined : Object.getOwnPropertyDescriptor(target, key)?.value;
    if (target !== null && typeof target === 'object') JSON_KEY_ORDER.set(target, order);
  }
  return value;
}

function loadArgvFile(relPath, text = null) {
  if (text === null) {
    try { text = readCallFile('--argv-file', relPath, { cwdOnly: true }).text; } catch (e) { return { error: e.message }; }
  }
  let argv;
  try { argv = strictJson(text); } catch { return { error: `--argv-file is not strict JSON: ${relPath}` }; }
  if (!Array.isArray(argv)) return { error: '--argv-file must hold a JSON array of strings' };
  if (!argv.length) return { error: '--argv-file holds an empty array; the first element is the command' };
  for (const [i, el] of argv.entries()) {
    if (typeof el !== 'string') return { error: `--argv-file element ${i} is not a string` };
    if (!el) return { error: `--argv-file element ${i} is empty` };
    if (el.includes('\u0000')) return { error: `--argv-file element ${i} holds a NUL character` };
    const remainder = ARGV_FILE_PLACEHOLDERS.reduce((s, placeholder) => s.replaceAll(placeholder, ''), el);
    if (/[{}]/.test(remainder)) return { error: `--argv-file element ${i} holds an unknown placeholder (only {model}, {effort} and {session})` };
    if (i === 0 && ARGV_FILE_PLACEHOLDERS.some((placeholder) => el.includes(placeholder))) return { error: '--argv-file element 0 is the command and holds no placeholder' };
  }
  const slots = Object.fromEntries(['model', 'effort', 'session'].map((name) => [name, argv.slice(1).some((el) => el.includes(`{${name}}`))]));
  return { argv, slots };
}

const CURSOR_MODES = new Set(['ask', 'plan']);
const ROUTE_VALUES = new Set(['router', 'unknown']);
// SPEC R4, 0c: a runtime id is a name checked by shape, never a table verdict; ids match exactly and case-sensitively.
const RUNTIME_ID_RE = /^[A-Za-z0-9][A-Za-z0-9-]{0,31}$/;
// SPEC R4: --prefer, --model-<cli> and --route-<cli> may name any cli; only the selected runtime's value is read.
const CLI_NAME_RE = /^[a-z0-9-]+$/;
function ownValue(obj, key) { return obj && Object.hasOwn(obj, key) ? obj[key] : undefined; }
// D-07 level token.
const LEVEL_RE = /^[a-z][a-z0-9_-]{0,15}$/;
// D-15 context label.
const CONTEXT_RE = /^[a-z0-9][a-z0-9._-]{0,15}$/;
// SPEC R7 session id.
const SESSION_ID_RE = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;
// SPEC R13 skill name.
const SKILL_NAME_RE = /^[a-z0-9][a-z0-9-]{0,63}$/;
// C0, DEL and C1 control characters.
const CONTROL_CHAR_RE = /[\x00-\x1f\x7f-\x9f]/;
// SPEC R6/R8 (D-13): the prompt-value control set, equal to ai_kit_spec.prompt_guard.is_control_char (shared fixture tests/fixtures/prompt_control_chars.json); used by the skill flags only.
const PROMPT_CONTROL_RE = /[\p{Cc}\p{Zl}\p{Zp}\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff]/u;

function parseArgs(argv) {
  const o = {
    runtime: null, prefer: null, model: null, toolsProfile: null,
    models: Object.create(null), routes: Object.create(null), mode: 'exec', timeout: null, outerTimeout: null,
    printArgv: false, preamble: true, selfTest: false, selfTestList: false, classifyOnly: null,
    codexEffort: null, codexServiceTier: null, cursorMode: null,
    prependFile: null, codexSandbox: null, childPgidFile: null,
    role: null, effort: null, context: null, escalateRuntime: false, escalateModel: false,
    sessionId: null, host: null, skillPaths: [], skillNames: [], skillArgs: [], mcpConfig: null, argvFile: null, describe: false, sweep: false, baseline: null, idleTimeout: null, forbid: [], planId: null, pool: null, blockedStatus: null, blockedClear: null,
  };
  let modeFlag = null;
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]; const v = () => { if (i + 1 >= argv.length) throw new Error(`${a} needs a value`); return argv[++i]; };
    if (a === '--runtime') {
      o.runtime = v();
      if (!RUNTIME_ID_RE.test(o.runtime)) throw new Error(`--runtime must match ${RUNTIME_ID_RE.source}`);
    }
    else if (a === '--prefer') o.prefer = v().split(',').filter(Boolean);
    else if (a === '--model') {
      // The universal floor (SPEC R5); the model flag may precede runtime selection.
      // The selected row's seed shape only advises, in main.
      o.model = v();
      if (!MODEL_ID_FLOOR.test(o.model)) throw new Error(`${a} must match ${MODEL_ID_FLOOR.source}`);
    } else if (a === '--tools-profile') {
      o.toolsProfile = v();
      if (!['exec', 'review', 'none'].includes(o.toolsProfile)) {
        throw new Error('--tools-profile must be exec, review or none');
      }
    } else if (a.startsWith('--model-')) {
      const cli = a.slice(8);
      if (!CLI_NAME_RE.test(cli)) throw new Error(`${a}: the cli name must match ${CLI_NAME_RE.source}`);
      const id = v();
      if (!MODEL_ID_FLOOR.test(id)) throw new Error(`${a} must match ${MODEL_ID_FLOOR.source}`);
      o.models[cli] = id;
    } else if (a.startsWith('--route-')) {
      const cli = a.slice(8);
      if (!CLI_NAME_RE.test(cli)) throw new Error(`${a}: the cli name must match ${CLI_NAME_RE.source}`);
      const route = v();
      if (!ROUTE_VALUES.has(route)) throw new Error(`${a} must be router or unknown`);
      o.routes[cli] = route;
    } else if (a === '--classify-only') o.classifyOnly = v();
    else if (a === '--pool') { o.pool = v(); if (!BLOCKED_POOL_RE.test(o.pool)) throw new Error('--pool must look like <provider>:free'); }
    else if (a === '--blocked-status' || a === '--blocked-clear') { const pool = v(); if (!BLOCKED_POOL_RE.test(pool)) throw new Error(`${a} must look like <provider>:free`); if (a === '--blocked-status') o.blockedStatus = pool; else o.blockedClear = pool; }
    else if (a === '--mode') { o.mode = v(); if (!['exec', 'review'].includes(o.mode)) throw new Error('--mode must be exec or review'); modeFlag = o.mode; }
    else if (a === '--timeout') { o.timeout = Number(v()); if (!(o.timeout > 0)) throw new Error('--timeout must be > 0'); }
    else if (a === '--outer-timeout') {
      o.outerTimeout = Number(v());
      if (!(o.outerTimeout > 0)) throw new Error('--outer-timeout must be > 0');
    } else if (a === '--print-argv') o.printArgv = true;
    else if (a === '--no-preamble') o.preamble = false;
    else if (a === '--prepend-file') o.prependFile = v();
    else if (a === '--codex-sandbox') {
      o.codexSandbox = v();
      if (o.codexSandbox !== 'workspace-write') {
        throw new Error('--codex-sandbox must be workspace-write');
      }
    } else if (a === '--child-pgid-file') o.childPgidFile = v();
    else if (a === '--codex-effort') {
      o.codexEffort = v();
      if (!LEVEL_RE.test(o.codexEffort)) throw new Error(`${a} must match ${LEVEL_RE.source}`);
    } else if (a === '--codex-service-tier') {
      o.codexServiceTier = v();
      if (!/^[A-Za-z0-9_-]+$/.test(o.codexServiceTier)) throw new Error('--codex-service-tier must match [A-Za-z0-9_-]+');
    } else if (a === '--cursor-mode') {
      o.cursorMode = v();
      if (!CURSOR_MODES.has(o.cursorMode)) throw new Error('--cursor-mode must be ask or plan');
    } else if (a === '--self-test') o.selfTest = true;
    else if (a === '--self-test-list') { o.selfTest = true; o.selfTestList = true; }
    else if (a === '--role') { o.role = v(); if (!['review', 'execute'].includes(o.role)) throw new Error('--role must be review or execute'); }
    else if (a === '--effort') { o.effort = v(); if (!LEVEL_RE.test(o.effort)) throw new Error(`${a} must match ${LEVEL_RE.source}`); }
    else if (a === '--context') { o.context = v(); if (!CONTEXT_RE.test(o.context)) throw new Error(`${a} must match ${CONTEXT_RE.source}`); }
    else if (a === '--escalate-runtime') o.escalateRuntime = true;
    else if (a === '--escalate-model') o.escalateModel = true;
    else if (a === '--session-id') { o.sessionId = v(); if (!SESSION_ID_RE.test(o.sessionId)) throw new Error(`${a} must match ${SESSION_ID_RE.source}`); }
    else if (a === '--host') { o.host = v(); if (!['auto', 'none'].includes(o.host)) throw new Error('--host must be auto or none'); }
    else if (a === '--skill-name') { const n = v(); if (PROMPT_CONTROL_RE.test(n) || !SKILL_NAME_RE.test(n)) throw new Error(`${a} must match ${SKILL_NAME_RE.source}`); o.skillNames.push(n); o.skillArgs.push({ flag: a, value: n }); }
    else if (['--skill-path', '--mcp-config', '--argv-file'].includes(a)) {
      const p = v();
      if (p === '' || (a === '--skill-path' ? PROMPT_CONTROL_RE : CONTROL_CHAR_RE).test(p)) throw new Error(`${a} must be a non-empty path without control characters`);
      if (a === '--skill-path') { o.skillPaths.push(p); o.skillArgs.push({ flag: a, value: p }); }
      else if (a === '--mcp-config') o.mcpConfig = p;
      else o.argvFile = p;
    } else if (a === '--idle-timeout') {
      const s = v();
      if (s === 'default') o.idleTimeout = 'default';
      else if (/^[0-9]+$/.test(s) && Number(s) <= IDLE_MAX_S) o.idleTimeout = Number(s);
      else throw new Error('--idle-timeout must be an integer from 0 to 86400 or default');
    } else if (a === '--baseline') {
      o.baseline = v(); if (!/^[0-9a-fA-F]{7,64}$/.test(o.baseline)) throw new Error('--baseline must be 7 to 64 hex characters');
    } else if (a === '--describe') o.describe = true;
    else if (a === '--sweep') o.sweep = true;
    else if (a === '--forbid') {
      const raw = v();
      if (!raw.trim()) throw new Error('--forbid needs a repo-relative path');
      const body = raw.endsWith('/') ? raw.slice(0, -1) : raw;
      if (CONTROL_CHAR_RE.test(raw) || raw.startsWith('/') || body.split('/').some((s) => s === '' || s === '.' || s === '..')) throw new Error("--forbid must be a repo-relative path with no empty, '.' or '..' segment and no control character");
      o.forbid.push(raw);
    }
    else if (a === '--plan-id') { o.planId = v(); if (!PLAN_ID_RE.test(o.planId)) throw new Error(`--plan-id must match ${PLAN_ID_RE.source}`); }
    else throw new Error(`unknown argument: ${a}`);
  }
  if (o.sweep && (o.printArgv || o.classifyOnly !== null)) throw new Error('--sweep cannot be combined with --print-argv or --classify-only');
  if ((o.blockedStatus !== null || o.blockedClear !== null) && ((o.blockedStatus !== null && o.blockedClear !== null) || o.printArgv || o.classifyOnly !== null || o.sweep || o.describe || o.selfTest)) throw new Error('--blocked-status and --blocked-clear cannot be combined with each other or with --print-argv, --classify-only, --sweep, --describe or --self-test');
  if (o.effort !== null && o.codexEffort !== null && o.effort !== o.codexEffort) throw new Error('--effort and --codex-effort disagree');
  if (o.effort === null) o.effort = o.codexEffort;
  if (o.role !== null) {
    const fromRole = o.role === 'execute' ? 'exec' : 'review';
    if (modeFlag !== null && modeFlag !== fromRole) throw new Error('--role and --mode disagree');
    o.mode = fromRole;
  }
  if (o.mode === 'exec' && o.cursorMode) throw new Error('--cursor-mode is review-only');
  // SPEC R6: only the entry that runs is checked; the ignored rest gets resolveRuntime's notice.
  if (o.runtime === null && o.prefer && o.prefer.length && !CLI_NAME_RE.test(o.prefer[0])) {
    throw new Error(`--prefer: the entry that runs must match ${CLI_NAME_RE.source}`);
  }
  return o;
}

// One runtime per call (SPEC R6, D-13): --runtime, then the first --prefer entry, then
// CONFIG.runtime, then the first CONFIG.prefer entry. A list is never walked.
function resolveRuntime(o) {
  const ignored = (source, first, rest) => (
    `cross-ai: ${source} reads only its first entry (${first}); ignored: ${rest.join(', ')}`
  );
  if (o.runtime) {
    const notes = [];
    if (o.prefer && o.prefer.length) {
      notes.push(`cross-ai: --runtime ${o.runtime} wins; ignored --prefer ${o.prefer.join(',')}`);
    }
    return { name: o.runtime, notes };
  }
  if (o.prefer && o.prefer.length) {
    const notes = [];
    if (o.prefer.length > 1) notes.push(ignored('--prefer', o.prefer[0], o.prefer.slice(1)));
    return { name: o.prefer[0], notes };
  }
  if (typeof CONFIG.runtime === 'string') {
    if (!RUNTIME_ID_RE.test(CONFIG.runtime)) return { error: `cross-ai: CONFIG.runtime must match ${RUNTIME_ID_RE.source}` };
    return { name: CONFIG.runtime, notes: [] };
  }
  const prefer = Array.isArray(CONFIG.prefer) ? CONFIG.prefer.filter((n) => typeof n === 'string' && n) : [];
  if (prefer.length) {
    if (!RUNTIME_ID_RE.test(prefer[0])) return { error: `cross-ai: the first CONFIG.prefer entry must match ${RUNTIME_ID_RE.source}` };
    const notes = [];
    if (prefer.length > 1) notes.push(ignored('CONFIG.prefer', prefer[0], prefer.slice(1)));
    return { name: prefer[0], notes };
  }
  return { error: 'cross-ai: no runtime: pass --runtime <id>' };
}

const FIXTURE_EVIDENCE_RE = /tests\/fixtures\/cross_ai_errors\/[a-z0-9-]+\.json/;
// 38.1 D-05: a runtime-level flag demotes every pattern except a row scoped to this host whose evidence names its fixture.
function patternFor(rt, cli, mode, cls) {
  const label = cls && cls.label ? cls.label : 'none';
  if (!rt) return 'unverified';
  const flagged = rt.errorsUnverified || (mode === 'exec' && rt.execLabel?.state === 'unverified');
  if (!flagged) return label;
  const row = cls && cls.rule ? PATTERNS.find((item) => item.id === cls.rule) : undefined;
  return row && row.cli === cli && row.label === 'verified' && FIXTURE_EVIDENCE_RE.test(row.evidence) ? label : 'unverified';
}

// Pure: one JSON line per case, then the status line. No spawn, no write, stdin unread.
function runClassifyOnly(file) {
  let raw;
  try {
    raw = fs.readFileSync(path.resolve(process.cwd(), file), 'utf8');
  } catch (e) {
    log(`cross-ai: --classify-only unreadable: ${e.message}`);
    return reportAndFinish('usage', { ...liveFields, tree: 'unknown', exit: 2 });
  }
  let cases;
  try { cases = JSON.parse(raw); } catch (e) {
    log(`cross-ai: --classify-only invalid JSON: ${e.message}`);
    return reportAndFinish('usage', { ...liveFields, tree: 'unknown', exit: 2 });
  }
  if (!Array.isArray(cases)) {
    log('cross-ai: --classify-only file must be a JSON array');
    return reportAndFinish('usage', { ...liveFields, tree: 'unknown', exit: 2 });
  }
  const lines = [];
  for (const entry of cases) {
    const cli = entry && entry.cli;
    if (typeof cli !== 'string' || !RUNTIME_ID_RE.test(cli)) {
      log(`cross-ai: --classify-only cli must match ${RUNTIME_ID_RE.source}`);
      return reportAndFinish('usage', { ...liveFields, tree: 'unknown', exit: 2 });
    }
    if (entry.route !== undefined && entry.route !== 'router-inferred' && !ROUTE_VALUES.has(entry.route)) {
      log(`cross-ai: --classify-only bad route: ${entry.route}`);
      return reportAndFinish('usage', { ...liveFields, tree: 'unknown', exit: 2 });
    }
    const route = entry.route === 'router' || entry.route === 'unknown' || entry.route === 'router-inferred'
      ? entry.route : routeOf(cli, entry.model || '', {});
    const cls = classifyStop({
      cli, route, model: entry.model || '', stderr: entry.stderr || '',
      events: extractEvents(cli, entry.stdout || ''),
      stdout: entry.stdout || '',
    });
    // Same rule as a live run (38.1 D-05, patternFor); a cli with no row reports unverified.
    const pattern = patternFor(Object.hasOwn(RUNTIMES, cli) ? RUNTIMES[cli] : undefined, cli, null, cls);
    lines.push(JSON.stringify({ name: entry.name, status: cls.status, rule: cls.rule, pattern, route }));
  }
  if (lines.length) process.stdout.write(`${lines.join('\n')}\n`);
  return reportAndFinish('ok', { ...liveFields, tree: 'clean', exit: 0, out: lines.length });
}

function readStdin() {
  if (process.stdin.isTTY) return null;
  try { return fs.readFileSync(0, 'utf8'); } catch { return null; }
}

function callOf(o, name, model, newSessionId, skillPlan = null, mcp = null) { return { model, effort: o.effort, context: o.context, sessionId: o.sessionId, newSessionId, sandbox: o.mode === 'exec' && Boolean(o.codexSandbox), configEffort: ownValue(CONFIG.effort, name) ?? null, escalateRuntime: o.escalateRuntime, escalateModel: o.escalateModel, skillPlan, mcp, hostSetting: { value: hostSettingValue(o.host, process.env.AIKIT_HOST).value, available: hostAvailable(process.env) } }; }

function logExecLabel(name, rt, mode) {
  if (mode === 'exec' && rt.execLabel && rt.execLabel.state === 'unverified') log(`cross-ai: note: ${name} execute formula is unverified (no live probe record)`);
}

// --describe reports the template generation from the header that the render keeps.
function ownTemplateVersion() {
  const head = readOr(fileURLToPath(import.meta.url), '').slice(0, 512);
  const match = head.match(/^\/\/ ai-kit-cross-ai generator=\S+ template=(\d+) /m);
  return match ? Number(match[1]) : null;
}

// Sorted keys at every depth (SPEC R9 ordering): the golden file stays stable.
function describeValue(value) {
  if (Array.isArray(value)) return value.map(describeValue);
  if (value instanceof RegExp) return value.source;
  if (typeof value === 'function') return undefined;
  if (value && Object.getPrototypeOf(value) === Object.prototype) {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, describeValue(value[key])]));
  }
  return value;
}

// SPEC R9 / D-10: what Python reads instead of mirroring the rows.
function describeJson(env) {
  const runtimes = {};
  // 0b-12: forms are copied keyed by setting, so a later row field shows up with no change here.
  for (const id of Object.keys(RUNTIMES).sort()) {
    const row = RUNTIMES[id];
    const label = (f) => typeof row[f] !== 'function' ? { state: 'unknown', source: 'no formula in the runner' } :
      FORMULA_LABELS[id]?.[f] ?? { state: 'unverified', source: 'unverified: no label recorded' };
    const entry = {
      formulas: { exec: typeof row.exec === 'function', review: typeof row.review === 'function', resume: typeof row.resume === 'function' },
      formula_labels: { exec: label('exec'), review: label('review'), resume: label('resume') },
      listing: row.list ? row.list.argv : null,
      listing_label: !row.list ? { state: 'unknown', source: 'no listing in the runner' } :
        FORMULA_LABELS[id]?.listing ?? { state: 'unverified', source: 'unverified: no label recorded' },
      source: typeof row.source === 'string' && row.source ? row.source : 'unverified',
    };
    for (const [setting, form] of Object.entries(row.forms || {})) entry[setting] = form;
    runtimes[id] = entry;
  }
  return {
    schema: 1,
    template_version: ownTemplateVersion(),
    settings: [...SETTING_NAMES],
    reasons: [...SETTING_REASONS],
    states: [...SETTING_STATES],
    runtimes,
    host: { available: hostAvailable(env) },
    statuses: Object.fromEntries(Object.entries(STATUS_TABLE).map(([name, row]) => [name, row.exit])),
    findings: FINDING_CODES.map((code) => ({ code, result: FINDING_RESULTS[code] ?? 'info' })),
    supervision_flags: [...SUPERVISION_FLAGS],
    classes: Object.fromEntries([...ROW_CLASSES, 'crash'].map((name) => [name, { exit: STATUS_TABLE[name].exit, router_quota: PATTERNS.some((row) => row.class === name && row.routerClass === 'quota') }])),
  };
}

// 38-08: the self-test harness ships only beside the template. A rendered copy has no
// sibling and refuses; a sibling that exists but fails to load is a crash, not a refusal.
const SELF_TEST_FILE = 'cross-ai-selftest.mjs';
async function loadSelfTest() {
  const file = path.join(path.dirname(RUNNER_FILE), SELF_TEST_FILE);
  let mod = null;
  try {
    fs.accessSync(file, fs.constants.R_OK);
    const st = fs.statSync(file);
    if (st.isFile() && st.size > 0) mod = await import(new URL(`./${SELF_TEST_FILE}`, import.meta.url));
  } catch (e) {
    // Only a file that is gone or unreadable refuses; a syntax or link error stays a crash.
    if (!['ENOENT', 'EACCES', 'EPERM', 'EISDIR', 'ERR_MODULE_NOT_FOUND'].includes(e && e.code)) throw e;
  }
  if (mod && typeof mod.blackBoxSelfTest === 'function') return mod.blackBoxSelfTest;
  log('cross-ai: the self-test is not shipped in this copy; run it from the template');
  return null;
}

async function main(argv) {
  runStartedMs = Date.now();
  finished = false;
  liveFields = {
    cli: '-', model: '-', cli_rc: '-', out: 0, tree: 'clean',
    route: 'unknown', rule: '-', pattern: 'none',
  };
  liveSettings = { report: [], sessionId: null, escalation: { runtime: false, model: false } };
  liveCheck = { coverage: '-', findings: [] };
  liveLock = null;
  lockUpdateFailed = false;
  liveBaseline = null;
  baselineFile = null;
  baselineNoted = false;
  let o;
  try { o = parseArgs(argv); } catch (e) {
    log(`cross-ai: ${e.message}`);
    return reportAndFinish('usage', { ...liveFields, tree: 'unknown', exit: 2 });
  }
  OVERLAY_IDS = new Set();
  // The self-test never reads the owner's real overlay; each case builds its own.
  if (o.selfTest) {
    const harness = await loadSelfTest();
    return harness ? harness(o.selfTestList) : 2;
  }
  if (o.describe) {
    process.stdout.write(`${JSON.stringify(describeValue(describeJson(process.env)), null, 2)}\n`);
    return reportAndFinish('ok', { ...liveFields, tree: 'clean', exit: 0, out: 0 });
  }
  if (o.sweep) {
    await sweepRuns({ explicit: true, hostingOff: false });
    return reportAndFinish('ok', { ...liveFields, tree: 'clean', exit: 0, out: 0 });
  }
  if (o.blockedStatus !== null) { process.stdout.write(`${blockedStatusLine(o.blockedStatus)}\n`); return reportAndFinish('ok', { ...liveFields, tree: 'clean', exit: 0, out: 0 }); }
  if (o.blockedClear !== null) { const done = blockedClear(o.blockedClear); if (done !== 'cleared' && done !== 'absent') { log(`cross-ai: blocked-until clear failed (${done})`); return reportAndFinish('crash', { ...liveFields, tree: 'clean', exit: 1, out: 0 }); } return reportAndFinish('ok', { ...liveFields, tree: 'clean', exit: 0, out: 0 }); }
  TABLE = mergeCatalog(PATTERNS, loadOverlay(process.env));
  if (o.classifyOnly !== null) return runClassifyOnly(o.classifyOnly);
  childPgidFile = o.childPgidFile;
  childPgidBroken = false;
  const picked = resolveRuntime(o);
  if (picked.error) {
    log(picked.error);
    return reportAndFinish('usage', { ...liveFields, tree: 'unknown', exit: 2 });
  }
  for (const note of picked.notes) log(note);
  const name = picked.name;
  let declared = null;
  if (o.argvFile) {
    if (!argvFileAllowed(ownValue(RUNTIMES, name), o.mode)) {
      log(`cross-ai: --argv-file needs a runtime with no ${o.mode === 'exec' ? 'execute' : 'review'} formula in the runner; ${name} has one`);
      return reportAndFinish('usage', { ...liveFields, tree: 'unknown', exit: 2 });
    }
    const loaded = loadArgvFile(o.argvFile);
    if (loaded.error) {
      log(loaded.error.startsWith('cross-ai: ') ? loaded.error : `cross-ai: ${loaded.error}`);
      return reportAndFinish('usage', { ...liveFields, tree: 'unknown', exit: 2 });
    }
    declared = argvFileRow(loaded);
  } else if (!Object.hasOwn(RUNTIMES, name)) {
    log(`cross-ai: no formula for ${name} in the runner; pass --argv-file, or use a runtime it has a formula for`);
    return reportAndFinish('usage', { ...liveFields, tree: 'unknown', exit: 2 });
  }
  const rt = declared || RUNTIMES[name];
  let skills, skillPlan, mcp;
  try { skills = loadSkills(o); skillPlan = planSkills(rt, skills); mcp = loadMcpConfig(o); } catch (e) {
    log(`cross-ai: ${redactSecrets(redactSecrets(String(e.message)).replace(/[\x00-\x1f\x7f-\x9f]/g, ''))}`);
    return reportAndFinish('usage', { ...liveFields, tree: 'unknown', exit: 2 });
  }
  if (o.model !== null && o.models[name] !== undefined) {
    // The flag is split from "wins" so the hardcoded-model guard reads no model name (HUB-09).
    log('cross-ai: --model' + ` wins; ignored --model-${name} ${o.models[name]}`);
  }
  const model = o.model ?? o.models[name] ?? ownValue(CONFIG.models, name);
  if (model && !MODEL_ID_FLOOR.test(model)) {
    log(`cross-ai: the model for ${name} must match ${MODEL_ID_FLOOR.source}`);
    return reportAndFinish('usage', { ...liveFields, tree: 'unknown', exit: 2 });
  }
  // SPEC R5: a seed shape advises and never refuses; the live listing below still ends bad_model.
  if (model && rt.modelId && !rt.modelId.test(model)) {
    log(redactSecrets(`cross-ai: note: model id shape is unusual for ${name} (seed shape: ${rt.modelId.source})`));
  }
  const c = {
    name, rt, model,
    bin: resolveBin(rt, process.env.PATH || ''),
  };
  if (o.mode === 'exec' && !rt.exec) {
    log(`cross-ai: ${name} is review-only (no exec formula)`);
    return reportAndFinish('usage', { ...liveFields, tree: 'unknown', exit: 2 });
  }
  const profile = o.toolsProfile ?? o.mode;
  if (o.mode === 'review' && profile === 'exec') {
    log('cross-ai: review mode allows only the review or none tools profile');
    return reportAndFinish('usage', { ...liveFields, tree: 'unknown', exit: 2 });
  }
  if (rt.profiles === null) {
    if (profile !== o.mode) {
      log(`cross-ai: ${name} has no tools profile ${profile}`);
      return reportAndFinish('usage', { ...liveFields, tree: 'unknown', exit: 2 });
    }
  } else if (!Object.hasOwn(rt.profiles, profile)) {
    log(`cross-ai: ${name} has no tools profile ${profile}`);
    return reportAndFinish('usage', { ...liveFields, tree: 'unknown', exit: 2 });
  }
  const profileFlags = rt.profiles ? rt.profiles[profile] : [];

  const dl = logDeadline(process.cwd(), process.env, o);
  if (dl.error) {
    log(dl.error);
    return reportAndFinish('usage', { ...liveFields, tree: 'unknown', exit: 2 });
  }
  // Read once: an edit during the call has no effect until the next call. runCli reads these
  // in 25.1-02; this call only resolves and logs them.
  // --print-argv is the documented read-only check (WR-53): it migrates and writes nothing.
  if (!o.printArgv) migrateRetrySources(process.cwd(), process.env);
  const resolved = resolveRetry(process.cwd(), process.env);
  if (o.codexSandbox && o.mode !== 'exec') {
    log('cross-ai: --codex-sandbox applies to exec mode only; review already runs read-only');
  }
  const hostNote = hostSettingValue(o.host, process.env.AIKIT_HOST).note;
  if (hostNote) log(hostNote);
  // SPEC R1: the first attempt's budget by attemptCapMs's own rule; runDeadline is not set yet on this path.
  const nowMs = Date.now();
  const idleBudgetMs = attemptCapMs({}, nowMs, 0, nowMs + dl.inner * 1000);
  const idlePlan = planIdle({ idleTimeout: o.idleTimeout, budgetMs: o.printArgv ? idleBudgetMs : null }, CONFIG, o.mode === 'exec' ? 'execute' : 'review');
  for (const note of idlePlan.notices) log(note);
  if (o.printArgv || idlePlan.idleS > 0) log(idlePlan.idleS > 0 ? `cross-ai: idle watchdog on timeout=${idlePlan.idleS}s` : 'cross-ai: idle watchdog off');
  if (o.printArgv) {
    const plan = c.model ? planSettings(rt, o.mode, callOf(o, name, c.model, '<sid>', skillPlan, mcp)) : null;
    if (plan?.error) {
      log(`cross-ai: ${plan.error}`);
      return reportAndFinish('usage', { ...liveFields, tree: 'unknown', exit: 2 });
    }
    const ctx = {
      cwd: process.cwd(), sid: plan ? (plan.sessionId ?? '<sid>') : '<sid>', outFile: '<tmp>/last-message.md',
      adds: plan ? plan.adds : undefined, codexServiceTier: o.codexServiceTier, cursorMode: o.cursorMode,
      codexSandbox: o.mode === 'exec' ? o.codexSandbox : null,
      profileFlags, promptArg: '<prompt>',
    };
    const formula = rt[o.mode];
    const argvOut = (c.model && typeof formula === 'function')
      ? withExtra(name, plan.resume ? rt.resume(plan.model, ctx, plan.sessionId, o.mode) : formula(plan.model, ctx)) : null;
    process.stdout.write(`${name}\t${c.bin || 'MISSING'}\t${argvOut ? JSON.stringify(shownArgv(rt, argvOut)) : 'NO MODEL'}\n`);
    if (plan && argvOut) {
      confirmReport(plan.report, argvOut, composePrompt(skillPlan.promptPrefix, null, '<prompt>', ''), o.mode);
      for (const line of reportLines(plan.report)) log(line);
      for (const line of skillBlockLines(plan.report)) log(line);
      log(`cross-ai: capabilities ${JSON.stringify(laneCapabilities(rt, o.mode, argvOut, plan.report))}`);
      logExecLabel(name, rt, o.mode);
      liveSettings.report = plan.report;
      liveSettings.sessionId = rt.argvFile ? plan.sessionId : (o.sessionId && sessionShown(o.sessionId) ? o.sessionId : null);
      liveSettings.escalation = { runtime: Boolean(o.escalateRuntime), model: Boolean(o.escalateModel) };
      log(`cross-ai: model-id ${redactKeyShapes(String(plan.model).replace(/[\x00-\x1f\x7f-\x9f]/g, ''))}`);
      const rung1 = sameSessionArgv(name, rt, plan.model, ctx, '<sid>', o.mode);
      if (rung1) log(`cross-ai: rung1 ${name} argv=${JSON.stringify(shownArgv(rt, rung1.argv))}`);
      else log(`cross-ai: rung1 ${name} unavailable`);
      const rung2 = newSessionArgv(name, rt, plan.model, ctx, o.mode, '<prompt>');
      log(`cross-ai: rung2 ${name} argv=${JSON.stringify(shownArgv(rt, rung2.argv))}`);
    }
    return reportAndFinish('ok', {
      ...liveFields, tree: 'clean', exit: 0, out: 0,
      retry: resolved.retry, capS: resolved.capS,
    });
  }
  const raw = readStdin();
  if (!raw || !raw.trim()) {
    log('cross-ai: pipe the prompt on stdin');
    return reportAndFinish('empty_stdin', { ...liveFields, tree: 'clean', exit: 2 });
  }
  let prepended = null;
  if (o.prependFile) {
    try {
      prepended = fs.readFileSync(path.resolve(process.cwd(), o.prependFile), 'utf8');
    } catch {
      log(`cross-ai: --prepend-file unreadable: ${o.prependFile}`);
      return reportAndFinish('usage', { ...liveFields, tree: 'unknown', exit: 2 });
    }
    // The guidance file's stamp lines are bookkeeping for a human editor, not prompt text.
  }
  const prompt = composePrompt(skillPlan.promptPrefix, prepended, raw, o.preamble ? (o.mode === 'exec' ? EXEC_PREAMBLE : REVIEW_PREAMBLE) : '');
  if (rt.argvPrompt) {
    const over = argvPromptProblem(prompt);
    if (over) {
      log(`cross-ai: ${name} takes the prompt on argv; ${over.bytes} bytes is over ${ARGV_PROMPT_MAX}`);
      return reportAndFinish('usage', { ...liveFields, cli: name, model: model || '-', tree: 'unknown', exit: 2 });
    }
  }
  const { outer, inner: innerS, innerDefault } = dl;
  runDeadline = Date.now() + innerS * 1000;
  const marginMs = (outer - innerDefault) * 1000;
  finalizeBy = runDeadline + Math.min(FINALIZE_CAP_MS, Math.floor(marginMs / 2));

  liveFields.cli = c.name;
  liveFields.model = c.model ?? '-';
  liveFields.route = routeOf(c.name, c.model || '', o.routes);
  // Decided once: a directory with no .git ancestor still dispatches (D-34).
  const noTree = !inGitTree(process.cwd());
  if (noTree) {
    log(`cross-ai: ${process.cwd()} is not inside a git work tree; running without the tree ` +
      'check (tree=unknown)');
    if (o.mode === 'review') {
      log('cross-ai: review mode cannot verify the read-only contract outside a git work tree');
    }
  }
  if (!c.bin) {
    log(`cross-ai: ${c.name} not installed; no other CLI runs (no automatic fallback)`);
    return reportAndFinish('not_installed', {
      ...liveFields, cli: c.name, model: c.model || '-', tree: 'clean', exit: 127,
    });
  }
  if (!c.model) {
    log(`cross-ai: no model configured for ${c.name} (--model-${c.name})`);
    return reportAndFinish('no_model', {
      ...liveFields, cli: c.name, model: '-', tree: 'clean', exit: 2,
    });
  }
  // The review argv is known before any spawn: a widening extra is a usage error, not a run.
  if (o.mode === 'review' && c.model) {
    const probe = {
      cwd: process.cwd(), sid: '<sid>', outFile: '<tmp>/last-message.md',
      cursorMode: o.cursorMode, profileFlags,
      promptArg: '<prompt>',
    };
    const bare = c.rt.review(c.model, probe);
    const problem = reviewArgvProblem(withExtra(c.name, bare), bare, c.rt.reviewExtras || []);
    if (problem) {
      const allowed = (c.rt.reviewExtras || []).join(', ') || 'none';
      log(`cross-ai: review argv for ${c.name} holds ${problem} from CONFIG.extraArgs; ` +
        `review extras allowed for ${c.name}: ${allowed}; refused`);
      return reportAndFinish('usage', { ...liveFields, tree: 'unknown', exit: 2 });
    }
  }
  // SPEC R2: one plan per call; lines print after the review-argv check and before the listing preflight and the spawn.
  const plan = planSettings(c.rt, o.mode, callOf(o, c.name, c.model, crypto.randomUUID(), skillPlan, mcp));
  if (plan.error) {
    log(`cross-ai: ${plan.error}`);
    return reportAndFinish('usage', { ...liveFields, tree: 'unknown', exit: 2 });
  }
  if (aborting) {
    return reportAndFinish('signal', { ...liveFields, exit: 128 + aborting }, 'signal');
  }
  // SPEC R3: after validation and the prompt read, before the first snapshot or spawn.
  let baselineHead = null;
  // SPEC R4: --baseline is checked against the repository before the lock (a usage error takes no lock).
  if (o.baseline !== null && o.mode !== 'exec') log('cross-ai: --baseline applies to execute runs only; ignored');
  else if (o.baseline !== null) {
    const git = noTree ? null : which('git', process.env.PATH || '');
    const r = git ? await runChild(git, ['rev-parse', '--verify', '-q', o.baseline + '^{commit}'], { cwd: process.cwd(), capMs: GIT_CAP_MS, limit: runDeadline }) : null;
    const head = r && !r.timedOut && !r.spawnErr && r.code === 0 ? r.stdout.trim() : '';
    const t = BASELINE_SHA_RE.test(head) ? await runChild(git, ['rev-parse', '--verify', '-q', head + '^{tree}'], { cwd: process.cwd(), capMs: GIT_CAP_MS, limit: runDeadline }) : null;
    const treeId = t && !t.timedOut && !t.spawnErr && t.code === 0 ? t.stdout.trim() : '';
    if (!BASELINE_SHA_RE.test(treeId)) {
      log(`cross-ai: --baseline ${o.baseline} is not a commit in this repository`);
      return reportAndFinish('usage', { ...liveFields, tree: 'unknown', exit: 2 });
    }
    baselineHead = { head, treeId };
  }
  await sweepRuns({ explicit: false, hostingOff: hostSettingValue(o.host, process.env.AIKIT_HOST).value === 'none' });
  const lockRoot = checkoutRoot(process.cwd());
  if (o.mode === 'exec') {
    const got = await acquireLock(lockRoot, { cli: c.name, model: c.model, hostingOff: hostSettingValue(o.host, process.env.AIKIT_HOST).value === 'none' });
    if (!got.ok) {
      log(got.line);
      if (got.hosted) log(got.hosted);
      return reportAndFinish('locked', { ...liveFields, cli: c.name, model: c.model, tree: 'clean', exit: 75, cli_rc: '-', out: 0 });
    }
  } else if (lockSeen(lockRoot)) log('cross-ai: note: an execute run holds this checkout; the tree check may void this review');
  const before = noTree ? null : await treeState(process.cwd(), runDeadline);
  if (aborting) {
    return reportAndFinish('signal', { ...liveFields, exit: 128 + aborting }, 'signal');
  }
  if (!noTree && before === null) {
    return reportAndFinish(gitFailStatus(), {
      ...liveFields, cli_rc: '-', tree: 'unknown', exit: 1,
    });
  }
  // SPEC R4: after the lock, from the start snapshot itself, keyed by the caller's own text; a non-git cwd has no baseline.
  if (o.mode === 'exec' && !noTree) await resolveBaseline(lockRoot, before, raw, { cli: c.name, model: c.model }, baselineHead, resolved.capS);
  const runCtx = { cwd: process.cwd(), sid: plan.sessionId ?? '<sid>', outFile: '<tmp>/last-message.md', codexServiceTier: o.codexServiceTier, cursorMode: o.cursorMode, codexSandbox: o.mode === 'exec' ? o.codexSandbox : null, profileFlags, promptArg: '<prompt>', adds: plan.adds };
  const resumed = plan.resume && plan.sessionId ? sameSessionArgv(c.name, c.rt, plan.model, runCtx, plan.sessionId, o.mode) : null;
  const firstArgv = resumed ? resumed.argv : withExtra(c.name, c.rt[o.mode](plan.model, runCtx));
  const report = confirmReport(plan.report, firstArgv, prompt, o.mode) || plan.report;
  for (const line of reportLines(report)) log(line);
  for (const line of skillBlockLines(report)) log(line);
  logExecLabel(c.name, c.rt, o.mode);
  liveSettings.report = report;
  const hostEntry = report.find((e) => e.name === 'host');
  const hostPlan = hostEntry && hostEntry.state === 'applied' && hostEntry.value === 'herdr' ? { role: o.mode === 'exec' ? 'execute' : 'review', runtime: c.name, entry: hostEntry, failed: false } : null;
  const sessionEntry = report.find((e) => e.name === 'session');
  liveSettings.sessionId = rt.argvFile ? plan.sessionId : (o.sessionId && sessionShown(o.sessionId) ? o.sessionId : null);
  liveSettings.escalation = { runtime: Boolean(o.escalateRuntime), model: Boolean(o.escalateModel) };
  const listEnv = childEnv(c.rt.env, process.env);
  const listing = await listModels(c.rt, c.bin, listEnv, runDeadline);
  if (listing.ok) {
    const listed = c.rt.modelSuffix ? plan.model.replace(c.rt.modelSuffix, '') : plan.model;
    if (listed !== plan.model) {
      log(`cross-ai: ${c.name} preflight checks ${listed}; the suffix ${plan.model.slice(listed.length)} is not validated`);
    }
    if (!listing.ids.includes(listed)) {
      log(`cross-ai: ${c.name} bad_model (${plan.model} not in model list)`);
      return reportAndFinish('bad_model', {
        ...liveFields, cli: c.name, model: c.model, tree: 'clean', cli_rc: '-',
      });
    }
  } else if (listing.reason !== 'no listing') {
    log(`cross-ai: ${c.name} model list unavailable (${listing.reason}); not preflighted`);
  }
  if (aborting) {
    return reportAndFinish('signal', { ...liveFields, exit: 128 + aborting }, 'signal');
  }
  // From here until the next snapshot nothing proves the tree clean (CR-03).
  liveFields.tree = 'unknown';
  const r = await runCli(c.name, c.rt, c.bin, plan.model, o.mode, prompt, {
    beforeSig: noTree ? null : stateSig(before),
    adds: plan.adds, sessionId: plan.sessionId ?? null, resume: Boolean(plan.resume), callSessionId: o.sessionId ?? null,
    // An argv-file retry re-runs the same filled argv, so its session is kept without the pin (no fresh id exists to refuse).
    pinSession: !rt.argvFile && Boolean(o.sessionId) && sessionEntry?.state === 'applied',
    codexServiceTier: o.codexServiceTier,
    cursorMode: o.cursorMode, codexSandbox: o.mode === 'exec' ? o.codexSandbox : null,
    route: liveFields.route, retry: resolved.retry, capS: resolved.capS,
    profileFlags,
    host: hostPlan,
    idleS: idlePlan.idleS,
    idlePlan,
  });
  liveFields.out = r.outBytes || 0;
  liveFields.cli_rc = r.cli_rc ?? '-';
  const counted = {
    attempts: r.attempts || 0, cycles: r.cycles || 0,
    retryAfterS: r.retryAfterS, cycle: r.cycle, reportDone: r.reportDone,
    firstFailureMs: r.firstFailureMs, lastFailureMs: r.lastFailureMs,
    dueAtMs: r.dueAtMs, check: r.check,
  };
  const why = r.stopped || (r.timedOut ? 'timeout' : 'class');
  // The snapshot reads against the finalize window, not the call deadline: an attempt may
  // legitimately run until the deadline (cycle-3 attempt cap), and the tree read comes after.
  let after = noTree ? null : await treeState(process.cwd(), finalizeBy);
  // A signal during this snapshot killed its git child: read once more on the signal budget.
  if (!noTree && aborting && after === null) after = await treeState(process.cwd(), finalizeBy);
  const tree = noTree ? 'unknown' : treeLabel(before, after);
  liveFields.tree = tree;
  if (aborting) {
    return reportAndFinish('signal', { ...liveFields, exit: 128 + aborting }, 'signal');
  }
  // SPEC R5: check only spawned runs, including failed runs without replacing their status.
  const checked = o.mode === 'exec' && (r.attempts || 0) > 0 && (noTree || (after && liveBaseline)) ? await executeFindings(raw, r, after, process.cwd(), o, noTree) : null;
  if (aborting) return reportAndFinish('signal', { ...liveFields, exit: 128 + aborting }, 'signal'); // Signal during post-run reads.
  // 38.1 R11: the record follows the attempt's class, whatever the tree state or a later git read says.
  if (r.ok) blockedClearAfterOk(o.pool); else blockedAfterStop(o.pool, c.model, { ...r, cli: c.name });
  if (
    r.status === 'contract_violation' || r.status === 'git_error' || r.status === 'git_timeout'
  ) {
    const treeField = r.status === 'contract_violation' ? tree : 'unknown';
    return reportAndFinish(r.status, {
      ...liveFields, tree: treeField, cli_rc: r.cli_rc ?? '-', exit: 1, ...counted,
    }, why);
  }
  // A classified status (live kill or post-hoc) wins over a bare timeout (cycle 3).
  if (r.timedOut && !r.status) {
    return reportAndFinish('timeout', {
      ...liveFields, tree, exit: 124, cli_rc: r.cli_rc ?? '-', ...counted,
    }, 'timeout');
  }
  if (o.mode === 'review' && before && after && tree === 'dirty') {
    return reportAndFinish('contract_violation', {
      ...liveFields, tree, cli_rc: r.cli_rc ?? '-', exit: 1, ...counted,
    }, 'class');
  }
  if (r.ok) {
    if (!noTree && (after === null || before === null)) {
      const status = gitFailStatus();
      return reportAndFinish(status, { ...liveFields, tree: 'unknown', cli_rc: 0, exit: 1 });
    }
    if (o.mode === 'exec' && tree === 'clean') {
      return reportAndFinish('no_change', {
        ...liveFields, cli: c.name, model: c.model, tree, cli_rc: 0, ...counted,
      });
    }
    // No change wins; unavailable git evidence fails closed before blocking findings.
    if (checked?.gitFailed) return reportAndFinish(gitFailStatus(), { ...liveFields, tree, cli_rc: 0, exit: 1, ...counted });
    if (checked?.blocking === 'contract_violation') return reportAndFinish('contract_violation', { ...liveFields, tree, cli_rc: 0, exit: 1, ...counted }, 'class');
    if (checked?.blocking === 'partial') return reportAndFinish('partial', { ...liveFields, tree, cli_rc: 0, exit: 1, ...counted }, 'class');
    process.stdout.write(r.text);
    return reportAndFinish('ok', {
      ...liveFields, tree, exit: 0, cli_rc: 0, out: r.outBytes || 0, ...counted,
    });
  }
  if (!noTree && after === null && r.exit !== 69 && r.retryAfterS === undefined) {
    const status = gitFailStatus();
    return reportAndFinish(status, {
      ...liveFields, tree: 'unknown', cli_rc: r.cli_rc ?? '-', exit: 1,
    });
  }
  const finalStatus = r.status || 'crash';
  return reportAndFinish(finalStatus, {
    ...liveFields, tree, cli_rc: r.cli_rc, cli: c.name, model: c.model,
    route: r.route, rule: r.rule, pattern: r.pattern, upstream: r.upstream,
    exit: r.exit, ...counted,
  }, why);
}

if (process.argv[1] && fs.realpathSync(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(process.argv.slice(2)).then(
    (code) => exitFlushed(code ?? 0),
    (e) => {
      log(`cross-ai: internal error: ${e && e.stack || e}`);
      exitFlushed(reportAndFinish(
        'crash', { ...liveFields, tree: 'unknown', exit: 1, cli_rc: '-' },
      ));
    },
  );
}

// 38-08: the names the self-test harness (cross-ai-selftest.mjs) imports. One list,
// never per-declaration exports (the test extractors read `function name(` lines).
export {
  ADMISSION_PHRASES_SEED,
  ARGV_PROMPT_MAX,
  BLOCKED_POOL_RE,
  CLAUDE_EXEC_FORMULA_RECORD,
  CLI_NAME_RE,
  CONFIG,
  CONTEXT_RE,
  CONTROL_CHAR_RE,
  CURSOR_MODEL_ID,
  EXEC_PREAMBLE,
  FINDING_CODES,
  FORBIDDEN_PATHS_SEED,
  HERDR_BIN,
  HERDR_VERBS,
  HOST_PATH_SAFE,
  SWEEP_HERDR_TIMEOUT_MS,
  IDLE_DEFAULT_S,
  IDLE_MAX_S,
  KEY_SHAPES,
  LEVEL_RE,
  MODEL_ID,
  MODEL_ID_FLOOR,
  OPENCODE_MODEL_ID,
  PATTERNS,
  PI_MODEL_ID,
  PLAN_ID_RE,
  PROMPT_CONTROL_RE,
  RESUME_MSG,
  RETRY_DEFAULTS,
  ROW_CLASSES,
  RUNNER_FILE,
  RUNTIMES,
  RUNTIME_ID_RE,
  SESSION_ID_RE,
  SETTING_NAMES,
  SETTING_REASONS,
  SETTING_STATES,
  SKILL_NAME_RE,
  SKILL_PROSE,
  STATUS_TABLE,
  TABLE,
  addFinding,
  admissionHits,
  aiKitConfigDir,
  argvFileAllowed,
  argvFileRow,
  argvPromptProblem,
  blockedAfterStop,
  blockedClearAfterOk,
  blockedClear,
  blockedStatusLine,
  blockedFilePath,
  blockedNext,
  blockedPoolKey,
  blockedPoolRow,
  blockedStatedS,
  blockedWithLock,
  baselinePath,
  baselineVerdict,
  capCodePoints,
  captureMaxBytes,
  checkGroup,
  checkoutRoot,
  clampAttemptTimeout,
  clampCapS,
  classifyStop,
  clearStaleLock,
  composePrompt,
  confirmReport,
  coverageOf,
  current,
  cycleFilePath,
  eventsWithRaw,
  extractEvents,
  findingDetail,
  findingLines,
  finish,
  forbiddenHits,
  groupMembers,
  hardWaitFor,
  statedResetS,
  resetCheckS,
  shortHardWait,
  idleBudgetNote,
  killGroup,
  ladderNext,
  ladderStop,
  laneCapabilities,
  launcherVerified,
  launcherGroupAlive,
  liveCheck,
  liveMatch,
  lockGroupAlive,
  lockPath,
  lockRecordValid,
  lockStartTime,
  lockUpdate,
  lockVerdict,
  log,
  makeLineRelay,
  mergeCatalog,
  migrateRetrySources,
  normalizeInput,
  overlayHits,
  overlaySpentMs,
  ownValue,
  parseArgs,
  parseCommitLog,
  parseTasks,
  parseTomlSubset,
  pathCovers,
  patternFor,
  pidAlive,
  planArgvFile,
  planFindings,
  planIdle,
  planSettings,
  planSkills,
  planSubjectRe,
  procGroup,
  procSession,
  procStartTime,
  promptFiles,
  providerAdmits,
  pushCapped,
  readCallFile,
  readBlocked,
  readCycleState,
  readLockOnce,
  readOr,
  redactSecrets,
  redactedValues,
  removeRetryBlock,
  replaceCopies,
  reportLines,
  resetAfterSeconds,
  resolveRetry,
  reviewArgvProblem,
  routeAdmits,
  setLog,
  setOverlayIds,
  setSelfTestHook,
  setTable,
  sleep,
  softWaitMs,
  splitTomlName,
  statusGroup,
  strictJson,
  stripCode,
  sweepRuns,
  taskDigest,
  upsertTomlKeys,
  upstreamFields,
  upstreamOf,
  validateRetryKey,
  validateRow,
  which,
  writeCycleState,
};

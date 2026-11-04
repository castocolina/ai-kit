#!/usr/bin/env node
// ai-kit-cross-ai generator=ai-kit-gsd-curated-config template=8 sha256=35e7cb64d25ae383287d96801fc63e8a0233c61f7fc7b53fd76c14d6bb9a660c
/*
 * cross-ai.mjs: the GSD `workflow.cross_ai_command` dispatcher (template v8).
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
 *   --runtime <id>                           the one CLI this call runs
 *   --prefer <list>                          alias: only the first entry runs (notice
 *                                            names the rest)
 *   --model <id>                             model for the selected runtime (wins over
 *                                            --model-<cli>)
 *   --model-<cli> <id>                       model per CLI, e.g. --model-cursor auto
 *   --route-<cli> router|unknown             confirmed route of that CLI (wins over CONFIG)
 *   --classify-only <path>                   classify a JSON case file and exit (no spawn,
 *                                            no write, stdin ignored; path relative to cwd)
 *   --mode exec|review                       exec = full permissions (default); review = read-only
 *   --tools-profile exec|review|none         named tool set from the runtime's table row
 *                                            (review accepts review or none)
 *   --timeout <s>                            inner deadline (lowers default; never above derived inner)
 *   --outer-timeout <s>                      outer deadline (replaces the GSD lookup and the
 *                                            CONFIG cap)
 *   --print-argv                             print the resolved command per CLI and exit (no model call)
 *   --no-preamble                            send the prompt unchanged
 *   --prepend-file <path>                    put this file before the prompt
 *                                            (path relative to the cwd)
 *   --codex-sandbox workspace-write          codex exec writes inside the cwd,
 *                                            plus /tmp and $TMPDIR, which
 *                                            workspace-write always allows
 *   --child-pgid-file <path>                 append spawn <pid> / exit <pid>
 *                                            per detached child, for a
 *                                            supervising caller's cleanup
 *   --codex-effort minimal|low|medium|high|xhigh   overrides CONFIG.effort.codex
 *   --codex-service-tier <id>                codex -c service_tier=
 *   --cursor-mode ask|plan                   review mode only (replaces cursor --mode)
 *   --self-test                              hermetic black-box checks (no real CLIs); its ceilings scale
 *                                            with load per CPU up to 4x, AIKIT_XAI_SELFTEST_LOAD overrides the reading
 *
 * CONFIG.effort pins the selected effort per runner: pi --thinking (skipped when the model
 * has a :level suffix) and codex model_reasoning_effort.
 *
 * Live outer timeout reads workflow.cross_ai_timeout the way gsd-tools config-get does:
 * .planning[/$GSD_PROJECT][/workstreams/$GSD_WORKSTREAM]/config.json, then the root config
 * under GSD_WORKSTREAM, else 300.
 * Retry config reads workflow.cross_ai_retry through the same files, then
 * ${XDG_CONFIG_HOME:-~/.config}/ai-kit/cross-ai.json key cross_ai_retry, then CONFIG.retry,
 * per key. The error catalog is PATTERNS (generated from cross-ai-errors.json) plus the owner
 * overlay ${XDG_CONFIG_HOME:-~/.config}/ai-kit/cross-ai-errors.json.
 * No idle watchdog in this version (D-43); only the overall deadline bounds each child.
 */
import { spawn, spawnSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import vm from 'node:vm';
import os from 'node:os';
import path from 'node:path';
import { StringDecoder } from 'node:string_decoder';
import { fileURLToPath } from 'node:url';

// <config>
const CONFIG = {
  "attemptTimeoutS": 0,
  "backoffS": [
    30,
    60
  ],
  "capS": 14400,
  "cooldownS": 600,
  "defaultOuterTimeoutS": 300,
  "effort": {},
  "extraArgs": {},
  "heartbeatS": 30,
  "models": {
    "codex": "gpt-5.6-luna",
    "cursor": "auto",
    "grok": "grok-4.7",
    "opencode": "router-env/my-coding",
    "pi": "router-env/my-coding"
  },
  "newSessionRetries": 3,
  "outerTimeoutS": 1800,
  "retries": 2,
  "retry": {
    "base_s": 1,
    "factor": 1.5,
    "hard_waits_s": [
      600,
      900,
      1800
    ],
    "max_retries": 5,
    "session_resets": 1
  },
  "routerBacked": {
    "opencode": true,
    "pi": true
  },
  "runtime": "pi",
  "sameSessionRetries": 3,
  "scrubEnv": [
    "AI_AGENT",
    "CLAUDECODE",
    "CLAUDE_CODE_ENTRYPOINT",
    "CLAUDE_CODE_SSE_PORT",
    "CODEX_SANDBOX",
    "CODEX_THREAD_ID",
    "CODEX_VERSION",
    "CURSOR_AGENT",
    "GROK_AGENT",
    "OPENCODE",
    "PI_CODING_AGENT"
  ],
  "timeoutMarginS": 30
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
    "label": "unverified",
    "evidence": "CHANGELOG 0a1265ea8"
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
    "evidence": "the Zhipu GLM capture"
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
    "label": "unverified",
    "evidence": "25-RESEARCH 2.2 CONTEXT, wrapper reproduced"
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
    "label": "unverified",
    "evidence": "25-RESEARCH 2.2 Go wording"
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
    "label": "unverified",
    "evidence": "25-RESEARCH 2.2 Zen wording"
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
    "evidence": "25-RESEARCH 2.2 probe"
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

const OVERLAY_MATCH_MS = 50;
const OVERLAY_CALL_BUDGET_MS = 200;
const ROW_CLASSES = ['quota', 'billing', 'auth', 'permission_blocked', 'bad_model', 'transient'];
const ROW_ID_RE = /^[a-z0-9][a-z0-9-]{1,63}$/;
const PROVIDER_RE = /^[a-z0-9][a-z0-9._-]{0,63}$/;
let OVERLAY_IDS = new Set();
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
  if (!['stderr', 'event', 'any'].includes(row.input)) return 'input is not stderr, event or any';
  if (typeof row.match !== 'string' || row.match.length > 200) {
    return 'match is not a string of at most 200 characters';
  }
  try { new RegExp(row.match, 'i'); } catch { return 'match is not a regex'; }
  if (!ROW_CLASSES.includes(row.class)) return 'class is not a known class';
  if (row.routerClass !== undefined && row.routerClass !== 'quota') return 'routerClass is not quota';
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
  usage: { exit: 2 },
  no_model: { exit: 2 },
  empty_stdin: { exit: 2 },
  permission_blocked: { exit: 69 },
  bad_model: { exit: 69 },
  auth: { exit: 69 },
  billing: { exit: 69 },
  quota: { exit: 75 },
  transient: { exit: 75 },
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
let finished = false;
let finishedExit = 1;
let runDeadline = 0;
let finalizeBy = 0;
let current = null;
let currentFinalize = null;
let aborting = 0;
let signalBy = 0;
let backstop = null;
const tempDirs = new Set();
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
      fields.dueAtMs || 0, fields.upstream || null);
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

function finish(status, fields) {
  if (finished) return finishedExit;
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
// No leading dash (read as a CLI option) and no shell or space characters (U-4).
const MODEL_ID = /^[A-Za-z0-9][A-Za-z0-9._:/#@+-]*$/;
// Cursor only: one trailing [k=v,...] bracket (D-18). No space, quote, `$` or `;`.
const CURSOR_MODEL_ID = /^[A-Za-z0-9][A-Za-z0-9._:/#@+-]*(?:\[[A-Za-z0-9._=,-]+\])?$/;
// pi: provider/model. pi matches the whole id first and splits a trailing :<thinking> only
// when it is one of the seven levels (its model-resolver), so `:` inside the model part
// (Ollama tags such as qwen3:8b) is part of the id; modelSuffix strips only a known level.
const PI_MODEL_ID = /^[A-Za-z0-9][A-Za-z0-9._@+-]*\/[A-Za-z0-9][A-Za-z0-9._:\/@+-]*$/;
// opencode: provider/model (`:` stays inside the model part) and one trailing #variant.
const OPENCODE_MODEL_ID = /^[A-Za-z0-9][A-Za-z0-9._@+-]*\/[A-Za-z0-9][A-Za-z0-9._:\/@+-]*(?:#[A-Za-z0-9._-]+)?$/;

// process.exit drops writes still queued on a pipe, so exit only once both streams have
// flushed (a stalled reader gets a bounded wait, shorter on the signal path).
function exitFlushed(code) {
  if (backstop) clearTimeout(backstop);
  process.exitCode = code;
  let pending = 2;
  const done = () => { if (--pending === 0) process.exit(code); };
  for (const s of [process.stdout, process.stderr]) {
    if (s.destroyed || s.writableEnded) done();
    else s.write('', done);
  }
  setTimeout(() => process.exit(code), aborting ? 300 : 5000).unref();
}

process.on('uncaughtException', (e) => {
  if (selfTestRoot) {
    process.stderr.write(`self-test: internal error: ${e && e.stack || e}\n`);
    selfTestAbort(1);
    return;
  }
  if (current) killGroup(current, 'SIGKILL');
  for (const dir of [...tempDirs]) dropTemp(dir);
  log(`cross-ai: internal error: ${e && e.stack || e}`);
  exitFlushed(reportAndFinish(
        'crash', { ...liveFields, tree: 'unknown', exit: 1, cli_rc: '-' },
      ));
});

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
  },
  // opencode 2.0.29 run --help formulas; partial bare profile: opencode still loads
  // ~/.agents/skills and ~/.config/opencode/skills (opencode docs). --standalone targets
  // opencode 2.x: a headless run executes on a private server, never inside the user's
  // long-lived managed service; listModels (`opencode models`) has no such flag and still
  // reads the shared service, read-only.
  opencode: {
    bins: ['opencode'],
    list: { argv: ['models'], parse: parseOpencodeListingIds },
    exec: (m) => ['run', '--model', m, '--auto', '--format', 'json', '--standalone'],
    review: (m) => ['run', '--model', m, '--agent', 'plan', '--format', 'json', '--standalone'],
    resume: (m, c, sid, mode) => [...RUNTIMES.opencode[mode](m, c), '--session', sid],
    parse: parseOpencode,
    modelSuffix: /#[^#/]+$/, // provider/model#variant; the listing has no variants
    modelId: OPENCODE_MODEL_ID,
    profiles: null,
    reviewExtras: [],
    env: { OPENCODE_DISABLE_AUTOUPDATE: '1', OPENCODE_DISABLE_CLAUDE_CODE_SKILLS: '1' },
  },
  pi: {
    bins: ['pi'],
    list: { argv: PI_RPC_ARGS, input: PI_RPC_REQUEST, parse: parsePiListingIds },
    exec: (m, c) => ['-p', '--model', m, ...piThinkingArgs(m, c), '--session-id', c.sid, '--no-skills', '--no-extensions', '--no-approve', '--offline',
      ...(c.profileFlags || [])],
    review: (m, c) => ['-p', '--model', m, ...piThinkingArgs(m, c), '--session-id', c.sid, '--no-skills', '--no-extensions', '--no-approve', '--offline',
      ...(c.profileFlags || [])],
    resume: (m, c, sid, mode) => RUNTIMES.pi[mode](m, c),
    parse: (out) => ({ text: out, sessionId: null, error: null }),
    // pi documents --model provider/id[:thinking]; the listing has bare ids.
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
  },
  // read-only enforcement not live-verified
  claude: {
    bins: ['claude'],
    list: null,
    exec: null,
    review: (m) => ['-p', '--model', m, '--output-format', 'json', '--permission-mode', 'plan'],
    resume: null,
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
  },
  // Flags documented in copilot 1.0.103 `--help` and `help permissions`; error, quota and
  // exit-code shapes unverified (no real copilot run in this phase).
  copilot: {
    bins: ['copilot'],
    list: null,
    argvPrompt: true,
    errorsUnverified: true,
    modelId: MODEL_ID,
    exec: (m, c) => ['-p', c.promptArg, '-s', '--no-ask-user', '--model', m, ...(c.profileFlags || [])],
    review: (m, c) => ['-p', c.promptArg, '-s', '--no-ask-user', '--model', m, ...(c.profileFlags || [])],
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
  },
};

// CONFIG.effort.pi pins thinking unless the model spec already carries a :level suffix
// (without either, pi runs the user's default, xhigh on some machines).
function piThinkingArgs(model, ctx) {
  return ctx.piThinking && !RUNTIMES.pi.modelSuffix.test(model) ? ['--thinking', ctx.piThinking] : [];
}

function withCodexKnobs(argv, ctx) {
  const out = [...argv];
  if (ctx.codexEffort) out.push('-c', `model_reasoning_effort=${ctx.codexEffort}`);
  if (ctx.codexServiceTier) out.push('-c', `service_tier=${ctx.codexServiceTier}`);
  return out;
}

// --codex-sandbox workspace-write confines exec to the cwd (codex still allows /tmp and
// $TMPDIR). Without the flag the bypass formula is unchanged.
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
  let sessionId = null, error = null;
  const msgs = new Map();
  for (const ev of jsonLines(out)) {
    sessionId = sessionId || ev.sessionID || null;
    if (ev.type === 'text' && ev.part && typeof ev.part.text === 'string') {
      if (!msgs.has(ev.part.messageID)) msgs.set(ev.part.messageID, new Map());
      msgs.get(ev.part.messageID).set(ev.part.id, ev.part.text);
    }
    if (ev.type === 'error') error = JSON.stringify(ev.error || ev).slice(0, 400);
  }
  const last = [...msgs.values()].pop();
  return { text: last ? [...last.values()].join('') : '', sessionId, error };
}

function normalize(text) {
  return text.replace(/\x1B\[[0-9;?]*[A-Za-z]/g, '').replace(/([.!?:])(#{1,6} \S)/g, '$1\n\n$2').trim() + '\n';
}

const INPUT_CAP = 65536;
// CSI color and cursor codes, and OSC sequences such as terminal hyperlinks (BEL or ST end).
const ANSI_RE = /\x1B\[[0-9;?]*[A-Za-z]|\x1B\][^\x07\x1B]*(?:\x07|\x1B\\)/g;
// Child text can echo credentials and identifiers. Key rules preserve the key and replace
// only its complete quoted or delimited value.
const SECRET_RES = [
  /(sk|rk)-[A-Za-z0-9_-]{8,}/gi,
  /(?<=\bBearer )[A-Za-z0-9._~+/=-]{8,}/gi,
  /(?<=\bBasic )[A-Za-z0-9+/=]{8,}/gi,
  /\bAIza[0-9A-Za-z_-]{20,}/g,
  /conn:[0-9a-f]{8,}/gi,
  /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/gi,
  /\bgh[pousr]_[A-Za-z0-9]{20,}\b/gi,
  /\bgithub_pat_[A-Za-z0-9_]{20,}\b/gi,
];
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

function normalizeInput(text) {
  const decoded = decodeUtf8(text).replace(ANSI_RE, '').replace(/\u2019/g, "'");
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
  for (const re of SECRET_RES) {
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

function rowAdmits(row, source) {
  if (row.input === 'any') return true;
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

function classifyStop({ cli, routerLane, route, model, stderr, events, eventRaw }, table = TABLE) {
  const callRoute = route ?? (routerLane ? 'router' : 'unknown');
  const lane = routerLane ?? (callRoute === 'router');
  const callModel = model || '';
  const normalizedStderr = normalizeInput(stderr || '');
  const sources = [['stderr', normalizedStderr, null]];
  for (let i = 0; i < (events || []).length; i += 1) {
    sources.push(['event', normalizeInput(events[i] || ''), eventRaw?.[i] ?? null]);
  }
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
      const line = source === 'stderr' ? text.slice(start, end < 0 ? undefined : end) : text;
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

function resultEventString(out) {
  const ev = lastJson(out, (j) => j.type === 'result');
  if (!ev || !ev.is_error) return [];
  return typeof ev.result === 'string' && ev.result ? [ev.result] : [];
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
      out.push(...resultEventString(text));
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

function upstreamFields(raw) {
  const text = String(raw || '');
  const start = text.indexOf('{');
  if (start < 0) return null;
  // shortcut: one parse from the first object opener; captures with a prose brace prefix
  // require a dedicated fixture before broadening this bounded parser.
  const outer = parseJson(text.slice(start));
  if (!outer || typeof outer !== 'object' || Array.isArray(outer)) return null;
  const body = outer.error?.response?.body;
  const nested = typeof body === 'string' ? parseJson(body) : null;
  const objects = [outer, outer.error, nested, nested?.error];
  const keys = ['retry_after', 'reset_at', 'retry_after_seconds', 'resetsAt'];
  const result = {};
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

function codexPair(message) {
  return [
    JSON.stringify({ type: 'error', message }),
    JSON.stringify({ type: 'turn.failed', error: { message } }),
  ].join('\n');
}

function ocError(error) {
  return JSON.stringify({ type: 'error', sessionID: 'ses_1', error });
}

const CLASSIFY_CASES = [
  {
    // A stack-trace line number is not an HTTP code (25 code review WR-06).
    name: 'stack-line-401-not-auth', cli: 'pi',
    stderr: 'TypeError: x is undefined\n    at run (/app/dist/cli.js:401:17)',
    expect: { status: 'crash', pattern: 'none', rule: '-' },
  },
  {
    name: 'stack-line-500-not-transient', cli: 'pi',
    stderr: 'Error: boom\n    at f (/app/index.js:500:3)',
    expect: { status: 'crash', pattern: 'none', rule: '-' },
  },
  {
    // A billing path segment is not a billing message, even on a router lane.
    name: 'billing-path-not-quota', cli: 'pi', route: 'router',
    stderr: "ENOENT: no such file or directory, open 'src/billing/x.ts'",
    expect: { status: 'crash', pattern: 'none', rule: '-' },
  },
  {
    name: 'codex-usage-limit-clock', cli: 'codex',
    stdout: codexPair(
      'You’ve hit your usage limit. Upgrade to Pro ' +
      '(https://chatgpt.com/explore/pro), visit https://chatgpt.com/settings/usage ' +
      'to purchase more credits or try again at 2:24 PM.',
    ),
    expect: { status: 'quota', pattern: 'verified' },
  },
  {
    name: 'codex-usage-limit-later', cli: 'codex',
    stdout: codexPair(
      'You’ve hit your usage limit. Upgrade to Pro, or try again later.',
    ),
    expect: { status: 'quota', pattern: 'verified' },
  },
  {
    name: 'codex-usage-limit-dated', cli: 'codex',
    stdout: codexPair(
      'You’ve hit your usage limit. Try again at Dec 31st, 2099 9:00 PM.',
    ),
    expect: { status: 'quota', pattern: 'verified' },
  },
  {
    name: 'codex-insufficient-quota', cli: 'codex',
    stdout: codexPair('Quota exceeded. Check your plan and billing details.'),
    expect: { status: 'billing', pattern: 'verified' },
  },
  {
    name: 'codex-insufficient-quota-router', cli: 'codex', route: 'router',
    stdout: codexPair('Quota exceeded. Check your plan and billing details.'),
    expect: { status: 'quota', pattern: 'verified' },
  },
  {
    name: 'codex-402-format', cli: 'codex',
    stdout: codexPair('unexpected status 402 Payment Required: {}, url: http://127.0.0.1/x'),
    expect: { status: 'billing', pattern: 'verified' },
  },
  {
    name: 'codex-refresh-reused', cli: 'codex',
    stderr: 'Failed to refresh token: refresh token was already used (refresh_token_reused)',
    expect: { status: 'auth', pattern: 'verified' },
  },
  {
    name: 'codex-item-error-ignored', cli: 'codex',
    stdout: JSON.stringify({
      type: 'item.completed',
      item: { type: 'error', message: 'Model metadata for x not found' },
    }),
    expect: { status: 'crash', pattern: 'none', rule: '-' },
  },
  {
    name: 'opencode-usage-limit', cli: 'opencode',
    stdout: ocError({
      type: 'provider.quota', message: 'The usage limit has been reached', status: 429,
      response: { body: JSON.stringify({ code: 'usage_limit_reached', resets_at: 1 }) },
    }),
    expect: { status: 'quota', pattern: 'verified' },
  },
  {
    name: 'opencode-insufficient-quota', cli: 'opencode',
    stdout: ocError({
      type: 'provider.quota', status: 429,
      message: 'You exceeded your current quota, please check your plan and billing details.',
      response: { body: JSON.stringify({ code: 'insufficient_quota' }) },
    }),
    expect: { status: 'billing', pattern: 'verified' },
  },
  {
    name: 'opencode-free-usage', cli: 'opencode',
    stdout: ocError({
      type: 'provider.quota', status: 429, message: 'Rate limit exceeded. Please try again later.',
      response: { body: JSON.stringify({ type: 'FreeUsageLimitError' }) },
    }),
    expect: { status: 'quota', pattern: 'verified' },
  },
  {
    name: 'opencode-requires-key', cli: 'opencode',
    stdout: ocError({
      type: 'provider.quota', status: 402, message: 'requires an opencode API key',
    }),
    expect: { status: 'auth', pattern: 'verified' },
  },
  {
    name: 'opencode-requires-key-router', cli: 'opencode', route: 'router',
    stdout: ocError({
      type: 'provider.quota', status: 402, message: 'requires an opencode API key',
    }),
    expect: { status: 'quota', pattern: 'verified' },
  },
  {
    name: 'opencode-monthly-limit', cli: 'opencode',
    stdout: ocError({
      type: 'provider.auth', status: 401,
      message: 'Your workspace has reached its monthly spending limit',
      response: { body: JSON.stringify({ type: 'MonthlyLimitError' }) },
    }),
    expect: { status: 'billing', pattern: 'unverified' },
  },
  {
    name: 'opencode-monthly-limit-router', cli: 'opencode', route: 'router',
    stdout: ocError({
      type: 'provider.auth', status: 401,
      message: 'Your workspace has reached its monthly spending limit',
      response: { body: JSON.stringify({ type: 'MonthlyLimitError' }) },
    }),
    expect: { status: 'quota', pattern: 'unverified' },
  },
  {
    name: 'opencode-spend-403', cli: 'opencode',
    stdout: ocError({
      type: 'provider.auth', status: 403,
      message: 'Error 403: spending limit reached for this team',
    }),
    expect: { status: 'billing', pattern: 'verified' },
  },
  {
    name: 'opencode-model-disabled', cli: 'opencode',
    stdout: ocError({
      type: 'provider.auth', status: 403, message: 'Model access is disabled',
      response: { body: JSON.stringify({ type: 'ModelDisabledError' }) },
    }),
    expect: { status: 'billing', pattern: 'unverified' },
  },
  {
    name: 'opencode-model-disabled-router', cli: 'opencode', route: 'router',
    stdout: ocError({
      type: 'provider.auth', status: 403, message: 'Model access is disabled',
    }),
    expect: { status: 'quota', pattern: 'unverified' },
  },
  {
    name: 'opencode-bad-key', cli: 'opencode',
    stdout: ocError({
      type: 'provider.auth', status: 401, message: 'Incorrect API key provided',
    }),
    expect: { status: 'auth', pattern: 'verified' },
  },
  {
    name: 'opencode-bad-key-router', cli: 'opencode', route: 'router',
    stdout: ocError({
      type: 'provider.auth', status: 401, message: 'Incorrect API key provided',
    }),
    expect: { status: 'auth', pattern: 'verified' },
  },
  {
    name: 'opencode-rate-limit', cli: 'opencode',
    stdout: ocError({
      type: 'provider.rate-limit', status: 429,
      message: 'rate_limit_exceeded',
      response: { body: JSON.stringify({ code: 'rate_limit_exceeded' }) },
    }),
    expect: { status: 'quota', pattern: 'verified' },
  },
  {
    name: 'opencode-legacy-shape', cli: 'opencode',
    stdout: ocError({
      name: 'APIError', data: { message: 'The usage limit has been reached', statusCode: 429 },
    }),
    expect: { status: 'quota', pattern: 'verified' },
  },
  {
    name: 'opencode-text-mode', cli: 'opencode',
    stderr: 'Error: The usage limit has been reached',
    expect: { status: 'quota', pattern: 'verified' },
  },
  {
    name: 'router-resource-pressure', cli: 'opencode',
    stderr: 'Error: Service temporarily unavailable due to resource pressure. Retry shortly.',
    expect: { status: 'transient', pattern: 'verified' },
  },
  {
    name: 'router-admission', cli: 'opencode',
    stderr: 'Chat admission capacity is temporarily unavailable',
    expect: { status: 'transient', pattern: 'verified' },
  },
  {
    name: 'router-prefilter', cli: 'opencode',
    stderr: 'all targets were skipped by pre-dispatch filters',
    expect: { status: 'quota', pattern: 'verified', rule: 'omniroute-all-targets-skipped' },
  },
  {
    name: 'router-prefilter-router', cli: 'opencode', route: 'router',
    stderr: 'all targets were skipped by pre-dispatch filters',
    expect: { status: 'quota', pattern: 'verified', rule: 'omniroute-all-targets-skipped' },
  },
  {
    name: 'evidence-all-targets-skipped-router', cli: 'pi', route: 'router',
    stderr: '429: {"message":"Service temporarily unavailable: all targets were skipped by ' +
      'pre-dispatch filters (weekly 100% ...) reset after 94h 42m 34s","type":"rate_limit_error",' +
      '"code":"ALL_TARGETS_SKIPPED","retry_after":340954,"reset_at":"2026-10-19T00:00:00.000Z"}',
    expect: { status: 'quota', pattern: 'verified', rule: 'omniroute-all-targets-skipped' },
  },
  {
    name: 'evidence-all-targets-skipped-unknown', cli: 'pi',
    stderr: '429: {"message":"Service temporarily unavailable: all targets were skipped by ' +
      'pre-dispatch filters (weekly 100% ...) reset after 94h 42m 34s","type":"rate_limit_error",' +
      '"code":"ALL_TARGETS_SKIPPED","retry_after":340954,"reset_at":"2026-10-19T00:00:00.000Z"}',
    expect: { status: 'quota', pattern: 'verified', rule: 'omniroute-all-targets-skipped' },
  },
  {
    name: 'evidence-sessions-5h', cli: 'opencode', route: 'router',
    stdout: ocError({
      type: 'provider.rate-limit', status: 429,
      message: 'Service temporarily unavailable: all targets were skipped by pre-dispatch ' +
        'filters (Session (5h) 100% conn:<8 hex>)',
    }),
    expect: { status: 'quota', pattern: 'verified', rule: 'omniroute-all-targets-skipped' },
  },
  {
    name: 'evidence-member-usage-limit', cli: 'opencode', route: 'router',
    stderr: '[429]: The usage limit has been reached (reset after 4h 15m 3s) ' +
      '{"retry_after":15303,"reset_at":"2026-10-25T08:42:03.640Z"}',
    expect: { status: 'quota', pattern: 'verified', rule: 'text-usage-limit' },
  },
  {
    name: 'evidence-member-402-router', cli: 'pi', route: 'router',
    stderr: '402: {"message":"[acme-cli/acme-4.7] [402]: Acme Build usage balance exhausted ' +
      '(reset after 2m)","retry_after":120,"reset_at":"2026-10-23T04:01:04.472Z"}',
    expect: { status: 'quota', pattern: 'verified', rule: 'code-402' },
  },
  {
    name: 'evidence-member-402-inferred', cli: 'pi', route: 'router-inferred',
    model: 'router-env/my-coding',
    stderr: '402: {"message":"[acme-cli/acme-4.7] [402]: Acme Build usage balance exhausted ' +
      '(reset after 2m)","retry_after":120,"reset_at":"2026-10-23T04:01:04.472Z"}',
    expect: { status: 'billing', pattern: 'verified', rule: 'code-402' },
  },
  {
    name: 'evidence-kimi-403', cli: 'pi',
    stderr: "[403]: You've reached your 5-hour usage limit. Your quota will reset when the " +
      'current 5-hour window ends.',
    expect: { status: 'quota', pattern: 'verified', rule: 'text-usage-limit' },
  },
  {
    name: 'evidence-glm-1310', cli: 'pi',
    stderr: '429: {"code":"1310","message":"\u60a8\u5df2\u8fbe\u5230\u6bcf\u5468\u6216' +
      '\u6bcf\u6708\u4f7f\u7528\u4e0a\u9650\uff0c\u9650\u989d\u5c06\u4e8e 2026-10-21 22:10:59 ' +
      '\u91cd\u7f6e"}',
    expect: { status: 'quota', pattern: 'verified', rule: 'vendor-zhipu-1310' },
  },
  {
    name: 'evidence-glm-omniroute', cli: 'pi', route: 'router',
    stderr: '[zai/glm-5.3-flash] [429]: Usage limit reached for 5 hour (reset after 3h 26m 12s)',
    expect: { status: 'quota', pattern: 'verified', rule: 'text-usage-limit' },
  },
  {
    name: 'evidence-model-unavailable', cli: 'pi', route: 'router',
    stderr: '503: {"message":"Model codex/gpt-6-luna-high is unavailable",' +
      '"type":"server_error","code":"service_unavailable"}',
    expect: { status: 'transient', pattern: 'verified', rule: 'omniroute-model-unavailable' },
  },
  {
    name: 'evidence-stream-stall', cli: 'pi', route: 'router',
    stderr: 'Streaming response reported an upstream error before content \u2014 marking as ' +
      'invalid for combo failover (stream content stall: no model output within the window)',
    expect: { status: 'crash', pattern: 'none', rule: '-' },
  },
  {
    name: 'evidence-quality-check', cli: 'pi', route: 'router',
    stderr: 'Model codex/gpt-6.1-sol-high returned 200 but failed quality check',
    expect: { status: 'crash', pattern: 'none', rule: '-' },
  },
  {
    name: 'evidence-opencode-go-400', cli: 'opencode',
    stderr: '[400]: event: error',
    expect: { status: 'transient', pattern: 'verified', rule: 'text-event-400' },
  },
  {
    name: 'evidence-claude-weekly', cli: 'claude',
    stderr: '429 rate_limit {"rateLimitType":"seven_day","resetsAt":1761181200} ' +
      "You've hit your weekly limit \u00b7 resets Oct 22, 10pm (America/Santiago)",
    expect: { status: 'quota', pattern: 'unverified', rule: 'text-hit-your-limit' },
  },
  {
    name: 'evidence-invalid-credential', cli: 'pi',
    stderr: 'request failed: Invalid credential (HTTP 401)',
    expect: { status: 'auth', pattern: 'verified', rule: 'code-401-403' },
  },
  {
    name: 'evidence-quota-preflight', cli: 'pi', route: 'router',
    stderr: '[QuotaPreflight] zai/glm weekly: 3.0% remaining \u2014 approaching cutoff',
    expect: { status: 'crash', pattern: 'none', rule: '-' },
  },
  {
    name: 'evidence-no-executable-targets', cli: 'opencode', route: 'router',
    stdout: ocError({
      type: 'provider.invalid-request', status: 404,
      message: 'Combo has no executable targets',
      response: { body: JSON.stringify({
        error: {
          message: 'Combo has no executable targets', type: 'invalid_request_error',
          code: 'model_not_found',
        },
        diagnostics: { terminalReason: 'no_executable_targets' },
      }) },
    }),
    expect: { status: 'bad_model', pattern: 'verified', rule: 'omniroute-no-executable-targets' },
  },
  {
    name: 'evidence-kimi-monthly-429', cli: 'pi', route: 'router',
    stderr: 'HTTP 429',
    expect: { status: 'quota', pattern: 'verified', rule: 'code-429' },
  },
  {
    name: 'evidence-all-targets-cooling-down', cli: 'pi', route: 'router',
    stderr: 'all_targets_cooling_down: provider/model: circuit_open (45s)',
    expect: { status: 'transient', pattern: 'unverified', rule: 'omniroute-all-targets-cooling-down' },
  },
  {
    name: 'evidence-circuit-open', cli: 'pi', route: 'router',
    stderr: 'circuit_open (45s)',
    expect: { status: 'transient', pattern: 'unverified', rule: 'omniroute-circuit-open' },
  },
  {
    name: 'evidence-model-cooldown', cli: 'pi', route: 'router',
    stderr: '{"code":"model_cooldown","retry_after":"2026-10-25T08:42:03.640Z"}',
    expect: { status: 'transient', pattern: 'unverified', rule: 'omniroute-model-cooldown' },
  },
  {
    name: 'evidence-endpoint-unavailable', cli: 'pi', route: 'router',
    stderr: '400: endpoint is unavailable',
    expect: { status: 'transient', pattern: 'unverified', rule: 'omniroute-endpoint-unavailable' },
  },
  {
    name: 'evidence-model-not-in-catalog', cli: 'pi', route: 'router',
    stderr: '{"code":"model_not_in_catalog"}',
    expect: { status: 'bad_model', pattern: 'unverified', rule: 'omniroute-model-not-in-catalog' },
  },
  {
    name: 'evidence-responses-frame', cli: 'pi',
    stderr: '{"status_code":429,"error_type":"rate_limit_error","retry_after_seconds":30}',
    expect: { status: 'quota', pattern: 'verified', rule: 'text-rate-limit' },
  },
  {
    name: 'evidence-precision-4021', cli: 'pi',
    stderr: 'wrote 4021 tokens',
    expect: { status: 'crash', pattern: 'none', rule: '-' },
  },
  {
    name: 'router-credential-gate', cli: 'opencode',
    stderr: 'Credential gate blocked opencode-zen/model',
    expect: { status: 'auth', pattern: 'verified' },
  },
  {
    name: 'router-credential-gate-router', cli: 'opencode', route: 'router',
    stderr: 'Credential gate blocked opencode-zen/model',
    expect: { status: 'quota', pattern: 'verified' },
  },
  {
    name: 'xai-spending-hyphen', cli: 'opencode',
    stderr: 'personal-team-blocked:spending-limit',
    expect: { status: 'billing', pattern: 'verified' },
  },
  {
    name: 'pi-insufficient-quota', cli: 'pi',
    stderr: '429: {"type":"insufficient_quota","code":"insufficient_quota",' +
      '"message":"You exceeded your current quota, please check your plan and billing details."}',
    expect: { status: 'billing', pattern: 'verified' },
  },
  {
    name: 'pi-402-format', cli: 'pi',
    stderr: '402: {"type":"monthly","message":"x"}',
    expect: { status: 'billing', pattern: 'verified' },
  },
  {
    name: 'pi-free-tier', cli: 'pi',
    stderr: '403: {"type":"FreeTierError"}',
    expect: { status: 'billing', pattern: 'verified' },
  },
  {
    name: 'pi-event-400', cli: 'pi',
    stderr: '[400]: event: error',
    expect: { status: 'transient', pattern: 'verified' },
  },
  {
    name: 'pi-session-warning', cli: 'pi',
    stderr: 'Warning: No project session found with id abc; creating a new session with that id.',
    expect: { status: 'crash', pattern: 'none', rule: '-' },
  },
  {
    name: 'pi-chatgpt-relative', cli: 'pi',
    stderr: 'You have hit your ChatGPT usage limit (plus plan). Try again in ~5 min.',
    expect: { status: 'quota', pattern: 'unverified' },
  },
  {
    name: 'kimi-429-router', cli: 'opencode', route: 'router',
    stderr: '429 monthly quota exhausted',
    expect: { status: 'quota', pattern: 'verified' },
  },
  {
    name: 'cursor-usage-limit', cli: 'cursor',
    stderr: "ActionRequiredError: You've hit your usage limit",
    expect: { status: 'quota', pattern: 'unverified' },
  },
  {
    name: 'cursor-named-models', cli: 'cursor',
    stderr: 'ActionRequiredError: Named models unavailable',
    expect: { status: 'billing', pattern: 'unverified' },
  },
  {
    name: 'cursor-free-plan-auto', cli: 'cursor',
    stderr: 'Free plans can only use Auto',
    expect: { status: 'billing', pattern: 'unverified' },
  },
  {
    name: 'cursor-action-required-alone', cli: 'cursor',
    stderr: 'ActionRequiredError: something else happened',
    expect: { status: 'crash', pattern: 'none', rule: '-' },
  },
  {
    name: 'cursor-bad-model', cli: 'cursor',
    stderr: 'Cannot use this model: example',
    expect: { status: 'bad_model', pattern: 'verified' },
  },
  {
    name: 'cursor-bad-key', cli: 'cursor',
    stderr: 'Warning: The provided API key is invalid',
    expect: { status: 'auth', pattern: 'verified' },
  },
  {
    name: 'cursor-result-error', cli: 'cursor',
    stdout: JSON.stringify({ type: 'result', is_error: true, result: '401 unauthorized' }),
    expect: { status: 'auth', pattern: 'verified' },
  },
  {
    name: 'claude-overloaded', cli: 'claude',
    stderr: 'Overloaded. try again in a moment',
    expect: { status: 'transient', pattern: 'unverified' },
  },
  {
    name: 'claude-resets', cli: 'claude',
    stderr: "You've hit your limit \u00b7 resets 9:30pm (America/Santiago)",
    expect: { status: 'quota', pattern: 'unverified' },
  },
  {
    name: 'edge-4021-tokens', cli: 'pi',
    stderr: 'used 4021 tokens',
    expect: { status: 'crash', pattern: 'none', rule: '-' },
  },
  {
    name: 'edge-empty', cli: 'pi',
    stderr: '',
    expect: { status: 'crash', pattern: 'none', rule: '-' },
  },
  {
    name: 'edge-answer-only-pi', cli: 'pi',
    stdout: 'You have hit your usage limit according to the model.',
    expect: { status: 'crash', pattern: 'none', rule: '-' },
  },
  {
    name: 'edge-answer-only-opencode', cli: 'opencode',
    stdout: JSON.stringify({
      type: 'text', sessionID: 'ses_1',
      part: { type: 'text', text: 'The usage limit has been reached, says the model.' },
    }),
    expect: { status: 'crash', pattern: 'none', rule: '-' },
  },
  {
    name: 'edge-ansi', cli: 'pi',
    stderr: '\u001b[31m402 payment required\u001b[0m',
    expect: { status: 'billing', pattern: 'verified' },
  },
  {
    name: 'edge-billing-and-quota', cli: 'pi',
    stderr: 'quota exceeded, check billing',
    expect: { status: 'billing', pattern: 'verified', rule: 'text-billing' },
  },
  {
    name: 'edge-vendor-code-beats-bare', cli: 'opencode',
    stderr: 'noise 401 from the transport',
    stdout: ocError({
      type: 'provider.auth', status: 401, message: 'wrapped',
      response: { body: JSON.stringify({ code: 'usage_limit_reached' }) },
    }),
    expect: { status: 'quota', pattern: 'verified', rule: 'vendor-usage-limit-reached' },
  },
];

// Flag, then an explicit CONFIG boolean, then the name heuristic, else unknown (D-05).
// Only `router` is a confirmed lane: an inferred route stays advisory.
function routeOf(cli, model, routes) {
  const flagged = routes && Object.hasOwn(routes, cli) ? routes[cli] : undefined;
  if (flagged === 'router' || flagged === 'unknown') return flagged;
  const baked = CONFIG.routerBacked[cli];
  // routerBacked is per CLI and was confirmed for its pinned model: another model on that CLI
  // is not the confirmed lane (ponytail review, 25).
  const pinned = CONFIG.models && CONFIG.models[cli];
  if (baked === true) return pinned && pinned !== model ? 'unknown' : 'router';
  if (baked === false) return 'unknown';
  const id = String(model || '').toLowerCase();
  if (ROUTER_HINTS.some((hint) => id.includes(hint))) return 'router-inferred';
  return 'unknown';
}

function confirmedRoute(route) {
  return route === 'router';
}

function classifyOne(entry, table) {
  return classifyStop({
    cli: entry.cli,
    route: entry.route || 'unknown',
    model: entry.model || '',
    stderr: entry.stderr || '',
    events: extractEvents(entry.cli, entry.stdout || ''),
  }, table);
}

function pureClassify(entry) {
  const got = classifyOne(entry);
  const want = entry.expect;
  if (got.status !== want.status) return `status ${got.status} expected ${want.status}`;
  if (got.label !== want.pattern) return `pattern ${got.label} expected ${want.pattern}`;
  if (want.rule !== undefined && got.rule !== want.rule) {
    return `rule ${got.rule} expected ${want.rule}`;
  }
  return null;
}

function classifyCases() {
  const generated = CLASSIFY_CASES.map((entry) => ({
    name: `pure-classify-${entry.name}`,
    pure: () => pureClassify(entry),
  }));
  const pinned = CLASSIFY_CASES.find((entry) => entry.name === 'edge-billing-and-quota');
  const twice = CLASSIFY_CASES.find((entry) => entry.name === 'opencode-monthly-limit-router');
  return [
    ...generated,
    {
      name: 'pure-classify-order-mutation',
      pure: () => {
        const forward = classifyOne(pinned);
        const reversed = classifyOne(pinned, [...PATTERNS].reverse());
        if (reversed.status === forward.status) return `reversal kept status ${forward.status}`;
        return null;
      },
    },
    {
      name: 'pure-classify-idempotent',
      pure: () => {
        const first = classifyOne(twice);
        const second = classifyOne(twice);
        if (JSON.stringify(first) !== JSON.stringify(second)) return 'classifyStop is not stable';
        return null;
      },
    },
    {
      // Without the tier-0 reason rows the same body matches a later provider row, so the
      // reason-code row is what decides it.
      name: 'pure-catalog-reason-code-wins',
      pure: () => {
        const entry = CLASSIFY_CASES.find((item) => item.name === 'evidence-all-targets-skipped-router');
        const withReason = classifyOne(entry);
        const without = classifyOne(entry, TABLE.filter((row) => row.tier !== 0));
        if (withReason.rule !== 'omniroute-all-targets-skipped') return `rule ${withReason.rule}`;
        if (without.rule === withReason.rule) return 'tier-0 rows did not decide the match';
        return null;
      },
    },
    {
      name: 'pure-catalog-tier-order',
      pure: () => {
        let prev = -1;
        for (const row of TABLE) {
          if (row.tier < prev) return `${row.id} tier ${row.tier} after ${prev}`;
          prev = row.tier;
        }
        return null;
      },
    },
    {
      name: 'pure-catalog-shipped-valid',
      pure: () => {
        const seen = new Set();
        for (const row of PATTERNS) {
          const reason = validateRow(row, RUNTIMES);
          if (reason) return `${row.id}: ${reason}`;
          if (seen.has(row.id)) return `duplicate ${row.id}`;
          seen.add(row.id);
        }
        return null;
      },
    },
    {
      name: 'pure-catalog-bad-rows',
      pure: () => {
        const base = {
          id: 'user-row', tier: 3, cli: '*', route: '*', provider: '*', input: 'any',
          match: 'acme', class: 'quota', terminal: false, label: 'unverified', evidence: 'probe',
        };
        const cases = [
          [{ ...base, class: 'doom' }, 'class'],
          [{ ...base, label: undefined }, 'label'],
          [{ ...base, evidence: '' }, 'evidence'],
          [{ ...base, route: 'direct' }, 'route'],
          [{ ...base, provider: 'Bad Prefix' }, 'provider'],
          [{ ...base, tier: 7 }, 'tier'],
          [{ ...base, match: 'a'.repeat(201) }, 'match'],
          [{ ...base, match: '(' }, 'match'],
          [{ ...base, cli: 'nosuch' }, 'cli'],
        ];
        for (const [row, field] of cases) {
          const reason = validateRow(row, RUNTIMES);
          if (!reason || !reason.includes(field)) return `${field}: ${reason}`;
        }
        return null;
      },
    },
    {
      name: 'pure-catalog-route-provider',
      pure: () => {
        const routerRow = { route: 'router' };
        if (!routeAdmits(routerRow, 'router') || routeAdmits(routerRow, 'unknown') ||
          routeAdmits(routerRow, 'router-inferred')) return 'route router';
        const unknownRow = { route: 'unknown' };
        if (routeAdmits(unknownRow, 'router') || !routeAdmits(unknownRow, 'unknown') ||
          !routeAdmits(unknownRow, 'router-inferred')) return 'route unknown';
        const zai = { provider: 'zai' };
        if (!providerAdmits(zai, 'unknown', 'zai-coding-cn/glm-5.3')) return 'zai model refused';
        if (providerAdmits(zai, 'unknown', 'kimi/k2')) return 'kimi admitted';
        if (!providerAdmits(zai, 'router', 'kimi/k2')) return 'router lane refused';
        return null;
      },
    },
    {
      name: 'pure-overlay-regex-timeout',
      pure: () => {
        const row = {
          id: 'user-catastrophic', tier: 3, cli: '*', route: '*', provider: '*', input: 'any',
          match: '^(a+)+$', class: 'quota', terminal: false, label: 'unverified', evidence: 'probe',
        };
        if (validateRow(row, RUNTIMES)) return 'row refused';
        const text = `${'a'.repeat(41)}!`;
        const started = Date.now();
        const logs = [];
        const real = log;
        log = (line) => logs.push(line);
        try {
          OVERLAY_IDS = new Set([row.id]);
          TABLE = mergeCatalog(PATTERNS, [row]);
          const first = classifyStop({ cli: 'pi', route: 'unknown', stderr: text });
          const second = classifyStop({ cli: 'pi', route: 'unknown', stderr: text });
          const elapsed = Date.now() - started;
          if (elapsed >= scaledMs(1000)) return `elapsed ${elapsed}`;
          const notices = logs.filter((line) => line === 'cross-ai: overlay disabled: match exceeded 50 ms');
          if (notices.length !== 1) return `notices ${notices.length}: ${logs.join('|')}`;
          if (first.rule === row.id || second.rule === row.id) return `matched overlay ${first.rule}`;
          return null;
        } finally {
          log = real;
          OVERLAY_IDS = new Set();
          TABLE = mergeCatalog(PATTERNS, []);
        }
      },
    },
    {
      name: 'pure-overlay-budget',
      pure: () => {
        const rows = [];
        for (let i = 0; i < 40; i += 1) {
          rows.push({
            id: `user-catastrophic-${i}`, tier: 3, cli: '*', route: '*', provider: '*', input: 'any',
            match: '^(a+)+$', class: 'quota', terminal: false, label: 'unverified', evidence: 'probe',
          });
        }
        const text = `${'a'.repeat(41)}!`;
        const logs = [];
        const real = log;
        log = (line) => logs.push(line);
        const started = Date.now();
        try {
          OVERLAY_IDS = new Set(rows.map((row) => row.id));
          TABLE = mergeCatalog(PATTERNS, rows);
          classifyStop({ cli: 'pi', route: 'unknown', stderr: text });
          const firstMs = Date.now() - started;
          const mid = logs.length;
          const again = Date.now();
          classifyStop({ cli: 'pi', route: 'unknown', stderr: text });
          const secondMs = Date.now() - again;
          const notices = logs.filter((line) => line === 'cross-ai: overlay disabled: match exceeded 50 ms');
          if (firstMs >= 300) return `first ${firstMs}`;
          if (notices.length !== 1) return `notices ${notices.length}`;
          if (logs.length !== mid) return 'second classification logged';
          if (secondMs >= 20) return `second ${secondMs}`;
          return null;
        } finally {
          log = real;
          OVERLAY_IDS = new Set();
          TABLE = mergeCatalog(PATTERNS, []);
        }
      },
    },
    {
      name: 'pure-overlay-call-budget',
      pure: () => {
        const row = {
          id: 'user-slow', tier: 3, cli: '*', route: '*', provider: '*', input: 'any',
          match: '^(a+)+$', class: 'quota', terminal: false, label: 'unverified', evidence: 'probe',
        };
        let sample = '';
        const re = new RegExp(row.match, 'i');
        for (let n = 12; n <= 24; n += 1) {
          const candidate = `${'a'.repeat(n)}!`;
          const t0 = performance.now();
          re.test(candidate);
          if (performance.now() - t0 < 10) sample = candidate;
        }
        if (!sample) return 'no sub-timeout sample';
        const logs = [];
        const real = log;
        log = (line) => logs.push(line);
        const started = Date.now();
        try {
          OVERLAY_IDS = new Set([row.id]);
          TABLE = mergeCatalog(PATTERNS, [row]);
          for (let i = 0; i < 1000; i += 1) overlayHits(sample);
          const elapsed = Date.now() - started;
          if (elapsed >= scaledMs(600)) return `elapsed ${elapsed}`;
          const timeouts = logs.filter((line) => line.includes('match exceeded'));
          if (timeouts.length) return `timeout notice: ${timeouts[0]}`;
          const notices = logs.filter((line) => line.startsWith('cross-ai: overlay disabled: matching used '));
          if (notices.length !== 1) return `notices ${notices.length}: ${logs.join('|')}`;
          const spent = Number(notices[0].match(/used (\d+) ms/)[1]);
          if (spent < 200 || spent > 260) return `spent ${spent}`;
          const before = overlaySpentMs;
          overlayHits(sample);
          if (overlaySpentMs !== before) return 'ran after the notice';
          return null;
        } finally {
          log = real;
          OVERLAY_IDS = new Set();
          TABLE = mergeCatalog(PATTERNS, []);
        }
      },
    },
    {
      // Live matching sees one line; a multi-line fixture is out of scope because post-hoc
      // matching sees the whole text.
      name: 'pure-live-agrees-posthoc',
      pure: () => {
        for (const entry of CLASSIFY_CASES) {
          if (entry.stderr === undefined || String(entry.stderr).includes('\n')) continue;
          const post = classifyOne(entry);
          const live = liveMatch(entry.cli, 'stderr', entry.stderr, entry.stderr,
            entry.route || 'unknown', entry.model || '');
          const liveRule = live ? live.rule : null;
          if (liveRule !== null && liveRule !== post.rule) {
            return `${entry.name} live ${liveRule} post ${post.rule}`;
          }
        }
        return null;
      },
    },
    {
      name: 'pure-redact-json-tail',
      pure: () => {
        const got = redactSecrets('{"message":"x","token":"abc","retry_after":120,"reset_at":"2026-10-23T04:01:04.472Z"}');
        return got === '{"message":"x","token":"<redacted>","retry_after":120,"reset_at":"2026-10-23T04:01:04.472Z"}' ? null : got;
      },
    },
    {
      name: 'pure-redact-shapes',
      pure: () => {
        const source = 'conn:ab12cd34 12345678-1234-abcd-1234-1234567890ab "connectionId":"x1" account_id=x2 "requestId": "x3" ghp_' + 'a'.repeat(36) + ' github_pat_' + 'b'.repeat(40) + ' retry_after":340954 reset_at":"2026-10-23T04:01:04.472Z"';
        const got = redactSecrets(source);
        for (const secret of ['ab12cd34', '12345678-1234-abcd-1234-1234567890ab', 'x1', 'x2', 'x3', 'ghp_', 'github_pat_']) if (got.includes(secret)) return `leaked ${secret}`;
        return got.includes('340954') && got.includes('2026-10-23') ? null : 'retry fields lost';
      },
    },
    {
      name: 'pure-redact-escaped-json',
      pure: () => {
        const input = '{"error":{"response":{"body":"{\\"accountId\\":\\"acct-123\\",\\"api_key\\":\\"sentinel\\",\\"requestId\\": \\"req-9\\",\\"retry_after\\":120}"}}}';
        const got = redactSecrets(input);
        for (const secret of ['acct-123', 'sentinel', 'req-9']) if (got.includes(secret)) return `leaked ${secret}`;
        return got.includes('retry_after') ? null : 'retry_after lost';
      },
    },
    {
      name: 'pure-redact-quoted-values',
      pure: () => {
        const inputs = [
          '{"secret":"alpha,beta","retry_after":120}',
          '{"accountId":"tenant private","reset_at":"2026-10-23T04:01:04.472Z"}',
          '{"token":"a\\"b,c"}',
          '\\"api_key\\":\\"x, y\\"',
        ];
        const outputs = inputs.map((text) => redactSecrets(text));
        return outputs[0].includes('alpha,beta') || !outputs[0].includes('retry_after') ||
          outputs[1].includes('tenant private') || !outputs[1].includes('reset_at') ||
          outputs[2].includes('a\\"b,c') || outputs[3].includes('x, y') ? 'quoted value redaction failed' : null;
      },
    },
    {
      name: 'pure-upstream-fields-redacted',
      pure: () => {
        const token = 'ghp_' + 'a'.repeat(36);
        const raw = `{"accountId":"acct-77","reset_at":"acct-77","token":"sentinel","retry_after":"sentinel","retry_after_seconds":"${token}","resetsAt":1761170400}`;
        const fields = upstreamFields(raw);
        const safe = Object.fromEntries(Object.entries(fields).map(([key, value]) => [key, typeof value === 'string' ? redactSecrets(replaceCopies(value, redactedValues(raw)), redactedValues(raw)) : value]));
        return JSON.stringify(safe) === '{"retry_after":"<redacted>","reset_at":"<redacted>","retry_after_seconds":"<redacted>","resetsAt":1761170400}' && !redactSecrets(raw).includes('acct-77') && redactedValues(raw).includes('acct-77') && redactSecrets('{"token":"1","retry_after":120}').includes('"retry_after":120') ? null : JSON.stringify(safe);
      },
    },
    {
      name: 'pure-events-with-raw',
      pure: () => {
        const raw = ocError({ message: 'first', response: { body: '{"message":"nested"}' } });
        const got = eventsWithRaw('opencode', raw);
        return got.events.length === 3 && got.eventRaw.every((line) => line === raw) ? null : JSON.stringify(got);
      },
    },
    {
      // Each event keeps its own stdout line as its raw text, never the whole multi-line output.
      name: 'pure-events-with-raw-per-line',
      pure: () => {
        const first = ocError({ message: 'first' });
        const second = ocError({ message: 'second' });
        const got = eventsWithRaw('opencode', `${first}\n${second}\n`);
        return got.eventRaw.length === 2 && got.eventRaw[0] === first && got.eventRaw[1] === second
          ? null : JSON.stringify(got.eventRaw);
      },
    },
    {
      name: 'pure-capture-cap',
      pure: () => {
        const buf = { chunks: [], bytes: 0, dropped: false };
        for (const s of ['aaaa', 'bbbb', 'cccc']) pushCapped(buf, Buffer.from(s), 8);
        const kept = Buffer.concat(buf.chunks).toString();
        return kept === 'bbbbcccc' && buf.bytes === 8 && buf.dropped ? null : `${kept} ${buf.bytes} ${buf.dropped}`;
      },
    },
    {
      // A copied value is matched literally, metacharacters included, and never throws.
      name: 'pure-replace-copies-literal',
      pure: () => {
        const values = ['a(b', 'q[1]', 'x.y', 'c\\d'];
        let got;
        try { got = replaceCopies('1 a(b 2 q[1] 3 x.y 4 xzy 5 c\\d', values); } catch (e) { return `threw: ${e.message}`; }
        return got === '1 <redacted> 2 <redacted> 3 <redacted> 4 xzy 5 <redacted>' ? null : got;
      },
    },
    {
      // 25.1 CR-02 (D-17): the relay strips ANSI before matching, and a value redacted on one
      // line (either stream) stays redacted on every later line and in the upstream body.
      name: 'pure-relay-redacts-copies-and-ansi',
      pure: () => {
        const out = [];
        const saved = log;
        log = (text) => { out.push(text); };
        const seen = new Set();
        try {
          const quiet = makeLineRelay({ seen, quiet: true });
          quiet.push('{"token":"zz7OUTsecretvalue7"}\n');
          const relay = makeLineRelay({ seen });
          relay.push('{"error":{"message":"bad","api_key":"zz9QQsecretvalue77"}}\n' +
            'retrying with key zz9QQsecretvalue77\n\x1b[31mapi_key\x1b[0m: zz8ANSIsecretvalue\n' +
            'stdout copy zz7OUTsecretvalue7 attempt 1\n');
          relay.flush();
        } finally {
          log = saved;
        }
        const text = out.join('\n');
        for (const leak of ['zz9QQsecretvalue77', 'zz8ANSIsecretvalue', 'zz7OUTsecretvalue7']) {
          if (text.includes(leak)) return `leaked ${leak}: ${text}`;
        }
        if (out.length !== 4 || !out[3].includes('attempt 1')) return `lines=${JSON.stringify(out)}`;
        const up = upstreamOf(null, { stderr: 'boom zz9QQsecretvalue77', redacted: [...seen] }, 'pi');
        return up && !up.body.includes('zz9QQ') ? null : `upstream=${JSON.stringify(up)}`;
      },
    },
    {
      // 25.1 WR-03: password keys, Basic auth, a Google `?key=` URL and a wide Bearer token.
      name: 'pure-redact-credential-shapes',
      pure: () => {
        const cases = [
          ['password=hunter2hunter2', 'hunter2hunter2'],
          ['{"passwd":"pw-secret-1"}', 'pw-secret-1'],
          ['Authorization: Basic dXNlcjpwYXNzd29yZA==', 'dXNlcjpwYXNzd29yZA'],
          ['GET https://x.googleapis.com/v1/m?key=AIzaSyA1234567890abcdefghijk 403', 'AIzaSyA12345'],
          ['GET https://x.example/v1?a=1&key=plainkey99 403', 'plainkey99'],
          ['bare AIzaSyB1234567890abcdefghijk here', 'AIzaSyB12345'],
          ['Authorization: Bearer abc~def+ghi/jkl=', 'ghi/jkl'],
        ];
        for (const [input, secret] of cases) {
          const got = redactSecrets(input);
          if (got.includes(secret)) return `leaked ${secret}: ${got}`;
        }
        const keep = redactSecrets('monkey=1 hotkey: x');
        return keep === 'monkey=1 hotkey: x' ? null : `over-redacted: ${keep}`;
      },
    },
    {
      // A mid-line credential keeps its line intact: the scheme word stays, no stray offset is
      // printed, and a hyperlink escape or an `=>` separator does not shield a key.
      name: 'pure-redact-mid-line-and-escapes',
      pure: () => {
        const tok = ['abcd', 'efgh', 'ijkl', 'mnop'].join('');
        const cases = [
          [`Authorization: Bearer ${tok}`, 'Authorization: Bearer <redacted>'],
          [`header Basic ${tok}== end`, 'header Basic <redacted> end'],
          [`see \x1B]8;;https://x.test/?key=${tok}\x1B\\link\x1B]8;;\x1B\\ ok`, 'see link ok'],
          [`api_key => ${tok}`, 'api_key => <redacted>'],
        ];
        for (const [raw, want] of cases) {
          const got = redactSecrets(normalizeInput(raw));
          if (got !== want) return JSON.stringify({ raw, got, want });
        }
        return null;
      },
    },
    {
      name: 'pure-redact-idempotent',
      pure: () => {
        const once = redactSecrets('{"accountId":"acct-77","token":"secret"}');
        return redactSecrets(once) === once ? null : redactSecrets(once);
      },
    },
    {
      name: 'pure-upstream-cap',
      pure: () => {
        const capped = capCodePoints('😀'.repeat(2500), 2000);
        return Array.from(capped).length === 2000 && !/[\\uD800-\\uDBFF]$/.test(capped) ? null : `codepoints=${Array.from(capped).length}`;
      },
    },
    {
      name: 'pure-upstream-fields',
      pure: () => {
        const cases = [
          ['429: {"retry_after":340954,"reset_at":"2026-10-19T00:00:00.000Z"}', '{"retry_after":340954,"reset_at":"2026-10-19T00:00:00.000Z"}'],
          ['{"retry_after_seconds":30}', '{"retry_after_seconds":30}'],
          ['{"type":"rate_limit","resetsAt":1761170400}', '{"resetsAt":1761170400}'],
          ['Kimi usage limit 403', 'null'], ['1310 GLM limit', 'null'],
        ];
        for (const [raw, expected] of cases) if (JSON.stringify(upstreamFields(raw) ?? null) !== expected) return raw;
        return null;
      },
    },
  ];
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

function readJsonObject(file, rootDir = null) {
  if (!fs.existsSync(file)) return { obj: null };
  if (rootDir != null) {
    const error = confinementError(file, rootDir);
    if (error) return { error };
  }
  let stat;
  try { stat = fs.statSync(file); } catch (e) { return { error: `unreadable (${e.code || e.message})` }; }
  if (!stat.isFile()) return { error: 'not a regular file' };
  if (stat.size > CONFIG_READ_MAX) return { error: `larger than ${CONFIG_READ_MAX} bytes` };
  const parsed = parseJson(readOr(file, ''));
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return { error: 'not a JSON object' };
  return { obj: parsed };
}

// ${XDG_CONFIG_HOME:-$HOME/.config}/ai-kit, for the overlay and the user retry file alike. An
// unset HOME is the account's own home, never a path relative to the working directory.
function aiKitConfigDir(env) {
  const configHome = env.XDG_CONFIG_HOME || path.join(env.HOME || os.homedir(), '.config');
  return path.join(configHome, 'ai-kit');
}

function loadOverlay(env) {
  const root = aiKitConfigDir(env);
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
// Last source of the retry cascade. Never validated and never refused: a cap below a default
// hard wait stops the hard tier first (25.1-03 hardWaitFor), it does not drop a key.
const RETRY_DEFAULTS = Object.freeze({
  base_s: 1, factor: 1.5, max_retries: 5, session_resets: 1,
  hard_waits_s: Object.freeze([600, 900, 1800]),
});
const RETRY_KEYS = ['base_s', 'factor', 'max_retries', 'session_resets', 'hard_waits_s'];

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
  if (!Array.isArray(value)) return 'wrong type';
  if (value.length < 1 || value.length > 6) return 'out of bounds (1..6 entries)';
  for (const entry of value) {
    if (!Number.isInteger(entry)) return 'non-integer entry';
    if (entry < 0 || entry > capS) return `entry out of bounds (0..${capS})`;
  }
  return null;
}

// Read once per call. Nothing here writes a config file. Each key falls through the sources
// on its own; a refusal names the key and the source and the next source fills it in.
function resolveRetry(cwd, env) {
  const rawCap = CONFIG.capS;
  const capS = clampCapS(rawCap);
  if (typeof rawCap === 'number' && rawCap > 14400) {
    log(`cross-ai: config capS ${rawCap} refused (CONFIG): above 14400; using 14400`);
  }
  const sources = [];
  for (const cfgPath of scopedConfigPaths(cwd, env)) {
    const label = path.relative(cwd, cfgPath);
    const got = workflowValue(cfgPath, 'cross_ai_retry', path.join(cwd, '.planning'));
    if (got.error) {
      log(`cross-ai: config ${label} ${got.error}; retry keys from the next source`);
      continue;
    }
    if (got.value === undefined) continue;
    sources.push({ label, value: got.value });
  }
  const userRoot = aiKitConfigDir(env);
  const userFile = path.join(userRoot, 'cross-ai.json');
  const userLabel = `user ${userFile}`;
  const userRead = readJsonObject(userFile, userRoot);
  if (userRead.error) {
    log(`cross-ai: config ${userLabel} ${userRead.error}; retry keys from the next source`);
  } else if (userRead.obj && Object.hasOwn(userRead.obj, 'cross_ai_retry')) {
    sources.push({ label: userLabel, value: userRead.obj.cross_ai_retry });
  }
  sources.push({ label: 'CONFIG', value: CONFIG.retry, config: true });
  const usable = [];
  for (const src of sources) {
    const named = src.config ? 'retry' : 'cross_ai_retry';
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
        const named = src.config ? 'retry' : 'cross_ai_retry';
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
    `session_resets=${retry.session_resets} hard_waits_s=${waits} cap_s=${capS}`);
  return { retry, capS };
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
// the one hard handler; the call never sleeps a hard wait. The admission checks apply to both
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

// The caller's hard tier (SPEC R3, D-08): cycle n waits hard_waits_s[n] as one exit-75 hint,
// the list's end or a wait that would pass the episode cap is a terminal stop, and the call
// itself never sleeps the wait. capLeftS is the seconds the episode cap still allows.
function hardWaitFor(cycle, waits, capLeftS) {
  if (cycle >= waits.length) return { stop: 'hard-waits' };
  if (waits[cycle] > capLeftS) return { stop: 'cap' };
  return { retryAfterS: Math.trunc(waits[cycle]), cycle };
}

// Rung 1 continues the captured session. Null when no session can be continued: no id,
// no resume formula, a sandboxed codex exec, or codex review (its resume argv has no
// read-only sandbox).
function sameSessionArgv(name, rt, model, ctx, sid, mode, input = RESUME_MSG) {
  if (!sid || !rt.resume) return null;
  if (name === 'codex' && (mode === 'review' || ctx.codexSandbox)) return null;
  return { argv: withExtra(name, rt.resume(model, ctx, sid, mode)), input };
}

// Rung 2 is a fresh argv on the same CLI and model. Pi gets a new session id.
function newSessionArgv(name, rt, model, ctx, mode, prompt) {
  if (name === 'pi') ctx.sid = crypto.randomUUID();
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
function readOr(p, dflt) { try { return fs.readFileSync(p, 'utf8'); } catch { return dflt; } }

// Quota cycles span calls. The file is keyed by lane and model under the XDG state dir
// (the home fallback is ~/.local/state, so a scratch HOME never reaches the real one).
const STATE_DELETE = new Set(['ok', 'auth', 'billing', 'permission_blocked', 'bad_model']);
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

// A case's state file, resolved inside the case's own XDG state dir. Router by default: the
// Phase 25 fixtures all sit on confirmed router lanes.
function caseCycleFile(ctx, cli, model, kind = 'router') {
  const home = path.join(ctx.env.XDG_STATE_HOME);
  return cycleFilePath(cli, model, kind, ctx.repo, home);
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

function deleteCycleState(file) {
  try { fs.rmSync(file, { force: true }); } catch { /* already gone */ }
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

// A noisy child must not exhaust memory before the status line: keep only the newest bytes per stream.
const CAPTURE_MAX_BYTES = 32 * 1024 * 1024;

function pushCapped(buf, d, max = CAPTURE_MAX_BYTES) {
  buf.chunks.push(d);
  buf.bytes += d.length;
  while (buf.bytes > max && buf.chunks.length > 1) {
    buf.bytes -= buf.chunks.shift().length;
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
    let code = null;
    let signal = null;
    const out = { chunks: [], bytes: 0, dropped: false };
    const err = { chunks: [], bytes: 0, dropped: false };

    // Caps are read when each wait starts, so a signal mid-finalize shortens what is left.
    const finalize = async (reason) => {
      if (settled) return;
      settled = true;
      if (timer) clearTimeout(timer);
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
        if (buf.dropped) log(`cross-ai: child ${label} passed ${CAPTURE_MAX_BYTES} bytes; kept the newest ${buf.bytes}`);
      }
      resolve({
        code, signal, timedOut, limited, spawnErr,
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
    current = child;
    currentFinalize = finalize;
    if (opts.input === null) {
      // stdin is `ignore`: there is no stream to write or end.
    } else if (opts.input !== undefined) {
      child.stdin.on('error', () => { /* closed early */ });
      child.stdin.end(opts.input);
    } else {
      child.stdin.end();
    }
    child.stdout.on('data', (d) => {
      pushCapped(out, d);
      opts.onStdout?.(d);
    });
    child.stderr.on('data', (d) => {
      pushCapped(err, d);
      opts.onStderr?.(d);
    });
    child.on('error', (e) => { spawnErr = e; finalize('error'); });
    child.on('exit', (c, s) => { code = c; signal = s; finalize('exit'); });
  });
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

function gitFailed(result, what) {
  gitFailure = { kind: result.timedOut ? 'timeout' : 'error', what };
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

async function treeState(cwd, limit, depth = 0) {
  const git = which('git', process.env.PATH || '');
  if (!git) { gitFailure = { kind: 'error', what: 'not found' }; return null; }
  // --verify -q: exit 1 with no message on an unborn HEAD, in any locale; 128 outside a repo.
  const headR = await runChild(git, ['rev-parse', '--verify', '-q', 'HEAD'], { cwd, capMs: GIT_CAP_MS, limit });
  if (headR.timedOut || headR.spawnErr || (headR.code !== 0 && headR.code !== 1)) {
    gitFailed(headR, 'rev-parse'); return null;
  }
  const head = headR.code === 0 ? headR.stdout.trim() : null;
  const idxDir = makeTemp('xai-idx-');
  const env = { ...process.env, GIT_INDEX_FILE: path.join(idxDir, 'index') };
  try {
    const addR = await runChild(git, ['add', '-A'], { cwd, env, capMs: GIT_CAP_MS, limit });
    if (addR.timedOut || addR.spawnErr || addR.code !== 0) {
      gitFailed(addR, 'add -A'); return null;
    }
    const wtR = await runChild(git, ['write-tree'], { cwd, env, capMs: GIT_CAP_MS, limit });
    if (wtR.timedOut || wtR.spawnErr || wtR.code !== 0) {
      gitFailed(wtR, 'write-tree'); return null;
    }
    // git add -A skips ignored files, so fold in a stat signature of each one (U-3): hashing
    // contents would be too slow for node_modules-sized trees, and a write changes ctime.
    // Fully ignored dirs list as one 'dir/' entry and are skipped, so a background cache or
    // indexer (.codegraph/, node_modules/) cannot read as an agent edit.
    const ignR = await runChild(git, ['ls-files', '-z', '-o', '-i', '--exclude-standard', '--directory'], { cwd, env, capMs: GIT_CAP_MS, limit });
    if (ignR.timedOut || ignR.spawnErr || ignR.code !== 0) {
      gitFailed(ignR, 'ls-files'); return null;
    }
    const ignHash = crypto.createHash('sha256');
    for (const rel of ignR.stdout.split('\0').filter((r) => r && !r.endsWith('/')).sort()) {
      let sig = 'gone';
      try {
        const st = fs.lstatSync(path.join(cwd, rel));
        sig = `${st.mode}:${st.size}:${st.mtimeMs}:${st.ctimeMs}`;
      } catch { /* removed since the listing */ }
      ignHash.update(`${rel}\0${sig}\0`);
    }
    // git add records a submodule (or any nested repo) as its HEAD only, so snapshot each
    // checked-out one too: edits inside it must count.
    const lsR = await runChild(git, ['ls-files', '-s', '-z'], { cwd, env, capMs: GIT_CAP_MS, limit });
    if (lsR.timedOut || lsR.spawnErr || lsR.code !== 0) { gitFailed(lsR, 'ls-files'); return null; }
    let nested = '';
    for (const entry of lsR.stdout.split('\0')) {
      if (!entry.startsWith('160000 ')) continue;
      const rel = entry.slice(entry.indexOf('\t') + 1);
      if (!fs.existsSync(path.join(cwd, rel, '.git'))) continue; // not checked out: the gitlink is all there is
      if (depth >= MAX_NESTED_REPOS) {
        gitFailure = { kind: 'error', what: 'nested repos' }; return null;
      }
      const sub = await treeState(path.join(cwd, rel), limit, depth + 1);
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
  const extra = CONFIG.extraArgs[cli];
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
    if (selfTestRoot) { selfTestAbort(128 + n); return; }
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
      for (const dir of [...tempDirs]) dropTemp(dir);
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

function watchChunk(cli, source, relay, state, chunk) {
  relay.push(chunk);
}

async function runOnce(bin, argv, input, env, cwd, label, opts = {}) {
  let outBytes = 0;
  let lastBytes = 0;
  const started = Date.now();
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
  const hb = setInterval(() => {
    const secs = Math.round((Date.now() - started) / 1000);
    log(`cross-ai: ${label} running ${secs}s, stdout +${outBytes - lastBytes} bytes`);
    lastBytes = outBytes;
  }, CONFIG.heartbeatS * 1000);
  const childLimit = opts.limit ?? runDeadline;
  // One decoder per stream: a multi-byte character split across two chunks decodes whole.
  const outDecoder = new StringDecoder('utf8');
  const errDecoder = new StringDecoder('utf8');
  const onErrText = (text) => {
    if (!text) return;
    watchChunk(cli, 'stderr', errRelay, state, text);
    errTail = (errTail + text).slice(-INPUT_CAP);
  };
  const r = await runChild(bin, argv, {
    cwd, env, input, capMs: budgetMs(opts.capMs ?? Number.POSITIVE_INFINITY, childLimit),
    limit: childLimit,
    onStdout: (d) => {
      outBytes += d.length;
      watchChunk(cli, 'stdout', outRelay, state, outDecoder.write(d));
    },
    onStderr: (d) => onErrText(errDecoder.write(d)),
  });
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
function attemptCapMs(opts, nowMs, quotaEndMs = 0) {
  const remaining = Math.max(0, runDeadline - nowMs);
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
function logReport(status, cli, model, route, attempts, cycles, firstMs, lastMs, stopped, dueMs = 0, upstream = null) {
  const iso = (ms) => (ms ? new Date(ms).toISOString() : '-');
  const dueIso = (ms) => (ms ? new Date(ms).toISOString().replace(/\.\d{3}Z$/, 'Z') : '-');
  log(`cross-ai: report status=${status} lane=${cli}/${model} route=${route || 'unknown'} ` +
    `attempts=${attempts} cycles=${cycles} first_failure=${iso(firstMs)} ` +
    `last_failure=${iso(lastMs)} due_at=${dueIso(dueMs)} stopped=${stopped} ` +
    `upstream=${upstream?.body ? 'present' : '-'}`);
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
    codexEffort: opts.codexEffort, codexServiceTier: opts.codexServiceTier,
    cursorMode: opts.cursorMode,
    piThinking: opts.piThinking, codexSandbox: opts.codexSandbox,
    profileFlags: opts.profileFlags || [],
    promptArg: '<prompt>',
  };
  const env = childEnv(rt.env, process.env);
  // A resume argv is checked against the runtime's own resume formula, so its session flag is
  // trusted and only extras beyond the formula count as a widening.
  const reviewProblem = (argv, sid = null) => {
    if (mode !== 'review') return null;
    const base = sid ? rt.resume(model, ctx, sid, mode) : rt.review(model, ctx);
    return reviewArgvProblem(argv, base, rt.reviewExtras || []);
  };
  const refuseReview = (problem) => {
    const allowed = (rt.reviewExtras || []).join(', ') || 'none';
    log(`cross-ai: review argv for ${name} holds ${problem}; review extras allowed for ${name}: ${allowed}; refused`);
    return { ok: false, status: 'usage', exit: 2, cli_rc: '-', outBytes: 0 };
  };
  if (rt.argvPrompt) ctx.promptArg = argvPromptElement(prompt);
  let argv = withExtra(name, rt[mode](model, ctx));
  const initialProblem = reviewProblem(argv);
  if (initialProblem) return refuseReview(initialProblem);
  let input = rt.argvPrompt ? null : prompt;
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
    if (STATE_DELETE.has(status) || (status !== 'quota' && !QUOTA_KEEP.has(status))) {
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
        attempts, last_sid: sid || null, task_digest: digest, ...record,
      });
      logState();
    } catch (e) {
      stateWritable = false;
      log(`cross-ai: cycle state unwritable: ${stateFile} (${e.code || e.message})`);
    }
  };
  // One hard handler for both soft classes (D-07). The call never sleeps the hard wait: the
  // next wait hard_waits_s[cycle] is one exit-75 hint the caller owns, and once the list is
  // spent or the cap would pass it, the call exits 69 with the stop persisted on disk (D-08,
  // D-09). A soft step refused for `cap` is already past the episode end, so it stops at once.
  const hardHandler = (r, evidence, why, sid, cls) => {
    const at = Date.now();
    const stopped = why === 'deadline' ? 'deadline' : 'rungs';
    const step = why === 'cap'
      ? { stop: 'cap' }
      : hardWaitFor(ladder.cycle, retryCfg.hard_waits_s,
          ladder.firstMs ? (ladder.firstMs + capMs - at) / 1000 : -1);
    if (step.stop) {
      saveCycle(sid, at, {
        class: cls, stopped: step.stop, stopped_at: at, retry_after_s: null, due_at: null,
      });
      return {
        ok: false, status: cls, timedOut: false,
        outBytes: r.outBytes, cli_rc: r.code ?? '-', ...evidence, ...counts(),
        cycle: ladder.cycle, exit: 69, stopped: step.stop,
      };
    }
    const dueAtMs = at + step.retryAfterS * 1000;
    saveCycle(sid, at, {
      class: cls, retry_after_s: step.retryAfterS, due_at: dueAtMs,
    });
    return {
      ok: false, status: cls, timedOut: false,
      outBytes: r.outBytes, cli_rc: r.code ?? '-', ...evidence, ...counts(),
      retryAfterS: stateWritable ? step.retryAfterS : undefined,
      dueAtMs: stateWritable ? dueAtMs : undefined,
      cycle: step.cycle, exit: 75, stopped,
    };
  };
  try {
    if (persisted && persisted.task_digest === digest && persisted.last_sid) {
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
      }
    }
    for (let attempt = 0; ; attempt++) {
      // Before the child runs: the snapshot after it would race the next attempt's edits.
      if (mode === 'exec' && seenSig !== null) {
        const seen = await treeState(ctx.cwd, runDeadline);
        if (seen) seenSig = stateSig(seen);
      }
      const startedMs = Date.now();
      const childCap = attemptCapMs(opts, startedMs, episodeEnd());
      const left = Math.max(0, Math.round(childCap / 1000));
      log(`cross-ai: cli=${name} bin=${binPath} mode=${mode} attempt=${attempt + 1} timeout=${left}s`);
      log(`cross-ai: argv=${JSON.stringify(displayArgv(argv, rt.argvPrompt ? ctx.promptArg : undefined))}`);
      const childLimit = episodeEnd() ? Math.min(runDeadline, episodeEnd()) : runDeadline;
      const route = opts.route || 'unknown';
      const r = await runOnce(binPath, argv, input, env, ctx.cwd, name,
        { capMs: childCap, limit: childLimit, route, model });
      // Self-test fakes only (FAKE_CALLS): a fake child stalls the post-run git snapshot only
      // while it is alive. A real run never touches the caller's home.
      if (process.env.FAKE_CALLS) {
        try { fs.rmSync(path.join(env.HOME || '', '.fake-git-hang')); } catch { /* not set */ }
      }
      if (aborting) return { ok: false, code: 128 + aborting, outBytes: r.outBytes, cli_rc: r.code };
      const lane = confirmedRoute(route);
      const evidenceOf = (cls) => {
        const rule = cls && cls.rule ? cls.rule : '-';
        // A runtime whose error wording is uncaptured reports every pattern unverified,
        // even a wildcard row the catalog itself labels verified.
        const pattern = rt.errorsUnverified ? 'unverified' : (cls && cls.label ? cls.label : 'none');
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
      // A live hit wins only when it ended the child: one that finished on its own with exit 0
      // and an answer succeeded, whatever it printed on stderr on the way.
      const finished = !r.timedOut && r.code === 0 && !p.error && Boolean(p.text.trim());
      if (r.liveHit && !r.limited && finished) r.liveHit = null;
      // A live terminal signal is the attempt's class; no second pass (D-09).
      let hit = null;
      let evidence = evidenceOf(null);
      // A non-retryable class ends the call here; both class checks below share it.
      const classStop = () => {
        attempts += 1;
        logAttempt(attempts, rungOf(), ladder.cycle, p.sessionId, hit, evidence.rule,
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
        const cls = classifyStop({ cli: name, route, model, stderr: captured, events, eventRaw });
        if (cls.status !== 'crash') {
          hit = cls.status;
          evidence = evidenceOf(cls);
        }
      } else {
        const { events, eventRaw } = eventsWithRaw(name, r.stdout);
        const cls = classifyStop({ cli: name, route, model, stderr: r.stderr, events, eventRaw });
        if (cls.status !== 'crash') {
          hit = cls.status;
          evidence = evidenceOf(cls);
        }
        const failed = r.code !== 0 || Boolean(p.error);
        if (!failed && p.text.trim()) {
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
      const sid = p.sessionId || (name === 'pi' ? ctx.sid : null);
      const rung = rungOf();
      logAttempt(attempts, rung, ladder.cycle, sid, hit || (r.timedOut ? 'timeout' : 'crash'),
        hit ? evidence.rule : '-', hit ? evidence.pattern : '-', startedMs);
      const soft = cls === 'transient' || cls === 'quota';
      if (soft && !ladder.firstMs) ladder.firstMs = Date.now();
      const sig = r.signal ? ' ' + r.signal : '';
      log(`cross-ai: ${name} failed (exit ${r.code}${sig}, rule=${hit ? evidence.rule : '-' })`);
      ladder.canResume = Boolean(sameSessionArgv(name, rt, model, ctx, sid, mode));
      // k restarts at 1 with every series, so the reset and the first retry after it both wait
      // about base_s, and the ordering floor applies within one series only.
      const k = ladder.retry < retryCfg.max_retries ? ladder.retry + 1 : 1;
      const prevMs = k === 1 ? 0 : ladder.prevWaitMs;
      const nominal = softWaitMs(retryCfg, k, Math.random, prevMs);
      const end = episodeEnd();
      const step = ladderNext(ladder, cls, Date.now(), {
        maxRetries: retryCfg.max_retries, sessionResets: retryCfg.session_resets,
        deadlineMs: runDeadline, waitMs: nominal, capMs,
      });
      const wait = end ? Math.min(nominal, Math.max(0, end - Date.now())) : nominal;
      log(`cross-ai: ladder ${name} next=${step.next} why=${step.why}`);
      if (step.next === 'hard') return hardHandler(r, evidence, step.why, sid, cls);
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
        const retry = sameSessionArgv(name, rt, model, ctx, sid, mode, resumed);
        const resumeProblem = reviewProblem(retry.argv, sid);
        if (resumeProblem) return refuseReview(resumeProblem);
        argv = retry.argv;
        input = retry.input;
      } else if (step.next === 'reset') {
        ladder.resets += 1;
        ladder.retry = 0;
        rungLabel = 'reset';
        const retry = newSessionArgv(name, rt, model, ctx, mode, nextInput);
        argv = retry.argv;
        input = retry.input;
      } else {
        ladder.retry += 1;
        rungLabel = 'new';
        // A new session with nothing to resume gets the task itself. The resume note is for a
        // session that already ran, or for a reset continuing one.
        const fresh = gated ? nextInput : prompt;
        const retry = newSessionArgv(name, rt, model, ctx, mode, fresh);
        argv = retry.argv;
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

// Null when the ignored or nested parts differ, or git fails: those changes have no path to
// account for. Otherwise the sorted paths that differ between the two write-tree ids.
async function changedPaths(before, mid, cwd) {
  const beforeParts = String(before || '').split('\t');
  const midParts = String(mid || '').split('\t');
  if (beforeParts.slice(1).join('\t') !== midParts.slice(1).join('\t')) return null;
  const git = which('git', process.env.PATH || '');
  if (!git || !beforeParts[0] || !midParts[0]) return null;
  const diff = await runChild(
    git, ['diff-tree', '-r', '--name-only', '-z', beforeParts[0], midParts[0]],
    { cwd, capMs: GIT_CAP_MS, limit: runDeadline },
  );
  if (diff.timedOut || diff.spawnErr || diff.code !== 0) return null;
  return diff.stdout.split('\0').filter(Boolean).sort();
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

const CODEX_EFFORTS = new Set(['minimal', 'low', 'medium', 'high', 'xhigh']);
const PI_THINKING = new Set(['off', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max']);
const CURSOR_MODES = new Set(['ask', 'plan']);
const ROUTE_VALUES = new Set(['router', 'unknown']);

function parseArgs(argv) {
  const o = {
    runtime: null, prefer: null, model: null, toolsProfile: null,
    models: {}, routes: {}, mode: 'exec', timeout: null, outerTimeout: null,
    printArgv: false, preamble: true, selfTest: false, classifyOnly: null,
    codexEffort: null, codexServiceTier: null, cursorMode: null,
    prependFile: null, codexSandbox: null, childPgidFile: null,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]; const v = () => { if (i + 1 >= argv.length) throw new Error(`${a} needs a value`); return argv[++i]; };
    if (a === '--runtime') o.runtime = v();
    else if (a === '--prefer') o.prefer = v().split(',').filter(Boolean);
    else if (a === '--model') {
      // The runtime is not known yet, and --model may come before --runtime, so this is the
      // superset charset (every MODEL_ID id plus one cursor bracket). The row's modelId is
      // checked in main on the selected runtime only.
      o.model = v();
      if (!CURSOR_MODEL_ID.test(o.model)) throw new Error(`--model must match ${CURSOR_MODEL_ID.source}`);
    } else if (a === '--tools-profile') {
      o.toolsProfile = v();
      if (!['exec', 'review', 'none'].includes(o.toolsProfile)) {
        throw new Error('--tools-profile must be exec, review or none');
      }
    } else if (a.startsWith('--model-')) {
      const id = v();
      const modelRe = a === '--model-cursor' ? CURSOR_MODEL_ID : MODEL_ID;
      if (!modelRe.test(id)) throw new Error(`${a} must match ${modelRe.source}`);
      o.models[a.slice(8)] = id;
    } else if (a.startsWith('--route-')) {
      const route = v();
      if (!ROUTE_VALUES.has(route)) throw new Error(`${a} must be router or unknown`);
      o.routes[a.slice(8)] = route;
    } else if (a === '--classify-only') o.classifyOnly = v();
    else if (a === '--mode') { o.mode = v(); if (!['exec', 'review'].includes(o.mode)) throw new Error('--mode must be exec or review'); }
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
      if (!CODEX_EFFORTS.has(o.codexEffort)) throw new Error('--codex-effort must be minimal|low|medium|high|xhigh');
    } else if (a === '--codex-service-tier') {
      o.codexServiceTier = v();
      if (!/^[A-Za-z0-9_-]+$/.test(o.codexServiceTier)) throw new Error('--codex-service-tier must match [A-Za-z0-9_-]+');
    } else if (a === '--cursor-mode') {
      o.cursorMode = v();
      if (!CURSOR_MODES.has(o.cursorMode)) throw new Error('--cursor-mode must be ask or plan');
    } else if (a === '--self-test') o.selfTest = true;
    else throw new Error(`unknown argument: ${a}`);
  }
  if (o.mode === 'exec' && o.cursorMode) throw new Error('--cursor-mode is review-only');
  const known = Object.keys(RUNTIMES).join(', ');
  if (o.runtime !== null && !Object.hasOwn(RUNTIMES, o.runtime)) {
    throw new Error(`unknown runtime: ${o.runtime} (known: ${known})`);
  }
  // SPEC R6: only the entry that runs is checked; the ignored rest gets resolveRuntime's notice.
  const runs = o.runtime === null && o.prefer && o.prefer.length ? [o.prefer[0]] : [];
  for (const n of [...runs, ...Object.keys(o.models), ...Object.keys(o.routes)]) {
    if (!Object.hasOwn(RUNTIMES, n)) throw new Error(`unknown cli: ${n} (known: ${known})`);
  }
  return o;
}

// One runtime per call (SPEC R6, D-13): --runtime, then the first --prefer entry, then
// CONFIG.runtime, then the first CONFIG.prefer entry. A list is never walked.
function resolveRuntime(o) {
  const known = (name) => typeof name === 'string' && Object.hasOwn(RUNTIMES, name);
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
    if (!known(CONFIG.runtime)) return { error: `cross-ai: unknown runtime: ${CONFIG.runtime}` };
    return { name: CONFIG.runtime, notes: [] };
  }
  const prefer = Array.isArray(CONFIG.prefer) ? CONFIG.prefer.filter((n) => typeof n === 'string' && n) : [];
  if (prefer.length) {
    if (!known(prefer[0])) return { error: `cross-ai: unknown runtime: ${prefer[0]}` };
    const notes = [];
    if (prefer.length > 1) notes.push(ignored('CONFIG.prefer', prefer[0], prefer.slice(1)));
    return { name: prefer[0], notes };
  }
  return { error: 'cross-ai: no runtime: pass --runtime <id>' };
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
    if (!Object.hasOwn(RUNTIMES, cli)) {
      log(`cross-ai: --classify-only unknown cli: ${cli}`);
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
    });
    // Same rule as a live run: an uncaptured runtime reports every pattern unverified.
    const pattern = RUNTIMES[cli].errorsUnverified ? 'unverified' : cls.label;
    lines.push(JSON.stringify({ name: entry.name, status: cls.status, rule: cls.rule, pattern, route }));
  }
  if (lines.length) process.stdout.write(`${lines.join('\n')}\n`);
  return reportAndFinish('ok', { ...liveFields, tree: 'clean', exit: 0, out: lines.length });
}

function readStdin() {
  if (process.stdin.isTTY) return null;
  try { return fs.readFileSync(0, 'utf8'); } catch { return null; }
}

function hermeticEnv(tmp, extra = {}) {
  const home = extra.HOME || path.join(tmp, 'home');
  const base = {
    PATH: path.join(tmp, 'bin'),
    HOME: home,
    XDG_CONFIG_HOME: extra.XDG_CONFIG_HOME || path.join(home, '.config'),
    GIT_CONFIG_GLOBAL: os.devNull,
    GIT_CONFIG_NOSYSTEM: '1',
    GIT_AUTHOR_NAME: 'xai-selftest',
    GIT_COMMITTER_NAME: 'xai-selftest',
    GIT_AUTHOR_EMAIL: 'xai-selftest@example.invalid',
    GIT_COMMITTER_EMAIL: 'xai-selftest@example.invalid',
    LANG: 'C',
    FAKE_CALLS: extra.FAKE_CALLS || path.join(tmp, 'calls.log'),
  };
  return { ...base, ...extra };
}

function writeCopy(tmp, name, override) {
  const src = fs.readFileSync(fileURLToPath(import.meta.url), 'utf8');
  // base_s 0 and hard waits of 0 keep every existing case instant. A partial override.retry
  // merges per key, so a case never falls back to the 1-second default by omission. An
  // override of a deleted Phase 25 key becomes a retry override (D-04). This comment must not
  // name the config sentinels: the copy rewrite stops at the first closing sentinel.
  const { retry: retryOverride, backoffS, cooldownS, ...rest } = override || {};
  const cfg = {
    attemptTimeoutS: 0, capS: 14400, effort: {}, extraArgs: {},
    heartbeatS: 30, models: {}, outerTimeoutS: 1800,
    runtime: 'pi', routerBacked: {},
    scrubEnv: [...CONFIG.scrubEnv],
    ...rest,
    retry: { base_s: 0, factor: 1.5, max_retries: 5, session_resets: 1, hard_waits_s: [0, 0, 0] },
  };
  if (Object.hasOwn(rest, 'prefer') && !Object.hasOwn(rest, 'runtime')) cfg.runtime = null;
  // Null normally removes an override; runtime null models prefer-only copies.
  for (const key of Object.keys(cfg)) {
    if (cfg[key] === null && !(key === 'runtime' && Object.hasOwn(rest, 'prefer'))) delete cfg[key];
  }
  const translated = {};
  if (Array.isArray(backoffS)) translated.base_s = backoffS[0] ?? 0;
  if (cooldownS !== undefined) translated.hard_waits_s = [cooldownS, cooldownS, cooldownS];
  if (retryOverride || backoffS !== undefined || cooldownS !== undefined) {
    cfg.retry = { ...cfg.retry, ...translated, ...retryOverride };
  }
  const block = `// <config>\nconst CONFIG = ${JSON.stringify(cfg, null, 2)};\n// </config>`;
  const out = src.replace(/\/\/ <config>[\s\S]*?\/\/ <\/config>/, block);
  const p = path.join(tmp, `runner-${name}.mjs`);
  fs.writeFileSync(p, out);
  return p;
}

// Every fake records "<name> <pid>" in $FAKE_PIDS so a case can reap what it spawned.
const FAKE_PRELUDE = String.raw`
const calls = process.env.FAKE_CALLS;
const log = (line) => { if (calls) fs.appendFileSync(calls, line + '\n'); };
const recordPid = (name, pid) => { if (process.env.FAKE_PIDS) fs.appendFileSync(process.env.FAKE_PIDS, name + ' ' + pid + '\n'); };
recordPid(process.argv[1].split('/').pop(), process.pid);
const argOf = (flag) => { const i = process.argv.indexOf(flag); return i >= 0 ? process.argv[i + 1] || '' : ''; };
`;

function writeExe(binDir, name, imports, body) {
  const p = path.join(binDir, name);
  fs.writeFileSync(p, `#!/usr/bin/env node\nimport fs from 'node:fs';\n${imports}${FAKE_PRELUDE}${body}`);
  fs.chmodSync(p, 0o755);
}

function writeGitWrapper(binDir, realGit) {
  writeExe(binDir, 'git', "import { spawnSync } from 'node:child_process';\nimport path from 'node:path';\n", `
const realGit = ${JSON.stringify(realGit)};
const home = process.env.HOME || '';
const sub = process.argv.slice(2);
if (sub[0] === 'write-tree') {
  if (fs.existsSync(path.join(home, '.fake-git-hang'))) { while (true) {} }
  if (fs.existsSync(path.join(home, '.fake-git-fail'))) process.exit(128);
}
if (sub[0] === 'rev-parse' && fs.existsSync(path.join(home, '.fake-git-l10n'))) {
  // A non-English locale: same exit code, translated message.
  const l = spawnSync(realGit, sub, { stdio: ['inherit', 'inherit', 'pipe'] });
  if (l.status !== 0) process.stderr.write("fatal: mehrdeutiges Argument 'HEAD': unbekannte Revision\\n");
  process.exit(l.status ?? 1);
}
const r = spawnSync(realGit, sub, { stdio: 'inherit' });
process.exit(r.status ?? 1);
`);
}

function writeFakePi(binDir) {
  writeExe(binDir, 'pi', "import { spawn, spawnSync } from 'node:child_process';\n", String.raw`
const args = process.argv;
const model = argOf('--model');
const fakeMode = model.startsWith('fake/') ? model.slice(5).replace(/:[a-z]+$/, '') : '';
const recordGc = (pid) => { fs.writeFileSync('gc.pid', String(pid)); recordPid('gc', pid); };
const STICKY_FAKE = new Set([
  'hang', 'hangonce', 'gcescape', 'outer-race', 'stubborn', 'slowok', 'big', 'sentinelsplit',
  'limit-mid', 'limit-partial', 'limit-flood', 'limit-partial-flood', 'auth-then-noise',
  'transient-hang', 'bare-429-hang', 'retry-notice', 'retry-notice-429', 'slowquota',
  'capclamp', 'reason-code-hang', 'slow-lines', 'router-stop-hang',
]);
let stdinBuf = '';
const FAKE_MODES = {
  ok: () => { fs.appendFileSync('a.txt', 'ok-line\n'); process.stdout.write('# Summary\nok'); },
  envmarker: () => {
    fs.writeFileSync('marker.seen', process.env.AI_KIT_CROSS_AI_CHILD ?? '<unset>');
    fs.appendFileSync('a.txt', 'm\n');
    process.stdout.write('# Summary\nok');
  },
  'stderr-then-ok': () => {
    process.stderr.write('tool bash: cat /root/x: Permission denied\n');
    fs.appendFileSync('a.txt', 'ok-line\n');
    process.stdout.write('# Summary\nok');
  },
  echoprompt: () => {
    fs.writeFileSync('prompt.seen', stdinBuf);
    fs.appendFileSync('a.txt', 'e\n');
    process.stdout.write('# Summary\nok');
  },
  ansi: () => { fs.appendFileSync('a.txt', 'x\n'); process.stdout.write('\x1B[0mDone.## Summary\nC# is fine. Use ## inline'); },
  nochange: () => { process.stdout.write('# Summary\nno edits'); },
  okwarn: () => {
    fs.appendFileSync('a.txt', 'w\n');
    process.stderr.write('provider returned 503 Service Unavailable; retrying\nwrote 401 lines\n');
    process.stdout.write('# Summary\nok');
  },
  emptyauth: () => { process.stderr.write('401 unauthorized\n'); },
  big: () => {
    fs.appendFileSync('a.txt', 'big\n');
    process.stderr.write('e'.repeat(300000) + '\n');
    process.stdout.write('# Summary\n' + 'y'.repeat(300000), () => process.exit(0));
  },
  slowok: () => {
    fs.writeFileSync('started', '1');
    setTimeout(() => { fs.appendFileSync('a.txt', 'slow\n'); process.stdout.write('# Summary\nok'); process.exit(0); }, 2500);
  },
  empty: () => {},
  crash: () => { process.exit(7); },
  quote: () => {
    fs.appendFileSync('a.txt', 'q\n');
    process.stdout.write('429 rate limit and billing noted.\n# Summary\nok');
  },
  router402: () => {
    const key = process.env.AIKIT_XAI_SENTINEL || 'sentinel';
    process.stderr.write('402: {"message":"[acme-cli/acme-4.7] [402]: Acme Build usage balance exhausted (reset after 2m)","retry_after":120,"reset_at":"2026-10-23T04:01:04.472Z","api_key":"' + key + '","connection":"conn:ab12cd34"}\n');
    process.exit(1);
  },
  'router402-nofields': () => {
    const key = process.env.AIKIT_XAI_SENTINEL || 'sentinel';
    process.stderr.write('402: {"message":"[acme-cli/acme-4.7] [402]: Acme Build usage balance exhausted (reset after 2m)","api_key":"' + key + '","connection":"conn:ab12cd34"}\n');
    process.exit(1);
  },
  'auth-then-noise': () => {
    process.stderr.write('Error: not logged in\nlater noise\n');
    setInterval(() => {}, 1 << 30);
  },
  'session-echo': () => {
    const session = argOf('--session-id') || '';
    process.stderr.write(session + '\n401 unauthorized\n');
    process.exit(1);
  },
  billing: () => { process.stderr.write('402 payment required\n'); process.exit(1); },
  'router-env-billing': () => { process.stderr.write('402 payment required\n'); process.exit(1); },
  spend403: () => { process.stderr.write('Error 403: spending limit reached for this team\n'); process.exit(1); },
  freetier: () => { process.stderr.write('403: {"type":"FreeTierError"}\n'); process.exit(1); },
  auth: () => { process.stderr.write('401 unauthorized\n'); process.exit(1); },
  perm: () => { process.stderr.write('permission denied\n'); process.exit(1); },
  quota: () => { process.stderr.write('quota exceeded\n'); process.exit(1); },
  'quota-until-8': () => {
    const home = process.env.HOME || '';
    const ctr = home + '/.fake-quota8-count';
    let n = 0;
    try { n = Number(fs.readFileSync(ctr, 'utf8')) || 0; } catch { /* first call */ }
    fs.writeFileSync(ctr, String(n + 1));
    if (n === 6 && stdinBuf.includes('a different task')) log('quota8-new-task');
    if (n < 7) { process.stderr.write('quota exceeded\n'); process.exit(1); }
    fs.writeFileSync('prompt.seen', stdinBuf);
    fs.appendFileSync('a.txt', 'ok-line\n');
    process.stdout.write('# Summary\nok');
  },
  slowquota: () => {
    const ctr = (process.env.HOME || '') + '/.fake-slowquota-count';
    let n = 0;
    try { n = Number(fs.readFileSync(ctr, 'utf8')) || 0; } catch { /* first */ }
    fs.writeFileSync(ctr, String(n + 1));
    process.stderr.write('429 Too Many Requests\n');
    if (n < 1) { process.exit(1); return; }
    setInterval(() => {}, 1 << 30);
  },
  capclamp: () => {
    const ctr = 'capclamp.count';
    let n = 0;
    try { n = Number(fs.readFileSync(ctr, 'utf8')) || 0; } catch { /* first */ }
    fs.writeFileSync(ctr, String(n + 1));
    if (n < 1) { process.stderr.write('429 Too Many Requests\n'); process.exit(1); }
    setInterval(() => {}, 1 << 30);
  },
  'router-env-quota': () => { process.stderr.write('429 too many requests\n'); process.exit(1); },
  sentinelrouter: () => {
    const key = process.env.AIKIT_XAI_CASE_SENTINEL || '';
    process.stderr.write('402 requires an opencode API key: ' + key + '\n');
    process.exit(1);
  },
  dirtycrash: () => { fs.appendFileSync('a.txt', 'd\n'); process.stderr.write('boom\n'); process.exit(7); },
  dirtyquota: () => { fs.appendFileSync('a.txt', 'dq\n'); process.stderr.write('quota exceeded\n'); process.exit(1); },
  dirtybilling: () => { fs.appendFileSync('a.txt', 'db\n'); process.stderr.write('402 payment required\n'); process.exit(1); },
  gitfailquota: () => {
    fs.writeFileSync((process.env.HOME || '') + '/.fake-git-fail', '1');
    process.stderr.write('quota exceeded\n');
    process.exit(1);
  },
  reedit: () => { fs.appendFileSync('dirty.txt', 'more\n'); process.stdout.write('# Summary\nok'); },
  subedit: () => { fs.appendFileSync('sub/f.txt', 'edit\n'); process.stdout.write('# Summary\nok'); },
  ignorededit: () => { fs.appendFileSync('x.local', 'edit\n'); process.stdout.write('# Summary\nok'); },
  cachewrite: () => { fs.appendFileSync('ign/x.txt', 'edit\n'); process.stdout.write('# Summary\nok'); },
  stubborn: () => {
    process.on('SIGTERM', () => {});
    process.on('SIGINT', () => {});
    fs.appendFileSync('a.txt', 'stubborn\n');
    fs.writeFileSync('cli.ready', '1');
    setInterval(() => {}, 1 << 30);
  },
  hang: () => {
    const gc = spawn(process.execPath, ['-e', 'while(true){}'], { stdio: 'ignore' });
    recordGc(gc.pid);
    setInterval(() => {}, 1 << 30);
  },
  'limit-mid': () => {
    process.stderr.write("You've hit your usage limit\n");
    setInterval(() => {}, 1 << 30);
  },
  'limit-partial': () => {
    process.stderr.write('quota exceeded');
    setInterval(() => {}, 1 << 30);
  },
  'answer-only-limit': () => {
    fs.appendFileSync('a.txt', 'a\n');
    process.stdout.write('# Summary\n' + "You've hit your usage limit, quoted from the task");
  },
  'retry-notice': () => {
    process.stderr.write('Retrying in 1s: 503 Service Unavailable\n');
    setTimeout(() => {
      fs.appendFileSync('a.txt', 'a\n');
      process.stdout.write('# Summary\nok');
      process.exit(0);
    }, 800);
  },
  'retry-notice-429': () => {
    process.stderr.write('Retrying in 1s: 429 Too Many Requests\n');
    setTimeout(() => {
      fs.appendFileSync('a.txt', 'a\n');
      process.stdout.write('# Summary\nok');
      process.exit(0);
    }, 800);
  },
  'limit-flood': () => {
    process.stderr.write('quota exceeded\n');
    const line = 'x'.repeat(200) + '\n';
    for (let i = 0; i < 512; i++) process.stderr.write(line);
    setInterval(() => {}, 1 << 30);
  },
  'transient-hang': () => {
    process.stderr.write('[400]: event: error\n');
    setInterval(() => {}, 1 << 30);
  },
  'limit-partial-flood': () => {
    process.stderr.write('quota exceeded');
    process.stderr.write('x'.repeat(100 * 1024));
    setInterval(() => {}, 1 << 30);
  },
  'bare-429-hang': () => {
    process.stderr.write('429 Too Many Requests\n');
    setInterval(() => {}, 1 << 30);
  },
  'reason-code-hang': () => {
    process.stderr.write('429: {"message":"Service temporarily unavailable: all targets were skipped by pre-dispatch filters (weekly 100% ...) reset after 94h 42m 34s","type":"rate_limit_error","code":"ALL_TARGETS_SKIPPED","retry_after":340954,"reset_at":"2026-10-19T00:00:00.000Z"}\n');
    setTimeout(() => process.exit(1), 2500);
  },
  'slow-lines': () => {
    const line = 'a'.repeat(20) + '!\n';
    process.stderr.write(line.repeat(2000));
    setInterval(() => {}, 1 << 30);
  },
  'catastrophic-flood': () => {
    const line = 'a'.repeat(41) + '!\n';
    process.stderr.write(line.repeat(100));
    setInterval(() => {}, 1 << 30);
  },
  'router-stop-hang': () => {
    process.stderr.write('acme router stop\n');
    setInterval(() => {}, 1 << 30);
  },
  gcpipe: () => {
    const gc = spawn(process.execPath, ['-e', 'while(true){}'], { stdio: 'inherit' });
    recordGc(gc.pid);
    fs.appendFileSync('a.txt', 'gp\n');
    process.stdout.write('# Summary\nok');
  },
  gcterm: () => {
    const gc = spawn(process.execPath, ['-e', 'process.on("SIGTERM",()=>{});while(true){}'], { stdio: 'inherit' });
    recordGc(gc.pid);
    fs.appendFileSync('a.txt', 'gt\n');
    process.stdout.write('# Summary\nok');
  },
  gcescape: () => {
    const gc = spawn(process.execPath, ['-e', 'const fs=require("fs");fs.writeFileSync("gc.pid",String(process.pid));if(process.env.FAKE_PIDS)fs.appendFileSync(process.env.FAKE_PIDS,"gc "+process.pid+String.fromCharCode(10));setInterval(()=>process.stderr.write("gc-late"+String.fromCharCode(10)),100);setInterval(()=>{},1<<30);'], { detached: true, stdio: ['ignore', 'pipe', 'pipe'] });
    gc.stderr.on('data', (d) => process.stderr.write(d));
    gc.unref();
    setInterval(() => {}, 1 << 30);
  },
  gitfail: () => {
    fs.appendFileSync('a.txt', 'gf\n');
    fs.writeFileSync((process.env.HOME || '') + '/.fake-git-fail', '1');
    process.stdout.write('# Summary\nok');
  },
  event400: () => {
    process.stderr.write('[400]: event: error\n');
    process.exit(1);
  },
  dirtyevent400: () => {
    fs.appendFileSync('a.txt', 'dirty\n');
    process.stderr.write('[400]: event: error\n');
    process.exit(1);
  },
  hangonce: () => {
    const home = process.env.HOME || '';
    const ctr = home + '/.fake-hangonce-count';
    let n = 0;
    try { n = Number(fs.readFileSync(ctr, 'utf8')) || 0; } catch { /* first call */ }
    fs.writeFileSync(ctr, String(n + 1));
    if (n < 1) { setInterval(() => {}, 1 << 30); return; }
    fs.appendFileSync('a.txt', 'ok-line\n');
    process.stdout.write('# Summary\nok');
    process.exit(0);
  },
  flaky: () => {
    const home = process.env.HOME || '';
    const ctr = home + '/.fake-flaky-count';
    let n = 0;
    try { n = Number(fs.readFileSync(ctr, 'utf8')) || 0; } catch { /* first call */ }
    if (n < 1) {
      fs.writeFileSync(ctr, '1');
      process.stderr.write('[400]: event: error\n');
      process.exit(1);
    }
    fs.appendFileSync('a.txt', 'ok-line\n');
    process.stdout.write('# Summary\nok');
  },
  overloaded: () => {
    process.stderr.write('[400]: event: error\n');
    process.exit(1);
  },
  sentinelquota: () => {
    const key = process.env.AIKIT_XAI_SENTINEL || '';
    process.stderr.write('quota exceeded for key ' + key + '\n');
    process.exit(1);
  },
  sentinelsplit: () => {
    const key = process.env.AIKIT_XAI_SENTINEL || '';
    const bearer = process.env.AIKIT_XAI_BEARER || '';
    const mid = Math.floor(key.length / 2);
    process.stderr.write(key.slice(0, mid));
    setTimeout(() => {
      process.stderr.write(key.slice(mid) + '\nBearer ' + bearer + '\n');
      process.exit(1);
    }, 50);
  },
  sentineloverlong: () => {
    const key = process.env.AIKIT_XAI_SENTINEL || '';
    process.stderr.write(key + 'x'.repeat(70000));
    process.exit(1);
  },
  'review-ok': () => { process.stdout.write('# Review\nok'); },
  'review-commit': () => {
    fs.appendFileSync('a.txt', 'commit-line\n');
    const r = spawnSync('git', ['add', 'a.txt'], { stdio: 'inherit' });
    if (r.status !== 0) process.exit(r.status || 1);
    const c = spawnSync('git', ['commit', '-q', '-m', 'fake'], { stdio: 'inherit' });
    if (c.status !== 0) process.exit(c.status || 1);
    fs.writeFileSync((process.env.HOME || '') + '/.fake-committed', '1');
    process.stdout.write('# Review\ncommitted');
  },
  'review-edit': () => {
    fs.appendFileSync('a.txt', 'edit-line\n');
    process.stdout.write('# Review\nedited');
  },
  'echo-len': () => { process.stdout.write(String(Buffer.byteLength(stdinBuf, 'utf8'))); },
  'review-gitfail': () => {
    fs.writeFileSync((process.env.HOME || '') + '/.fake-git-fail', '1');
    process.stdout.write('# Review\nok');
  },
  'review-event400': () => {
    process.stderr.write('[400]: event: error\n');
    process.exit(1);
  },
  'review-flaky-edit': () => {
    const home = process.env.HOME || '';
    const ctr = home + '/.fake-review-flaky-count';
    let n = 0;
    try { n = Number(fs.readFileSync(ctr, 'utf8')) || 0; } catch { /* first */ }
    if (n < 1) {
      fs.writeFileSync(ctr, '1');
      fs.appendFileSync('a.txt', 'flaky-edit\n');
      process.stderr.write('[400]: event: error\n');
      process.exit(1);
    }
    process.stdout.write('# Review\nok');
  },
  'outer-race': () => {
    fs.writeFileSync((process.env.HOME || '') + '/.fake-git-hang', '1');
    const gc = spawn(process.execPath, ['-e', 'process.on("SIGTERM",()=>{setInterval(()=>process.stderr.write("gc-late"+String.fromCharCode(10)),100);});while(true){}'], { stdio: ['ignore', 'pipe', 'pipe'] });
    gc.stderr.on('data', (d) => process.stderr.write(d));
    recordGc(gc.pid);
    process.on('SIGTERM', () => {
      process.stderr.write('gc-late\n');
      try { process.kill(gc.pid, 'SIGTERM'); } catch { /* esrch */ }
    });
    setInterval(() => {}, 1 << 30);
  },
};
const modeIdx = args.indexOf('--mode');
if (modeIdx >= 0 && args[modeIdx + 1] === 'rpc') {
  log('pi rpc');
  if (process.env.FAKE_PI_LIST === 'hang') {
    setInterval(() => {}, 1 << 30);
  } else {
    if (process.env.FAKE_PI_LIST === 'broken') { console.log('not json'); process.exit(0); }
    if (process.env.FAKE_PI_LIST === 'fail') process.exit(1);
    const models = Object.keys(FAKE_MODES).map((k) => ({ provider: 'fake', id: k }));
    console.log(JSON.stringify({ id: '1', type: 'response', command: 'get_available_models', success: true, data: { models } }));
    process.exit(0);
  }
} else {
log('pi ' + (fakeMode || model));
process.stdin.setEncoding('utf8');
process.stdin.on('data', (d) => { stdinBuf += d; });
process.stdin.on('end', () => {
  if (process.env.FAKE_SIDS) {
    const sid = argOf('--session-id');
    const head = 'You were interrupted by a provider error.';
    let kind = 'other';
    if (stdinBuf.startsWith(head)) {
      kind = stdinBuf.includes('\n\n') ? 'resume-plus' : 'resume';
    } else if (stdinBuf.includes(head)) {
      kind = 'resume-plus';
    } else if (stdinBuf.length) kind = 'prompt';
    fs.appendFileSync(process.env.FAKE_SIDS, sid + ' ' + kind + '\n');
  }
  const fn = FAKE_MODES[fakeMode];
  if (!fn) process.exit(1);
  fn();
  if (!STICKY_FAKE.has(fakeMode)) process.exit(0);
});
}
`);
}

function writeFakeCursor(binDir) {
  writeExe(binDir, 'cursor-agent', '', String.raw`
const sub = process.argv.slice(2);
if (sub[0] === 'models') {
  log('cursor-agent models');
  console.log('Available models');
  console.log('');
  if (process.env.FAKE_CURSOR_LIST === 'nameless') {
    console.log('\x1b[1mauto\x1b[0m (current, default)');
    console.log('composer-2.5 - Composer 2.5');
  } else if (process.env.FAKE_CURSOR_LIST !== 'empty') {
    for (const id of [
      'fake-ok-cursor', 'fake-err-cursor', 'fake-event400-cursor', 'fake-flaky-cursor', 'fake-dirty400-cursor', 'fake-latedirty-cursor', 'composer-2.5',
    ]) console.log(id + ' - label');
  }
  process.exit(0);
}
const model = argOf('--model');
log('cursor-agent ' + model);
process.stdin.on('data', () => {}).on('end', () => {
  if (model === 'fake-err-cursor') {
    console.log(JSON.stringify({ type: 'result', is_error: true, result: '401 unauthorized', session_id: 'c2' }));
    process.exit(0);
  }
  if (model === 'fake-event400-cursor') {
    process.stderr.write('[400]: event: error\n');
    process.exit(1);
  }
  if (model === 'fake-latedirty-cursor') {
    const ctr = process.env.HOME + '/.fake-latedirty-cursor-count';
    const n = fs.existsSync(ctr) ? Number(fs.readFileSync(ctr, 'utf8')) : 0;
    fs.writeFileSync(ctr, String(n + 1));
    if (n >= 1) fs.appendFileSync('a.txt', 'late-dirty\n');
    process.stderr.write('[400]: event: error\n');
    process.exit(1);
  }
  if (model === 'fake-dirty400-cursor') {
    fs.appendFileSync('a.txt', 'dirty\n');
    process.stderr.write('[400]: event: error\n');
    process.exit(1);
  }
  if (model === 'fake-flaky-cursor') {
    const ctr = process.env.HOME + '/.fake-flaky-cursor-count';
    const n = fs.existsSync(ctr) ? Number(fs.readFileSync(ctr, 'utf8')) : 0;
    fs.writeFileSync(ctr, String(n + 1));
    log('cursor-agent flaky resume=' + (argOf('--resume') || '-'));
    if (n === 0) {
      process.stderr.write('503 Service Unavailable\n');
      console.log(JSON.stringify({ type: 'result', is_error: true, result: '503 Service Unavailable', session_id: 'c3' }));
      process.exit(1);
    }
    console.log(JSON.stringify({ type: 'result', subtype: 'success', is_error: false, result: '## Summary\nok', session_id: 'c3' }));
    process.exit(0);
  }
  fs.appendFileSync('a.txt', 'cursor\n');
  console.log(JSON.stringify({ type: 'result', subtype: 'success', is_error: false, result: '## Summary\nok', session_id: 'c1' }));
});
`);
}

function writeFakeOpencode(binDir) {
  writeExe(binDir, 'opencode', '', String.raw`
const sub = process.argv.slice(2);
if (sub[0] === 'models') {
  log('opencode models');
  console.log('fake/ok');
  process.exit(0);
}
const model = argOf('--model');
log('opencode ' + model);
process.stdin.on('data', () => {}).on('end', () => {
  if (model === 'fake/ok' && ['upstream-event', 'two-events'].includes(process.env.FAKE_OPENCODE_MODE)) {
    const acct = 'acct-' + process.pid;
    const token = process.env.AIKIT_XAI_SENTINEL || 'sentinel';
    const events = process.env.FAKE_OPENCODE_MODE === 'upstream-event'
      ? [JSON.stringify({ type: 'error', sessionID: 'ses_fake', error: { type: 'provider.quota', status: 429, message: 'The usage limit has been reached', response: { body: JSON.stringify({ accountId: acct, api_key: token, retry_after: 30 }) } } })]
      : [JSON.stringify({ type: 'error', sessionID: 'ses_fake', error: { type: 'provider.quota', status: 429, message: 'unrelated event' } }), JSON.stringify({ type: 'error', sessionID: 'ses_fake', error: { type: 'provider.quota', status: 429, message: 'The usage limit has been reached', response: { body: JSON.stringify({ retry_after: 120 }) } } })];
    for (const event of events) console.log(event);
    process.exit(1);
  }
  fs.appendFileSync('a.txt', 'oc\n');
  const lines = [
    JSON.stringify({ type: 'text', sessionID: 'ses_1', part: { id: 'p1', messageID: 'm1', type: 'text', text: 'Plan first.' } }),
    JSON.stringify({ type: 'tool_use', sessionID: 'ses_1', part: { type: 'tool', tool: 'bash' } }),
    JSON.stringify({ type: 'text', sessionID: 'ses_1', part: { id: 'p2', messageID: 'm2', type: 'text', text: '## Summary\ndone' } }),
  ];
  for (const l of lines) console.log(l);
});
`);
}

function writeFakeCopilot(binDir) {
  writeExe(binDir, 'copilot', '', String.raw`
const model = argOf('--model');
const mode = model.startsWith('fake-') ? model.slice(5) : '';
log('copilot ' + mode);
const seen = process.env.FAKE_COPILOT_SEEN;
const tokenNames = ['COPILOT_GITHUB_TOKEN', 'GH_TOKEN', 'GITHUB_TOKEN'];
let stdinFifo = false;
let stdinBytes = 0;
let stdinError = null;
try {
  stdinFifo = fs.fstatSync(0).isFIFO();
  stdinBytes = fs.readFileSync(0).length;
} catch (e) {
  stdinError = String(e && e.code || e && e.message || e);
}
const tokens = tokenNames.filter((name) => process.env[name]);
if (seen) {
  fs.writeFileSync(seen, JSON.stringify({
    argv: process.argv.slice(2), prompt: argOf('-p'),
    promptBytes: Buffer.byteLength(argOf('-p')), stdinFifo, stdinBytes, stdinError,
    tokens, allowAll: process.env.COPILOT_ALLOW_ALL !== undefined,
  }));
}
if (!tokens.length) {
  process.stderr.write('Error: not logged in. Run copilot login or set COPILOT_GITHUB_TOKEN.\n');
  process.exit(1);
}
if (mode === 'event400') {
  process.stderr.write('[400]: event: error\n');
  process.exit(1);
}
fs.appendFileSync('a.txt', 'ok-line\n');
process.stderr.write('copilot: using token ' + process.env[tokens[0]] + '\n');
process.stdout.write('# Summary\nok');
`);
}

function writeFakeClaude(binDir) {
  writeExe(binDir, 'claude', '', String.raw`
log('claude ' + argOf('--model'));
process.stdin.on('data', () => {}).on('end', () => {
  console.log(JSON.stringify({ type: 'result', result: 'ok', session_id: 'x', is_error: false }));
  process.exit(0);
});
`);
}

function writeFakeCodex(binDir) {
  writeExe(binDir, 'codex', '', String.raw`
const sub = process.argv.slice(2);
if (sub[0] === 'debug' && sub[1] === 'models') {
  log('codex models');
  const listed = [
    'fake-ok-codex', 'fake-retry-codex', 'fake-limit-codex',
    'fake-error-then-ok-codex', 'fake-bare-error-hang-codex', 'fake-event400-codex',
  ];
  console.log(JSON.stringify({ models: listed.map((slug) => ({ slug, visibility: 'list' })) }));
  process.exit(0);
}
const outFile = argOf('-o');
if (sub[0] === 'exec' && sub[1] === 'resume') log('codex-resume ' + argOf('-m'));
log('codex ' + argOf('-m'));
process.stdin.on('data', () => {}).on('end', () => {
  const model = argOf('-m');
  if (model !== 'fake-event400-codex') fs.appendFileSync('a.txt', 'cx\n');
  if (outFile) fs.writeFileSync(outFile, '## Summary\nok');
  console.log(JSON.stringify({ type: 'thread.started', thread_id: 't1' }));
  const limitText = 'You\u2019ve hit your usage limit. Upgrade to Pro, or try again later.';
  if (model === 'fake-retry-codex') {
    console.log(JSON.stringify({ type: 'error', message: 'stream disconnected; retrying 1/5' }));
    console.log(JSON.stringify({ type: 'turn.completed' }));
  } else if (model === 'fake-limit-codex') {
    console.log(JSON.stringify({ type: 'error', message: limitText }));
    console.log(JSON.stringify({ type: 'turn.failed', error: { message: limitText } }));
    setInterval(() => {}, 1 << 30);
    return;
  } else if (model === 'fake-error-then-ok-codex') {
    console.log(JSON.stringify({ type: 'error', message: limitText }));
    setTimeout(() => {
      if (outFile) fs.writeFileSync(outFile, '## Summary\nok');
      console.log(JSON.stringify({ type: 'turn.completed' }));
      process.exit(0);
    }, 500);
    return;
  } else if (model === 'fake-bare-error-hang-codex') {
    console.log(JSON.stringify({ type: 'error', message: limitText }));
    setInterval(() => {}, 1 << 30);
    return;
  } else if (model === 'fake-event400-codex') {
    console.log(JSON.stringify({
      type: 'turn.failed', error: { message: 'stream disconnected before completion' },
    }));
    setTimeout(() => process.exit(1), 50);
    return;
  }
});
`);
}

const STATUS_HEAD_RE = new RegExp(
  '^(.* action=stop)(?: (route=\\S+ rule=\\S+ pattern=\\S+))?' +
  '(?: (attempts=\\S+ cycles=\\S+))?(?: (retry_after_s=\\S+ cycle=\\S+))?(?: upstream=\\S+)?$',
);

function statusLineOk(stderr, pattern) {
  const lines = stderr.split('\n').filter((l) => l.trim());
  const hits = lines.filter((l) => l.startsWith('AIKIT-XAI '));
  if (hits.length !== 1) return `expected one AIKIT-XAI line, got ${hits.length}`;
  if (hits[0] !== lines[lines.length - 1]) return 'AIKIT-XAI line is not last stderr line';
  const parts = STATUS_HEAD_RE.exec(hits[0]);
  if (!parts) return `status line mismatch: ${hits[0]}`;
  if (!pattern.test(parts[1])) return `status line mismatch: ${hits[0]}`;
  return null;
}

function retryLine(r, fragment) {
  const lines = (r.stderr || '').split('\n').filter((l) => l.startsWith('cross-ai: retry '));
  if (lines.length !== 1) return `retry lines=${lines.length}`;
  return lines[0].includes(fragment) ? null : lines[0];
}

function statusTail(stderr) {
  const line = stderr.split('\n').filter((l) => l.startsWith('AIKIT-XAI ')).pop() || '';
  const parts = STATUS_HEAD_RE.exec(line);
  if (!parts || !parts[2]) return null;
  const tail = [parts[2], parts[3], parts[4]].filter(Boolean).join(' ');
  const tok = Object.fromEntries(tail.split(' ').map((t) => t.split('=')));
  return {
    route: tok.route, rule: tok.rule, pattern: tok.pattern,
    attempts: tok.attempts, cycles: tok.cycles,
    retry_after_s: tok.retry_after_s, cycle: tok.cycle,
  };
}

function pidAlive(pid) {
  try { process.kill(pid, 0); } catch { return false; }
  try { return !/^\d+ \(.*\) Z/.test(fs.readFileSync(`/proc/${pid}/stat`, 'utf8')); } catch { return true; }
}

// Self-test load scaling (D-10): every ceiling is multiplied by one factor read once per run
// (load per CPU clamped to 1..4); floors and the real run limits are never scaled.
let selfTestLoadFactor = 1;
// The signal-to-exit ceiling of a case, before scaling.
const SELF_TEST_SIGNAL_EXIT_MS = 2900;

function loadFactor(perCpu) {
  return Number.isFinite(perCpu) && perCpu > 0 ? Math.min(4, Math.max(1, perCpu)) : 1;
}

function measuredLoadPerCpu() {
  // An injected load per CPU, read only by the self-test.
  if (process.env.AIKIT_XAI_SELFTEST_LOAD !== undefined) return Number(process.env.AIKIT_XAI_SELFTEST_LOAD);
  const cpus = typeof os.availableParallelism === 'function' ? os.availableParallelism() : os.cpus().length;
  return os.loadavg()[0] / cpus;
}

function scaledMs(ms, factor = selfTestLoadFactor) {
  return Math.ceil(ms * factor);
}

// A SIGKILLed descendant can outlive the runner by a few ms under load (or sit as an unreaped
// zombie), so "still alive" means alive after a bounded wait, not at the first probe.
function pidLingers(pid, ms = scaledMs(3000)) {
  const deadline = Date.now() + ms;
  while (pidAlive(pid)) {
    if (Date.now() >= deadline) return true;
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 50);
  }
  return false;
}

// Linux: every self-test process runs with its cwd under the self-test tmp dir.
const HAVE_PROC = fs.existsSync('/proc/self/cwd');
function pidsUnder(root) {
  if (!HAVE_PROC) return [];
  const out = [];
  for (const n of fs.readdirSync('/proc')) {
    if (!/^\d+$/.test(n) || Number(n) === process.pid) continue;
    let cwd = '';
    try { cwd = fs.readlinkSync(`/proc/${n}/cwd`); } catch { continue; }
    if (cwd === root || cwd.startsWith(root + path.sep)) out.push(Number(n));
  }
  return out;
}

function recordedPids(pidFile) {
  const out = {};
  for (const line of readOr(pidFile, '').split('\n')) {
    const [name, pid] = line.split(' ');
    if (Number(pid) > 0) (out[name] ||= []).push(Number(pid));
  }
  return out;
}

// Kill every process a case left behind: its runner group, the fakes' own groups and any
// escaped grandchild. On Linux only pids whose cwd is under `root` are touched (no pid reuse
// hits); elsewhere the recorded pids are the best available list.
function reapUnder(root, pidFiles) {
  const pids = new Set(pidsUnder(root));
  if (!HAVE_PROC) for (const f of pidFiles) for (const list of Object.values(recordedPids(f))) list.forEach((p) => pids.add(p));
  for (const pid of pids) {
    for (const target of [-pid, pid]) {
      try { process.kill(target, 'SIGKILL'); } catch { /* gone or not a group */ }
    }
  }
}

function waitFor(pred, ms) {
  return new Promise((resolve) => {
    const deadline = Date.now() + ms;
    const tick = () => {
      if (pred()) return resolve(true);
      if (Date.now() >= deadline) return resolve(false);
      setTimeout(tick, 25);
    };
    tick();
  });
}

const caseRunners = new Set();

// One harness for every case: the runner gets its own process group, so a hung or failing
// case can always be reaped as a unit.
function runCaseProcess(spec, c) {
  return new Promise((resolve) => {
    const t0 = Date.now();
    const child = spawn(process.execPath, [c.copy, ...(spec.args || [])], {
      cwd: c.repo, env: c.env, stdio: ['pipe', 'pipe', 'pipe'], detached: true,
    });
    caseRunners.add(child);
    let stdout = '';
    let stderr = '';
    let sigMs = null;
    let code = null;
    let done = false;
    const end = (reason) => {
      if (done) return;
      done = true;
      clearTimeout(hard);
      caseRunners.delete(child);
      resolve({ reason, status: code, stdout, stderr, elapsedMs: Date.now() - t0, sinceSignalMs: sigMs === null ? null : Date.now() - sigMs });
    };
    const hardMs = scaledMs(30000);
    const hard = setTimeout(() => end(`case hung past ${hardMs}ms`), hardMs);
    child.stdout.on('data', (d) => { stdout += d.toString('utf8'); });
    child.stderr.on('data', (d) => {
      stderr += d.toString('utf8');
    });
    child.stdin.on('error', () => { /* runner exited early */ });
    child.stdin.end(spec.stdin ?? 'prompt\n');
    if (spec.closeStderr) waitFor(() => spec.closeStderr(c), scaledMs(10000)).then(() => child.stderr.destroy());
    if (spec.signal) {
      waitFor(() => spec.signal.when(c, stderr), scaledMs(10000)).then((ready) => {
        if (done) return;
        if (!ready) { end('signal precondition never met'); return; }
        sigMs = Date.now();
        try { child.kill(spec.signal.sig); } catch { /* exited */ }
        if (spec.signal.again) setTimeout(() => { try { child.kill(spec.signal.again); } catch { /* exited */ } }, 200);
      });
    }
    child.on('exit', (exitCode) => {
      code = exitCode;
      Promise.race([new Promise((r) => child.on('close', r)), sleep(scaledMs(2000))]).then(() => end(null));
    });
  });
}

// A second invocation of the same copy, sharing the case's XDG state dir and HOME.
async function runTwice(spec, c, second) {
  const first = await runCaseProcess({ ...spec, args: c.args || spec.args }, c);
  if (first.reason) return { reason: `first: ${first.reason}` };
  if (first.status !== spec.exit) return { reason: `first exit ${first.status}` };
  const calls1 = fs.existsSync(c.calls)
    ? fs.readFileSync(c.calls, 'utf8').trim().split('\n').filter(Boolean) : [];
  fs.writeFileSync(c.calls, '');
  const again = await runCaseProcess({
    ...spec, args: second.args || c.args || spec.args, stdin: second.stdin ?? spec.stdin, exit: second.exit,
  }, c);
  if (again.reason) return { reason: `second: ${again.reason}` };
  if (again.status !== second.exit) return { reason: `second exit ${again.status}` };
  const calls2 = fs.existsSync(c.calls)
    ? fs.readFileSync(c.calls, 'utf8').trim().split('\n').filter(Boolean) : [];
  return { first, again, calls1, calls2, ...c };
}

async function checkCase(spec, c) {
  if (spec.second) {
    const both = await runTwice(spec, c, spec.second);
    if (both.reason) return both.reason;
    const err = statusLineOk(both.again.stderr || '', spec.second.status);
    if (err) return `second: ${err}`;
    return spec.check ? spec.check(both, { ...c, calls: both.calls2 }) : null;
  }
  const r = await runCaseProcess({ ...spec, args: c.args || spec.args }, c);
  if (r.reason) return r.reason;
  if (r.status !== spec.exit) return `exit ${r.status} expected ${spec.exit}`;

  if (!spec.closeStderr) {
    const err = statusLineOk(r.stderr || '', spec.status);
    if (err) return err;
  }
  if (spec.signal && r.sinceSignalMs > scaledMs(spec.signal.withinMs ?? SELF_TEST_SIGNAL_EXIT_MS)) return `exit ${r.sinceSignalMs}ms after the signal`;
  const callLines = fs.existsSync(c.calls) ? fs.readFileSync(c.calls, 'utf8').trim().split('\n').filter(Boolean) : [];
  const ctx = { ...c, calls: callLines, elapsedMs: r.elapsedMs, pids: recordedPids(c.pidFile) };
  return spec.check ? spec.check(r, ctx) : null;
}

function nestedRepoSetup(c) {
  const sub = path.join(c.repo, 'sub');
  fs.mkdirSync(sub);
  fs.writeFileSync(path.join(sub, 'f.txt'), 'base\n');
  for (const [cwd, argv] of [[sub, ['init', '-q']], [sub, ['add', 'f.txt']], [sub, ['commit', '-q', '-m', 's']],
    [c.repo, ['add', 'sub']], [c.repo, ['commit', '-q', '-m', 'gitlink']]]) {
    const g = spawnSync('git', argv, { cwd, env: c.env, encoding: 'utf8' });
    if (g.status !== 0) return `setup git ${argv.join(' ')}: ${g.stderr}`;
  }
  return null;
}

function ignoredFileSetup(c) {
  fs.writeFileSync(path.join(c.repo, '.gitignore'), 'ign/\n*.local\n');
  fs.mkdirSync(path.join(c.repo, 'ign'));
  fs.writeFileSync(path.join(c.repo, 'ign', 'x.txt'), 'seed\n');
  fs.writeFileSync(path.join(c.repo, 'x.local'), 'seed\n');
  for (const argv of [['add', '.gitignore'], ['commit', '-q', '-m', 'ignore']]) {
    const g = spawnSync('git', argv, { cwd: c.repo, env: c.env, encoding: 'utf8' });
    if (g.status !== 0) return `setup git ${argv.join(' ')}: ${g.stderr}`;
  }
  return null;
}

// Fails unless each named recorded process (or gc.pid) existed and is dead now.
function deadCheck(ctx, names) {
  for (const name of names) {
    const list = ctx.pids[name] || [];
    if (!list.length) return `no ${name} pid recorded`;
    for (const pid of list) if (pidLingers(pid)) return `${name} ${pid} still alive`;
  }
  return null;
}

// Hard-tier no-switch rule (owner rule, SPEC R3): every child the case spawned named the same
// CLI and model. The `rpc` listing is the runner's own preflight, not a model call; the fake
// records its mode label (`pi event400`), so the fake/ prefix is dropped here.
function sameLane(ctx, cli, model) {
  const label = String(model || '').replace(/^fake\//, '');
  const bad = ctx.calls.filter((l) => l !== `${cli} rpc` && l !== `${cli} ${label}`);
  return bad.length ? `other calls: ${bad.join('|')}` : null;
}

// The prior hard-tier record a case starts from (25.1-03): first attempted a minute ago, due
// a second ago, at `cycle` with class `cls`, in the kind's file. `extra` overrides fields.
function writePriorRecord(c, cli, model, kind, cls, cycle, extra = {}) {
  const minute = 60 * 1000;
  const file = caseCycleFile(c, cli, model, kind);
  writeCycleState(file, {
    first_seen: Date.now() - minute, last_attempt_at: Date.now() - minute,
    cycle, attempts: 6 * (cycle + 1), last_sid: null, task_digest: 'other',
    retry_after_s: 600, due_at: Date.now() - 1000, class: cls, ...extra,
  });
  return file;
}

// The shared hard_waits list of the 25.1-03 hard-tier cases: real waits, never slept.
const HARD_TIER_RETRY = Object.freeze({
  max_retries: 0, session_resets: 0, hard_waits_s: [600, 900, 1800],
});

async function runSelfTestCase(tmp, spec) {
  if (typeof spec.pure === 'function') return spec.pure();
  const repo = path.join(tmp, `r-${spec.name}`);
  fs.mkdirSync(repo, { recursive: true });
  const gitEnv = hermeticEnv(tmp, { HOME: path.join(tmp, 'home-git') });
  spawnSync('git', ['init', '-q'], { cwd: repo, env: gitEnv });
  fs.writeFileSync(path.join(repo, 'a.txt'), 'base\n');
  spawnSync('git', ['add', 'a.txt'], { cwd: repo, env: gitEnv });
  spawnSync('git', ['commit', '-q', '-m', 'init'], { cwd: repo, env: gitEnv });
  if (spec.planningConfig != null) {
    fs.mkdirSync(path.join(repo, '.planning'), { recursive: true });
    fs.writeFileSync(path.join(repo, '.planning', 'config.json'), JSON.stringify(spec.planningConfig));
  }
  if (spec.workstream) {
    const wdir = path.join(repo, '.planning', 'workstreams', spec.workstream.ws);
    fs.mkdirSync(wdir, { recursive: true });
    if (spec.workstream.config) fs.writeFileSync(path.join(wdir, 'config.json'), JSON.stringify(spec.workstream.config));
  }
  for (const [rel, body] of Object.entries(spec.files || {})) {
    fs.mkdirSync(path.dirname(path.join(repo, rel)), { recursive: true });
    fs.writeFileSync(path.join(repo, rel), JSON.stringify(body));
  }
  const home = path.join(tmp, `home-${spec.name}`);
  fs.mkdirSync(home, { recursive: true });
  const calls = path.join(tmp, `calls-${spec.name}.log`);
  const pidFile = path.join(tmp, `pids-${spec.name}.log`);
  const copy = writeCopy(tmp, spec.name, spec.config || {});
  const env = hermeticEnv(tmp, {
    HOME: home, XDG_CONFIG_HOME: path.join(home, '.config'),
    XDG_STATE_HOME: path.join(home, '.local', 'state', spec.name),
    FAKE_CALLS: calls, FAKE_PIDS: pidFile,
    FAKE_SIDS: path.join(tmp, `sids-${spec.name}.log`),
    AIKIT_XAI_SENTINEL: 'sk-aikit-SENTINEL-' + process.pid,
    AIKIT_XAI_BEARER: 'brtok-' + process.pid,
    ...(spec.fakeOpencodeMode ? { FAKE_OPENCODE_MODE: spec.fakeOpencodeMode } : {}),
    ...(spec.env || {}),
  });
  const c = { tmp, repo, home, calls, pidFile, copy, env };
  let reason;
  try {
    reason = (spec.setup && spec.setup(c)) || await checkCase(spec, c);
  } finally {
    reapUnder(repo, [pidFile]);
  }
  if (!spec.expectFailure) return reason;
  if (!reason) return 'case was expected to fail';
  return spec.afterReap({ ...c, pids: recordedPids(pidFile) });
}

// Self-test mode owns SIGTERM/SIGINT/SIGHUP: reap every case process, drop the tmp dir, exit.
let selfTestRoot = null;
function selfTestAbort(code) {
  for (const child of caseRunners) killGroup(child, 'SIGKILL');
  if (selfTestRoot) {
    reapUnder(selfTestRoot, fs.readdirSync(selfTestRoot).filter((f) => f.startsWith('pids-')).map((f) => path.join(selfTestRoot, f)));
    fs.rmSync(selfTestRoot, { recursive: true, force: true });
  }
  process.exit(code);
}

async function blackBoxSelfTest() {
  OVERLAY_IDS = new Set();
  TABLE = mergeCatalog(PATTERNS, []);
  const gitBin = which('git');
  if (!gitBin) {
    process.stderr.write('self-test: git not found\n');
    return 1;
  }
  selfTestLoadFactor = loadFactor(measuredLoadPerCpu());
  process.stderr.write(`self-test load factor ${selfTestLoadFactor}\n`);
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'xai-st-'));
  selfTestRoot = tmp;
  try {
    const binDir = path.join(tmp, 'bin');
    fs.mkdirSync(binDir, { recursive: true });
    fs.symlinkSync(process.execPath, path.join(binDir, 'node'));
    writeGitWrapper(binDir, gitBin);
    const binNoCodex = path.join(tmp, 'bin-nocodex');
    fs.mkdirSync(binNoCodex, { recursive: true });
    writeFakePi(binDir);
    writeFakeCursor(binDir);
    writeFakeOpencode(binDir);
    writeFakeCodex(binDir);
    writeFakeClaude(binDir);
    writeFakeCopilot(binDir);
    for (const name of fs.readdirSync(binDir)) {
      if (name === 'codex') continue;
      const src = path.join(binDir, name);
      const dst = path.join(binNoCodex, name);
      if (!fs.existsSync(dst)) fs.symlinkSync(src, dst);
    }

    // D-09 self-tests: another CLI's `agent` first on PATH; `script` is what it runs.
    const otherAgentFirst = (c, name, script = '#!/bin/sh\nexit 0\n') => {
      const dir = path.join(c.tmp, name);
      fs.mkdirSync(dir);
      const other = path.join(dir, 'other-agent-1.0.52-linux-x86_64');
      fs.writeFileSync(other, script);
      fs.chmodSync(other, 0o755);
      for (const b of ['node', 'git']) fs.symlinkSync(path.join(c.tmp, 'bin', b), path.join(dir, b));
      fs.symlinkSync(other, path.join(dir, 'agent'));
      return dir;
    };
    const cwdCursorAgent = (c) => {
      fs.symlinkSync(path.join(c.tmp, 'bin', 'cursor-agent'), path.join(c.repo, 'agent'));
      spawnSync('git', ['add', 'agent'], { cwd: c.repo, env: c.env });
      spawnSync('git', ['commit', '-q', '-m', 'agent'], { cwd: c.repo, env: c.env });
    };

    const cases = [
      {
        name: 'ok',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 cli_rc=0 elapsed=\d+s out=\d+ tree=dirty action=stop$/,
        check: (r) => (r.stdout.includes('# Summary') ? null : 'stdout missing # Summary'),
      },
      {
        name: 'empty_stdin',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: '',
        exit: 2,
        status: /^AIKIT-XAI status=empty_stdin .* action=stop$/,
      },
      {
        name: 'no_model',
        args: ['--prefer', 'pi'],
        exit: 2,
        status: /^AIKIT-XAI status=no_model .* action=stop$/,
      },
      // U-4: a model id must not read as an option or carry shell/space characters.
      ...['--yolo', 'a b', 'x;rm'].map((model, i) => ({
        name: `bad-model-id-${i}`,
        args: ['--prefer', 'pi', '--model-pi', model],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* action=stop$/,
      })),
      ...['--yolo', 'a b', 'x;rm'].map((model, i) => ({
        name: `bad-model-flag-${i}`,
        args: ['--runtime', 'pi', '--model', model],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* action=stop$/,
      })),
      {
        name: 'model-flag-cursor-bracket',
        args: ['--runtime', 'cursor', '--model', 'fake-ok-cursor[effort=high]', '--print-argv'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const line = (r.stdout || '').split('\n').find((l) => l.startsWith('cursor\t'));
          if (!line) return 'missing argv line';
          const argv = JSON.parse(line.split('\t')[2]);
          return argv.includes('fake-ok-cursor[effort=high]') ? null : `argv=${JSON.stringify(argv)}`;
        },
      },
      {
        name: 'model-flag-cursor-bracket-order',
        args: ['--model', 'fake-ok-cursor[effort=high]', '--runtime', 'cursor', '--print-argv'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const line = (r.stdout || '').split('\n').find((l) => l.startsWith('cursor\t'));
          if (!line) return 'missing argv line';
          const argv = JSON.parse(line.split('\t')[2]);
          return argv.includes('fake-ok-cursor[effort=high]') ? null : `argv=${JSON.stringify(argv)}`;
        },
      },
      {
        name: 'model-flag-pi-thinking',
        args: ['--runtime', 'pi', '--model', 'fake/ok:high', '--print-argv'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const line = (r.stdout || '').split('\n').find((l) => l.startsWith('pi\t'));
          if (!line) return 'missing argv line';
          const argv = JSON.parse(line.split('\t')[2]);
          if (!argv.includes('fake/ok:high')) return `argv=${JSON.stringify(argv)}`;
          return argv.includes('--thinking') ? 'unexpected --thinking' : null;
        },
      },
      {
        // One case, three runtimes: --model works for opencode, codex and claude review.
        name: 'model-flag-each',
        args: ['--print-argv', '--runtime', 'opencode', '--model', 'fake/ok#fast'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: async (_r, ctx) => {
          const runs = [
            ['opencode', 'exec', 'fake/ok#fast'],
            ['codex', 'exec', 'fake-ok-codex'],
            ['claude', 'review', 'opus'],
          ];
          for (const [rt, mode, model] of runs) {
            const got = await runCaseProcess({
              args: ['--print-argv', '--runtime', rt, '--mode', mode, '--model', model],
            }, ctx);
            if (got.status !== 0) return `${rt} exit ${got.status}`;
            const line = (got.stdout || '').split('\n').find((l) => l.startsWith(`${rt}\t`));
            if (!line) return `missing ${rt} argv line`;
            const argv = JSON.parse(line.split('\t')[2]);
            if (!argv.includes(model)) return `${rt} argv=${JSON.stringify(argv)}`;
          }
          return null;
        },
      },
      ...[
        ['opencode', 'fake/ok#fast', 'exec'],
        ['codex', 'fake-ok-codex', 'exec'],
        ['claude', 'opus', 'review'],
      ].map(([rt, model, mode]) => ({
        name: `model-flag-each-${rt}`,
        args: ['--print-argv', '--runtime', rt, '--mode', mode, '--model', model],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const line = (r.stdout || '').split('\n').find((l) => l.startsWith(`${rt}\t`));
          if (!line) return 'missing argv line';
          const argv = JSON.parse(line.split('\t')[2]);
          return argv.includes(model) ? null : `argv=${JSON.stringify(argv)}`;
        },
      })),
      {
        name: 'model-and-alias',
        args: ['--runtime', 'pi', '--model', 'fake/ok', '--model-pi', 'fake/other', '--print-argv'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          if (!(r.stderr || '').includes('cross-ai: --model wins; ignored --model-pi fake/other')) {
            return 'missing --model wins note';
          }
          const line = (r.stdout || '').split('\n').find((l) => l.startsWith('pi\t'));
          const argv = JSON.parse(line.split('\t')[2]);
          if (!argv.includes('fake/ok')) return `argv=${JSON.stringify(argv)}`;
          return argv.includes('fake/other') ? 'alias model reached argv' : null;
        },
      },
      {
        name: 'model-invalid-pi-bare',
        args: ['--runtime', 'pi', '--model', 'glm'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
        check: (r) => {
          const line = (r.stderr || '').split('\n').find((l) => l.includes('must match'));
          if (!line || !line.includes('pi model glm must match')) return `line=${line}`;
          return line.includes(PI_MODEL_ID.source) ? null : 'message omits the pi grammar';
        },
      },
      {
        name: 'model-invalid-bracket-pi',
        args: ['--runtime', 'pi', '--model', 'fake/ok[x=1]'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
      },
      {
        // 25.1 WR-05: a colon that is not a thinking level is part of pi's model id.
        name: 'model-pi-colon-id',
        args: ['--runtime', 'pi', '--model', 'fake/ok:free', '--print-argv'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const line = (r.stdout || '').split('\n').find((l) => l.startsWith('pi\t'));
          if (!line) return 'missing argv line';
          return JSON.parse(line.split('\t')[2]).includes('fake/ok:free') ? null : line;
        },
      },
      {
        name: 'model-opencode-colon',
        args: ['--runtime', 'opencode', '--model', 'or/meta/llama:free', '--print-argv'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
      },
      {
        name: 'model-opencode-two-variants',
        args: ['--runtime', 'opencode', '--model', 'fake/ok#a#b', '--print-argv'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
      },
      {
        name: 'model-other-runtime-not-checked',
        args: [
          '--runtime', 'cursor', '--model-cursor', 'fake-ok-cursor', '--model-pi', 'glm',
          '--print-argv',
        ],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const line = (r.stdout || '').split('\n').find((l) => l.startsWith('cursor\t'));
          if (!line) return 'missing argv line';
          const argv = JSON.parse(line.split('\t')[2]);
          return argv.includes('fake-ok-cursor') ? null : `argv=${JSON.stringify(argv)}`;
        },
      },
      {
        name: 'pure-review-extras',
        pure: () => {
          const ctx = {
            cwd: '/tmp/x', sid: 'sid', outFile: '/tmp/x/out.md', cursorMode: 'ask',
            promptArg: '<prompt>',
          };
          const attacks = {
            codex: ['-s danger-full-access', '--sandbox=danger-full-access',
              '-c sandbox_mode="danger-full-access"', '--config x=y'],
            pi: ['-t bash', '--tools bash', '-e x.ts', '--extension x.ts', '--skill --tools'],
            opencode: ['--agent build', '--auto'],
            cursor: ['--force', '--mode agent'],
            claude: ['--permission-mode bypassPermissions', '--dangerously-skip-permissions'],
            copilot: ['--available-tools=bash', '--allow-tool shell', '--allow-all-tools'],
          };
          for (const [name, rt] of Object.entries(RUNTIMES)) {
            const formulas = [rt.review(name === 'cursor' ? 'm' : 'fake/m', ctx)];
            if (rt.resume) formulas.push(rt.resume('fake/m', ctx, 'sid', 'review'));
            for (const base of formulas) {
              if (reviewArgvProblem(base, base, rt.reviewExtras || [])) {
                return `${name} bare review formula refused`;
              }
              for (const extra of attacks[name]) {
                const argv = [...base, ...extra.split(' ')];
                const problem = reviewArgvProblem(argv, base, rt.reviewExtras || []);
                if (!problem) return `${name} accepted ${extra}`;
                if (!String(problem).includes(extra.split(' ')[0])) {
                  return `${name} ${extra} reason ${problem} omits the element`;
                }
              }
            }
          }
          const pi = RUNTIMES.pi.review('fake/ok', ctx);
          if (reviewArgvProblem([...pi, '--skill', 'skills/x/SKILL.md'], pi, ['--skill'])) {
            return 'pi --skill path refused';
          }
          if (reviewArgvProblem([...pi, '--skill=skills/x/SKILL.md'], pi, ['--skill'])) {
            return 'pi --skill=path refused';
          }
          return null;
        },
      },
      {
        // A check of the table itself. --trust is deliberately absent: cursor's review
        // baseline carries it, and it trusts the workspace rather than granting a tool.
        name: 'pure-profiles-read-only',
        pure: () => {
          const granting = ['--force', '--auto', '--yolo', '--allow-all', '--allow-all-paths',
            '--allow-all-urls', '--allow-all-tools', '--allow-tool', '--approve-mcps',
            '--dangerously-bypass-approvals-and-sandbox', '--dangerously-skip-permissions'];
          // --allow-all-tools is accepted in a review formula only beside an --available-tools=
          // allowlist whose names are all read-only: a wrong name then narrows, never widens.
          const readOnlyTools = new Set(['view', 'grep', 'rg', 'glob']);
          const confined = (argv) => {
            const list = argv.find((t) => String(t).startsWith('--available-tools='));
            if (!list) return false;
            return list.slice('--available-tools='.length).split(',')
              .every((one) => readOnlyTools.has(one));
          };
          const ctx = {
            cwd: '/tmp/x', sid: 'sid', outFile: '/tmp/x/out.md', cursorMode: 'ask',
            promptArg: '<prompt>',
          };
          for (const [name, rt] of Object.entries(RUNTIMES)) {
            const profiles = rt.profiles
              ? Object.entries(rt.profiles).filter(([p]) => p === 'review' || p === 'none')
              : [['review', []]];
            for (const [profile, flags] of profiles) {
              const argv = [...rt.review('m', { ...ctx, profileFlags: [] }), ...flags];
              const hit = granting.find((f) => argv.some((t) => t === f || t.startsWith(`${f}=`) || t.startsWith(`${f},`)));
              if (hit && !(hit === '--allow-all-tools' && confined(argv))) {
                return `${name} ${profile} grants ${hit}`;
              }
              const tools = argv.flatMap((t, i) => (t === '--tools' ? [argv[i + 1]] : []));
              for (const value of tools) {
                for (const one of String(value).split(',')) {
                  if (!['read', 'grep', 'find', 'ls'].includes(one)) {
                    return `${name} ${profile} --tools ${one}`;
                  }
                }
              }
            }
          }
          return null;
        },
      },
      {
        name: 'pure-model-grammar',
        pure: () => {
          const accept = [
            [PI_MODEL_ID, 'fake/ok:high'], [PI_MODEL_ID, 'router-env/my-coding:high'],
            [OPENCODE_MODEL_ID, 'fake/ok#fast'], [OPENCODE_MODEL_ID, 'or/meta/llama:free'],
            // 25.1 WR-05: a colon inside pi's model part is part of the id (Ollama tags).
            [PI_MODEL_ID, 'fake/ok:free'], [PI_MODEL_ID, 'ollama/qwen3:8b'],
            [PI_MODEL_ID, 'ollama/qwen3:8b:high'],
          ];
          const refuse = [
            [PI_MODEL_ID, 'glm'], [PI_MODEL_ID, 'fake/ok[x=1]'], [PI_MODEL_ID, 'ollama/:8b'],
            [OPENCODE_MODEL_ID, 'glm'], [OPENCODE_MODEL_ID, 'fake/ok#a#b'],
          ];
          for (const [re, id] of accept) if (!re.test(id)) return `${re} refused ${id}`;
          for (const [re, id] of refuse) if (re.test(id)) return `${re} accepted ${id}`;
          const rows = {
            pi: PI_MODEL_ID, opencode: OPENCODE_MODEL_ID, cursor: CURSOR_MODEL_ID,
            codex: MODEL_ID, claude: MODEL_ID,
          };
          for (const [name, re] of Object.entries(rows)) {
            if (RUNTIMES[name].modelId !== re) return `${name} modelId is not the declared regex`;
          }
          return null;
        },
      },
      {
        // SPEC R6: --prefer reads only its first entry; an ignored entry is a notice, never a
        // usage error, whatever it names.
        name: 'prefer-ignored-unknown-entry',
        args: ['--prefer', 'pi,nosuchcli', '--model-pi', 'fake/ok', '--print-argv'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => ((r.stderr || '').includes(
          'cross-ai: --prefer reads only its first entry (pi); ignored: nosuchcli') ? null : 'missing notice'),
      },
      {
        // With HOME and XDG_CONFIG_HOME unset, the user retry file is the account's own
        // ~/.config/ai-kit/cross-ai.json, never one relative to the working directory.
        name: 'pure-retry-user-config-without-home',
        pure: () => {
          const root = fs.mkdtempSync(path.join(os.tmpdir(), 'xai-home-'));
          const home = path.join(root, 'home');
          const work = path.join(root, 'work');
          for (const [dir, base] of [[home, 3], [work, 7]]) {
            fs.mkdirSync(path.join(dir, '.config', 'ai-kit'), { recursive: true });
            fs.writeFileSync(path.join(dir, '.config', 'ai-kit', 'cross-ai.json'),
              JSON.stringify({ cross_ai_retry: { base_s: base } }));
          }
          const savedHome = os.homedir;
          const savedLog = log;
          const savedCwd = process.cwd();
          os.homedir = () => home;
          log = () => {};
          try {
            process.chdir(work);
            const got = resolveRetry(work, {}).retry.base_s;
            return got === 3 ? null : `base_s=${got}`;
          } finally {
            process.chdir(savedCwd);
            os.homedir = savedHome;
            log = savedLog;
            fs.rmSync(root, { recursive: true, force: true });
          }
        },
      },
      {
        // A CLI that cannot be executed at spawn time (its interpreter is gone) is not_installed
        // with exit 127, as when it is missing from PATH, never a crash.
        name: 'spawn-enoent-not-installed',
        setup: (c) => {
          const dir = path.join(c.tmp, 'bin-enoent');
          fs.mkdirSync(dir);
          for (const b of ['node', 'git']) fs.symlinkSync(path.join(c.tmp, 'bin', b), path.join(dir, b));
          fs.writeFileSync(path.join(dir, 'pi'), '#!/nonexistent/interpreter\n');
          fs.chmodSync(path.join(dir, 'pi'), 0o755);
          c.env.PATH = dir;
          return null;
        },
        args: ['--runtime', 'pi', '--model', 'fake/ok'],
        config: { retry: { max_retries: 0, session_resets: 0 } },
        exit: 127,
        status: /^AIKIT-XAI status=not_installed cli=pi model=fake\/ok exit=127 .* action=stop$/,
      },
      {
        // A multi-byte character split across two pipe chunks is decoded whole (StringDecoder),
        // never as two U+FFFD.
        name: 'utf8-split-across-chunks',
        setup: (c) => {
          const dir = path.join(c.tmp, 'bin-utf8');
          fs.mkdirSync(dir);
          for (const b of ['node', 'git']) fs.symlinkSync(path.join(c.tmp, 'bin', b), path.join(dir, b));
          fs.writeFileSync(path.join(dir, 'pi'), '#!/usr/bin/env node\n' +
            "if (process.argv.includes('rpc')) process.exit(1);\n" +
            "const b = Buffer.from('caf\\u00e9 boom\\n');\n" +
            'process.stderr.write(b.subarray(0, 4));\n' +
            'setTimeout(() => { process.stderr.write(b.subarray(4)); process.exitCode = 1; }, 150);\n');
          fs.chmodSync(path.join(dir, 'pi'), 0o755);
          c.env.PATH = dir;
          return null;
        },
        args: ['--runtime', 'pi', '--model', 'fake/ok'],
        config: { retry: { max_retries: 0, session_resets: 0 } },
        exit: 1,
        status: /^AIKIT-XAI status=crash cli=pi model=fake\/ok exit=1 .* action=stop$/,
        check: (r) => {
          const err = r.stderr || '';
          if (err.includes('\uFFFD')) return 'split character decoded as U+FFFD';
          return err.includes('caf\u00e9 boom') ? null : 'relayed line missing';
        },
      },
      {
        name: 'unknown_prefer',
        args: ['--prefer', 'nosuchcli', '--model-nosuchcli', 'x'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* action=stop$/,
      },
      ...['pi', 'cursor', 'opencode', 'codex'].flatMap((rt) => {
        const model = rt === 'pi' ? 'fake/ok' : rt === 'cursor' ? 'fake-ok-cursor' : rt === 'opencode' ? 'fake/ok' : 'fake-ok-codex';
        const flag = `--model-${rt}`;
        return [
          {
            name: `argv-exec-${rt}`,
            args: ['--print-argv', '--mode', 'exec', '--prefer', rt, flag, model],
            exit: 0,
            status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
            check: (r, ctx) => {
              const line = (r.stdout || '').split('\n').find((l) => l.startsWith(rt + '\t'));
              if (!line) return 'missing argv line';
              const argv = JSON.parse(line.split('\t')[2]);
              const must = {
                pi: ['-p'], cursor: ['--trust', '--force', 'disabled'], opencode: ['--auto', '--standalone'],
                codex: ['--dangerously-bypass-approvals-and-sandbox'],
              }[rt];
              for (const f of must) if (!argv.includes(f)) return `exec argv missing ${f}`;
              if (!argv.includes(model)) return 'model missing from argv';
              if (argv.some((t) => /\s/.test(t))) return 'whitespace token';
              return null;
            },
          },
          {
            name: `argv-review-${rt}`,
            args: ['--print-argv', '--mode', 'review', '--prefer', rt, flag, model],
            exit: 0,
            status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
            check: (r) => {
              const line = (r.stdout || '').split('\n').find((l) => l.startsWith(rt + '\t'));
              if (!line) return 'missing argv line';
              const argv = JSON.parse(line.split('\t')[2]);
              const never = ['--force', '--auto', '--dangerously-bypass-approvals-and-sandbox'];
              for (const f of never) if (argv.includes(f)) return `review argv has ${f}`;
              if (rt === 'opencode' && !argv.includes('--standalone')) return 'review argv missing --standalone';
              if (rt === 'pi') {
                for (const f of ['--tools', 'read,grep,find,ls', '--no-mcp', '--no-context-files']) {
                  if (!argv.includes(f)) return `review argv missing ${f}`;
                }
              }
              if (!argv.includes(model)) return 'model missing';
              return null;
            },
          },
        ];
      }),
      {
        name: 'parser-cursor',
        args: ['--prefer', 'cursor', '--model-cursor', 'fake-ok-cursor'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=dirty action=stop$/,
        check: (r) => (r.stdout === '## Summary\nok\n' ? null : `stdout=${JSON.stringify(r.stdout)}`),
      },
      {
        name: 'parser-opencode',
        args: ['--prefer', 'opencode', '--model-opencode', 'fake/ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=dirty action=stop$/,
        check: (r, ctx) => {
          if (r.stdout !== '## Summary\ndone\n') return `stdout=${JSON.stringify(r.stdout)}`;
          const mi = ctx.calls.indexOf('opencode models');
          const ri = ctx.calls.findIndex((l) => l.startsWith('opencode fake/'));
          if (mi < 0 || ri < 0 || mi > ri) return `calls=${ctx.calls.join('|')}`;
          return null;
        },
      },
      {
        name: 'parser-codex',
        args: ['--prefer', 'codex', '--model-codex', 'fake-ok-codex'],
        config: { prefer: ['codex'] },
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=dirty action=stop$/,
        check: (r, ctx) => {
          if (r.stdout !== '## Summary\nok\n') return `stdout=${JSON.stringify(r.stdout)}`;
          const mi = ctx.calls.indexOf('codex models');
          const ri = ctx.calls.findIndex((l) => l.startsWith('codex fake-'));
          if (mi < 0 || ri < 0 || mi > ri) return `calls=${ctx.calls.join('|')}`;
          return null;
        },
      },
      {
        // A recovered stream error before turn.completed is not a failure.
        name: 'parser-codex-recovered',
        args: ['--prefer', 'codex', '--model-codex', 'fake-retry-codex'],
        config: { prefer: ['codex'] },
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=codex model=fake-retry-codex exit=0 .* tree=dirty action=stop$/,
      },
      {
        name: 'parser-pi-ansi',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ansi'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=dirty action=stop$/,
        check: (r) => (r.stdout === 'Done.\n\n## Summary\nC# is fine. Use ## inline\n' ? null : `stdout=${JSON.stringify(r.stdout)}`),
      },
      {
        name: 'quote',
        args: ['--prefer', 'pi', '--model-pi', 'fake/quote'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/quote exit=0 cli_rc=0 elapsed=\d+s out=\d+ tree=dirty action=stop$/,
      },
      {
        name: 'okwarn',
        args: ['--prefer', 'pi', '--model-pi', 'fake/okwarn'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/okwarn exit=0 cli_rc=0 elapsed=\d+s out=\d+ tree=dirty action=stop$/,
        check: (r) => (r.stdout === '# Summary\nok\n' ? null : `stdout=${JSON.stringify(r.stdout)}`),
      },
      {
        // WR-01: a large answer and stderr through pipes arrive whole, status line last.
        name: 'big-pipe',
        args: ['--prefer', 'pi', '--model-pi', 'fake/big'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/big exit=0 .* tree=dirty action=stop$/,
        check: (r) => (r.stdout === `# Summary\n${'y'.repeat(300000)}\n` ? null : `stdout ${r.stdout.length} bytes`),
      },
      {
        // WR-02: the stderr reader goes away mid-run; the runner must still finish the run.
        name: 'stderr-closed',
        args: ['--prefer', 'pi', '--model-pi', 'fake/slowok'],
        config: { heartbeatS: 1 },
        closeStderr: (c) => fs.existsSync(path.join(c.repo, 'started')),
        exit: 0,
        check: (r) => (r.stdout === '# Summary\nok\n' ? null : `stdout=${JSON.stringify(r.stdout)}`),
      },
      {
        name: 'empty-auth',
        args: ['--prefer', 'pi', '--model-pi', 'fake/emptyauth'],
        exit: 69,
        status: /^AIKIT-XAI status=auth cli=pi model=fake\/emptyauth exit=69 cli_rc=0 .* tree=clean action=stop$/,
      },
      {
        name: 'billing',
        args: ['--prefer', 'pi', '--model-pi', 'fake/billing'],
        exit: 69,
        status: /^AIKIT-XAI status=billing cli=pi model=fake\/billing exit=69 cli_rc=1 elapsed=\d+s out=\d+ tree=clean action=stop$/,
      },
      {
        name: 'billing-router',
        args: ['--prefer', 'pi', '--model-pi', 'fake/billing'],
        config: { routerBacked: { pi: true } },
        exit: 75,
        status: /^AIKIT-XAI status=quota cli=pi model=fake\/billing exit=75 cli_rc=1 elapsed=\d+s out=\d+ tree=clean action=stop$/,
      },
      {
        // routerBacked covers only the CLI's pinned model: a direct model on it stops on billing.
        name: 'billing-unpinned-model-on-router-cli',
        args: ['--prefer', 'pi', '--model-pi', 'fake/billing'],
        config: { routerBacked: { pi: true }, models: { pi: 'fake/pinned-router' } },
        exit: 69,
        status: /^AIKIT-XAI status=billing cli=pi model=fake\/billing exit=69 .* action=stop$/,
        check: (r) => ((r.stderr || '').includes('action=stop route=unknown ') ? null
          : 'route was not unknown'),
      },
      {
        name: 'billing-403-router',
        args: ['--prefer', 'pi', '--model-pi', 'fake/spend403'],
        config: { routerBacked: { pi: true } },
        exit: 75,
        status: /^AIKIT-XAI status=quota cli=pi model=fake\/spend403 exit=75 cli_rc=1 .* tree=clean action=stop$/,
      },
      {
        name: 'billing-free-tier',
        args: ['--prefer', 'pi', '--model-pi', 'fake/freetier'],
        exit: 69,
        status: /^AIKIT-XAI status=billing cli=pi model=fake\/freetier exit=69 cli_rc=1 .* tree=clean action=stop$/,
      },
      {
        name: 'auth',
        args: ['--prefer', 'pi', '--model-pi', 'fake/auth'],
        exit: 69,
        status: /^AIKIT-XAI status=auth cli=pi model=fake\/auth exit=69 cli_rc=1 elapsed=\d+s out=\d+ tree=clean action=stop$/,
      },
      {
        name: 'perm',
        args: ['--prefer', 'pi', '--model-pi', 'fake/perm'],
        exit: 69,
        status: /^AIKIT-XAI status=permission_blocked cli=pi model=fake\/perm exit=69 cli_rc=1 elapsed=\d+s out=\d+ tree=clean action=stop$/,
      },
      {
        name: 'quota',
        args: ['--prefer', 'pi', '--model-pi', 'fake/quota'],
        exit: 75,
        status: /^AIKIT-XAI status=quota cli=pi model=fake\/quota exit=75 cli_rc=1 elapsed=\d+s out=\d+ tree=clean action=stop$/,
        check: (r) => {
          const tail = statusTail(r.stderr || '');
          if (!tail) return 'status line has no evidence tail';
          if (tail.route !== 'unknown') return `route=${tail.route}`;
          if (!/^\S+$/.test(tail.rule) || tail.rule === '-') return `rule=${tail.rule}`;
          if (tail.pattern !== 'verified' && tail.pattern !== 'unverified') return `pattern=${tail.pattern}`;
          return null;
        },
      },
      {
        // One cycle of a confirmed router lane: the soft series, exit 75, cycle 0 persisted.
        name: 'router-quota-one-cycle',
        args: ['--prefer', 'pi', '--model-pi', 'fake/quota-until-8'],
        config: { routerBacked: { pi: true }, retry: { max_retries: 2, session_resets: 1 } },
        exit: 75,
        status: new RegExp('^AIKIT-XAI status=quota cli=pi model=fake/quota-until-8 ' +
          'exit=75 .* tree=clean action=stop$'),
        check: (r, ctx) => {
          const n = ctx.calls.filter((l) => l === 'pi quota-until-8').length;
          if (n !== 6) return `calls=${n}`;
          const tail = statusTail(r.stderr || '');
          if (!tail || tail.retry_after_s !== '0' || tail.cycle !== '0') {
            return `tail=${JSON.stringify(tail)}`;
          }
          if (tail.attempts !== '6' || tail.cycles !== '0') {
            return `counts=${tail.attempts}/${tail.cycles}`;
          }
          const file = caseCycleFile(ctx, 'pi', 'fake/quota-until-8');
          const saved = readCycleState(file);
          return saved && saved.cycle === 0 ? null : 'state file missing cycle 0';
        },
      },
      {
        // The second invocation resumes the same session and the fake answers on call 8.
        name: 'router-quota-second-cycle',
        args: ['--prefer', 'pi', '--model-pi', 'fake/quota-until-8'],
        config: {
          routerBacked: { pi: true }, capS: 3600,
          retry: { max_retries: 2, session_resets: 1 },
        },
        exit: 75,
        status: /^AIKIT-XAI status=quota .* action=stop$/,
        second: {
          exit: 0,
          status: new RegExp('^AIKIT-XAI status=ok cli=pi model=fake/quota-until-8 ' +
            'exit=0 .* action=stop$'),
        },
        check: (both, ctx) => {
          const runs = (rows) => rows.filter((l) => l === 'pi quota-until-8');
          if (runs(both.calls1).length !== 6) return `first calls=${runs(both.calls1).length}`;
          // The fake answers on its 8th call, so the re-entry fails once, then retries and answers.
          if (runs(both.calls2).length !== 2) return `second calls=${runs(both.calls2).length}`;
          const rows = readOr(ctx.env.FAKE_SIDS, '').trim().split('\n').map((l) => l.split(' '));
          if (rows.length !== 8) return `sids=${rows.length}`;
          if (rows[6][0] !== rows[5][0] || rows[7][0] !== rows[5][0]) {
            return 'second cycle did not resume the session';
          }
          if (rows[6][1] !== 'prompt' || rows[7][1] !== 'resume') {
            return `inputs ${rows[6][1]},${rows[7][1]}`;
          }
          const tail = statusTail(both.again.stderr || '');
          if (!tail || tail.attempts !== '8' || tail.cycles !== '1') {
            return `tail=${JSON.stringify(tail)}`;
          }
          const file = caseCycleFile(ctx, 'pi', 'fake/quota-until-8');
          return readCycleState(file) ? 'state file survived an ok run' : null;
        },
      },
      {
        // A different prompt never joins the previous task's session.
        name: 'router-quota-second-cycle-new-task',
        args: ['--prefer', 'pi', '--model-pi', 'fake/quota-until-8', '--no-preamble'],
        config: {
          routerBacked: { pi: true }, capS: 3600,
          retry: { max_retries: 2, session_resets: 1 },
        },
        exit: 75,
        status: /^AIKIT-XAI status=quota .* action=stop$/,
        second: {
          exit: 0,
          stdin: '<objective>a different task</objective>\n',
          status: /^AIKIT-XAI status=ok .* action=stop$/,
        },
        check: (both, ctx) => {
          const runs2 = both.calls2.filter((l) => l === 'pi quota-until-8');
          if (runs2.length !== 2) return `second calls=${runs2.length}`;
          const rows = readOr(ctx.env.FAKE_SIDS, '').trim().split('\n').map((l) => l.split(' '));
          if (rows.length !== 8) return `sids=${rows.length}`;
          if (rows[6][0] === rows[0][0] || rows[7][0] === rows[0][0]) {
            return 'new task resumed the old session';
          }
          if (rows[6][1] !== 'prompt' || rows[7][1] !== 'resume') {
            return `inputs ${rows[6][1]},${rows[7][1]}`;
          }
          return both.calls2.includes('quota8-new-task') ? null : 'new prompt was not sent';
        },
      },
      {
        // The hard wait is the re-entry gate: a re-entry inside it spawns nothing.
        name: 'router-quota-early-reentry',
        args: ['--prefer', 'pi', '--model-pi', 'fake/quota'],
        config: {
          routerBacked: { pi: true }, capS: 3600,
          retry: { max_retries: 2, session_resets: 1, hard_waits_s: [600, 600, 600] },
        },
        exit: 75,
        status: /^AIKIT-XAI status=quota .* action=stop$/,
        second: { exit: 75, status: /^AIKIT-XAI status=quota .* action=stop$/ },
        check: (both) => {
          const all = [...both.calls1, ...both.calls2].filter((l) => l === 'pi quota');
          if (all.length !== 6) return `calls=${all.length}`;
          const tail = statusTail(both.again.stderr || '');
          // The re-entry reports what is left of the 600 s wait, so it shrinks by the gap between
          // the two runs; that gap is a load-scaled ceiling, not an exact 600.
          const left = tail ? Number(tail.retry_after_s) : NaN;
          if (!tail || tail.cycle !== '0' || !(left <= 600 && left >= 600 - Math.ceil(scaledMs(10000) / 1000))) {
            return `tail=${JSON.stringify(tail)}`;
          }
          const spawned = both.calls2.filter((l) => l !== 'pi rpc');
          return spawned.length === 0 ? null : 're-entry spawned a child';
        },
      },
      {
        // Both timestamps past the cap: the file is stale and a fresh cycle starts.
        name: 'stale-state-fresh-start',
        setup: (c) => {
          const file = caseCycleFile(c, 'pi', 'fake/quota');
          const old = Date.now() - 5 * 3600 * 1000;
          writeCycleState(file, {
            first_seen: old, last_attempt_at: old, cycle: 3, attempts: 21,
            last_sid: 'old', task_digest: 'old', retry_after_s: 0, due_at: old,
            class: 'quota',
          });
          return null;
        },
        args: ['--prefer', 'pi', '--model-pi', 'fake/quota'],
        config: { routerBacked: { pi: true } },
        exit: 75,
        status: /^AIKIT-XAI status=quota .* action=stop$/,
        check: (r, ctx) => {
          if (!(r.stderr || '').includes('stale-state-fresh-start')) return 'missing stale note';
          const n = ctx.calls.filter((l) => l === 'pi quota').length;
          if (n !== 12) return `calls=${n}`;
          const tail = statusTail(r.stderr || '');
          return tail && tail.cycle === '0' ? null : `cycle=${tail && tail.cycle}`;
        },
      },
      {
        // An active episode past the cap stops before any child.
        name: 'expired-state-cap-stop',
        setup: (c) => {
          const file = caseCycleFile(c, 'pi', 'fake/quota');
          writeCycleState(file, {
            first_seen: Date.now() - 5 * 3600 * 1000, last_attempt_at: Date.now(),
            cycle: 2, attempts: 14, last_sid: 'old', task_digest: 'old',
            retry_after_s: 0, due_at: 0, class: 'quota',
          });
          return null;
        },
        args: ['--prefer', 'pi', '--model-pi', 'fake/quota'],
        config: { routerBacked: { pi: true } },
        exit: 69,
        status: /^AIKIT-XAI status=quota .* exit=69 .* action=stop$/,
        check: (r, ctx) => {
          const runs = ctx.calls.filter((l) => l !== 'pi rpc');
          if (runs.length) return `spawned: ${runs.join('|')}`;
          if (!(r.stderr || '').includes('stopped=cap')) return 'missing stopped=cap';
          // 25.1-03: the early return persists its stop (D-09), so a later session can surface it.
          const saved = readCycleState(caseCycleFile(ctx, 'pi', 'fake/quota'));
          if (!saved) return 'cap stop was not persisted';
          if (saved.stopped !== 'cap' || typeof saved.stopped_at !== 'number') {
            return `record=${JSON.stringify(saved)}`;
          }
          if (saved.retry_after_s !== null || saved.due_at !== null) {
            return 'wait fields not cleared';
          }
          return null;
        },
      },
      {
        // A quota-class deadline stop still starts the cycle accounting. The first attempt
        // fails at once so a retry is admitted; the second hangs until the deadline refuses it.
        name: 'quota-deadline-cycle',
        args: ['--prefer', 'pi', '--model-pi', 'fake/slowquota', '--timeout', '4'],
        config: { routerBacked: { pi: true } },
        exit: 75,
        status: /^AIKIT-XAI status=quota .* exit=75 .* action=stop$/,
        check: (r, ctx) => {
          if (!(r.stderr || '').includes('stopped=deadline')) return 'missing stopped=deadline';
          const tail = statusTail(r.stderr || '');
          if (!tail || tail.cycle !== '0') return `cycle=${tail && tail.cycle}`;
          const file = caseCycleFile(ctx, 'pi', 'fake/slowquota');
          return readCycleState(file) ? null : 'deadline stop wrote no state';
        },
      },
      {
        // About 90 s of cap left: the admitted child is stopped at the cap.
        name: 'quota-cap-clamp-child',
        stdin: 'clamp-probe\n',
        setup: (c) => {
          const file = caseCycleFile(c, 'pi', 'fake/capclamp');
          const first = Date.now() - (3600 * 1000 - 8000);
          writeCycleState(file, {
            first_seen: first, last_attempt_at: Date.now() - 1000, cycle: 0, attempts: 7,
            last_sid: '00000000-0000-4000-8000-000000000001',
            task_digest: taskDigest('clamp-probe\n'), retry_after_s: 0, due_at: 0,
            class: 'quota',
          });
          return null;
        },
        args: ['--prefer', 'pi', '--model-pi', 'fake/capclamp', '--outer-timeout', '200',
          '--no-preamble'],
        config: { routerBacked: { pi: true }, capS: 3600 },
        exit: 69,
        status: /^AIKIT-XAI status=quota .* exit=69 .* action=stop$/,
        check: (r, ctx) => {
          if (ctx.elapsedMs >= scaledMs(80000)) return `elapsed ${ctx.elapsedMs}`;
          if (!(r.stderr || '').includes('stopped=cap')) return 'missing stopped=cap';
          return deadCheck(ctx, ['pi']);
        },
      },
      {
        // 300 s of cap left, hard wait 600 s: a deadline stop becomes the cap's exit 69.
        name: 'quota-deadline-near-cap',
        setup: (c) => {
          const file = caseCycleFile(c, 'pi', 'fake/slowquota');
          writeCycleState(file, {
            first_seen: Date.now() - (14400 - 300) * 1000, last_attempt_at: Date.now() - 1000,
            cycle: 1, attempts: 7, last_sid: null, task_digest: 'other', retry_after_s: 0,
            due_at: 0, class: 'quota',
          });
          return null;
        },
        args: ['--prefer', 'pi', '--model-pi', 'fake/slowquota', '--timeout', '4'],
        config: {
          routerBacked: { pi: true },
          retry: { hard_waits_s: [600, 600, 600] },
        },
        exit: 69,
        status: /^AIKIT-XAI status=quota .* exit=69 .* action=stop$/,
        check: (r) => ((r.stderr || '').includes('stopped=cap') ? null : 'missing stopped=cap'),
      },
      {
        // An unconfirmed call on the router lane's CLI and model neither inherits nor deletes
        // its cycle state.
        name: 'unconfirmed-route-ignores-state',
        setup: (c) => {
          const file = caseCycleFile(c, 'pi', 'fake/ok');
          writeCycleState(file, {
            first_seen: Date.now() - 60000, last_attempt_at: Date.now() - 1000, cycle: 1,
            attempts: 7, last_sid: null, task_digest: 'other', retry_after_s: 600,
            due_at: Date.now() + 600000, class: 'quota',
          });
          return null;
        },
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* action=stop$/,
        check: (_r, ctx) => (readCycleState(caseCycleFile(ctx, 'pi', 'fake/ok'))
          ? null : 'router state deleted by an unconfirmed call'),
      },
      {
        // A terminal stderr line from a child that then exits 0 with an answer is a success.
        name: 'live-hit-then-success',
        args: ['--prefer', 'pi', '--model-pi', 'fake/stderr-then-ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/stderr-then-ok exit=0 .* action=stop$/,
      },
      {
        // An unwritable state dir keeps the quota class: a bare 75, never a crash.
        name: 'quota-state-unwritable',
        setup: (c) => {
          const blocker = path.join(c.home, 'state-is-a-file');
          fs.writeFileSync(blocker, 'x');
          c.env.XDG_STATE_HOME = blocker;
          return null;
        },
        args: ['--prefer', 'pi', '--model-pi', 'fake/quota'],
        config: { routerBacked: { pi: true } },
        exit: 75,
        status: /^AIKIT-XAI status=quota cli=pi model=fake\/quota exit=75 (?!.*retry_after_s=).* action=stop$/,
        check: (r) => {
          const err = r.stderr || '';
          if (!err.includes('cycle state unwritable')) return 'missing unwritable note';
          if (err.includes('cross-ai: state ')) return 'state line without a written file';
          return null;
        },
      },
      {
        // The lane is the checkout, CLI, model and route kind, not the task: a different
        // prompt on a lane with a pending due_at is refused without a model call too.
        name: 'hard-tier-other-task-refused',
        setup: (c) => {
          writePriorRecord(c, 'pi', 'fake/event400', 'other', 'transient', 0, {
            due_at: Date.now() + 5 * 60 * 1000,
          });
          return null;
        },
        args: ['--prefer', 'pi', '--model-pi', 'fake/event400', '--no-preamble'],
        stdin: 'another task\n',
        config: { retry: { ...HARD_TIER_RETRY } },
        exit: 75,
        status: new RegExp('^AIKIT-XAI status=transient cli=pi model=fake/event400 ' +
          'exit=75 .* action=stop$'),
        check: (r, ctx) => {
          const spawned = ctx.calls.filter((l) => l !== 'pi rpc');
          if (spawned.length) return `spawned: ${spawned.join('|')}`;
          const tail = statusTail(r.stderr || '');
          const left = tail ? Number(tail.retry_after_s) : NaN;
          if (!(left >= 290 && left <= 300)) return `retry_after_s=${tail && tail.retry_after_s}`;
          const report = (r.stderr || '').split('\n')
            .find((l) => l.startsWith('cross-ai: report '));
          return report && report.includes('stopped=rungs') ? null : `report=${report}`;
        },
      },
      {
        // Once due_at has passed, a different task starts in a fresh session and never
        // resumes the record's last_sid.
        name: 'hard-tier-other-task-fresh-session',
        setup: (c) => {
          writePriorRecord(c, 'pi', 'fake/event400', 'other', 'transient', 0, {
            last_sid: 'old-sid',
          });
          return null;
        },
        args: ['--prefer', 'pi', '--model-pi', 'fake/event400', '--no-preamble'],
        stdin: 'another task\n',
        config: { retry: { ...HARD_TIER_RETRY } },
        exit: 75,
        status: new RegExp('^AIKIT-XAI status=transient cli=pi model=fake/event400 ' +
          'exit=75 .* action=stop$'),
        check: (r, ctx) => {
          const rows = readOr(ctx.env.FAKE_SIDS, '').trim().split('\n').map((l) => l.split(' '));
          if (rows.length !== 1) return `rows=${rows.length}`;
          if (rows[0][1] !== 'prompt') return `kind=${rows[0][1]}`;
          if (rows[0][0] === 'old-sid') return 'resumed the record session';
          const tail = statusTail(r.stderr || '');
          if (!tail || tail.retry_after_s !== '900' || tail.cycle !== '1') {
            return `tail=${JSON.stringify(tail)}`;
          }
          return sameLane(ctx, 'pi', 'fake/event400');
        },
      },
      {
        // The route kind keys the file: a pending router record neither refuses, deletes nor
        // steers an unconfirmed spend on the same CLI and model; it keeps its bytes.
        name: 'hard-tier-route-files-separate',
        setup: (c) => {
          const router = writePriorRecord(c, 'pi', 'fake/event400', 'router', 'quota', 1, {
            due_at: Date.now() + 5 * 60 * 1000,
          });
          c.routerBytes = fs.readFileSync(router, 'utf8');
          return null;
        },
        args: ['--prefer', 'pi', '--model-pi', 'fake/event400'],
        config: { retry: { ...HARD_TIER_RETRY } },
        exit: 75,
        status: new RegExp('^AIKIT-XAI status=transient cli=pi model=fake/event400 ' +
          'exit=75 .* action=stop$'),
        check: (r, ctx) => {
          if (ctx.calls.filter((l) => l === 'pi event400').length !== 1) return 'call count';
          const tail = statusTail(r.stderr || '');
          if (!tail || tail.retry_after_s !== '600' || tail.cycle !== '0') {
            return `tail=${JSON.stringify(tail)}`;
          }
          const saved = readCycleState(caseCycleFile(ctx, 'pi', 'fake/event400', 'other'));
          if (!saved || saved.class !== 'transient' || saved.cycle !== 0) {
            return `other=${JSON.stringify(saved)}`;
          }
          const router = caseCycleFile(ctx, 'pi', 'fake/event400', 'router');
          if (fs.readFileSync(router, 'utf8') !== ctx.routerBytes) {
            return 'router file was touched';
          }
          return sameLane(ctx, 'pi', 'fake/event400');
        },
      },
      {
        // A spent transient series on an unconfirmed route gets the caller's hard tier too:
        // one hint (hard_waits_s[0]), the state line naming the `other` file, and a record
        // with the class, the cycle and the wait (D-07, route-keyed files).
        name: 'hard-tier-transient-cycle0',
        args: ['--prefer', 'pi', '--model-pi', 'fake/event400'],
        config: { retry: { max_retries: 1, session_resets: 0, hard_waits_s: [600, 900, 1800] } },
        exit: 75,
        status: new RegExp('^AIKIT-XAI status=transient cli=pi model=fake/event400 ' +
          'exit=75 .* action=stop$'),
        check: (r, ctx) => {
          const n = ctx.calls.filter((l) => l === 'pi event400').length;
          if (n !== 2) return `calls=${n}`;
          const err = r.stderr || '';
          const file = caseCycleFile(ctx, 'pi', 'fake/event400', 'other');
          if (!err.includes(`cross-ai: state ${file}`)) return 'missing state line for the other file';
          const tail = statusTail(err);
          if (!tail || tail.retry_after_s !== '600' || tail.cycle !== '0') {
            return `tail=${JSON.stringify(tail)}`;
          }
          const report = err.split('\n').find((l) => l.startsWith('cross-ai: report '));
          if (!report || !/due_at=\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ /.test(report)) {
            return `report=${report}`;
          }
          const saved = readCycleState(file);
          if (!saved) return 'no transient record saved';
          if (saved.class !== 'transient' || saved.cycle !== 0 || saved.retry_after_s !== 600) {
            return `record=${JSON.stringify(saved)}`;
          }
          if (typeof saved.due_at !== 'number' || saved.due_at <= Date.now() - 1000) {
            return `due_at=${saved.due_at}`;
          }
          return sameLane(ctx, 'pi', 'fake/event400');
        },
      },
      {
        // A transient series cut by the call deadline gets the same hint, never a bare 75.
        name: 'hard-tier-transient-deadline',
        args: ['--prefer', 'pi', '--model-pi', 'fake/event400', '--timeout', '3'],
        config: { retry: { max_retries: 1, session_resets: 0, hard_waits_s: [600, 900, 1800] } },
        exit: 75,
        status: new RegExp('^AIKIT-XAI status=transient cli=pi model=fake/event400 ' +
          'exit=75 .* action=stop$'),
        check: (r, ctx) => {
          if (ctx.elapsedMs >= scaledMs(5000)) return `elapsed ${ctx.elapsedMs}ms`;
          const n = ctx.calls.filter((l) => l === 'pi event400').length;
          if (n !== 1) return `calls=${n}`;
          const err = r.stderr || '';
          if (!err.includes('stopped=deadline')) return 'missing stopped=deadline';
          const tail = statusTail(err);
          if (!tail || tail.retry_after_s !== '600' || tail.cycle !== '0') {
            return `tail=${JSON.stringify(tail)}`;
          }
          return sameLane(ctx, 'pi', 'fake/event400');
        },
      },
      {
        // After a record at cycle 0 the next hard wait is hard_waits_s[1].
        name: 'hard-tier-cycle1',
        setup: (c) => {
          writePriorRecord(c, 'pi', 'fake/event400', 'other', 'transient', 0);
          return null;
        },
        args: ['--prefer', 'pi', '--model-pi', 'fake/event400'],
        config: { retry: { ...HARD_TIER_RETRY } },
        exit: 75,
        status: new RegExp('^AIKIT-XAI status=transient cli=pi model=fake/event400 ' +
          'exit=75 .* action=stop$'),
        check: (r, ctx) => {
          if (ctx.calls.filter((l) => l === 'pi event400').length !== 1) return 'call count';
          const tail = statusTail(r.stderr || '');
          if (!tail || tail.retry_after_s !== '900' || tail.cycle !== '1') {
            return `tail=${JSON.stringify(tail)}`;
          }
          const saved = readCycleState(caseCycleFile(ctx, 'pi', 'fake/event400', 'other'));
          if (!saved || saved.cycle !== 1 || saved.retry_after_s !== 900) {
            return `record=${JSON.stringify(saved)}`;
          }
          return sameLane(ctx, 'pi', 'fake/event400');
        },
      },
      {
        // After a record at cycle 1 the next hard wait is hard_waits_s[2].
        name: 'hard-tier-cycle2',
        setup: (c) => {
          writePriorRecord(c, 'pi', 'fake/event400', 'other', 'transient', 1);
          return null;
        },
        args: ['--prefer', 'pi', '--model-pi', 'fake/event400'],
        config: { retry: { ...HARD_TIER_RETRY } },
        exit: 75,
        status: new RegExp('^AIKIT-XAI status=transient cli=pi model=fake/event400 ' +
          'exit=75 .* action=stop$'),
        check: (r, ctx) => {
          if (ctx.calls.filter((l) => l === 'pi event400').length !== 1) return 'call count';
          const tail = statusTail(r.stderr || '');
          if (!tail || tail.retry_after_s !== '1800' || tail.cycle !== '2') {
            return `tail=${JSON.stringify(tail)}`;
          }
          return sameLane(ctx, 'pi', 'fake/event400');
        },
      },
      {
        // The list's end is terminal: exit 69, the stop on the report line and on disk.
        name: 'hard-tier-stop',
        setup: (c) => {
          writePriorRecord(c, 'pi', 'fake/event400', 'other', 'transient', 2);
          return null;
        },
        args: ['--prefer', 'pi', '--model-pi', 'fake/event400'],
        config: { retry: { ...HARD_TIER_RETRY } },
        exit: 69,
        status: new RegExp('^AIKIT-XAI status=transient cli=pi model=fake/event400 ' +
          'exit=69 .* action=stop$'),
        check: (r, ctx) => {
          if (ctx.calls.filter((l) => l === 'pi event400').length !== 1) return 'call count';
          const err = r.stderr || '';
          const report = err.split('\n').find((l) => l.startsWith('cross-ai: report '));
          if (!report || !report.includes('stopped=hard-waits')) return `report=${report}`;
          const tail = statusTail(err);
          if (tail && tail.retry_after_s !== undefined) return `tail=${JSON.stringify(tail)}`;
          const saved = readCycleState(caseCycleFile(ctx, 'pi', 'fake/event400', 'other'));
          if (!saved || saved.stopped !== 'hard-waits' || typeof saved.stopped_at !== 'number') {
            return `record=${JSON.stringify(saved)}`;
          }
          return sameLane(ctx, 'pi', 'fake/event400');
        },
      },
      {
        // 900 s of wait against 600 s of cap: the cap wins over the list entry.
        name: 'hard-tier-cap-first',
        setup: (c) => {
          writePriorRecord(c, 'pi', 'fake/event400', 'other', 'transient', 0, {
            first_seen: Date.now() - (3 * 3600 + 50 * 60) * 1000,
          });
          return null;
        },
        args: ['--prefer', 'pi', '--model-pi', 'fake/event400'],
        config: { retry: { ...HARD_TIER_RETRY } },
        exit: 69,
        status: new RegExp('^AIKIT-XAI status=transient cli=pi model=fake/event400 ' +
          'exit=69 .* action=stop$'),
        check: (r, ctx) => {
          const report = (r.stderr || '').split('\n')
            .find((l) => l.startsWith('cross-ai: report '));
          if (!report || !report.includes('stopped=cap')) return `report=${report}`;
          return sameLane(ctx, 'pi', 'fake/event400');
        },
      },
      {
        // A stopped record refuses every call on the lane without a model call, logs the state
        // path and the owner reset line, and holds its bytes until stale or deleted (D-08).
        name: 'hard-tier-stopped-refused',
        setup: (c) => {
          const file = writePriorRecord(c, 'pi', 'fake/event400', 'other', 'transient', 2, {
            stopped: 'hard-waits', stopped_at: Date.now() - 60000,
            retry_after_s: null, due_at: null,
          });
          c.stoppedBytes = fs.readFileSync(file, 'utf8');
          return null;
        },
        args: ['--prefer', 'pi', '--model-pi', 'fake/event400'],
        config: { retry: { ...HARD_TIER_RETRY } },
        exit: 69,
        status: new RegExp('^AIKIT-XAI status=transient cli=pi model=fake/event400 ' +
          'exit=69 .* action=stop$'),
        check: (r, ctx) => {
          const spawned = ctx.calls.filter((l) => l !== 'pi rpc');
          if (spawned.length) return `spawned: ${spawned.join('|')}`;
          const err = r.stderr || '';
          const file = caseCycleFile(ctx, 'pi', 'fake/event400', 'other');
          if (!err.includes(`cross-ai: state ${file}`)) return 'missing state line';
          if (!err.includes('cross-ai: lane stopped=hard-waits at ') ||
            !err.includes(`delete ${file} to start a new episode`)) {
            return 'missing lane stopped line';
          }
          const tail = statusTail(err);
          if (tail && tail.retry_after_s !== undefined) return `tail=${JSON.stringify(tail)}`;
          if (fs.readFileSync(file, 'utf8') !== ctx.stoppedBytes) {
            return 'stopped record was rewritten';
          }
          return sameLane(ctx, 'pi', 'fake/event400');
        },
      },
      {
        // 25.1 IN-01: a hand-edited stopped record with no stopped_at still refuses (69), no crash.
        name: 'hard-tier-stopped-no-stop-time',
        setup: (c) => {
          writePriorRecord(c, 'pi', 'fake/event400', 'other', 'transient', 2, {
            stopped: 'hard-waits', retry_after_s: null, due_at: null,
          });
          return null;
        },
        args: ['--prefer', 'pi', '--model-pi', 'fake/event400'],
        config: { retry: { ...HARD_TIER_RETRY } },
        exit: 69,
        status: new RegExp('^AIKIT-XAI status=transient cli=pi model=fake/event400 ' +
          'exit=69 .* action=stop$'),
        check: (r, ctx) => {
          if (!(r.stderr || '').includes('cross-ai: lane stopped=hard-waits at -;')) {
            return 'missing lane stopped line';
          }
          return sameLane(ctx, 'pi', 'fake/event400');
        },
      },
      {
        // The stale rule is the owner's time-based reset: a stopped record older than the cap
        // is deleted and the lane starts a fresh episode.
        name: 'hard-tier-stopped-stale',
        setup: (c) => {
          writePriorRecord(c, 'pi', 'fake/event400', 'other', 'transient', 2, {
            stopped: 'hard-waits', stopped_at: Date.now() - 5 * 3600 * 1000,
            last_attempt_at: Date.now() - 5 * 3600 * 1000,
            first_seen: Date.now() - 5 * 3600 * 1000,
            retry_after_s: null, due_at: null,
          });
          return null;
        },
        args: ['--prefer', 'pi', '--model-pi', 'fake/event400'],
        config: { retry: { ...HARD_TIER_RETRY } },
        exit: 75,
        status: new RegExp('^AIKIT-XAI status=transient cli=pi model=fake/event400 ' +
          'exit=75 .* action=stop$'),
        check: (r, ctx) => {
          if (!(r.stderr || '').includes('stale-state-fresh-start')) return 'missing stale note';
          const tail = statusTail(r.stderr || '');
          if (!tail || tail.retry_after_s !== '600' || tail.cycle !== '0') {
            return `tail=${JSON.stringify(tail)}`;
          }
          return sameLane(ctx, 'pi', 'fake/event400');
        },
      },
      {
        // The hard_waits list itself is project config: precedence over the rendered copy.
        name: 'hard-tier-config-waits',
        planningConfig: { workflow: { cross_ai_retry: { hard_waits_s: [60] } } },
        args: ['--prefer', 'pi', '--model-pi', 'fake/event400'],
        config: { retry: { max_retries: 1, session_resets: 0 } },
        exit: 75,
        status: new RegExp('^AIKIT-XAI status=transient cli=pi model=fake/event400 ' +
          'exit=75 .* action=stop$'),
        check: (r, ctx) => {
          if (ctx.calls.filter((l) => l === 'pi event400').length !== 2) return 'call count';
          const tail = statusTail(r.stderr || '');
          if (!tail || tail.retry_after_s !== '60' || tail.cycle !== '0') {
            return `tail=${JSON.stringify(tail)}`;
          }
          return sameLane(ctx, 'pi', 'fake/event400');
        },
      },
      {
        // A confirmed router quota starts its own ladder at cycle 0 in the router file.
        name: 'hard-tier-router-quota-cycle0',
        args: ['--prefer', 'pi', '--model-pi', 'fake/quota', '--route-pi', 'router'],
        config: { retry: { ...HARD_TIER_RETRY } },
        exit: 75,
        status: new RegExp('^AIKIT-XAI status=quota cli=pi model=fake/quota exit=75 .* action=stop$'),
        check: (r, ctx) => {
          if (ctx.calls.filter((l) => l === 'pi quota').length !== 1) return 'call count';
          const tail = statusTail(r.stderr || '');
          if (!tail || tail.retry_after_s !== '600' || tail.cycle !== '0') {
            return `tail=${JSON.stringify(tail)}`;
          }
          const saved = readCycleState(caseCycleFile(ctx, 'pi', 'fake/quota'));
          if (!saved || saved.class !== 'quota' || saved.cycle !== 0 ||
            saved.retry_after_s !== 600) {
            return `record=${JSON.stringify(saved)}`;
          }
          return sameLane(ctx, 'pi', 'fake/quota');
        },
      },
      {
        // A pending due_at refuses the re-entry with the seconds left, the record's class and
        // Phase 25's stopped=rungs, and spawns nothing (SPEC R1 idempotency).
        name: 'hard-tier-early-reentry',
        setup: (c) => {
          writePriorRecord(c, 'pi', 'fake/event400', 'other', 'transient', 0, {
            due_at: Date.now() + 5 * 60 * 1000,
          });
          return null;
        },
        args: ['--prefer', 'pi', '--model-pi', 'fake/event400'],
        config: { retry: { ...HARD_TIER_RETRY } },
        exit: 75,
        status: new RegExp('^AIKIT-XAI status=transient cli=pi model=fake/event400 ' +
          'exit=75 .* action=stop$'),
        check: (r, ctx) => {
          const spawned = ctx.calls.filter((l) => l !== 'pi rpc');
          if (spawned.length) return `spawned: ${spawned.join('|')}`;
          const tail = statusTail(r.stderr || '');
          const left = tail ? Number(tail.retry_after_s) : NaN;
          if (!(left >= 290 && left <= 300)) return `retry_after_s=${tail && tail.retry_after_s}`;
          if (tail.cycle !== '0') return `cycle=${tail.cycle}`;
          const report = (r.stderr || '').split('\n')
            .find((l) => l.startsWith('cross-ai: report '));
          if (!report || !report.includes('status=transient') || !report.includes('stopped=rungs')) {
            return `report=${report}`;
          }
          return sameLane(ctx, 'pi', 'fake/event400');
        },
      },
      {
        // An unwritable state file never leaves a hint the runner cannot track: a spent
        // transient ladder is a bare 75 with the notice, no state line, no retry_after_s.
        name: 'hard-tier-transient-unwritable',
        setup: (c) => {
          const blocker = path.join(c.home, 'state-is-a-file');
          fs.writeFileSync(blocker, 'x');
          c.env.XDG_STATE_HOME = blocker;
          return null;
        },
        args: ['--prefer', 'pi', '--model-pi', 'fake/event400'],
        config: { retry: { max_retries: 1, session_resets: 0, hard_waits_s: [600, 900, 1800] } },
        exit: 75,
        status: /^AIKIT-XAI status=transient cli=pi model=fake\/event400 exit=75 (?!.*retry_after_s=).* action=stop$/,
        check: (r) => {
          const err = r.stderr || '';
          if (!err.includes('cycle state unwritable')) return 'missing unwritable note';
          if (err.includes('cross-ai: state ')) return 'state line without a written file';
          return null;
        },
      },
      {
        // Off a router lane a quota stops after one call and writes no state.
        name: 'plain-quota-no-retry',
        args: ['--prefer', 'pi', '--model-pi', 'fake/quota'],
        exit: 75,
        status: /^AIKIT-XAI status=quota .* exit=75 .* action=stop$/,
        check: (_r, ctx) => {
          const n = ctx.calls.filter((l) => l === 'pi quota').length;
          if (n !== 1) return `calls=${n}`;
          const file = caseCycleFile(ctx, 'pi', 'fake/quota');
          return readCycleState(file) ? 'off-router quota wrote a state file' : null;
        },
      },
      {
        // An inferred lane keeps the base billing class and never cycles.
        name: 'inferred-quota-no-cycle',
        args: ['--prefer', 'pi', '--model-pi', 'fake/router-env-billing'],
        config: { routerBacked: {} },
        exit: 69,
        status: new RegExp('^AIKIT-XAI status=billing cli=pi ' +
          'model=fake/router-env-billing exit=69 .* action=stop$'),
        check: (r, ctx) => {
          const n = ctx.calls.filter((l) => l === 'pi router-env-billing').length;
          if (n !== 1) return `calls=${n}`;
          const tail = statusTail(r.stderr || '');
          if (!tail || tail.route !== 'router-inferred') return `route=${tail && tail.route}`;
          return tail.cycle !== undefined ? 'inferred lane printed a cycle token' : null;
        },
      },
      {
        // An inferred route's own quota text stops at once with no cycle state.
        name: 'inferred-quota-stop',
        args: ['--prefer', 'pi', '--model-pi', 'fake/router-env-quota'],
        config: { routerBacked: {} },
        exit: 75,
        status: new RegExp('^AIKIT-XAI status=quota cli=pi ' +
          'model=fake/router-env-quota exit=75 .* action=stop$'),
        check: (r, ctx) => {
          const n = ctx.calls.filter((l) => l === 'pi router-env-quota').length;
          if (n !== 1) return `calls=${n}`;
          const tail = statusTail(r.stderr || '');
          if (!tail || tail.route !== 'router-inferred') return `route=${tail && tail.route}`;
          if (tail.cycle !== undefined) return 'inferred quota printed a cycle token';
          const file = caseCycleFile(ctx, 'pi', 'fake/router-env-quota');
          return readCycleState(file) ? 'inferred quota wrote a state file' : null;
        },
      },
      {
        // The key is built here and handed to the fake: the fake's pid is not this one.
        name: 'sentinel-evidence',
        setup: (c) => {
          c.env.AIKIT_XAI_CASE_SENTINEL = 'sk-aikit-SENTINEL-' + process.pid;
          return null;
        },
        args: ['--prefer', 'pi', '--model-pi', 'fake/sentinelrouter'],
        config: { routerBacked: { pi: true }, retry: { max_retries: 2, session_resets: 1 } },
        exit: 75,
        status: /^AIKIT-XAI status=quota .* action=stop$/,
        check: (r, ctx) => {
          const key = 'sk-aikit-SENTINEL-' + process.pid;
          const logText = `${r.stderr || ''}\n${r.stdout || ''}`;
          if (logText.includes(key)) return 'sentinel key leaked into the log';
          const attempts = (r.stderr || '').split('\n')
            .filter((l) => l.startsWith('cross-ai: attempt '));
          if (attempts.length !== 6) return `attempt lines=${attempts.length}`;
          const reports = (r.stderr || '').split('\n')
            .filter((l) => l.startsWith('cross-ai: report '));
          if (reports.length !== 1) return `report lines=${reports.length}`;
          if (!reports[0].includes('stopped=rungs')) return `report=${reports[0]}`;
          const runs = ctx.calls.filter((l) => l === 'pi sentinelrouter');
          return runs.length === 6 ? null : `calls=${runs.length}`;
        },
      },
      {
        // Off a router lane a quota over edits stops after the one call.
        name: 'dirty-quota',
        args: ['--prefer', 'pi', '--model-pi', 'fake/dirtyquota'],
        exit: 75,
        status: /^AIKIT-XAI status=quota cli=pi model=fake\/dirtyquota exit=75 cli_rc=1 .* tree=dirty action=stop$/,
        check: (r, ctx) => {
          const runs = ctx.calls.filter((l) => l === 'pi dirtyquota');
          if (runs.length !== 1) return `calls=${runs.length}`;
          return (r.stderr || '').includes('stopped=class') ? null : 'missing stopped=class';
        },
      },
      {
        // A router quota over edits finishes its first series, then the dirty tree stops the reset.
        name: 'dirty-billing-router',
        args: ['--prefer', 'pi', '--model-pi', 'fake/dirtybilling'],
        config: { routerBacked: { pi: true }, retry: { max_retries: 2, session_resets: 1 } },
        exit: 75,
        status: /^AIKIT-XAI status=quota cli=pi model=fake\/dirtybilling exit=75 cli_rc=1 .* tree=dirty action=stop$/,
        check: (r, ctx) => {
          const runs = ctx.calls.filter((l) => l === 'pi dirtybilling');
          if (runs.length !== 3) return `calls=${runs.length}`;
          const rows = readOr(ctx.env.FAKE_SIDS, '').trim().split('\n').map((l) => l.split(' '));
          if (new Set(rows.map((row) => row[0])).size !== 1) return 'series 1 switched session';
          return (r.stderr || '').includes('stopped=dirty-tree') ? null : 'missing dirty-tree';
        },
      },
      {
        name: 'sentinel-failed-line',
        args: ['--prefer', 'pi', '--model-pi', 'fake/sentinelquota'],
        exit: 75,
        status: /^AIKIT-XAI status=quota cli=pi model=fake\/sentinelquota exit=75 .* action=stop$/,
        check: (r) => {
          const key = 'sk-aikit-SENTINEL-' + process.pid;
          if ((r.stderr || '').includes(key)) return 'sentinel key leaked into the log';
          if (!(r.stderr || '').includes('<redacted>')) return 'stderr relay was not redacted';
          return null;
        },
      },
      {
        name: 'sentinelsplit',
        args: ['--prefer', 'pi', '--model-pi', 'fake/sentinelsplit'],
        exit: 1,
        status: /^AIKIT-XAI status=crash cli=pi model=fake\/sentinelsplit exit=1 .* action=stop$/,
        check: (r) => {
          const key = 'sk-aikit-SENTINEL-' + process.pid;
          const bearer = 'brtok-' + process.pid;
          const logText = r.stderr || '';
          if (logText.includes(key)) return 'split sentinel key leaked into the log';
          if (logText.includes(bearer)) return 'bearer sentinel leaked into the log';
          if (!logText.includes('<redacted>')) return 'split stderr was not redacted';
          return null;
        },
      },
      {
        name: 'sentinel-overlong',
        args: ['--prefer', 'pi', '--model-pi', 'fake/sentineloverlong'],
        exit: 1,
        status: /^AIKIT-XAI status=crash cli=pi model=fake\/sentineloverlong exit=1 .* action=stop$/,
        check: (r) => {
          const key = 'sk-aikit-SENTINEL-' + process.pid;
          const logText = r.stderr || '';
          if (logText.includes(key)) return 'overlong sentinel key leaked into the log';
          if (logText.includes('x'.repeat(66000))) return 'overlong line was not truncated';
          return null;
        },
      },
      {
        name: 'git-after-quota',
        args: ['--prefer', 'pi,cursor', '--model-pi', 'fake/gitfailquota', '--model-cursor', 'fake-ok-cursor'],
        exit: 1,
        status: new RegExp('^AIKIT-XAI status=git_error cli=pi model=fake/gitfailquota ' +
          'exit=1 cli_rc=1 .* tree=unknown action=stop$'),
        check: (_r, ctx) => (ctx.calls.some((l) => l.startsWith('cursor-agent')) ? 'cursor ran' : null),
      },
      {
        name: 'upstream-opencode-event',
        fakeOpencodeMode: 'upstream-event',
        args: ['--prefer', 'opencode', '--model-opencode', 'fake/ok', '--route-opencode', 'router'],
        config: { retry: { max_retries: 0, session_resets: 0, hard_waits_s: [600] } },
        exit: 75,
        status: /^AIKIT-XAI status=quota .* action=stop$/,
        check: (r, ctx) => {
          const body = (r.stderr || '').split('\n').find((line) => line.startsWith('cross-ai: upstream body='));
          const fields = (r.stderr || '').split('\n').find((line) => line.startsWith('cross-ai: upstream fields='));
          const all = `${r.stdout}\n${r.stderr}`;
          return body && body.includes('response') && fields === 'cross-ai: upstream fields={"retry_after":30}' &&
            !all.includes(ctx.env.AIKIT_XAI_SENTINEL) && !/acct-\\d+/.test(all)
            ? null : 'nested opencode event was not preserved and redacted';
        },
      },
      {
        name: 'upstream-two-events',
        fakeOpencodeMode: 'two-events',
        args: ['--prefer', 'opencode', '--model-opencode', 'fake/ok', '--route-opencode', 'router'],
        config: { retry: { max_retries: 0, session_resets: 0, hard_waits_s: [600] } },
        exit: 75,
        status: /^AIKIT-XAI status=quota .* action=stop$/,
        check: (r) => {
          const body = (r.stderr || '').split('\n').find((line) => line.startsWith('cross-ai: upstream body='));
          const text = body ? JSON.parse(body.slice(body.indexOf('=') + 1)) : '';
          if (!text.includes('The usage limit has been reached')) return 'matched event provenance lost';
          return text.includes('unrelated event') ? 'body holds the earlier event too' : null;
        },
      },
      {
        name: 'upstream-live-kill',
        args: ['--prefer', 'pi', '--model-pi', 'fake/auth-then-noise', '--timeout', '8'],
        exit: 69,
        status: /^AIKIT-XAI status=auth .* action=stop$/,
        check: (r) => {
          const body = (r.stderr || '').split('\n').find((line) => line.startsWith('cross-ai: upstream body='));
          return body && JSON.parse(body.slice(body.indexOf('=') + 1)) === 'Error: not logged in' ? null : 'live match provenance lost';
        },
      },
      {
        name: 'upstream-pi-session-masked',
        args: ['--prefer', 'pi', '--model-pi', 'fake/session-echo'],
        exit: 69,
        status: /^AIKIT-XAI status=auth .* action=stop$/,
        check: (r) => {
          const lines = (r.stderr || '').split('\n');
          const relay = lines.find((line) => line.includes('<redacted>'));
          const attempt = lines.find((line) => line.startsWith('cross-ai: attempt '));
          return relay && attempt && /session=([0-9a-f-]+)/.test(attempt) && !attempt.includes('session=<redacted>')
            ? null : 'session id masking mismatch';
        },
      },
      {
        name: 'upstream-waits-identical',
        args: ['--prefer', 'pi', '--model-pi', 'fake/router402', '--route-pi', 'router'],
        config: { retry: { base_s: 0.02, factor: 1.5, max_retries: 2, session_resets: 0, hard_waits_s: [600] } },
        exit: 75,
        status: /^AIKIT-XAI status=quota .* action=stop$/,
        second: {
          args: ['--prefer', 'pi', '--model-pi', 'fake/router402-nofields', '--route-pi', 'router'],
          exit: 75,
          status: /^AIKIT-XAI status=quota .* action=stop$/,
        },
        check: (both) => {
          if (!both.first || !both.again) return `twice results missing: ${Object.keys(both)}`;
          const countAttempts = (stderr) => (stderr.match(/cross-ai: attempt n=/g) || []).length;
          if (!both.again.stderr.includes('cross-ai: upstream body=')) return 'second run did not exercise upstream capture';
          if (countAttempts(both.first.stderr) !== countAttempts(both.again.stderr)) return `attempt count changed ${countAttempts(both.first.stderr)} vs ${countAttempts(both.again.stderr)}`;
          const waits = (stderr) => [...stderr.matchAll(/cross-ai: wait ms=(\d+)/g)].map((match) => Number(match[1]));
          const a = waits(both.first.stderr);
          const b = waits(both.again.stderr);
          if (a.length !== b.length || a.length !== 2) return `wait step sequence ${a.length} vs ${b.length}`;
          for (let i = 0; i < a.length; i += 1) {
            const expected = 20 * 1.5 ** i;
            if (Math.abs(a[i] - expected) > expected * 0.1 || Math.abs(b[i] - expected) > expected * 0.1) return `wait outside configured series: ${a[i]} vs ${b[i]}`;
          }
          const tails = [statusTail(both.first.stderr), statusTail(both.again.stderr)];
          return tails.every((tail) => tail?.retry_after_s === '600' && tail.cycle === '0') ? null : 'hard hint changed';
        },
      },
      {
        name: 'upstream-none',
        args: ['--prefer', 'pi', '--model-pi', 'fake/crash'],
        exit: 1,
        status: /^AIKIT-XAI status=crash .* action=stop$/,
        check: (r) => (r.stderr || '').includes('upstream=-') && !(r.stderr || '').includes('cross-ai: upstream ')
          ? null : 'empty upstream should have no trailer',
      },
      {
        name: 'crash',
        args: ['--prefer', 'pi', '--model-pi', 'fake/crash'],
        exit: 1,
        status: /^AIKIT-XAI status=crash cli=pi model=fake\/crash exit=1 cli_rc=7 elapsed=\d+s out=\d+ tree=clean action=stop$/,
        check: (r, ctx) => {
          const n = ctx.calls.filter((l) => l === 'pi crash').length;
          if (n !== 1) return `calls=${n}`;
          if ((r.stderr || '').includes('cross-ai: wait ')) return 'a crash waited';
          const report = (r.stderr || '').split('\n').find((l) => l.startsWith('cross-ai: report '));
          return report && report.includes('status=crash') ? null : `report=${report}`;
        },
      },
      {
        name: 'nochange',
        args: ['--prefer', 'pi', '--model-pi', 'fake/nochange'],
        exit: 1,
        status: /^AIKIT-XAI status=no_change cli=pi model=fake\/nochange exit=1 cli_rc=0 elapsed=\d+s out=\d+ tree=clean action=stop$/,
      },
      {
        name: 'empty',
        args: ['--prefer', 'pi', '--model-pi', 'fake/empty'],
        exit: 1,
        status: /^AIKIT-XAI status=empty_answer cli=pi model=fake\/empty exit=1 cli_rc=0 elapsed=\d+s out=\d+ tree=clean action=stop$/,
      },
      {
        name: 'upstream-cursor-result',
        args: ['--prefer', 'cursor', '--model-cursor', 'fake-err-cursor'],
        exit: 69,
        status: /^AIKIT-XAI status=auth .* action=stop$/,
        check: (r) => (r.stderr || '').includes('cross-ai: upstream body=') &&
          JSON.parse((r.stderr || '').split('\n').find((line) => line.startsWith('cross-ai: upstream body=')).split('=').slice(1).join('=')).includes('"is_error":true')
          ? null : 'cursor error event was not passed through',
      },
      {
        name: 'cursor-error',
        args: ['--prefer', 'cursor', '--model-cursor', 'fake-err-cursor'],
        exit: 69,
        status: /^AIKIT-XAI status=auth cli=cursor model=fake-err-cursor exit=69 cli_rc=0 elapsed=\d+s out=\d+ tree=clean action=stop$/,
        check: (_r, ctx) => {
          const mi = ctx.calls.indexOf('cursor-agent models');
          const ri = ctx.calls.indexOf('cursor-agent fake-err-cursor');
          if (mi < 0 || ri < 0 || mi > ri) return `calls=${ctx.calls.join('|')}`;
          return null;
        },
      },
      {
        name: 'dirtycrash',
        args: ['--prefer', 'pi,cursor', '--model-pi', 'fake/dirtycrash', '--model-cursor', 'fake-ok-cursor'],
        exit: 1,
        status: /^AIKIT-XAI status=crash cli=pi model=fake\/dirtycrash exit=1 cli_rc=7 elapsed=\d+s out=\d+ tree=dirty action=stop$/,
        check: (_r, ctx) => (ctx.calls.some((l) => l.startsWith('cursor-agent')) ? 'cursor ran after dirty crash' : null),
      },
      {
        name: 'no-change-no-fallback',
        args: ['--prefer', 'pi,cursor', '--model-pi', 'fake/nochange', '--model-cursor', 'fake-ok-cursor'],
        exit: 1,
        status: /^AIKIT-XAI status=no_change cli=pi model=fake\/nochange exit=1 cli_rc=0 elapsed=\d+s out=\d+ tree=clean action=stop$/,
        check: (_r, ctx) => (ctx.calls.some((l) => l.startsWith('cursor-agent')) ? 'cursor ran' : null),
      },
      {
        name: 'reedit',
        setup: (ctx) => { fs.writeFileSync(path.join(ctx.repo, 'dirty.txt'), 'seed\n'); return null; },
        args: ['--prefer', 'pi', '--model-pi', 'fake/reedit'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/reedit exit=0 cli_rc=0 elapsed=\d+s out=\d+ tree=dirty action=stop$/,
      },
      {
        name: 'hang',
        args: ['--prefer', 'pi', '--model-pi', 'fake/hang', '--timeout', '2'],
        exit: 124,
        status: /^AIKIT-XAI status=timeout cli=pi model=fake\/hang exit=124 cli_rc=.* elapsed=\d+s out=\d+ tree=.* action=stop$/,
        check: (_r, ctx) => deadCheck(ctx, ['gc']),
      },
      {
        // SPEC R4: a terminal usage-limit line, then the child stays alive. Stopped at the grace.
        name: 'live-limit-kill',
        args: ['--prefer', 'pi', '--model-pi', 'fake/limit-mid', '--timeout', '60'],
        exit: 75,
        status: /^AIKIT-XAI status=quota cli=pi model=fake\/limit-mid exit=75 .* action=stop$/,
        check: (_r, ctx) => (
          ctx.elapsedMs >= scaledMs(15000) ? `elapsed ${ctx.elapsedMs}` : deadCheck(ctx, ['pi'])
        ),
      },
      {
        // An unterminated `quota exceeded` matches the terminal rows before the buffer trim,
        // so the grace stops the child well inside the deadline (a live kill, not post-hoc).
        name: 'live-partial-kill',
        args: ['--prefer', 'pi', '--model-pi', 'fake/limit-partial', '--timeout', '3'],
        exit: 75,
        status: /^AIKIT-XAI status=quota cli=pi model=fake\/limit-partial exit=75 .* action=stop$/,
        check: (_r, ctx) => (
          ctx.elapsedMs >= scaledMs(15000) ? `elapsed ${ctx.elapsedMs}` : deadCheck(ctx, ['pi'])
        ),
      },
      {
        // A limit phrase in the answer alone is ignored (SPEC R4 precision).
        name: 'answer-only-ok',
        args: ['--prefer', 'pi', '--model-pi', 'fake/answer-only-limit'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/answer-only-limit exit=0 .* action=stop$/,
        check: (_r, ctx) => {
          const runs = ctx.calls.filter((l) => l.startsWith('pi ') && l !== 'pi rpc');
          return runs.length === 1 ? null : `pi calls ${ctx.calls.join('|')}`;

        },
      },
      {
        // A 503 retry notice is not a terminal signal.
        name: 'retry-notice-no-kill',
        args: ['--prefer', 'pi', '--model-pi', 'fake/retry-notice', '--timeout', '60'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/retry-notice exit=0 .* action=stop$/,
        check: (_r, ctx) => {
          const runs = ctx.calls.filter((l) => l.startsWith('pi ') && l !== 'pi rpc');
          return runs.length === 1 ? null : `pi calls ${ctx.calls.join('|')}`;
        },
      },
      {
        // The reason-code row is not terminal, so a child that prints it and stays alive past
        // the grace is not killed. Post-hoc classification still names that row.
        name: 'live-reason-code-no-kill',
        args: ['--prefer', 'pi', '--model-pi', 'fake/reason-code-hang', '--timeout', '60'],
        config: { retry: { max_retries: 1, session_resets: 0 } },
        exit: 75,
        status: /^AIKIT-XAI status=quota cli=pi model=fake\/reason-code-hang exit=75 cli_rc=1 .* action=stop$/,
        check: (r, ctx) => {
          if (ctx.elapsedMs < 2500) return `killed live at ${ctx.elapsedMs}ms`;
          const tail = statusTail(r.stderr || '');
          if (!tail || tail.rule !== 'omniroute-all-targets-skipped') return `rule=${tail && tail.rule}`;
          if (tail.retry_after_s !== undefined) return `retry_after_s=${tail.retry_after_s}`;
          const runs = ctx.calls.filter((l) => l.startsWith('pi ') && l !== 'pi rpc');
          return runs.length === 1 ? null : `pi calls ${ctx.calls.join('|')}`;
        },
      },
      {
        name: 'overlay-expensive-rows-signal',
        setup: (c) => {
          const rows = [];
          for (let i = 0; i < 40; i += 1) {
            rows.push({
              id: `user-catastrophic-${i}`, tier: 3, cli: '*', route: '*', provider: '*',
              input: 'any', match: '^(a+)+$', class: 'quota', terminal: false,
              label: 'unverified', evidence: 'probe',
            });
          }
          const dir = path.join(c.home, '.config', 'ai-kit');
          fs.mkdirSync(dir, { recursive: true });
          fs.writeFileSync(path.join(dir, 'cross-ai-errors.json'), JSON.stringify(rows));
          return null;
        },
        args: ['--prefer', 'pi', '--model-pi', 'fake/catastrophic-flood', '--timeout', '60'],
        signal: {
          when: (c) => readOr(c.calls, '').includes('pi catastrophic-flood'),
          sig: 'SIGTERM', withinMs: SELF_TEST_SIGNAL_EXIT_MS,
        },
        exit: 143,
        status: /^AIKIT-XAI status=signal .* exit=143 .* action=stop$/,
      },
      {
        name: 'overlay-sub-timeout-lines-signal',
        setup: (c) => {
          const dir = path.join(c.home, '.config', 'ai-kit');
          fs.mkdirSync(dir, { recursive: true });
          fs.writeFileSync(path.join(dir, 'cross-ai-errors.json'), JSON.stringify([{
            id: 'user-slow', tier: 3, cli: '*', route: '*', provider: '*', input: 'any',
            match: '^(a+)+$', class: 'quota', terminal: false, label: 'unverified', evidence: 'probe',
          }]));
          return null;
        },
        args: ['--prefer', 'pi', '--model-pi', 'fake/slow-lines', '--timeout', '60'],
        signal: {
          // Signal only after the runner spent its overlay budget; signalling at the fake's start raced the first chunk.
          when: (c, err) => err.includes('cross-ai: overlay disabled:'),
          sig: 'SIGTERM', withinMs: SELF_TEST_SIGNAL_EXIT_MS,
        },
        exit: 143,
        status: /^AIKIT-XAI status=signal .* exit=143 .* action=stop$/,
        check: (r) => {
          const lines = (r.stderr || '').split('\n');
          const notices = lines.filter((line) => line.startsWith('cross-ai: overlay disabled:'));
          return notices.length === 1 ? null : `notices ${notices.length}`;
        },
      },
      {
        name: 'overlay-row-used',
        setup: (c) => {
          const dir = path.join(c.home, '.config', 'ai-kit');
          fs.mkdirSync(dir, { recursive: true });
          fs.writeFileSync(path.join(dir, 'cross-ai-errors.json'), JSON.stringify([{
            id: 'user-acme-quota', tier: 3, cli: '*', route: '*', provider: '*', input: 'any',
            match: 'acme credits gone', class: 'quota', terminal: false,
            label: 'unverified', evidence: 'probe',
          }]));
          fs.writeFileSync(path.join(c.repo, 'fixtures.json'), JSON.stringify([
            { name: 'acme', cli: 'pi', stderr: 'acme credits gone' },
          ]));
          return null;
        },
        args: ['--classify-only', 'fixtures.json'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* action=stop$/,
        check: (r) => {
          const line = (r.stdout || '').split('\n').find(Boolean);
          const got = JSON.parse(line || '{}');
          if (got.rule !== 'user-acme-quota' || got.pattern !== 'unverified') return JSON.stringify(got);
          return (r.stderr || '').includes('cross-ai: overlay 1 rows') ? null : 'missing overlay count';
        },
      },
      {
        name: 'overlay-router-row-live',
        setup: (c) => {
          const dir = path.join(c.home, '.config', 'ai-kit');
          fs.mkdirSync(dir, { recursive: true });
          fs.writeFileSync(path.join(dir, 'cross-ai-errors.json'), JSON.stringify([{
            id: 'user-router-stop', tier: 2, cli: '*', route: 'router', provider: '*', input: 'any',
            match: 'acme router stop', class: 'quota', terminal: true,
            label: 'unverified', evidence: 'probe',
          }]));
          return null;
        },
        args: ['--prefer', 'pi', '--model-pi', 'fake/router-stop-hang', '--route-pi', 'router',
          '--timeout', '60'],
        config: { retry: { max_retries: 0, session_resets: 0, hard_waits_s: [600] } },
        exit: 75,
        status: /^AIKIT-XAI status=quota .* exit=75 .* action=stop$/,
        check: (r, ctx) => {
          if (ctx.elapsedMs >= scaledMs(10000)) return `not killed at ${ctx.elapsedMs}`;
          const tail = statusTail(r.stderr || '');
          return tail && tail.rule === 'user-router-stop' ? null : `rule=${tail && tail.rule}`;
        },
      },
      {
        name: 'overlay-router-row-unconfirmed',
        setup: (c) => {
          const dir = path.join(c.home, '.config', 'ai-kit');
          fs.mkdirSync(dir, { recursive: true });
          fs.writeFileSync(path.join(dir, 'cross-ai-errors.json'), JSON.stringify([{
            id: 'user-router-stop', tier: 2, cli: '*', route: 'router', provider: '*', input: 'any',
            match: 'acme router stop', class: 'quota', terminal: true,
            label: 'unverified', evidence: 'probe',
          }]));
          return null;
        },
        args: ['--prefer', 'pi', '--model-pi', 'fake/router-stop-hang', '--timeout', '3'],
        exit: 124,
        status: /^AIKIT-XAI status=timeout .* action=stop$/,
        check: (r) => {
          const tail = statusTail(r.stderr || '');
          return tail && tail.rule === '-' ? null : `unconfirmed rule=${tail && tail.rule}`;
        },
      },
      {
        name: 'overlay-bad-row-refused',
        setup: (c) => {
          const dir = path.join(c.home, '.config', 'ai-kit');
          fs.mkdirSync(dir, { recursive: true });
          const file = path.join(dir, 'cross-ai-errors.json');
          const good = {
            id: 'user-kept', tier: 3, cli: '*', route: '*', provider: '*', input: 'any',
            match: 'acme kept', class: 'quota', terminal: false, label: 'unverified', evidence: 'probe',
          };
          fs.writeFileSync(file, JSON.stringify([
            { ...good, id: 'user-doom', class: 'doom' },
            { ...good, id: 'user-nolabel', label: undefined },
            { ...good, id: 'code-429' },
            { ...good, id: 'user-direct', route: 'direct' },
            good,
          ]));
          fs.writeFileSync(path.join(c.repo, 'fixtures.json'), JSON.stringify([
            { name: 'kept', cli: 'pi', stderr: 'acme kept' },
          ]));
          c.overlayFile = file;
          return null;
        },
        args: ['--classify-only', 'fixtures.json'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* action=stop$/,
        check: (r, ctx) => {
          const got = JSON.parse((r.stdout || '').split('\n').find(Boolean) || '{}');
          if (got.rule !== 'user-kept') return `rule=${got.rule}`;
          const err = r.stderr || '';
          for (const id of ['user-doom', 'user-nolabel', 'code-429', 'user-direct']) {
            const line = err.split('\n').find((item) => item.startsWith(`cross-ai: overlay row ${id} refused`));
            if (!line || !line.includes(ctx.overlayFile)) return `missing refusal ${id}`;
          }
          return err.includes('cross-ai: overlay 1 rows') ? null : 'good row dropped';
        },
      },
      {
        // A FIFO overlay is refused by type before any read, so it can never block the runner.
        name: 'overlay-fifo-refused',
        setup: (c) => {
          const dir = path.join(c.home, '.config', 'ai-kit');
          fs.mkdirSync(dir, { recursive: true });
          const made = spawnSync('mkfifo', [path.join(dir, 'cross-ai-errors.json')]);
          if (made.status !== 0) return 'mkfifo unavailable';
          fs.writeFileSync(path.join(c.repo, 'fixtures.json'), JSON.stringify([
            { name: 'plain', cli: 'pi', stderr: '402 payment required' },
          ]));
          return null;
        },
        args: ['--classify-only', 'fixtures.json'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* action=stop$/,
        check: (r) => ((r.stderr || '').includes('not a regular file') ? null : 'missing notice'),
      },
      {
        name: 'overlay-malformed',
        setup: (c) => {
          const dir = path.join(c.home, '.config', 'ai-kit');
          fs.mkdirSync(dir, { recursive: true });
          fs.writeFileSync(path.join(dir, 'cross-ai-errors.json'), '[');
          fs.writeFileSync(path.join(c.repo, 'fixtures.json'), JSON.stringify([
            { name: 'plain', cli: 'pi', stderr: '402 payment required' },
          ]));
          return null;
        },
        args: ['--classify-only', 'fixtures.json'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* action=stop$/,
        check: (r) => {
          if (!(r.stderr || '').includes('not a JSON array')) return 'missing notice';
          const got = JSON.parse((r.stdout || '').split('\n').find(Boolean) || '{}');
          return got.status === 'billing' && got.rule === 'text-payment-required' ? null : JSON.stringify(got);
        },
      },
      {
        name: 'overlay-position',
        setup: (c) => {
          const dir = path.join(c.home, '.config', 'ai-kit');
          fs.mkdirSync(dir, { recursive: true });
          fs.writeFileSync(path.join(dir, 'cross-ai-errors.json'), JSON.stringify([
            {
              id: 'user-usage-acme', tier: 3, cli: '*', route: '*', provider: '*', input: 'any',
              match: 'usage limit \\(acme\\)', class: 'quota', terminal: false,
              label: 'unverified', evidence: 'probe',
            },
            {
              id: 'user-bare-403', tier: 6, cli: '*', route: '*', provider: '*', input: 'any',
              match: '\\b403\\b', class: 'quota', terminal: false,
              label: 'unverified', evidence: 'probe',
            },
          ]));
          fs.writeFileSync(path.join(c.repo, 'fixtures.json'), JSON.stringify([
            { name: 'acme', cli: 'pi', stderr: 'usage limit (acme)' },
            {
              name: 'kimi', cli: 'pi',
              stderr: "[403]: You've reached your 5-hour usage limit.",
            },
          ]));
          return null;
        },
        args: ['--classify-only', 'fixtures.json'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* action=stop$/,
        check: (r) => {
          const lines = (r.stdout || '').split('\n').filter(Boolean).map((line) => JSON.parse(line));
          if (lines[0]?.rule !== 'user-usage-acme') return `acme ${lines[0]?.rule}`;
          if (lines[1]?.rule !== 'text-usage-limit') return `kimi ${lines[1]?.rule}`;
          return null;
        },
      },
      {
        // A 429 inside a retry notice never kills: the bare-code rows are not terminal.
        name: 'retry-notice-429-no-kill',
        args: ['--prefer', 'pi', '--model-pi', 'fake/retry-notice-429', '--timeout', '60'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/retry-notice-429 exit=0 .* action=stop$/,
        check: (_r, ctx) => {
          const runs = ctx.calls.filter((l) => l.startsWith('pi ') && l !== 'pi rpc');
          return runs.length === 1 ? null : `pi calls ${ctx.calls.join('|')}`;
        },
      },
      {
        // A completed transient line on a timed-out attempt is a transient rung, and a
        // deadline this short cannot admit one, so the run stops before any rung.
        name: 'post-hoc-timeout-transient-stays',
        args: ['--prefer', 'pi', '--model-pi', 'fake/transient-hang', '--timeout', '3'],
        config: { backoffS: [30, 60] },
        exit: 124,
        status: new RegExp('^AIKIT-XAI status=timeout cli=pi model=fake/transient-hang ' +
          'exit=124 .* action=stop$'),
        check: (_r, ctx) => deadCheck(ctx, ['pi']),
      },
      {
        // An unterminated quota line plus a newline-free flood: the pre-trim match kills live.
        name: 'live-partial-flood',
        args: ['--prefer', 'pi', '--model-pi', 'fake/limit-partial-flood', '--timeout', '3'],
        exit: 75,
        status: new RegExp('^AIKIT-XAI status=quota cli=pi model=fake/limit-partial-flood ' +
          'exit=75 .* action=stop$'),
        check: (_r, ctx) => (
          ctx.elapsedMs >= scaledMs(15000) ? `elapsed ${ctx.elapsedMs}` : deadCheck(ctx, ['pi'])
        ),
      },
      {
        // A complete non-terminal 429 line never kills live; the post-hoc pass still labels quota.
        name: 'post-hoc-timeout-429',
        args: ['--prefer', 'pi', '--model-pi', 'fake/bare-429-hang', '--timeout', '3'],
        exit: 75,
        status: /^AIKIT-XAI status=quota cli=pi model=fake\/bare-429-hang exit=75 .* action=stop$/,
        check: (_r, ctx) => {
          if (ctx.elapsedMs < 2500) return `elapsed ${ctx.elapsedMs} (killed live)`;
          return deadCheck(ctx, ['pi']);
        },
      },
      {
        // A flood after a terminal line cannot hide the signal recorded at first sight.
        name: 'live-limit-flood',
        args: ['--prefer', 'pi', '--model-pi', 'fake/limit-flood', '--timeout', '60'],
        exit: 75,
        status: /^AIKIT-XAI status=quota cli=pi model=fake\/limit-flood exit=75 .* action=stop$/,
        check: (_r, ctx) => deadCheck(ctx, ['pi']),
      },
      {
        // turn.failed carrying limit text is terminal; the grace stops the child.
        name: 'live-codex-turn-failed',
        args: ['--prefer', 'codex', '--model-codex', 'fake-limit-codex', '--timeout', '60'],
        config: { prefer: ['codex'] },
        exit: 75,
        status: /^AIKIT-XAI status=quota cli=codex model=fake-limit-codex exit=75 .* action=stop$/,
        check: (_r, ctx) => (
          ctx.elapsedMs >= scaledMs(15000) ? `elapsed ${ctx.elapsedMs}` : deadCheck(ctx, ['codex'])
        ),
      },
      {
        // Ruling Q1: a bare codex error event is recorded, never a kill.
        name: 'live-codex-bare-error-no-kill',
        args: ['--prefer', 'codex', '--model-codex', 'fake-error-then-ok-codex', '--timeout', '60'],
        config: { prefer: ['codex'] },
        exit: 0,
        status: new RegExp('^AIKIT-XAI status=ok cli=codex model=fake-error-then-ok-codex ' +
          'exit=0 .* action=stop$'),
      },
      {
        // A bare codex error is never terminal, so the deadline passes and post-hoc labels quota.
        name: 'post-hoc-timeout-codex-error',
        args: [
          '--prefer', 'codex', '--model-codex', 'fake-bare-error-hang-codex', '--timeout', '3',
        ],
        config: { prefer: ['codex'] },
        exit: 75,
        status: new RegExp('^AIKIT-XAI status=quota cli=codex ' +
          'model=fake-bare-error-hang-codex exit=75 .* action=stop$'),
        check: (_r, ctx) => {
          if (ctx.elapsedMs < 2500) return `elapsed ${ctx.elapsedMs} (killed live)`;
          return deadCheck(ctx, ['codex']);
        },
      },
      {
        name: 'not-installed-codex',
        args: ['--prefer', 'codex', '--model-codex', 'x'],
        env: { PATH: `${path.join(tmp, 'bin-nocodex')}` },
        exit: 127,
        status: /^AIKIT-XAI status=not_installed .* exit=127 .* action=stop$/,
      },
      {
        name: 'sigterm-hang',
        args: ['--prefer', 'pi', '--model-pi', 'fake/hang', '--timeout', '60'],
        signal: { when: (c) => fs.existsSync(path.join(c.repo, 'gc.pid')), sig: 'SIGTERM' },
        exit: 143,
        // gc.pid is an untracked file the fake wrote, so the real tree is dirty.
        status: /^AIKIT-XAI status=signal cli=pi model=fake\/hang exit=143 .* tree=dirty action=stop$/,
        check: (_r, ctx) => deadCheck(ctx, ['pi', 'gc']),
      },
      {
        // CR-03/CR-04: a CLI that ignores SIGTERM after editing; the runner must report the
        // real tree and SIGKILL the group well inside run-with-timeout's 3 s grace.
        name: 'sigterm-stubborn',
        args: ['--prefer', 'pi', '--model-pi', 'fake/stubborn', '--timeout', '60'],
        signal: { when: (c) => fs.existsSync(path.join(c.repo, 'cli.ready')), sig: 'SIGTERM', withinMs: SELF_TEST_SIGNAL_EXIT_MS },
        exit: 143,
        status: /^AIKIT-XAI status=signal cli=pi model=fake\/stubborn exit=143 .* tree=dirty action=stop$/,
        check: (_r, ctx) => deadCheck(ctx, ['pi']),
      },
      {
        name: 'sigterm-twice',
        args: ['--prefer', 'pi', '--model-pi', 'fake/stubborn', '--timeout', '60'],
        signal: { when: (c) => fs.existsSync(path.join(c.repo, 'cli.ready')), sig: 'SIGTERM', again: 'SIGINT', withinMs: SELF_TEST_SIGNAL_EXIT_MS },
        exit: 143,
        status: /^AIKIT-XAI status=signal cli=pi model=fake\/stubborn exit=143 .* action=stop$/,
        check: (_r, ctx) => deadCheck(ctx, ['pi']),
      },
      {
        name: 'sigterm-backoff',
        args: ['--prefer', 'pi', '--model-pi', 'fake/overloaded', '--timeout', '200'],
        config: { retry: { base_s: 20 } },
        signal: { when: (c) => readOr(c.calls, '').includes('pi overloaded'), sig: 'SIGTERM', withinMs: SELF_TEST_SIGNAL_EXIT_MS },
        exit: 143,
        status: /^AIKIT-XAI status=signal cli=pi model=fake\/overloaded exit=143 .* tree=clean action=stop$/,
      },
      {
        // The harness itself: a runner killed mid-case leaves its CLI group behind; the
        // per-case reaper must still kill it.
        name: 'reap-after-failure',
        args: ['--prefer', 'pi', '--model-pi', 'fake/hang', '--timeout', '60'],
        signal: { when: (c) => fs.existsSync(path.join(c.repo, 'gc.pid')), sig: 'SIGKILL' },
        exit: 0,
        status: /^$/,
        expectFailure: true,
        afterReap: (c) => {
          const dead = deadCheck(c, ['pi', 'gc']);
          if (dead) return dead;
          const left = pidsUnder(c.repo);
          return left.length ? `survivors ${left.join(',')}` : null;
        },
      },
      {
        name: 'gcescape',
        args: ['--prefer', 'pi', '--model-pi', 'fake/gcescape', '--timeout', '2'],
        exit: 124,
        status: /^AIKIT-XAI status=timeout cli=pi model=fake\/gcescape exit=124 .* action=stop$/,
        check: (r, ctx) => {
          if (ctx.elapsedMs >= scaledMs(10000)) return `elapsed ${ctx.elapsedMs}`;
          const lines = (r.stderr || '').split('\n');
          const late = lines.filter((l) => l.includes('gc-late'));
          const statusIdx = lines.findIndex((l) => l.startsWith('AIKIT-XAI '));
          if (!(r.stderr || '').includes('gc-late')) return 'no gc-late';
          if (late.some((l) => lines.indexOf(l) >= statusIdx && statusIdx >= 0)) return 'gc-late after status';
          return ctx.pids.gc ? null : 'no gc pid recorded';
        },
      },
      {
        name: 'gcpipe',
        args: ['--prefer', 'pi', '--model-pi', 'fake/gcpipe', '--timeout', '60'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/gcpipe exit=0 .* action=stop$/,
        check: (_r, ctx) => (ctx.elapsedMs >= scaledMs(15000) ? `elapsed ${ctx.elapsedMs}` : deadCheck(ctx, ['gc'])),
      },
      {
        name: 'gcterm',
        args: ['--prefer', 'pi', '--model-pi', 'fake/gcterm', '--timeout', '60'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/gcterm exit=0 .* action=stop$/,
        check: (_r, ctx) => (ctx.elapsedMs >= scaledMs(15000) ? `elapsed ${ctx.elapsedMs}` : deadCheck(ctx, ['gc'])),
      },
      {
        name: 'git-before-fail',
        setup: (ctx) => { fs.writeFileSync(path.join(ctx.home, '.fake-git-fail'), '1'); return null; },
        args: ['--prefer', 'pi,cursor', '--model-pi', 'fake/ok', '--model-cursor', 'fake-ok-cursor'],
        exit: 1,
        status: new RegExp('^AIKIT-XAI status=git_error cli=pi model=fake/ok exit=1 cli_rc=- ' +
          'elapsed=\\d+s out=0 tree=unknown action=stop$'),
        check: (_r, ctx) => {
          if (ctx.calls.some((l) => l === 'pi ok' || l.startsWith('cursor-agent'))) return `calls=${ctx.calls.join(',')}`;
          return null;
        },
      },
      {
        name: 'git-after-fail',
        args: ['--prefer', 'pi,cursor', '--model-pi', 'fake/gitfail', '--model-cursor', 'fake-ok-cursor'],
        exit: 1,
        status: new RegExp('^AIKIT-XAI status=git_error cli=pi model=fake/gitfail exit=1 cli_rc=0' +
          ' elapsed=\\d+s out=\\d+ tree=unknown action=stop$'),
        check: (_r, ctx) => (ctx.calls.some((l) => l.startsWith('cursor-agent')) ? 'cursor ran' : null),
      },
      {
        name: 'git-hang',
        setup: (ctx) => { fs.writeFileSync(path.join(ctx.home, '.fake-git-hang'), '1'); return null; },
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok', '--timeout', '3'],
        exit: 1,
        status: new RegExp('^AIKIT-XAI status=git_timeout cli=pi model=fake/ok exit=1 cli_rc=- ' +
          'elapsed=\\d+s out=0 tree=unknown action=stop$'),
        check: (_r, ctx) => (ctx.elapsedMs >= scaledMs(10000) ? `elapsed ${ctx.elapsedMs}` : null),
      },
      {
        // D-34: outside any git work tree the CLI still runs, once, with tree=unknown.
        name: 'non-git-exec',
        setup: (c) => {
          fs.rmSync(path.join(c.repo, '.git'), { recursive: true, force: true });
          c.env.GIT_CEILING_DIRECTORIES = path.dirname(c.repo);
          return null;
        },
        args: [
          '--prefer', 'pi,cursor', '--model-pi', 'fake/ok', '--model-cursor', 'fake-ok-cursor',
        ],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=unknown action=stop$/,
        check: (r, ctx) => {
          if (!(r.stderr || '').includes('is not inside a git work tree')) {
            return 'missing tree line';
          }
          return ctx.calls.some((l) => l.startsWith('cursor-agent')) ? 'cursor ran' : null;
        },
      },
      {
        name: 'non-git-review',
        setup: (c) => {
          fs.rmSync(path.join(c.repo, '.git'), { recursive: true, force: true });
          c.env.GIT_CEILING_DIRECTORIES = path.dirname(c.repo);
          return null;
        },
        args: ['--mode', 'review', '--prefer', 'pi', '--model-pi', 'fake/review-ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=unknown action=stop$/,
        check: (r) => (
          (r.stderr || '').includes('cannot verify the read-only contract')
            ? null : 'missing review line'
        ),
      },
      {
        name: 'non-git-no-fallback',
        setup: (c) => {
          fs.rmSync(path.join(c.repo, '.git'), { recursive: true, force: true });
          c.env.GIT_CEILING_DIRECTORIES = path.dirname(c.repo);
          return null;
        },
        args: [
          '--prefer', 'pi,cursor', '--model-pi', 'fake/crash', '--model-cursor', 'fake-ok-cursor',
        ],
        exit: 1,
        status: /^AIKIT-XAI status=crash cli=pi .* tree=unknown action=stop$/,
        check: (_r, ctx) => (
          ctx.calls.some((l) => l.startsWith('cursor-agent')) ? 'cursor ran' : null
        ),
      },

      {
        // WR-12: git add records a nested repo as its HEAD only; an edit inside it still counts.
        name: 'submodule-edit',
        setup: nestedRepoSetup,
        args: ['--prefer', 'pi', '--model-pi', 'fake/subedit'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/subedit exit=0 .* tree=dirty action=stop$/,
      },
      {
        // U-3: an edit only to a gitignored file still reads dirty.
        name: 'ignored-edit',
        setup: ignoredFileSetup,
        args: ['--prefer', 'pi', '--model-pi', 'fake/ignorededit'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ignorededit exit=0 .* tree=dirty action=stop$/,
      },
      {
        // ...but a write inside a fully ignored dir (a cache) does not.
        name: 'ignored-dir-write',
        setup: ignoredFileSetup,
        args: ['--mode', 'review', '--prefer', 'pi', '--model-pi', 'fake/cachewrite'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/cachewrite exit=0 .* tree=clean action=stop$/,
      },
      {
        name: 'ignored-review-ok',
        setup: ignoredFileSetup,
        args: ['--mode', 'review', '--prefer', 'pi', '--model-pi', 'fake/review-ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/review-ok exit=0 .* tree=clean action=stop$/,
      },
      {
        name: 'submodule-review-ok',
        setup: nestedRepoSetup,
        args: ['--mode', 'review', '--prefer', 'pi', '--model-pi', 'fake/review-ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/review-ok exit=0 .* tree=clean action=stop$/,
      },
      {
        name: 'unborn-head-l10n',
        setup: (c) => {
          fs.rmSync(path.join(c.repo, '.git'), { recursive: true, force: true });
          spawnSync('git', ['init', '-q'], { cwd: c.repo, env: c.env });
          fs.writeFileSync(path.join(c.home, '.fake-git-l10n'), '1');
          return null;
        },
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
      },
      {
        name: 'bad-model',
        args: ['--prefer', 'pi,cursor', '--model-pi', 'fake/missing', '--model-cursor', 'fake-ok-cursor'],
        exit: 69,
        status: /^AIKIT-XAI status=bad_model cli=pi model=fake\/missing exit=69 .* tree=clean action=stop$/,
        check: (r, ctx) => {
          if (!(r.stderr || '').includes('bad_model')) return 'stderr missing bad_model';
          if (!ctx.calls.includes('pi rpc')) return 'missing pi rpc';
          if (ctx.calls.some((l) => l === 'pi missing')) return 'pi run should not happen';
          if (ctx.calls.some((l) => l.startsWith('cursor-agent'))) return 'cursor ran';
          return null;
        },
      },
      {
        name: 'model-suffix-pi',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok:high'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok:high exit=0 .* tree=dirty action=stop$/,
        check: (r) => ((r.stderr || '').includes('suffix :high is not validated') ? null : 'missing suffix note'),
      },
      {
        name: 'model-suffix-opencode',
        args: ['--prefer', 'opencode', '--model-opencode', 'fake/ok#high'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=opencode model=fake\/ok#high exit=0 .* tree=dirty action=stop$/,
      },
      {
        name: 'model-suffix-bad-base',
        args: ['--prefer', 'pi', '--model-pi', 'fake/missing:high'],
        exit: 69,
        status: /^AIKIT-XAI status=bad_model cli=pi model=fake\/missing:high exit=69 .* action=stop$/,
      },
      {
        name: 'bad-model-only',
        args: ['--prefer', 'pi', '--model-pi', 'fake/missing'],
        exit: 69,
        status: /^AIKIT-XAI status=bad_model cli=pi model=fake\/missing exit=69 .* action=stop$/,
      },
      {
        name: 'list-broken',
        env: { FAKE_PI_LIST: 'broken' },
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* action=stop$/,
        check: (r) => ((r.stderr || '').includes('model list unavailable (unparseable)') ? null : 'missing unparseable note'),
      },
      {
        name: 'list-fail',
        env: { FAKE_PI_LIST: 'fail' },
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* action=stop$/,
        check: (r) => ((r.stderr || '').includes('model list unavailable (exit 1)') ? null : 'missing exit 1 note'),
      },
      {
        name: 'list-zero',
        env: { FAKE_CURSOR_LIST: 'empty' },
        args: ['--prefer', 'cursor', '--model-cursor', 'fake-ok-cursor'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=cursor model=fake-ok-cursor exit=0 .* action=stop$/,
        check: (r) => ((r.stderr || '').includes('model list unavailable (no ids)') ? null : 'missing no ids note'),
      },
      {
        name: 'print-argv-no-preflight',
        env: { FAKE_PI_LIST: 'fail' },
        args: ['--print-argv', '--model-pi', 'fake/ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r, ctx) => {
          if ((r.stderr || '').includes('model list unavailable')) return 'preflight ran under print-argv';
          if (ctx.calls.length) return `calls=${ctx.calls.join(',')}`;
          return null;
        },
      },
      {
        name: 'list-hang',
        env: { FAKE_PI_LIST: 'hang' },
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok', '--timeout', '4'],
        exit: 124,
        // The CLI never ran, so it has no exit code to report (IN-07).
        status: /^AIKIT-XAI status=timeout cli=pi model=fake\/ok exit=124 cli_rc=- .* action=stop$/,
        check: (r, ctx) => {
          if (!(r.stderr || '').includes('model list unavailable (timeout)')) return 'missing timeout note';
          if (ctx.elapsedMs >= scaledMs(10000)) return `elapsed ${ctx.elapsedMs}`;
          if (!ctx.calls.includes('pi rpc')) return 'missing pi rpc';
          if (ctx.calls.some((l) => l === 'pi ok')) return 'pi ok should not run';
          return null;
        },
      },
      {
        name: 'flaky',
        args: ['--prefer', 'pi', '--model-pi', 'fake/flaky'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/flaky exit=0 .* action=stop$/,
        check: (r, ctx) => {
          const flaky = ctx.calls.filter((l) => l === 'pi flaky');
          if (flaky.length !== 2) return `flaky calls=${flaky.length}`;
          if (!/attempt=1 timeout=2\d\ds/.test(r.stderr)) return 'attempt line lacks the time left'; // IN-01
          const sids = readOr(ctx.env.FAKE_SIDS, '').trim().split('\n');
          if (sids.length !== 2) return `sids=${sids.join('|')}`;
          const [a, b] = sids.map((l) => l.split(' '));
          if (a[0] !== b[0]) return 'flaky switched session';
          if (b[1] !== 'resume') return `second input ${b[1]}`;
          const st = spawnSync('git', ['status', '--porcelain'], { cwd: ctx.repo, env: ctx.env, encoding: 'utf8' });
          const lines = (st.stdout || '').trim().split('\n').filter(Boolean);
          if (lines.length !== 1 || !lines[0].endsWith(' a.txt')) return `porcelain=${lines.join('|')}`;
          return null;
        },
      },
      {
        name: 'overloaded',
        args: ['--prefer', 'pi', '--model-pi', 'fake/overloaded'],
        exit: 75,
        status: /^AIKIT-XAI status=transient cli=pi model=fake\/overloaded exit=75 .* action=stop$/,
        check: (_r, ctx) => {
          const n = ctx.calls.filter((l) => l === 'pi overloaded').length;
          return n === 12 ? null : `overloaded calls=${n}`;
        },
      },
      {
        name: 'backoff-deadline',
        args: ['--prefer', 'pi', '--model-pi', 'fake/overloaded', '--timeout', '3'],
        config: { backoffS: [30, 60] },
        exit: 75,
        status: new RegExp('^AIKIT-XAI status=transient cli=pi model=fake/overloaded ' +
          'exit=75 cli_rc=1 .* tree=clean action=stop$'),
        check: (r, ctx) => {
          if (ctx.elapsedMs >= scaledMs(5000)) return `elapsed ${ctx.elapsedMs}ms`;
          const n = ctx.calls.filter((l) => l === 'pi overloaded').length;
          if (n !== 1) return `calls=${n}`;
          // 25.1-03: a deadline-cut transient series carries the caller's hint, not a bare 75.
          const tail = statusTail(r.stderr || '');
          return tail && tail.retry_after_s === '0' && tail.cycle === '0'
            ? null : `tail=${JSON.stringify(tail)}`;
        },
      },
      {
        // A quota-free timeout is a transient rung when the deadline still admits one.
        name: 'ladder-timeout-then-ok',
        args: ['--prefer', 'pi', '--model-pi', 'fake/hangonce', '--timeout', '120'],
        config: { attemptTimeoutS: 10, backoffS: [0, 0] },
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/hangonce exit=0 .* action=stop$/,
        check: (_r, ctx) => {
          const n = ctx.calls.filter((l) => l === 'pi hangonce').length;
          if (n !== 2) return `hangonce calls=${n}`;
          return deadCheck(ctx, ['pi']);
        },
      },
      {
        // After the attempt fewer than 60 s remain, so no rung is admitted.
        name: 'ladder-timeout-no-budget',
        args: ['--prefer', 'pi', '--model-pi', 'fake/hang', '--timeout', '15'],
        config: { attemptTimeoutS: 8 },
        exit: 124,
        status: /^AIKIT-XAI status=timeout cli=pi model=fake\/hang exit=124 .* action=stop$/,
        check: (_r, ctx) => {
          const n = ctx.calls.filter((l) => l === 'pi hang').length;
          if (n !== 1) return `hang calls=${n}`;
          return deadCheck(ctx, ['gc']);
        },
      },
      {
        // One series of 6, one session reset, a second series of 6. Same model every call.
        name: 'ladder-transient-exhausted',
        args: ['--prefer', 'pi', '--model-pi', 'fake/event400'],
        exit: 75,
        status: new RegExp('^AIKIT-XAI status=transient cli=pi model=fake/event400 ' +
          'exit=75 .* tree=clean action=stop$'),
        check: (r, ctx) => {
          const runs = ctx.calls.filter((l) => l.startsWith('pi ') && l !== 'pi rpc');
          if (runs.length !== 12) return `calls=${runs.length}`;
          if (runs.some((l) => l !== 'pi event400')) return `model changed: ${runs.join('|')}`;
          const rows = readOr(ctx.env.FAKE_SIDS, '').trim().split('\n').map((l) => l.split(' '));
          if (rows.length !== 12) return `sids=${rows.length}`;
          const ids = rows.map((r) => r[0]);
          if (new Set(ids.slice(0, 6)).size !== 1) return 'series 1 switched session';
          if (new Set(ids.slice(6)).size !== 1) return 'series 2 switched session';
          if (ids[6] === ids[0]) return 'the reset reused the first session id';
          const kinds = rows.map((r) => r[1]);
          if (kinds[0] !== 'prompt' || kinds[6] !== 'resume-plus') return `inputs ${kinds.join(',')}`;
          if (kinds.slice(1, 6).some((k) => k !== 'resume')) return `series 1 ${kinds.join(',')}`;
          if (kinds.slice(7).some((k) => k !== 'resume-plus')) return `series 2 ${kinds.join(',')}`;
          // 25.1-03: the spent transient series hands the caller its (zeroed) hard wait.
          const tail = statusTail(r.stderr || '');
          return tail && tail.retry_after_s === '0' && tail.cycle === '0'
            ? null : `tail=${JSON.stringify(tail)}`;
        },
      },
      {
        // Every changed path is named by the prompt, so the reset continues with the resume message.
        name: 'ladder-dirty-inside',
        stdin: '<tasks>\n<task>\n<files>a.txt</files>\n</task>\n</tasks>\n',
        args: ['--prefer', 'pi', '--model-pi', 'fake/dirtyevent400', '--no-preamble'],
        config: { retry: { max_retries: 1, session_resets: 1 } },
        exit: 75,
        status: new RegExp('^AIKIT-XAI status=transient cli=pi model=fake/dirtyevent400 ' +
          'exit=75 .* tree=dirty action=stop$'),
        check: (r, ctx) => {
          const rows = readOr(ctx.env.FAKE_SIDS, '').trim().split('\n').map((l) => l.split(' '));
          if (rows.length !== 4) return `calls=${rows.length}`;
          if (rows[0][1] !== 'prompt' || rows[1][1] !== 'resume') return `series 1 ${rows[1][1]}`;
          const fresh = rows.slice(2).map((row) => row[1]);
          if (fresh.some((k) => k !== 'resume-plus')) return `reset input ${fresh.join(',')}`;
          return null;
        },
      },
      {
        // A change the prompt never names stops the ladder at the first fresh session.
        name: 'ladder-dirty-outside',
        stdin: 'prompt\n',
        args: ['--prefer', 'pi', '--model-pi', 'fake/dirtyevent400', '--no-preamble'],
        config: { retry: { max_retries: 1, session_resets: 1 } },
        exit: 75,
        status: new RegExp('^AIKIT-XAI status=transient cli=pi model=fake/dirtyevent400 ' +
          'exit=75 .* tree=dirty action=stop$'),
        check: (r, ctx) => {
          const n = ctx.calls.filter((l) => l === 'pi dirtyevent400').length;
          if (n !== 2) return `calls=${n}`;
          return (r.stderr || '').includes('why=dirty-tree') ? null : 'missing dirty-tree line';
        },
      },
      {
        // The failed attempt's own edit is judged before a fresh session opens: cursor has no
        // session, so its next rung is new, and an edit the prompt never names stops it.
        name: 'ladder-new-dirty-cursor',
        stdin: 'prompt\n',
        args: ['--runtime', 'cursor', '--model', 'fake-dirty400-cursor', '--no-preamble'],
        config: { retry: { max_retries: 2, session_resets: 0, base_s: 0 } },
        exit: 75,
        status: new RegExp('^AIKIT-XAI status=transient cli=cursor model=fake-dirty400-cursor ' +
          'exit=75 .* tree=dirty action=stop$'),
        check: (r, ctx) => {
          const n = ctx.calls.filter((l) => l === 'cursor-agent fake-dirty400-cursor').length;
          if (n !== 1) return `calls=${n}`;
          return (r.stderr || '').includes('why=dirty-tree') ? null : 'missing dirty-tree line';
        },
      },
      {
        // Every fresh session is gated, not only the first: an edit made by a later failed
        // attempt stops the next one.
        name: 'ladder-later-dirty-cursor',
        stdin: 'prompt\n',
        args: ['--runtime', 'cursor', '--model', 'fake-latedirty-cursor', '--no-preamble'],
        config: { retry: { max_retries: 3, session_resets: 0, base_s: 0 } },
        exit: 75,
        status: new RegExp('^AIKIT-XAI status=transient cli=cursor model=fake-latedirty-cursor ' +
          'exit=75 .* tree=dirty action=stop$'),
        check: (r, ctx) => {
          const n = ctx.calls.filter((l) => l === 'cursor-agent fake-latedirty-cursor').length;
          if (n !== 2) return `calls=${n}`;
          return (r.stderr || '').includes('why=dirty-tree') ? null : 'missing dirty-tree line';
        },
      },
      {
        // Outside a git work tree nothing can account for an edit, so no fresh session starts.
        name: 'ladder-non-git',
        setup: (c) => {
          fs.rmSync(path.join(c.repo, '.git'), { recursive: true, force: true });
          c.env.GIT_CEILING_DIRECTORIES = path.dirname(c.repo);
          return null;
        },
        args: ['--prefer', 'pi', '--model-pi', 'fake/event400'],
        config: { retry: { max_retries: 1, session_resets: 1 } },
        exit: 75,
        status: new RegExp('^AIKIT-XAI status=transient cli=pi model=fake/event400 ' +
          'exit=75 .* tree=unknown action=stop$'),
        check: (r, ctx) => {
          const n = ctx.calls.filter((l) => l === 'pi event400').length;
          if (n !== 2) return `calls=${n}`;
          return (r.stderr || '').includes('why=dirty-tree') ? null : 'missing dirty-tree line';
        },
      },
      {
        // Cursor never prints a session id, so every soft retry is a new session and the
        // reset count does nothing (D-10). Rewritten with its edge cases in Task 3.
        name: 'ladder-no-session-cursor',
        args: ['--prefer', 'cursor', '--model-cursor', 'fake-event400-cursor'],
        exit: 75,
        status: new RegExp('^AIKIT-XAI status=transient cli=cursor ' +
          'model=fake-event400-cursor exit=75 .* action=stop$'),
        check: (r, ctx) => {
          const n = ctx.calls.filter((l) => l === 'cursor-agent fake-event400-cursor').length;
          if (n !== 6) return `cursor calls=${n}`;
          if ((r.stderr || '').includes('next=reset')) return 'a no-resume CLI was offered a reset';
          const news = (r.stderr || '').split('\n').filter((l) => l.startsWith('cross-ai: wait ') && l.includes('next=new'));
          return news.length === 5 ? null : `new-session waits=${news.length}`;
        },
      },
      {
        // No same-session retry: the first failure goes straight to the reset.
        name: 'soft-ladder-zero-retries',
        args: ['--prefer', 'pi', '--model-pi', 'fake/event400'],
        config: { retry: { max_retries: 0 } },
        exit: 75,
        status: /^AIKIT-XAI status=transient cli=pi model=fake\/event400 exit=75 .* action=stop$/,
        check: (_r, ctx) => {
          const n = ctx.calls.filter((l) => l === 'pi event400').length;
          if (n !== 2) return `calls=${n}`;
          const rows = readOr(ctx.env.FAKE_SIDS, '').trim().split('\n').map((l) => l.split(' '));
          if (rows.length !== 2) return `sids=${rows.length}`;
          if (rows[0][0] === rows[1][0]) return 'the reset reused the first session';
          if (rows[1][1] !== 'resume-plus') return `reset input ${rows[1][1]}`;
          return null;
        },
      },
      {
        // No session reset: one series, then the hard step.
        name: 'soft-ladder-zero-resets',
        args: ['--prefer', 'pi', '--model-pi', 'fake/event400'],
        config: { retry: { session_resets: 0 } },
        exit: 75,
        status: /^AIKIT-XAI status=transient cli=pi model=fake\/event400 exit=75 .* action=stop$/,
        check: (_r, ctx) => {
          const n = ctx.calls.filter((l) => l === 'pi event400').length;
          if (n !== 6) return `calls=${n}`;
          const rows = readOr(ctx.env.FAKE_SIDS, '').trim().split('\n').map((l) => l.split(' '));
          if (new Set(rows.map((row) => row[0])).size !== 1) return 'series switched session';
          return null;
        },
      },
      {
        // The 7th call is the reset, a new session with the task, never a 7th resume.
        name: 'soft-ladder-adjacency',
        args: ['--prefer', 'pi', '--model-pi', 'fake/event400'],
        exit: 75,
        status: /^AIKIT-XAI status=transient cli=pi model=fake\/event400 exit=75 .* action=stop$/,
        check: (_r, ctx) => {
          const rows = readOr(ctx.env.FAKE_SIDS, '').trim().split('\n').map((l) => l.split(' '));
          if (rows.length < 7) return `calls=${rows.length}`;
          const first = rows[0][0];
          if (rows.slice(0, 6).some((row) => row[0] !== first)) return 'series 1 switched session';
          if (rows[6][0] === first) return 'the 7th call resumed the first session';
          if (rows[6][1] !== 'resume-plus') return `7th input ${rows[6][1]}`;
          return null;
        },
      },
      {
        // Codex review has no read-only resume, so every retry is a fresh review run.
        name: 'ladder-codex-review-fresh',
        args: ['--mode', 'review', '--prefer', 'codex', '--model-codex', 'fake-event400-codex'],
        config: { prefer: ['codex'], retry: { max_retries: 2, session_resets: 1 } },
        exit: 75,
        status: new RegExp('^AIKIT-XAI status=transient cli=codex ' +
          'model=fake-event400-codex exit=75 .* action=stop$'),
        check: (_r, ctx) => {
          const n = ctx.calls.filter((l) => l === 'codex fake-event400-codex').length;
          if (n !== 3) return `codex calls=${n}`;
          if (ctx.calls.some((l) => l.startsWith('codex-resume'))) return 'review resumed';
          return null;
        },
      },
      {
        // Codex exec captures thread.started: one series resumes it, the reset starts another.
        name: 'ladder-codex-exec-resume',
        args: ['--prefer', 'codex', '--model-codex', 'fake-event400-codex'],
        config: { prefer: ['codex'], retry: { max_retries: 2, session_resets: 1 } },
        exit: 75,
        status: new RegExp('^AIKIT-XAI status=transient cli=codex ' +
          'model=fake-event400-codex exit=75 .* action=stop$'),
        check: (_r, ctx) => {
          const n = ctx.calls.filter((l) => l === 'codex fake-event400-codex').length;
          if (n !== 6) return `codex calls=${n}`;
          const resumed = ctx.calls.filter((l) => l === 'codex-resume fake-event400-codex');
          return resumed.length === 4 ? null : `resumes=${resumed.length}`;
        },
      },
      {
        // Review mode resumes pi with its read-only flags, then the reset starts a new session.
        name: 'ladder-review-resume',
        args: ['--mode', 'review', '--prefer', 'pi', '--model-pi', 'fake/review-event400'],
        config: { retry: { max_retries: 2, session_resets: 1 } },
        exit: 75,
        status: new RegExp('^AIKIT-XAI status=transient cli=pi ' +
          'model=fake/review-event400 exit=75 .* action=stop$'),
        check: (_r, ctx) => {
          const rows = readOr(ctx.env.FAKE_SIDS, '').trim().split('\n').map((l) => l.split(' '));
          if (rows.length !== 6) return `calls=${rows.length}`;
          const ids = rows.map((r) => r[0]);
          if (new Set(ids.slice(0, 3)).size !== 1) return 'series 1 switched session';
          if (new Set(ids.slice(3)).size !== 1) return 'series 2 switched session';
          if (ids[3] === ids[0]) return 'the reset reused the first session id';
          return null;
        },
      },
      {
        // Defaults with a resumable session: same x5, one reset, same x5, then the hard step,
        // for both soft classes.
        name: 'pure-ladder-sequence',
        pure: () => {
          const lim = {
            maxRetries: 5, sessionResets: 1, deadlineMs: 100000000, waitMs: 0, capMs: 14400000,
          };
          const want = [
            ...Array(5).fill('same/soft-retry'), 'reset/session-reset',
            ...Array(5).fill('same/soft-retry'), 'hard/soft-spent',
          ];
          for (const cls of ['transient', 'quota']) {
            const st = { retry: 0, resets: 0, canResume: true, firstMs: 0, cycle: 0 };
            const got = [];
            for (let i = 0; i < 12; i++) {
              const step = ladderNext(st, cls, 0, lim);
              got.push(`${step.next}/${step.why}`);
              if (step.next === 'same') st.retry += 1;
              else if (step.next === 'reset') { st.resets += 1; st.retry = 0; }
            }
            if (JSON.stringify(got) !== JSON.stringify(want)) return `${cls}: ${got.join(',')}`;
          }
          return null;
        },
      },
      {
        // The shared episode cap and the deadline admission apply to both soft classes.
        name: 'pure-ladder-cap-both-classes',
        pure: () => {
          const first = 1000000;
          const capMs = 14400000;
          for (const cls of ['transient', 'quota']) {
            const st = { retry: 0, resets: 0, canResume: true, firstMs: first, cycle: 0 };
            const capped = ladderNext(st, cls, first + capMs - 59999, {
              maxRetries: 5, sessionResets: 1, deadlineMs: first + capMs + 1000000,
              waitMs: 0, capMs,
            });
            if (capped.next !== 'stop' || capped.why !== 'cap') {
              return `${cls} cap=${capped.next}/${capped.why}`;
            }
            const inside = ladderNext(st, cls, first + capMs - 60000, {
              maxRetries: 5, sessionResets: 1, deadlineMs: first + capMs + 1000000,
              waitMs: 0, capMs,
            });
            if (inside.next !== 'same') return `${cls} inside cap=${inside.next}/${inside.why}`;
            const now = 5000000;
            const late = ladderNext(st, cls, now, {
              maxRetries: 5, sessionResets: 1, deadlineMs: now + 59999, waitMs: 0, capMs,
            });
            if (late.next !== 'stop' || late.why !== 'deadline') {
              return `${cls} deadline=${late.next}/${late.why}`;
            }
          }
          return null;
        },
      },
      {
        // The resolved soft series, logged: 5 same, the reset, 5 same, each within +-10% + 1 ms
        // and never under 0.9 x the previous wait of its series.
        name: 'soft-ladder-waits',
        args: ['--prefer', 'pi', '--model-pi', 'fake/event400'],
        config: { retry: { base_s: 0.02 } },
        exit: 75,
        status: new RegExp('^AIKIT-XAI status=transient cli=pi model=fake/event400 ' +
          'exit=75 .* action=stop$'),
        check: (r) => {
          const waits = (r.stderr || '').split('\n')
            .map((l) => l.match(/^cross-ai: wait ms=(\d+(?:\.\d+)?) next=(\S+) retry=(\d+)$/))
            .filter(Boolean);
          if (waits.length !== 11) return `wait lines=${waits.length}`;
          const nominal = [20, 30, 45, 67.5, 101.25];
          const want = [
            ...nominal.map((ms, i) => ['same', i + 1, ms]),
            ['reset', 1, 20],
            ...nominal.map((ms, i) => ['same', i + 1, ms]),
          ];
          let prev = 0;
          for (let i = 0; i < want.length; i++) {
            const [, step, k, ms] = [null, ...want[i]];
            const got = Number(waits[i][1]);
            if (waits[i][2] !== step || Number(waits[i][3]) !== k) {
              return `line ${i}: next=${waits[i][2]} retry=${waits[i][3]}`;
            }
            if (Math.abs(got - ms) > ms * 0.1 + 1) return `line ${i}: ${got} ms, want ${ms}`;
            if (k > 1 && got < 0.9 * prev) return `line ${i}: ${got} < 0.9 x ${prev}`;
            prev = k === 1 ? 0 : got;
          }
          return null;
        },
      },
      {
        // The ladder reads the values resolveRetry resolved: 1 retry, no reset, 2 calls.
        name: 'retry-config-drives-ladder',
        args: ['--prefer', 'pi', '--model-pi', 'fake/event400'],
        planningConfig: { workflow: { cross_ai_retry: { max_retries: 1, session_resets: 0 } } },
        exit: 75,
        status: new RegExp('^AIKIT-XAI status=transient cli=pi model=fake/event400 ' +
          'exit=75 .* action=stop$'),
        check: (_r, ctx) => {
          const n = ctx.calls.filter((l) => l === 'pi event400').length;
          return n === 2 ? null : `calls=${n}`;
        },
      },
      {
        // A transient episode near the cap gets one attempt and the cap stop, no soft series.
        name: 'soft-ladder-transient-cap',
        args: ['--prefer', 'pi', '--model-pi', 'fake/event400'],
        config: { capS: 2, retry: { base_s: 0.5 } },
        exit: 69,
        status: new RegExp('^AIKIT-XAI status=transient cli=pi model=fake/event400 ' +
          'exit=69 .* action=stop$'),
        check: (r, ctx) => {
          const n = ctx.calls.filter((l) => l === 'pi event400').length;
          if (n !== 1) return `calls=${n}`;
          const err = r.stderr || '';
          if (!err.includes('stopped=cap')) return 'missing stopped=cap';
          const report = err.split('\n').find((l) => l.startsWith('cross-ai: report '));
          if (!report || !report.includes('status=transient')) return `report=${report}`;
          return null;
        },
      },
      {
        // No session to continue: every soft retry is a new session, and no reset is offered.
        name: 'pure-ladder-no-resume',
        pure: () => {
          const lim = {
            maxRetries: 5, sessionResets: 1, deadlineMs: 100000000, waitMs: 0, capMs: 14400000,
          };
          const st = { retry: 0, resets: 0, canResume: false, firstMs: 0, cycle: 0 };
          const got = [];
          for (let i = 0; i < 6; i++) {
            const step = ladderNext(st, 'transient', 0, lim);
            got.push(`${step.next}/${step.why}`);
            if (step.next === 'new') st.retry += 1;
          }
          const want = [...Array(5).fill('new/soft-retry'), 'hard/soft-spent'];
          return JSON.stringify(got) === JSON.stringify(want) ? null : `steps=${got.join(',')}`;
        },
      },
      {
        // Hand-checked boundary: nowMs + waitMs + 60000 passes the deadline at +59999 and is
        // inside it at +60000 (waitMs 0).
        name: 'pure-ladder-deadline',
        pure: () => {
          const st = { retry: 0, resets: 0, canResume: true, firstMs: 0, cycle: 0 };
          const now = 1000000;
          const lim = { maxRetries: 5, sessionResets: 1, waitMs: 0, capMs: 14400000 };
          const early = ladderNext(st, 'transient', now, { ...lim, deadlineMs: now + 59999 });
          const on = ladderNext(st, 'transient', now, { ...lim, deadlineMs: now + 60000 });
          if (early.next !== 'stop' || early.why !== 'deadline') {
            return `early=${early.next}/${early.why}`;
          }
          if (on.next !== 'same' || on.why !== 'soft-retry') {
            return `boundary=${on.next}/${on.why}`;
          }
          return null;
        },
      },
      {
        name: 'pure-ladder-clamps',
        pure: () => {
          if (clampCapS(99999) !== 14400) return `99999 -> ${clampCapS(99999)}`;
          if (clampCapS(-1) !== 0) return `-1 -> ${clampCapS(-1)}`;
          if (clampAttemptTimeout(0) !== 0) return `0 -> ${clampAttemptTimeout(0)}`;
          if (clampAttemptTimeout(5) !== 10) return `5 -> ${clampAttemptTimeout(5)}`;
          if (clampAttemptTimeout(1801) !== 1800) return `1801 -> ${clampAttemptTimeout(1801)}`;
          return null;
        },
      },
      {
        name: 'load-factor-math',
        pure: () => {
          const want = [[0, 1], [0.5, 1], [1, 1], [2.5, 2.5], [4, 4], [10, 4], [NaN, 1], [Infinity, 1]];
          for (const [reading, f] of want) {
            if (loadFactor(reading) !== f) return `loadFactor(${reading}) -> ${loadFactor(reading)} expected ${f}`;
          }
          if (scaledMs(1001, 1.5) !== 1502) return `scaledMs(1001, 1.5) -> ${scaledMs(1001, 1.5)}`;
          if (scaledMs(1000, 1) !== 1000) return `scaledMs(1000, 1) -> ${scaledMs(1000, 1)}`;
          return null;
        },
      },
      {
        // A timeout class walks the soft series; a spent series ends transient, a pre-series
        // deadline stop stays a timeout.
        name: 'pure-ladder-timeout',
        pure: () => {
          const lim = {
            maxRetries: 5, sessionResets: 1, deadlineMs: 100000000, waitMs: 0, capMs: 14400000,
          };
          const st = { retry: 0, resets: 0, canResume: true, firstMs: 0, cycle: 0 };
          const first = ladderNext(st, 'transient', 0, lim);
          if (first.next !== 'same') return `timeout class did not walk: ${first.next}`;
          const spent = ladderStop({ why: 'soft-spent' }, true, true, 'crash');
          if (spent.status !== 'transient' || spent.timedOut) return `spent stop ${spent.status}`;
          const early = ladderStop({ why: 'deadline' }, true, false, 'crash');
          if (early.status !== 'timeout' || !early.timedOut) return `deadline stop ${early.status}`;
          return null;
        },
      },
      {
        // A router quota walks the same soft series and ends on the hard step, never a cooldown.
        name: 'pure-ladder-quota-cycle',
        pure: () => {
          const lim = {
            maxRetries: 5, sessionResets: 1, deadlineMs: 100000000, waitMs: 0, capMs: 14400000,
          };
          const st = { retry: 0, resets: 0, canResume: true, firstMs: 0, cycle: 0 };
          const got = [];
          for (let i = 0; i < 12; i++) {
            const step = ladderNext(st, 'quota', 0, lim);
            got.push(`${step.next}/${step.why}`);
            if (step.next === 'same') st.retry += 1;
            else if (step.next === 'reset') { st.resets += 1; st.retry = 0; }
          }
          const want = [
            ...Array(5).fill('same/soft-retry'), 'reset/session-reset',
            ...Array(5).fill('same/soft-retry'), 'hard/soft-spent',
          ];
          return JSON.stringify(got) === JSON.stringify(want) ? null : `steps=${got.join(',')}`;
        },
      },
      {
        // Exactly 60 s of cap headroom is inside; one millisecond less is past it.
        name: 'pure-ladder-cap-boundary',
        pure: () => {
          const first = 1000000;
          const capMs = 14400000;
          const st = { retry: 0, resets: 0, canResume: true, firstMs: first, cycle: 0 };
          const lim = { maxRetries: 5, sessionResets: 1, capMs, deadlineMs: 100000000, waitMs: 0 };
          const inside = ladderNext(st, 'quota', first + capMs - 60000, lim);
          if (inside.next !== 'same') return `inside=${inside.next}/${inside.why}`;
          const past = ladderNext(st, 'quota', first + capMs - 59999, lim);
          return past.next === 'stop' && past.why === 'cap'
            ? null : `past=${past.next}/${past.why}`;
        },
      },
      {
        // The cap never exceeds 14400 s and a negative one is 0.
        name: 'pure-ladder-cap-clamp',
        pure: () => {
          if (clampCapS(99999) !== 14400) return `capS=${clampCapS(99999)}`;
          return clampCapS(-5) === 0 ? null : `capS=${clampCapS(-5)}`;
        },
      },
      {
        // The caller's hard tier, pure: one wait per cycle from the list, the list's end and a
        // wait past the cap left both stop, and the boundary sits on the wait itself.
        name: 'pure-hard-wait',
        pure: () => {
          const waits = [600, 900, 1800];
          const seq = [0, 1, 2].map((c) => hardWaitFor(c, waits, 14400));
          const want = [
            { retryAfterS: 600, cycle: 0 }, { retryAfterS: 900, cycle: 1 },
            { retryAfterS: 1800, cycle: 2 },
          ];
          if (JSON.stringify(seq) !== JSON.stringify(want)) return `waits=${JSON.stringify(seq)}`;
          const onBoundary = hardWaitFor(1, waits, 900);
          if (onBoundary.retryAfterS !== 900 || onBoundary.cycle !== 1) {
            return `boundary=${JSON.stringify(onBoundary)}`;
          }
          const capped = hardWaitFor(1, waits, 899);
          if (!capped || capped.stop !== 'cap') return `capped=${JSON.stringify(capped)}`;
          const spent = hardWaitFor(3, waits, 14400);
          if (!spent || spent.stop !== 'hard-waits') return `spent=${JSON.stringify(spent)}`;
          const short = hardWaitFor(1, [60], 1e9);
          return short && short.stop === 'hard-waits' ? null : `short=${JSON.stringify(short)}`;
        },
      },
      {
        // An off-router quota and an inferred route never start a cycle.
        name: 'pure-ladder-plain-quota',
        pure: () => {
          const step = ladderNext(
            { retry: 0, resets: 0, canResume: true, firstMs: 0, cycle: 0 }, 'stop', 0,
            { maxRetries: 5, sessionResets: 1, deadlineMs: 100000000, capMs: 14400000, waitMs: 0 },
          );
          return step.next === 'stop' && step.why === 'class'
            ? null : `got=${step.next}/${step.why}`;
        },
      },
      {
        name: 'pure-ladder-inferred-no-cycle',
        pure: () => {
          const step = ladderNext(
            { retry: 0, resets: 0, canResume: true, firstMs: 0, cycle: 0 }, 'stop', 0,
            { maxRetries: 5, sessionResets: 1, deadlineMs: 100000000, capMs: 14400000, waitMs: 0 },
          );
          return step.next === 'hard' ? 'inferred route reached the hard step' : null;
        },
      },
      {
        name: 'pure-prompt-files',
        pure: () => {
          const text = '<files>`a.txt`, "./b.txt", c.txt</files>\n' +
            '<files>d.txt, </files>\nnotes <files>e.txt</files>';
          const got = [...promptFiles(text)].sort();
          const want = ['a.txt', 'b.txt', 'c.txt', 'd.txt', 'e.txt'];
          return JSON.stringify(got) === JSON.stringify(want)
            ? null : `files=${got.join(',')}`;
        },
      },
      {
        name: 'review-ok',
        args: ['--mode', 'review', '--prefer', 'pi', '--model-pi', 'fake/review-ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/review-ok exit=0 .* tree=clean action=stop$/,
      },
      {
        name: 'review-commit',
        args: ['--mode', 'review', '--prefer', 'pi', '--model-pi', 'fake/review-commit'],
        exit: 1,
        status: /^AIKIT-XAI status=contract_violation cli=pi model=fake\/review-commit exit=1 .* action=stop$/,
        check: (_r, ctx) => (fs.existsSync(path.join(ctx.home, '.fake-committed')) ? null : 'fake never committed'),
      },
      {
        name: 'review-edit',
        args: ['--mode', 'review', '--prefer', 'pi', '--model-pi', 'fake/review-edit'],
        exit: 1,
        status: /^AIKIT-XAI status=contract_violation cli=pi model=fake\/review-edit exit=1 .* action=stop$/,
      },
      {
        name: 'review-edit-no-fallback',
        args: ['--mode', 'review', '--prefer', 'pi,cursor', '--model-pi', 'fake/review-edit', '--model-cursor', 'fake-ok-cursor'],
        exit: 1,
        status: /^AIKIT-XAI status=contract_violation .* action=stop$/,
        check: (_r, ctx) => (ctx.calls.some((l) => l.startsWith('cursor-agent')) ? 'cursor ran' : null),
      },
      {
        name: 'review-gitfail',
        args: ['--mode', 'review', '--prefer', 'pi', '--model-pi', 'fake/review-gitfail'],
        exit: 1,
        status: new RegExp('^AIKIT-XAI status=git_error cli=pi model=fake/review-gitfail exit=1 ' +
          '.* tree=unknown action=stop$'),
      },
      {
        name: 'review-git-before-fail',
        setup: (ctx) => { fs.writeFileSync(path.join(ctx.home, '.fake-git-fail'), '1'); return null; },
        args: ['--mode', 'review', '--prefer', 'pi', '--model-pi', 'fake/review-ok'],
        exit: 1,
        status: /^AIKIT-XAI status=git_error .* tree=unknown action=stop$/,
        check: (_r, ctx) => (ctx.calls.some((l) => l.startsWith('pi ')) ? `calls=${ctx.calls.join(',')}` : null),
      },
      {
        name: 'review-flaky-edit',
        args: ['--mode', 'review', '--prefer', 'pi', '--model-pi', 'fake/review-flaky-edit'],
        exit: 1,
        status: /^AIKIT-XAI status=contract_violation cli=pi model=fake\/review-flaky-edit exit=1 .* action=stop$/,
        check: (_r, ctx) => {
          const n = ctx.calls.filter((l) => l === 'pi review-flaky-edit').length;
          return n === 1 ? null : `calls=${n}`;
        },
      },
      {
        // A review-mode same-session retry carries the runtime's own resume flag, never a widening.
        name: 'review-resume-cursor',
        args: ['--mode', 'review', '--runtime', 'cursor', '--model', 'fake-flaky-cursor'],
        config: { retry: { max_retries: 1, session_resets: 0, base_s: 0 } },
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=cursor model=fake-flaky-cursor exit=0 .* action=stop$/,
        check: (_r, ctx) => {
          const calls = ctx.calls.filter((l) => l.startsWith('cursor-agent flaky'));
          return calls.join('|') === 'cursor-agent flaky resume=-|cursor-agent flaky resume=c3' ? null : calls.join('|');
        },
      },
      {
        name: 'claude-exec-usage',
        args: ['--prefer', 'claude', '--mode', 'exec', '--model-claude', 'fake-ok'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
        check: (r) => ((r.stderr || '').includes('claude is review-only') ? null : 'missing review-only line'),
      },
      {
        // A later review-only entry is ignored, never started, and never rejects the first.
        name: 'review-only-later-menu-ok',
        args: ['--prefer', 'pi,claude', '--mode', 'exec', '--model-pi', 'fake/ok', '--model-claude', 'fake-ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        check: (r, ctx) => {
          if ((r.stderr || '').includes('is review-only')) return 'review-only refusal';
          if (!(r.stderr || '').includes('ignored: claude')) return 'missing ignored-entries note';
          if (ctx.calls.some((l) => l.startsWith('claude '))) return 'claude ran';
          return ctx.calls.some((l) => l.startsWith('pi ')) ? null : 'pi did not run';
        },
      },
      {
        name: 'prefer-proto-key',
        args: ['--prefer', 'constructor', '--model-constructor', 'x'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
      },
      {
        name: 'claude-review-ok',
        args: ['--prefer', 'claude', '--mode', 'review', '--model-claude', 'fake-ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=claude model=fake-ok exit=0 .* tree=clean action=stop$/,
      },
      {
        name: 'no-preamble-len',
        args: ['--mode', 'review', '--no-preamble', '--prefer', 'pi', '--model-pi', 'fake/echo-len'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const want = Buffer.byteLength('prompt\n', 'utf8');
          return r.stdout.trim() === String(want) ? null : `stdout=${JSON.stringify(r.stdout.trim())} want=${want}`;
        },
      },
      {
        name: 'preamble-len',
        args: ['--mode', 'review', '--prefer', 'pi', '--model-pi', 'fake/echo-len'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const base = Buffer.byteLength('prompt\n', 'utf8');
          const got = Number(r.stdout.trim());
          return got > base ? null : `stdout len ${got} not > ${base}`;
        },
      },
      {
        name: 'argv-retry-codex-review',
        args: ['--print-argv', '--mode', 'review', '--prefer', 'codex', '--model-codex', 'x'],
        config: { prefer: ['codex'] },
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const stdoutLine = (r.stdout || '').split('\n').find((l) => l.startsWith('codex\t'));
          if (!stdoutLine) return 'missing codex stdout';
          const reviewArgv = stdoutLine.split('\t')[2];
          const err = r.stderr || '';
          if (!err.includes('cross-ai: rung1 codex unavailable')) return 'rung 1 was available';
          const m = err.match(/cross-ai: rung2 codex argv=(\S+)/);
          if (!m) return 'missing rung2 line';
          if (m[1] !== reviewArgv) return 'rung2 argv mismatch';
          const parsed = JSON.parse(m[1]);
          if (!parsed.includes('--sandbox') || !parsed.includes('read-only')) return 'missing sandbox';
          if (parsed.some((t) => String(t).includes('resume'))) return 'has resume';
          return null;
        },
      },
      {
        name: 'argv-retry-codex-exec',
        args: ['--print-argv', '--mode', 'exec', '--prefer', 'codex', '--model-codex', 'x',
          '--codex-effort', 'high', '--codex-service-tier', 'flex'],
        config: { prefer: ['codex'] },
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const m = (r.stderr || '').match(/cross-ai: rung1 codex argv=(\S+)/);
          if (!m) return 'missing rung1 line';
          const parsed = JSON.parse(m[1]);
          if (!parsed.includes('resume')) return 'missing resume';
          if (!parsed.includes('--dangerously-bypass-approvals-and-sandbox')) return 'missing bypass';
          for (const k of ['model_reasoning_effort=high', 'service_tier=flex']) {
            if (!parsed.includes(k)) return `rung1 argv missing ${k}`;
          }
          return null;
        },
      },
      {
        // Rung 1 reopens the same pi session; rung 2 differs only by the session id.
        name: 'argv-retry-pi-review',
        args: ['--print-argv', '--mode', 'review', '--prefer', 'pi', '--model-pi', 'fake/ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const line = (r.stdout || '').split('\n').find((l) => l.startsWith('pi\t'));
          const first = JSON.parse(line.split('\t')[2]);
          const err = r.stderr || '';
          const one = err.match(/cross-ai: rung1 pi argv=(\S+)/);
          const two = err.match(/cross-ai: rung2 pi argv=(\S+)/);
          if (!one || !two) return 'missing rung line';
          const rung1 = JSON.parse(one[1]);
          const rung2 = JSON.parse(two[1]);
          if (JSON.stringify(rung1) !== JSON.stringify(first)) {
            return 'rung1 differs from the first argv';
          }
          const sid = (a) => a[a.indexOf('--session-id') + 1];
          if (sid(rung2) === sid(first)) return 'rung2 reuses the session id';
          const same = (a) => JSON.stringify(a.filter((t) => t !== sid(a)));
          if (same(rung2) !== same(first)) return 'rung2 differs beyond the session id';
          for (const f of ['--tools', 'read,grep,find,ls', '--no-mcp', '--no-context-files']) {
            if (!rung1.includes(f)) return `resumed review argv missing ${f}`;
          }
          return null;
        },
      },
      {
        name: 'argv-retry-cursor-review',
        args: ['--print-argv', '--mode', 'review', '--prefer', 'cursor', '--model-cursor', 'x'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const stdoutLine = (r.stdout || '').split('\n').find((l) => l.startsWith('cursor\t'));
          if (!stdoutLine) return 'missing cursor stdout';
          const review = JSON.parse(stdoutLine.split('\t')[2]);
          const m = (r.stderr || '').match(/cross-ai: rung1 cursor argv=(\S+)/);
          if (!m) return 'missing rung1 line';
          const parsed = JSON.parse(m[1]);
          if (!parsed.includes('--mode') || parsed[parsed.indexOf('--mode') + 1] !== 'ask') {
            return 'lost --mode ask';
          }
          if (!parsed.includes('--resume')) return 'missing --resume';
          const dropped = parsed.filter((t) => t !== '--resume' && t !== '<sid>');
          if (JSON.stringify(dropped) !== JSON.stringify(review)) {
            return 'rung1 differs beyond --resume';
          }
          return null;
        },
      },
      {
        // Nominal series at the defaults, then the 10% ordering rule at factors near 1.
        name: 'pure-soft-waits',
        pure: () => {
          const mid = { base_s: 1, factor: 1.5 };
          const series = [1, 2, 3, 4, 5].map((k) => softWaitMs(mid, k, () => 0.5));
          const want = [1000, 1500, 2250, 3375, 5063];
          if (JSON.stringify(series) !== JSON.stringify(want)) return `mid=${series.join(',')}`;
          for (let i = 1; i < series.length; i++) {
            if (!(series[i] > series[i - 1])) return `not increasing at ${i}`;
          }
          for (const factor of [1.5, 1.01, 1.0]) {
            const retry = { base_s: 1, factor };
            // Alternating 1 then 0: the two jitter extremes, with the previous wait threaded.
            let flip = 0;
            const alt = () => { flip = 1 - flip; return flip; };
            let prev = 0;
            for (let k = 1; k <= 5; k++) {
              const ms = softWaitMs(retry, k, alt, prev);
              const nominal = 1000 * factor ** (k - 1);
              if (ms < Math.ceil(0.9 * prev)) return `factor ${factor} k ${k} below 0.9 x ${prev}`;
              // Half a millisecond: the +-10% is applied before rounding to the nearest ms.
              if (Math.abs(ms - nominal) > nominal * 0.1 + 0.5) {
                return `factor ${factor} k ${k} = ${ms} outside +-10% of ${nominal}`;
              }
              prev = ms;
            }
            if (factor > 1) {
              let prevN = 0;
              for (let k = 1; k <= 5; k++) {
                const ms = softWaitMs(retry, k, () => 0.5);
                if (k > 1 && !(ms > prevN)) return `nominal not increasing at factor ${factor} k ${k}`;
                prevN = ms;
              }
            }
          }
          const edges = { base_s: 2, factor: 1.5 };
          for (const rand of [() => 0, () => 0.999]) {
            const ms = softWaitMs(edges, 2, rand);
            const nominal = 3000;
            if (Math.abs(ms - nominal) > nominal * 0.1 + 0.5) return `edge ${ms}`;
          }
          return null;
        },
      },
      {
        name: 'pure-retry-defaults',
        pure: () => {
          const want = { base_s: 1, factor: 1.5, max_retries: 5, session_resets: 1 };
          for (const [k, v] of Object.entries(want)) {
            if (RETRY_DEFAULTS[k] !== v) return `${k}=${RETRY_DEFAULTS[k]}`;
          }
          if (JSON.stringify([...RETRY_DEFAULTS.hard_waits_s]) !== JSON.stringify([600, 900, 1800])) {
            return `hard_waits_s=${RETRY_DEFAULTS.hard_waits_s}`;
          }
          const secs = [1, 2, 3, 4, 5].map((k) => softWaitMs(RETRY_DEFAULTS, k, () => 0.5) / 1000);
          // 1, 1.5 and 2.25 are exact; one decimal only after 2.25 (SPEC R7 precision).
          const shown = secs.map((s) => (s === 1 || s === 1.5 || s === 2.25 ? s : Math.round(s * 10) / 10));
          const expect = [1, 1.5, 2.25, 3.4, 5.1];
          if (JSON.stringify(shown) !== JSON.stringify(expect)) return `secs=${shown.join(',')}`;
          for (let i = 1; i < secs.length; i++) {
            if (!(secs[i] > secs[i - 1])) return `defaults not increasing at ${i}`;
          }
          return null;
        },
      },
      {
        // Inclusive limits pass; one step outside, a wrong type and an unknown key are refused.
        name: 'pure-retry-validate',
        pure: () => {
          const cap = 14400;
          const ok = [
            ['base_s', 0], ['base_s', 60], ['factor', 1], ['factor', 3],
            ['max_retries', 0], ['max_retries', 10], ['session_resets', 0], ['session_resets', 3],
            ['hard_waits_s', [0]], ['hard_waits_s', [0, 1, 2, 3, 4, cap]],
          ];
          for (const [key, value] of ok) {
            const reason = validateRetryKey(key, value, cap);
            if (reason) return `${key} ${JSON.stringify(value)} refused: ${reason}`;
          }
          const bad = [
            ['base_s', -0.01], ['base_s', 60.01], ['factor', 0.99], ['factor', 3.01],
            ['max_retries', -1], ['max_retries', 1.5], ['max_retries', 11], ['session_resets', 4],
            ['hard_waits_s', []], ['hard_waits_s', [0, 1, 2, 3, 4, 5, 6]],
            ['hard_waits_s', [cap + 1]], ['hard_waits_s', [1.5]],
            ['base_s', true], ['factor', '1'], ['max_retries', NaN], ['cap_s', 1],
          ];
          for (const [key, value] of bad) {
            if (validateRetryKey(key, value, cap) === null) {
              return `${key} ${JSON.stringify(value)} accepted`;
            }
          }
          if (validateRetryKey('hard_waits_s', [0], 0) !== null) return '[0] refused at capS 0';
          if (validateRetryKey('hard_waits_s', [1], 0) === null) return '[1] accepted at capS 0';
          return null;
        },
      },
      {
        name: 'retry-config-project',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        planningConfig: { workflow: { cross_ai_retry: { max_retries: 1, session_resets: 0 } } },
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        check: (r) => {
          const lines = (r.stderr || '').split('\n').filter((l) => l.startsWith('cross-ai: retry '));
          if (lines.length !== 1) return `retry lines=${lines.length}`;
          const want = 'cross-ai: retry base_s=0 factor=1.5 max_retries=1 session_resets=0 ' +
            'hard_waits_s=0,0,0 cap_s=14400';
          return lines[0] === want ? null : lines[0];
        },
      },
      {
        name: 'retry-config-user',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          const dir = path.join(c.home, '.config', 'ai-kit');
          fs.mkdirSync(dir, { recursive: true });
          fs.writeFileSync(path.join(dir, 'cross-ai.json'), JSON.stringify({
            cross_ai_retry: { max_retries: 2, session_resets: 0 },
          }));
          return null;
        },
        check: (r) => retryLine(r, 'max_retries=2 session_resets=0'),
      },
      {
        // The project key wins where both set it; the user key fills a key the project lacks.
        name: 'retry-config-per-key',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        planningConfig: { workflow: { cross_ai_retry: { max_retries: 1 } } },
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          const dir = path.join(c.home, '.config', 'ai-kit');
          fs.mkdirSync(dir, { recursive: true });
          fs.writeFileSync(path.join(dir, 'cross-ai.json'), JSON.stringify({
            cross_ai_retry: { max_retries: 3, session_resets: 0 },
          }));
          return null;
        },
        check: (r) => retryLine(r, 'max_retries=1 session_resets=0'),
      },
      {
        name: 'retry-config-workstream',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        env: { GSD_WORKSTREAM: 'ws1' },
        planningConfig: { workflow: { cross_ai_retry: { max_retries: 2 } } },
        workstream: { ws: 'ws1', config: { workflow: { cross_ai_retry: { max_retries: 1 } } } },
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        check: (r) => retryLine(r, 'max_retries=1'),
      },
      {
        // A scoped file without the key falls through to the root config.
        name: 'retry-config-workstream-fallback',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        env: { GSD_WORKSTREAM: 'ws1' },
        planningConfig: { workflow: { cross_ai_retry: { max_retries: 2 } } },
        workstream: { ws: 'ws1', config: { workflow: {} } },
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        check: (r) => retryLine(r, 'max_retries=2'),
      },
      {
        name: 'retry-config-refused',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        planningConfig: { workflow: { cross_ai_retry: { base_s: 61, max_retries: '1' } } },
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          const dir = path.join(c.home, '.config', 'ai-kit');
          fs.mkdirSync(dir, { recursive: true });
          fs.writeFileSync(path.join(dir, 'cross-ai.json'), JSON.stringify({
            cross_ai_retry: { max_retries: 1, session_resets: 0 },
          }));
          return null;
        },
        check: (r) => {
          const err = r.stderr || '';
          for (const key of ['base_s', 'max_retries']) {
            const line = `cross-ai: config cross_ai_retry.${key} refused (.planning/config.json):`;
            if (!err.includes(line)) return `missing refusal ${key}`;
          }
          return retryLine(r, 'base_s=0') || retryLine(r, 'max_retries=1');
        },
      },
      {
        // A FIFO user retry file is refused by type before any read and the run goes on.
        name: 'retry-config-fifo',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* action=stop$/,
        setup: (c) => {
          const dir = path.join(c.home, '.config', 'ai-kit');
          fs.mkdirSync(dir, { recursive: true });
          const made = spawnSync('mkfifo', [path.join(dir, 'cross-ai.json')]);
          return made.status === 0 ? null : 'mkfifo unavailable';
        },
        check: (r) => ((r.stderr || '').includes('not a regular file') ? null : 'missing notice'),
      },
      {
        name: 'retry-config-malformed',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          fs.mkdirSync(path.join(c.repo, '.planning'), { recursive: true });
          fs.writeFileSync(path.join(c.repo, '.planning', 'config.json'), '{');
          return null;
        },
        check: (r) => {
          const notice = 'cross-ai: config .planning/config.json not a JSON object; ' +
            'retry keys from the next source';
          if (!(r.stderr || '').includes(notice)) return 'missing malformed notice';
          return retryLine(r, 'base_s=0 factor=1.5 max_retries=5 session_resets=1 hard_waits_s=0,0,0 cap_s=14400');
        },
      },
      {
        name: 'retry-config-unknown-key',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        planningConfig: { workflow: { cross_ai_retry: { cap_s: 99999 } } },
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        check: (r) => {
          const notice = 'cross-ai: config cross_ai_retry.cap_s refused (.planning/config.json): unknown key';
          if (!(r.stderr || '').includes(notice)) return 'missing unknown-key notice';
          return retryLine(r, 'cap_s=14400');
        },
      },
      {
        name: 'retry-config-caps-clamp',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        config: { capS: 99999 },
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        check: (r) => {
          const notice = 'cross-ai: config capS 99999 refused (CONFIG): above 14400; using 14400';
          if (!(r.stderr || '').includes(notice)) return 'missing capS notice';
          return retryLine(r, 'cap_s=14400');
        },
      },
      {
        name: 'retry-config-read-only',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        planningConfig: { workflow: { cross_ai_retry: { max_retries: 1 } } },
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        second: {
          args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
          stdin: 'do the thing\n',
          exit: 0,
          status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        },
        setup: (c) => {
          const dir = path.join(c.home, '.config', 'ai-kit');
          fs.mkdirSync(dir, { recursive: true });
          fs.writeFileSync(path.join(dir, 'cross-ai.json'), JSON.stringify({
            cross_ai_retry: { session_resets: 0 },
          }));
          const stamp = (p) => {
            const st = fs.statSync(p);
            return { bytes: fs.readFileSync(p), mtime: st.mtimeMs };
          };
          c.retryStamp = {
            project: stamp(path.join(c.repo, '.planning', 'config.json')),
            user: stamp(path.join(dir, 'cross-ai.json')),
          };
          return null;
        },
        check: (both) => {
          const stamp = (p) => {
            const st = fs.statSync(p);
            return { bytes: fs.readFileSync(p), mtime: st.mtimeMs };
          };
          const dir = path.join(both.home, '.config', 'ai-kit');
          const now = {
            project: stamp(path.join(both.repo, '.planning', 'config.json')),
            user: stamp(path.join(dir, 'cross-ai.json')),
          };
          for (const which of ['project', 'user']) {
            const before = both.retryStamp[which];
            if (!before.bytes.equals(now[which].bytes)) return `${which} bytes changed`;
            if (before.mtime !== now[which].mtime) return `${which} mtime changed`;
          }
          const one = retryLine(both.first, 'max_retries=1 session_resets=0');
          if (one) return one;
          const a = (both.first.stderr || '').split('\n').find((l) => l.startsWith('cross-ai: retry '));
          const b = (both.again.stderr || '').split('\n').find((l) => l.startsWith('cross-ai: retry '));
          return a === b ? null : `lines differ: ${b}`;
        },
      },
      {
        // A CONFIG hard wait above capS is refused; the defaults stay whole as the last source.
        name: 'retry-config-small-cap',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        config: { capS: 300, retry: { hard_waits_s: [600] } },
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        // An empty project file: no earlier source supplies hard_waits_s, so only CONFIG is refused.
        setup: (c) => {
          fs.mkdirSync(path.join(c.repo, '.planning'), { recursive: true });
          fs.writeFileSync(path.join(c.repo, '.planning', 'config.json'), '{}');
          return null;
        },
        check: (r) => {
          const notice = 'cross-ai: config retry.hard_waits_s refused (CONFIG):';
          if (!(r.stderr || '').includes(notice)) return 'missing hard_waits_s refusal';
          return retryLine(r, 'hard_waits_s=600,900,1800 cap_s=300');
        },
      },
      {
        // The retry read refuses a symlink out of .planning; the timeout read still follows it.
        name: 'retry-config-outside',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          const outside = path.join(c.tmp, 'outside-config.json');
          fs.writeFileSync(outside, JSON.stringify({
            workflow: { cross_ai_retry: { max_retries: 7 }, cross_ai_timeout: 600 },
          }));
          fs.mkdirSync(path.join(c.repo, '.planning'), { recursive: true });
          fs.symlinkSync(outside, path.join(c.repo, '.planning', 'config.json'));
          const dir = path.join(c.home, '.config', 'ai-kit');
          fs.mkdirSync(dir, { recursive: true });
          fs.writeFileSync(path.join(dir, 'cross-ai.json'), JSON.stringify({
            cross_ai_retry: { max_retries: 2 },
          }));
          return null;
        },
        check: (r) => {
          const err = r.stderr || '';
          for (const word of ['resolves outside', 'confined', 'retry keys from the next source']) {
            if (!err.includes(word)) return `missing ${word}`;
          }
          if (!err.includes('cross-ai: deadline 570s (outer 600s)')) return 'deadline did not follow the symlink';
          const line = retryLine(r, 'max_retries=2');
          if (line) return line;
          return err.includes('max_retries=7') ? 'symlink value used' : null;
        },
      },
      {
        name: 'deadline-default',
        args: ['--print-argv', '--model-pi', 'fake/ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => ((r.stderr || '').includes('cross-ai: deadline 270s (outer 300s)') ? null : 'deadline line'),
      },
      {
        name: 'deadline-1800',
        args: ['--print-argv', '--model-pi', 'fake/ok'],
        planningConfig: { workflow: { cross_ai_timeout: 1800 } },
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => ((r.stderr || '').includes('cross-ai: deadline 1770s (outer 1800s)') ? null : 'deadline line'),
      },
      {
        name: 'deadline-config-cap',
        args: ['--print-argv', '--model-pi', 'fake/ok'],
        planningConfig: { workflow: { cross_ai_timeout: 3600 } },
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => ((r.stderr || '').includes('cross-ai: deadline 1770s (outer 1800s)') ? null : 'deadline line'),
      },
      {
        name: 'deadline-20',
        args: ['--print-argv', '--model-pi', 'fake/ok'],
        planningConfig: { workflow: { cross_ai_timeout: 20 } },
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => ((r.stderr || '').includes('cross-ai: deadline 16s (outer 20s)') ? null : 'deadline line'),
      },
      {
        name: 'deadline-workstream',
        args: ['--print-argv', '--model-pi', 'fake/ok'],
        env: { GSD_WORKSTREAM: 'ws' },
        workstream: { ws: 'ws', config: { workflow: { cross_ai_timeout: 600 } } },
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => ((r.stderr || '').includes('cross-ai: deadline 570s (outer 600s)') ? null : 'deadline line'),
      },
      {
        // config-get rejects the segment, so GSD falls back to its 300 s default too.
        name: 'deadline-workstream-bad',
        args: ['--print-argv', '--model-pi', 'fake/ok'],
        env: { GSD_WORKSTREAM: '../x' },
        planningConfig: { workflow: { cross_ai_timeout: 600 } },
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => ((r.stderr || '').includes('cross-ai: deadline 270s (outer 300s)') ? null : 'deadline line'),
      },
      ...[
        ['deadline-workstream-inherit', { GSD_WORKSTREAM: 'ws' }, { '.planning/workstreams/ws/STATE.md': {} }, '1770s (outer 1800s)'],
        ['deadline-workstream-nokey', { GSD_WORKSTREAM: 'ws' }, { '.planning/workstreams/ws/config.json': { workflow: {} } }, '1770s (outer 1800s)'],
        ['deadline-project', { GSD_PROJECT: 'p' }, { '.planning/p/config.json': { workflow: { cross_ai_timeout: 600 } } }, '570s (outer 600s)'],
        ['deadline-project-no-root', { GSD_PROJECT: 'p' }, { '.planning/p/config.json': { workflow: {} } }, '270s (outer 300s)'],
        ['deadline-project-workstream', { GSD_PROJECT: 'p', GSD_WORKSTREAM: 'ws' },
          { '.planning/p/workstreams/ws/config.json': { workflow: { cross_ai_timeout: 900 } } }, '870s (outer 900s)'],
      ].map(([name, env, files, want]) => ({
        name,
        args: ['--print-argv', '--model-pi', 'fake/ok'],
        env,
        files,
        planningConfig: { workflow: { cross_ai_timeout: 1800 } },
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => ((r.stderr || '').includes(`cross-ai: deadline ${want}`) ? null : 'deadline line'),
      })),
      {
        name: 'deadline-outer-min',
        args: ['--print-argv', '--model-pi', 'fake/ok'],
        planningConfig: { workflow: { cross_ai_timeout: 1 } },
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
      },
      {
        name: 'deadline-timeout-cap',
        args: ['--print-argv', '--timeout', '5', '--model-pi', 'fake/ok'],
        planningConfig: { workflow: { cross_ai_timeout: 1800 } },
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => ((r.stderr || '').includes('cross-ai: deadline 5s (outer 1800s)') ? null : 'deadline line'),
      },
      {
        name: 'deadline-timeout-above-inner',
        args: ['--print-argv', '--timeout', '5000', '--model-pi', 'fake/ok'],
        planningConfig: { workflow: { cross_ai_timeout: 1800 } },
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => ((r.stderr || '').includes('cross-ai: deadline 1770s (outer 1800s)') ? null : 'deadline line'),
      },
      {
        // D-18: an explicit outer deadline replaces both the GSD lookup and the CONFIG cap.
        name: 'outer-timeout-flag',
        args: [
          '--print-argv', '--outer-timeout', '1830', '--timeout', '1800', '--model-pi', 'fake/ok',
        ],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => (
          (r.stderr || '').includes('cross-ai: deadline 1800s (outer 1830s)')
            ? null : 'deadline line'
        ),
      },
      {
        name: 'outer-timeout-bad',
        args: ['--print-argv', '--outer-timeout', '0', '--model-pi', 'fake/ok'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
      },
      {
        name: 'codex-knobs',
        args: ['--print-argv', '--prefer', 'codex', '--model-codex', 'x', '--codex-effort', 'high', '--codex-service-tier', 'flex'],
        config: { prefer: ['codex'] },
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const line = (r.stdout || '').split('\n').find((l) => l.startsWith('codex\t'));
          if (!line) return 'missing codex line';
          const argv = JSON.parse(line.split('\t')[2]);
          const i = argv.indexOf('-c');
          const blob = argv.join('\0');
          if (!blob.includes('model_reasoning_effort=high') || !blob.includes('service_tier=flex')) return `argv=${JSON.stringify(argv)}`;
          return null;
        },
      },
      ...[
        ['argv-pi-thinking', 'pi', 'fake/ok', { effort: { pi: 'medium' } }, [], ['--thinking', 'medium']],
        ['argv-pi-thinking-suffix', 'pi', 'fake/ok:high', { effort: { pi: 'medium' } }, [], null],
        ['argv-codex-effort-config', 'codex', 'x', { prefer: ['codex'], effort: { codex: 'low' } }, [], ['-c', 'model_reasoning_effort=low']],
        ['argv-codex-effort-flag-wins', 'codex', 'x', { prefer: ['codex'], effort: { codex: 'low' } },
          ['--codex-effort', 'high'], ['-c', 'model_reasoning_effort=high']],
      ].map(([name, rt, model, config, extra, want]) => ({
        // WR-06: the plan's baked effort reaches the CLI (exec and review argv alike).
        name,
        args: ['--print-argv', '--prefer', rt, `--model-${rt}`, model, ...extra],
        config,
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const line = (r.stdout || '').split('\n').find((l) => l.startsWith(`${rt}\t`));
          const argv = JSON.parse(line.split('\t')[2]);
          const flag = want ? want[0] : '--thinking';
          const hits = argv.flatMap((t, i) => (t === flag && (rt !== 'codex' || /effort/.test(argv[i + 1])) ? [argv[i + 1]] : []));
          if (!want) return hits.length ? `unexpected ${flag} ${hits}` : null;
          return hits.length === 1 && hits[0] === want[1] ? null : `argv=${JSON.stringify(argv)}`;
        },
      })),
      {
        name: 'codex-effort-bogus',
        args: ['--codex-effort', 'bogus', '--prefer', 'codex', '--model-codex', 'x'],
        config: { prefer: ['codex'] },
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
      },
      {
        name: 'cursor-mode-plan',
        args: ['--print-argv', '--prefer', 'cursor', '--model-cursor', 'x', '--mode', 'review', '--cursor-mode', 'plan'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const line = (r.stdout || '').split('\n').find((l) => l.startsWith('cursor\t'));
          const argv = JSON.parse(line.split('\t')[2]);
          const mi = argv.indexOf('--mode');
          return mi >= 0 && argv[mi + 1] === 'plan' ? null : `argv=${JSON.stringify(argv)}`;
        },
      },
      {
        name: 'cursor-mode-exec-usage',
        args: ['--mode', 'exec', '--cursor-mode', 'plan', '--prefer', 'pi', '--model-pi', 'fake/ok'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
      },
      {
        // D-18: a cursor bracket id is preflighted without the suffix, then run whole.
        name: 'cursor-bracket-model',
        args: [
          '--prefer', 'cursor', '--model-cursor', 'fake-ok-cursor[effort=high,fast=false]',
        ],
        config: { prefer: ['cursor'] },
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=cursor .* exit=0 .* tree=dirty action=stop$/,
        check: (_r, ctx) => {
          const listed = ctx.calls.indexOf('cursor-agent models');
          const ran = ctx.calls.indexOf(
            'cursor-agent fake-ok-cursor[effort=high,fast=false]',
          );
          if (listed < 0 || ran < 0 || listed > ran) return `calls=${ctx.calls.join('|')}`;
          return null;
        },
      },
      {
        // Brackets are cursor-only; every other --model-<rt> keeps the template-2 charset.
        name: 'cursor-bracket-other-rt',
        args: ['--print-argv', '--model-pi', 'fake/ok[x=1]'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
      },
      {
        // D-02: a bare `agent` whose real path is not cursor-agent is not cursor.
        name: 'bare-agent-guard',
        args: ['--print-argv', '--prefer', 'cursor', '--model-cursor', 'fake-ok-cursor'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        setup: (c) => {
          const dir = path.join(c.tmp, 'bin-agent-bare-agent-guard');
          fs.mkdirSync(dir);
          const other = path.join(dir, 'other-agent-1.0.52-linux-x86_64');
          fs.writeFileSync(other, '#!/bin/sh\nexit 0\n');
          fs.chmodSync(other, 0o755);
          const shared = path.join(c.tmp, 'bin');
          fs.symlinkSync(path.join(shared, 'node'), path.join(dir, 'node'));
          fs.symlinkSync(path.join(shared, 'git'), path.join(dir, 'git'));
          fs.symlinkSync(other, path.join(dir, 'agent'));
          c.env.PATH = dir;
          return null;
        },
        check: (r) => {
          const line = (r.stdout || '').split('\n').find((l) => l.startsWith('cursor\t'));
          if (!line || !line.startsWith('cursor\tMISSING\t')) return `line=${line}`;
          return null;
        },
      },
      {
        // The same bare name is cursor when its real path is cursor-agent.
        name: 'agent-cursor-realpath',
        args: ['--print-argv', '--prefer', 'cursor', '--model-cursor', 'fake-ok-cursor'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        setup: (c) => {
          const dir = path.join(c.tmp, 'bin-agent-agent-cursor-realpath');
          fs.mkdirSync(dir);
          const shared = path.join(c.tmp, 'bin');
          fs.symlinkSync(path.join(shared, 'node'), path.join(dir, 'node'));
          fs.symlinkSync(path.join(shared, 'git'), path.join(dir, 'git'));
          fs.symlinkSync(path.join(shared, 'cursor-agent'), path.join(dir, 'agent'));
          c.env.PATH = dir;
          return null;
        },
        check: (_r, ctx) => {
          const agent = path.join(ctx.tmp, 'bin-agent-agent-cursor-realpath', 'agent');
          const line = (_r.stdout || '').split('\n').find((l) => l.startsWith('cursor\t'));
          if (!line || !line.includes(`\t${agent}\t`)) return `line=${line}`;
          return null;
        },
      },
      {
        name: 'agent-other-first-then-cursor',
        args: ['--print-argv', '--prefer', 'cursor', '--model-cursor', 'fake-ok-cursor'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        setup: (c) => {
          const dir2 = path.join(c.tmp, 'bin-agent-cursor-later');
          fs.mkdirSync(dir2);
          fs.symlinkSync(path.join(c.tmp, 'bin', 'cursor-agent'), path.join(dir2, 'agent'));
          c.env.PATH = otherAgentFirst(c, 'bin-agent-other-first') + path.delimiter + dir2;
          return null;
        },
        check: (r, ctx) => {
          const line = (r.stdout || '').split('\n').find((l) => l.startsWith('cursor\t'));
          const expected = path.join(ctx.tmp, 'bin-agent-cursor-later', 'agent');
          if (!line || !line.includes(`\t${expected}\t`)) return `line=${line}`;
          return null;
        },
      },
      {
        name: 'agent-other-first-then-cursor-cwd',
        args: ['--print-argv', '--prefer', 'cursor', '--model-cursor', 'fake-ok-cursor'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        setup: (c) => {
          cwdCursorAgent(c);
          c.env.PATH = otherAgentFirst(c, 'bin-agent-other-first-cwd') + path.delimiter;
          return null;
        },
        check: (r, ctx) => {
          const line = (r.stdout || '').split('\n').find((l) => l.startsWith('cursor\t'));
          if (!line || !line.includes(`\t${path.join(ctx.repo, 'agent')}\t`)) return `line=${line}`;
          return null;
        },
      },
      {
        name: 'agent-other-first-then-cursor-cwd-spawn',
        args: ['--mode', 'exec', '--prefer', 'cursor', '--model-cursor', 'composer-2.5'],
        stdin: 'exercise guarded cwd dispatch',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=cursor model=composer-2.5 exit=0 cli_rc=0 elapsed=\d+s out=\d+ tree=dirty action=stop$/,
        setup: (c) => {
          cwdCursorAgent(c);
          const marker = path.join(c.tmp, 'other-ran');
          const dir = otherAgentFirst(c, 'bin-agent-other-first-cwd-spawn', `#!/bin/sh\nprintf 'other ran' > '${marker}'\nexit 1\n`);
          c.env.PATH = dir + path.delimiter;
          return null;
        },
        check: (_r, ctx) => {
          if (!ctx.calls.some((line) => line.startsWith('cursor-agent '))) return `calls=${ctx.calls.join('|')}`;
          if (fs.existsSync(path.join(ctx.tmp, 'other-ran'))) return 'the other agent ran';
          return null;
        },
      },
      {
        // CR-01: a nameless, ANSI-wrapped `auto (current, default)` line is a listed model.
        name: 'cursor-nameless-listing-preflight',
        env: { FAKE_CURSOR_LIST: 'nameless' },
        args: ['--prefer', 'cursor', '--model-cursor', 'auto'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=cursor model=auto exit=0 .* action=stop$/,
        check: (r) => {
          const err = r.stderr || '';
          if (err.includes('bad_model')) return 'auto rejected as bad_model';
          return err.includes('not preflighted') ? 'listing not used' : null;
        },
      },
      {
        // 26 D-24: every child carries AI_KIT_CROSS_AI_CHILD=1, even when the parent holds another value.
        name: 'child-marker-env',
        args: ['--runtime', 'pi', '--model', 'fake/envmarker'],
        env: { AI_KIT_CROSS_AI_CHILD: '0' },
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/envmarker exit=0 .* action=stop$/,
        check: (_r, ctx) => {
          const seen = readOr(path.join(ctx.repo, 'marker.seen'), '<missing>');
          return seen === '1' ? null : `marker.seen=${JSON.stringify(seen)}`;
        },
      },
      {
        // D-30: a file's content goes before the stdin prompt, and nothing else with --no-preamble;
        // its leading HTML-comment lines (the guidance file's stamp) never reach the model.
        name: 'prepend-file',
        args: [
          '--prefer', 'pi', '--model-pi', 'fake/echoprompt', '--no-preamble',
          '--prepend-file', 'guide.md',
        ],
        stdin: 'TASK-BODY',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/echoprompt exit=0 .* action=stop$/,
        setup: (c) => {
          fs.writeFileSync(path.join(c.repo, 'guide.md'), '<!-- a -->\n<!-- b -->\nPREPEND-MARKER-18-1');
          return null;
        },
        check: (_r, ctx) => {
          const seen = readOr(path.join(ctx.repo, 'prompt.seen'), '');
          if (!seen.startsWith('PREPEND-MARKER-18-1')) {
            return `start=${JSON.stringify(seen.slice(0, 40))}`;
          }
          const body = seen.indexOf('TASK-BODY');
          if (body < 0 || body < seen.indexOf('PREPEND-MARKER-18-1')) return 'TASK-BODY order';
          if (seen.includes('<executor_rules>') || seen.includes('<reviewer_rules>')) {
            return 'preamble leaked';
          }
          return null;
        },
      },
      {
        name: 'prepend-file-missing',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok', '--prepend-file', 'nope.md'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
        check: (_r, ctx) => {
          return ctx.calls.some((l) => l.startsWith('pi ')) ? `calls=${ctx.calls.join('|')}` : null;
        },
      },
      {
        // D-27: workspace-write replaces the bypass, and a retry stays a fresh sandboxed run.
        name: 'codex-sandbox-exec',
        args: [
          '--print-argv', '--prefer', 'codex', '--model-codex', 'x', '--mode', 'exec',
          '--codex-sandbox', 'workspace-write',
        ],
        config: { prefer: ['codex'] },
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const line = (r.stdout || '').split('\n').find((l) => l.startsWith('codex\t'));
          if (!line) return 'missing codex line';
          const argv = JSON.parse(line.split('\t')[2]);
          const sandboxed = argv.includes('--sandbox') && argv.includes('workspace-write')
            && argv.includes('-C');
          if (!sandboxed) return `argv=${JSON.stringify(argv)}`;
          if (argv.includes('--dangerously-bypass-approvals-and-sandbox')) {
            return 'bypass still present';
          }
          const err = r.stderr || '';
          if (!err.includes('cross-ai: rung1 codex unavailable')) return 'rung 1 was available';
          const rung2 = err.split('\n').find((l) => l.includes('rung2 codex argv='));
          if (!rung2) return 'missing rung2 argv';
          const rung2Argv = JSON.parse(rung2.slice(rung2.indexOf('[')));
          if (rung2Argv.includes('resume')) return 'rung 2 resumed';
          return null;
        },
      },
      {
        name: 'codex-sandbox-default',
        args: ['--print-argv', '--prefer', 'codex', '--model-codex', 'x', '--mode', 'exec'],
        config: { prefer: ['codex'] },
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const line = (r.stdout || '').split('\n').find((l) => l.startsWith('codex\t'));
          if (!line) return 'missing codex line';
          const argv = JSON.parse(line.split('\t')[2]);
          return argv.includes('--dangerously-bypass-approvals-and-sandbox')
            ? null : `argv=${JSON.stringify(argv)}`;
        },
      },
      {
        name: 'codex-sandbox-bad',
        args: [
          '--print-argv', '--prefer', 'codex', '--model-codex', 'x', '--mode', 'exec',
          '--codex-sandbox', 'danger-full-access',
        ],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
      },
      {
        // The runner records each detached CLI child so a supervisor can reap a wedged run.
        name: 'child-pgid-file',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          const pgid = path.join(c.tmp, 'pgid-child-pgid-file');
          c.args = [
            '--prefer', 'pi', '--model-pi', 'fake/ok', '--child-pgid-file', pgid,
          ];
          c.pgidFile = pgid;
          return null;
        },
        check: (_r, ctx) => {
          const text = readOr(ctx.pgidFile, '');
          const spawns = [...text.matchAll(/^spawn (\d+)$/gm)].map((m) => m[1]);
          if (!spawns.length) return `pgid file=${JSON.stringify(text)}`;
          for (const n of spawns) {
            const spawnAt = text.indexOf(`spawn ${n}`);
            const exitAt = text.indexOf(`exit ${n}`, spawnAt + 1);
            if (exitAt < 0) return `no exit for ${n}: ${text}`;
          }
          return null;
        },
      },
      {
        name: 'child-pgid-file-unwritable',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          c.args = [
            '--prefer', 'pi', '--model-pi', 'fake/ok', '--child-pgid-file',
            path.join(c.tmp, 'missing-dir', 'pgid'),
          ];
          return null;
        },
        check: (r) => {
          const hits = (r.stderr || '').split('\n')
            .filter((l) => l.includes('--child-pgid-file unwritable'));
          return hits.length === 1 ? null : `hits=${hits.length}`;
        },
      },
      {
        name: 'extra-args-pi',
        args: ['--print-argv', '--prefer', 'pi', '--model-pi', 'fake/ok'],
        config: { extraArgs: { pi: ['--skill', 'skills/x/SKILL.md'] } },
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const line = (r.stdout || '').split('\n').find((l) => l.startsWith('pi\t'));
          const argv = JSON.parse(line.split('\t')[2]);
          const tail = argv.slice(-2);
          return tail[0] === '--skill' && tail[1] === 'skills/x/SKILL.md' ? null : `tail=${JSON.stringify(tail)}`;
        },
      },
      {
        name: 'profile-pi-review-argv',
        args: ['--runtime', 'pi', '--mode', 'review', '--model', 'fake/ok', '--print-argv'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const line = (r.stdout || '').split('\n').find((l) => l.startsWith('pi\t'));
          const argv = JSON.parse(line.split('\t')[2]);
          const at = argv.indexOf('--tools');
          const flags = ['--tools', 'read,grep,find,ls', '--no-mcp', '--no-context-files'];
          if (JSON.stringify(argv.slice(at, at + flags.length)) !== JSON.stringify(flags)) {
            return `argv=${JSON.stringify(argv)}`;
          }
          return at > argv.indexOf('--offline') ? null : 'profile flags precede the base';
        },
      },
      {
        name: 'profile-pi-none-argv',
        args: [
          '--runtime', 'pi', '--mode', 'review', '--tools-profile', 'none',
          '--model', 'fake/ok', '--print-argv',
        ],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const line = (r.stdout || '').split('\n').find((l) => l.startsWith('pi\t'));
          const argv = JSON.parse(line.split('\t')[2]);
          const flags = ['--no-tools', '--no-mcp', '--no-context-files'];
          const at = argv.indexOf('--no-tools');
          if (JSON.stringify(argv.slice(at)) !== JSON.stringify(flags)) return `argv=${JSON.stringify(argv)}`;
          return argv.includes('--tools') ? 'none profile still has --tools' : null;
        },
      },
      {
        name: 'profile-pi-exec-default',
        args: ['--runtime', 'pi', '--mode', 'exec', '--model', 'fake/ok', '--print-argv'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const line = (r.stdout || '').split('\n').find((l) => l.startsWith('pi\t'));
          const argv = JSON.parse(line.split('\t')[2]);
          const extra = ['--tools', '--no-tools', '--no-mcp', '--no-context-files'];
          const hit = extra.find((f) => argv.includes(f));
          return hit ? `exec argv gained ${hit}` : null;
        },
      },
      {
        name: 'profile-review-widen-refused',
        args: ['--runtime', 'pi', '--mode', 'review', '--tools-profile', 'exec', '--model', 'fake/ok'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
        check: (r) => ((r.stderr || '').includes('review mode allows only the review or none') ? null : 'missing refusal'),
      },
      {
        name: 'profile-unsupported-cursor',
        args: ['--runtime', 'cursor', '--tools-profile', 'none', '--model', 'fake-ok-cursor'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
        check: (r) => ((r.stderr || '').includes('cursor has no tools profile none') ? null : 'missing refusal'),
      },
      {
        name: 'profile-bad-name',
        args: ['--tools-profile', 'write'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
      },
      {
        name: 'no-passthrough',
        args: ['--runtime', 'pi', '--model', 'fake/ok', '--', '--yolo'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
      },
      {
        name: 'no-passthrough-extra-arg',
        args: ['--runtime', 'pi', '--model', 'fake/ok', '--extra-arg', 'x'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
      },
      {
        // One case, three widening extras: each exits 2 before any fake call.
        name: 'review-extra-args-widen-refused',
        config: { extraArgs: { pi: ['--tools', 'bash'] }, prefer: ['pi'], retry: { max_retries: 1 } },
        args: ['--mode', 'review', '--model-pi', 'fake/ok'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
        check: async (r, ctx) => {
          if (ctx.calls.length) return `spawned: ${ctx.calls.join('|')}`;
          if (!(r.stderr || '').includes('review argv for pi holds --tools')) return 'element not named';
          const more = [
            [{ pi: ['-e', 'x.ts'] }, 'pi', '-e'],
            [{ opencode: ['--agent', 'build'] }, 'opencode', '--agent'],
          ];
          for (const [extraArgs, cli, element] of more) {
            const copy = writeCopy(ctx.tmp, `widen-${cli}`, {
              extraArgs, prefer: [cli], retry: { max_retries: 1 },
            });
            const got = await runCaseProcess({
              args: ['--mode', 'review', '--model-pi', 'fake/ok', '--model-opencode', 'fake/ok'],
            }, { ...ctx, copy });
            if (got.status !== 2) return `${cli} exit ${got.status}`;
            const err = got.stderr || '';
            if (!err.includes(`review argv for ${cli} holds ${element}`)) return `${cli} element not named`;
            if (!err.includes(`review extras allowed for ${cli}:`)) return `${cli} allowlist not named`;
          }
          return null;
        },
      },
      ...[
        { pi: ['--tools', 'bash'] },
        { pi: ['-e', 'x.ts'] },
        { opencode: ['--agent', 'build'] },
      ].map((extraArgs, i) => ({
        name: `review-extra-args-widen-refused-${i}`,
        args: ['--mode', 'review', '--model-pi', 'fake/ok', '--model-opencode', 'fake/ok'],
        config: { extraArgs, prefer: [Object.keys(extraArgs)[0]] },
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
        check: (r, ctx) => {
          if (ctx.calls.length) return `spawned: ${ctx.calls.join('|')}`;
          const err = r.stderr || '';
          const cli = Object.keys(extraArgs)[0];
          const element = extraArgs[cli][0];
          if (!err.includes(`review argv for ${cli} holds ${element}`)) return 'element not named';
          return err.includes(`review extras allowed for ${cli}:`) ? null : 'allowlist not named';
        },
      })),
      {
        name: 'review-extra-args-skill-ok',
        args: ['--mode', 'review', '--prefer', 'pi', '--model-pi', 'fake/review-ok'],
        config: { extraArgs: { pi: ['--skill', 'skills/x/SKILL.md'] } },
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi .* tree=clean action=stop$/,
      },
      ...[
        { mode: 'crash', exit: 1, status: 'crash', tree: 'clean' },
        { mode: 'quota', exit: 75, status: 'quota', tree: 'clean' },
        {
          // The transient hard tier never switches either: a spent series exits 75 on pi only.
          mode: 'transient', model: 'event400', exit: 75, status: 'transient', tree: 'clean',
          config: { retry: { max_retries: 1, session_resets: 0 } },
        },
        {
          // A spent hard tier (record at cycle 2) stops on the same lane, still one CLI only.
          mode: 'hard-waits', model: 'event400', exit: 69, status: 'transient', tree: 'clean',
          config: { retry: { max_retries: 0, session_resets: 0 } },
          setup: (c) => {
            writePriorRecord(c, 'pi', 'fake/event400', 'other', 'transient', 2);
            return null;
          },
        },
        { mode: 'billing', exit: 69, status: 'billing', tree: 'clean' },
        { mode: 'auth', exit: 69, status: 'auth', tree: 'clean' },
        { mode: 'perm', exit: 69, status: 'permission_blocked', tree: 'clean' },
        { mode: 'empty', exit: 1, status: 'empty_answer', tree: 'clean' },
        { mode: 'nochange', exit: 1, status: 'no_change', tree: 'clean' },
        {
          mode: 'hang', exit: 124, status: 'timeout', tree: '.*',
          extra: ['--timeout', '2'], dead: ['pi', 'gc'],
        },
        { mode: 'missing', exit: 69, status: 'bad_model', tree: 'clean' },
      ].map((row) => ({
        name: `no-second-cli-${row.mode}`,
        ...(row.setup ? { setup: row.setup } : {}),
        args: [
          '--prefer', 'pi,cursor,opencode', '--model-pi', `fake/${row.model || row.mode}`,
          '--model-cursor', 'fake-ok-cursor', '--model-opencode', 'fake/ok',
          ...(row.extra || []),
        ],
        ...(row.config ? { config: row.config } : {}),
        exit: row.exit,
        status: new RegExp(`^AIKIT-XAI status=${row.status} cli=pi model=fake/${row.model || row.mode} ` +
          `exit=${row.exit} .* tree=${row.tree} action=stop$`),
        check: (r, ctx) => {
          if (!(r.stderr || '').includes('ignored: cursor, opencode')) return 'missing ignored-entries note';
          const other = ctx.calls.find((l) => (
            l.startsWith('cursor-agent') || l.startsWith('opencode')
          ));
          if (other) return `second cli: ${other}`;
          return row.dead ? deadCheck(ctx, row.dead) : null;
        },
      })),
      {
        name: 'no-second-cli-review-edit',
        args: [
          '--mode', 'review', '--prefer', 'pi,cursor,opencode', '--model-pi', 'fake/review-edit',
          '--model-cursor', 'fake-ok-cursor', '--model-opencode', 'fake/ok',
        ],
        exit: 1,
        status: new RegExp('^AIKIT-XAI status=contract_violation cli=pi ' +
          'model=fake/review-edit exit=1 .* action=stop$'),
        check: (r, ctx) => {
          if (!(r.stderr || '').includes('ignored: cursor, opencode')) return 'missing ignored-entries note';
          const other = ctx.calls.find((l) => (
            l.startsWith('cursor-agent') || l.startsWith('opencode')
          ));
          return other ? `second cli: ${other}` : null;
        },
      },
      {
        name: 'config-prefer-first-only',
        config: {
          runtime: null,
          prefer: ['pi', 'cursor'],
          models: { pi: 'fake/crash', cursor: 'fake-ok-cursor', opencode: 'fake/ok' },
        },
        args: [],
        exit: 1,
        status: /^AIKIT-XAI status=crash cli=pi model=fake\/crash exit=1 .* action=stop$/,
        check: (r, ctx) => {
          if (!(r.stderr || '').includes('CONFIG.prefer reads only its first entry (pi); ignored: cursor')) {
            return 'missing CONFIG ignored-entries note';
          }
          const other = ctx.calls.find((l) => (
            l.startsWith('cursor-agent') || l.startsWith('opencode')
          ));
          return other ? `second cli: ${other}` : null;
        },
      },
      {
        name: 'runtime-flag',
        args: ['--runtime', 'pi', '--model-pi', 'fake/ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        check: (_r, ctx) => (ctx.calls.some((l) => l.startsWith('pi ')) ? null : 'pi did not run'),
      },
      {
        name: 'runtime-and-prefer',
        args: ['--runtime', 'pi', '--prefer', 'cursor', '--model-pi', 'fake/ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        check: (r, ctx) => {
          if (!(r.stderr || '').includes('cross-ai: --runtime pi wins; ignored --prefer cursor')) {
            return 'missing --runtime wins note';
          }
          return ctx.calls.some((l) => l.startsWith('cursor-agent')) ? 'cursor ran' : null;
        },
      },
      {
        name: 'prefer-first-only-notice',
        args: ['--prefer', 'pi,cursor', '--model-pi', 'fake/ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        check: (r, ctx) => {
          if (!(r.stderr || '').includes('--prefer reads only its first entry (pi); ignored: cursor')) {
            return 'missing ignored-entries note';
          }
          return ctx.calls.some((l) => l.startsWith('cursor-agent')) ? 'cursor ran' : null;
        },
      },
      {
        name: 'config-runtime',
        config: { runtime: 'pi', prefer: ['cursor'], models: { pi: 'fake/ok', cursor: 'fake-ok-cursor' } },
        args: [],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        check: (_r, ctx) => (ctx.calls.some((l) => l.startsWith('cursor-agent')) ? 'cursor ran' : null),
      },
      {
        name: 'runtime-unknown',
        args: ['--runtime', 'nosuch'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
      },
      {
        name: 'runtime-none',
        config: { prefer: null },
        args: [],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
        check: (r) => ((r.stderr || '').includes('no runtime: pass --runtime <id>') ? null : 'missing usage line'),
      },
      {
        name: 'not-installed-first',
        setup: (c) => {
          const dir = path.join(c.tmp, `bin-nopi-${c.repo.split('/').pop()}`);
          fs.mkdirSync(dir);
          for (const name of fs.readdirSync(path.join(c.tmp, 'bin'))) {
            if (name === 'pi') continue;
            fs.symlinkSync(path.join(c.tmp, 'bin', name), path.join(dir, name));
          }
          c.env.PATH = dir;
          return null;
        },
        args: [
          '--prefer', 'pi,cursor', '--model-pi', 'fake/ok', '--model-cursor', 'fake-ok-cursor',
        ],
        exit: 127,
        status: /^AIKIT-XAI status=not_installed cli=pi .* exit=127 .* action=stop$/,
        check: (r, ctx) => {
          if (ctx.calls.length) return `calls=${ctx.calls.join('|')}`;
          const line = 'pi not installed; no other CLI runs';
          return (r.stderr || '').includes(line) ? null : 'missing line';
        },
      },
      {
        name: 'no-model-first',
        args: ['--prefer', 'pi,cursor', '--model-cursor', 'fake-ok-cursor'],
        exit: 2,
        status: /^AIKIT-XAI status=no_model cli=pi .* exit=2 .* action=stop$/,
        check: (_r, ctx) => (ctx.calls.length ? `calls=${ctx.calls.join('|')}` : null),
      },
      {
        name: 'review-only-first-refused',
        args: [
          '--mode', 'exec', '--prefer', 'claude,pi', '--model-claude', 'fake-ok',
          '--model-pi', 'fake/ok',
        ],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
        check: (r, ctx) => {
          if (!(r.stderr || '').includes('claude is review-only')) {
            return 'missing review-only line';
          }
          return ctx.calls.some((l) => l.startsWith('pi ')) ? 'pi ran' : null;
        },
      },
      {
        name: 'outer-race',
        config: { outerTimeoutS: 40 },
        args: ['--prefer', 'pi', '--model-pi', 'fake/outer-race', '--timeout', '8'],
        exit: 124,
        status: /^AIKIT-XAI status=timeout cli=pi model=fake\/outer-race exit=124 .* action=stop$/,
        check: (r, ctx) => {
          if (ctx.elapsedMs >= scaledMs(30000)) return `elapsed ${ctx.elapsedMs}`;
          const lines = (r.stderr || '').split('\n');
          const statusIdx = lines.findIndex((l) => l.startsWith('AIKIT-XAI '));
          if (statusIdx < 0) return 'no status';
          if (lines.slice(statusIdx + 1).some((l) => l.trim())) return 'output after status';
          const late = lines.filter((l) => l.includes('gc-late'));
          if (!late.length) return 'no gc-late';
          if (late.some((l) => lines.indexOf(l) >= statusIdx)) return 'gc-late after status';
          return deadCheck(ctx, ['gc']);
        },
      },
      ...classifyCases(),
      {
        name: 'classify-only-fixtures',
        setup: (c) => {
          const rows = CLASSIFY_CASES.map((entry) => {
            const row = { name: entry.name, cli: entry.cli };
            if (entry.route !== undefined) row.route = entry.route;
            if (entry.model !== undefined) row.model = entry.model;
            if (entry.stderr !== undefined) row.stderr = entry.stderr;
            if (entry.stdout !== undefined) row.stdout = entry.stdout;
            return row;
          });
          fs.writeFileSync(path.join(c.repo, 'fixtures.json'), JSON.stringify(rows));
          return null;
        },
        args: ['--classify-only', 'fixtures.json'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const lines = (r.stdout || '').split('\n').filter(Boolean);
          if (lines.length !== CLASSIFY_CASES.length) {
            return `fixture lines ${lines.length} expected ${CLASSIFY_CASES.length}`;
          }
          for (let i = 0; i < lines.length; i++) {
            const got = JSON.parse(lines[i]);
            const want = CLASSIFY_CASES[i];
            if (got.status !== want.expect.status) {
              return `${want.name} status ${got.status} expected ${want.expect.status}`;
            }
            if (got.pattern !== want.expect.pattern) {
              return `${want.name} pattern ${got.pattern} expected ${want.expect.pattern}`;
            }
            if (want.expect.rule !== undefined && got.rule !== want.expect.rule) {
              return `${want.name} rule ${got.rule} expected ${want.expect.rule}`;
            }
          }
          return null;
        },
      },
      {
        name: 'classify-only-no-spawn',
        setup: (c) => {
          fs.writeFileSync(path.join(c.repo, 'fixtures.json'), JSON.stringify([
            { name: 'x', cli: 'pi', stderr: '402 payment required' },
          ]));
          return null;
        },
        args: ['--classify-only', 'fixtures.json'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (_r, ctx) => (ctx.calls.length ? `spawned: ${ctx.calls.join('|')}` : null),
      },
      {
        // 25.1 WR-02: an uncaptured runtime reads unverified here too, as on a live run.
        name: 'classify-only-copilot-unverified',
        setup: (c) => {
          fs.writeFileSync(path.join(c.repo, 'fixtures.json'), JSON.stringify([
            { name: 'x', cli: 'copilot', stderr: 'Error: quota exceeded' },
          ]));
          return null;
        },
        args: ['--classify-only', 'fixtures.json'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const got = JSON.parse((r.stdout || '').split('\n')[0] || '{}');
          return got.status === 'quota' && got.pattern === 'unverified' ? null : JSON.stringify(got);
        },
      },
      {
        name: 'classify-only-bad-file',
        args: ['--classify-only', 'missing.json'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* action=stop$/,
      },
      {
        name: 'route-config',
        args: ['--prefer', 'pi', '--model-pi', 'fake/billing'],
        config: { routerBacked: { pi: true } },
        exit: 75,
        status: /^AIKIT-XAI status=quota cli=pi model=fake\/billing exit=75 cli_rc=1 .* tree=clean action=stop$/,
        check: (r) => {
          const tail = statusTail(r.stderr || '');
          return tail && tail.route === 'router' ? null : `route=${tail && tail.route}`;
        },
      },
      {
        name: 'route-flag-wins',
        args: ['--prefer', 'pi', '--model-pi', 'fake/billing', '--route-pi', 'unknown'],
        config: { routerBacked: { pi: true } },
        exit: 69,
        status: /^AIKIT-XAI status=billing cli=pi model=fake\/billing exit=69 cli_rc=1 .* tree=clean action=stop$/,
        check: (r) => {
          const tail = statusTail(r.stderr || '');
          return tail && tail.route === 'unknown' ? null : `route=${tail && tail.route}`;
        },
      },
      {
        name: 'route-heuristic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/router-env-billing'],
        config: { routerBacked: {} },
        exit: 69,
        status: /^AIKIT-XAI status=billing cli=pi model=fake\/router-env-billing exit=69 cli_rc=1 .* tree=clean action=stop$/,
        check: (r) => {
          const tail = statusTail(r.stderr || '');
          return tail && tail.route === 'router-inferred' ? null : `route=${tail && tail.route}`;
        },
      },
      {
        name: 'upstream-router-402',
        args: ['--prefer', 'pi', '--model-pi', 'fake/router402', '--route-pi', 'router'],
        config: { retry: { max_retries: 0, session_resets: 0, hard_waits_s: [600] } },
        exit: 75,
        status: /^AIKIT-XAI status=quota .* action=stop$/,
        check: (r, ctx) => {
          if (!r.stderr) return 'missing captured stderr';
          const report = (r.stderr || '').indexOf('cross-ai: report ');
          const body = (r.stderr || '').indexOf('cross-ai: upstream body=');
          const fields = (r.stderr || '').indexOf('cross-ai: upstream fields=');
          const status = (r.stderr || '').indexOf('AIKIT-XAI ');
          if (!(report >= 0 && body > report && fields > body && status > fields)) return 'upstream trailer order';
          const bodyLine = (r.stderr || '').split('\n').find((line) => line.startsWith('cross-ai: upstream body='));
          const fieldsLine = (r.stderr || '').split('\n').find((line) => line.startsWith('cross-ai: upstream fields='));
          if (!JSON.parse(bodyLine.slice(bodyLine.indexOf('=') + 1)).includes('Acme Build')) return 'body missing upstream text';
          if (fieldsLine !== 'cross-ai: upstream fields={"retry_after":120,"reset_at":"2026-10-23T04:01:04.472Z"}') return 'fields mismatch';
          const state = fs.existsSync(ctx.env.XDG_STATE_HOME)
            ? fs.readdirSync(ctx.env.XDG_STATE_HOME, { withFileTypes: true }).filter((entry) => entry.isFile()).map((entry) => fs.readFileSync(path.join(ctx.env.XDG_STATE_HOME, entry.name), 'utf8')).join('\n')
            : '';
          const all = `${r.stdout}\n${r.stderr}\n${state}`;
          if (all.includes(ctx.env.AIKIT_XAI_SENTINEL)) return 'sentinel leaked';
          if (all.includes('ab12cd34')) return 'connection suffix leaked';
          return (r.stderr || '').includes('upstream=present') ? null : 'missing upstream marker';
        },
      },
      {
        name: 'route-flag-bad',
        args: ['--prefer', 'pi', '--route-pi', 'maybe'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* action=stop$/,
      },
      {
        name: 'copilot-exec-ok',
        args: ['--runtime', 'copilot', '--model', 'fake-ok'],
        env: {
          COPILOT_GITHUB_TOKEN: 'github_pat_' + 'selftest'.padEnd(22, 'x'),
          COPILOT_ALLOW_ALL: 'true',
        },
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=copilot model=fake-ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          c.seen = path.join(c.tmp, 'copilot-seen-exec.json');
          c.env.FAKE_COPILOT_SEEN = c.seen;
          return null;
        },
        check: (r, ctx) => {
          const seen = JSON.parse(fs.readFileSync(ctx.seen, 'utf8'));
          const at = seen.argv.indexOf('-p');
          if (at < 0 || seen.argv[at + 1] !== seen.prompt) return 'prompt not on argv after -p';
          if (!seen.prompt.includes('prompt')) return 'argv prompt missing the stdin text';
          if (seen.stdinFifo !== false) return `stdinFifo=${seen.stdinFifo}`;
          if (seen.stdinBytes !== 0) return `stdinBytes=${seen.stdinBytes}`;
          if (seen.stdinError) return `stdinError=${seen.stdinError}`;
          if (seen.allowAll !== false) return 'COPILOT_ALLOW_ALL reached the child';
          const logged = (r.stderr || '').split('\n').filter((l) => l.startsWith('cross-ai: argv='));
          if (!logged.length) return 'no argv log line';
          if (logged.some((l) => l.includes('prompt\n'))) return 'argv log carries the prompt text';
          return logged.every((l) => l.includes('"<prompt>"')) ? null : 'argv log omits <prompt>';
        },
      },
      {
        name: 'copilot-argv-exec',
        args: ['--runtime', 'copilot', '--model', 'fake-ok', '--print-argv'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const line = (r.stdout || '').split('\n').find((l) => l.startsWith('copilot\t'));
          if (!line) return 'missing argv line';
          const argv = JSON.parse(line.split('\t')[2]);
          const want = ['-p', '<prompt>', '-s', '--no-ask-user', '--model', 'fake-ok',
            '--allow-all-tools'];
          return JSON.stringify(argv) === JSON.stringify(want) ? null : `argv=${JSON.stringify(argv)}`;
        },
      },
      {
        name: 'copilot-token-passthrough',
        args: ['--runtime', 'copilot', '--model', 'fake-ok'],
        env: {
          COPILOT_GITHUB_TOKEN: 'github_pat_' + 'a'.repeat(40),
          GH_TOKEN: 'gho_' + 'b'.repeat(36),
          GITHUB_TOKEN: 'ghs_' + 'c'.repeat(36),
        },
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=copilot model=fake-ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          c.seen = path.join(c.tmp, 'copilot-seen-tokens.json');
          c.env.FAKE_COPILOT_SEEN = c.seen;
          c.tokens = {
            COPILOT_GITHUB_TOKEN: c.env.COPILOT_GITHUB_TOKEN,
            GH_TOKEN: c.env.GH_TOKEN, GITHUB_TOKEN: c.env.GITHUB_TOKEN,
          };
          return null;
        },
        check: (r, ctx) => {
          const seen = JSON.parse(fs.readFileSync(ctx.seen, 'utf8'));
          const names = ['COPILOT_GITHUB_TOKEN', 'GH_TOKEN', 'GITHUB_TOKEN'];
          if (JSON.stringify(seen.tokens) !== JSON.stringify(names)) {
            return `tokens=${JSON.stringify(seen.tokens)}`;
          }
          const relayed = (r.stderr || '').split('\n').filter((l) => l.includes('using token'));
          if (relayed.length !== 1 || !relayed[0].includes('<redacted>')) return 'token line not redacted';
          let state = '';
          if (fs.existsSync(ctx.env.XDG_STATE_HOME)) {
            // Recursive: the lane records live under ai-kit/spec/cycles/<root-hash>/.
            state = fs.readdirSync(ctx.env.XDG_STATE_HOME, { withFileTypes: true, recursive: true })
              .filter((e) => e.isFile())
              .map((e) => fs.readFileSync(path.join(e.parentPath, e.name), 'utf8'))
              .join('\n');
          }
          const all = `${r.stdout}\n${r.stderr}\n${state}`;
          for (const value of Object.values(ctx.tokens)) {
            if (all.includes(value)) return 'a token value reached an output';
          }
          return null;
        },
      },
      {
        name: 'copilot-no-token-auth',
        args: ['--runtime', 'copilot', '--model', 'fake-ok'],
        config: { retry: { max_retries: 1 } },
        exit: 69,
        status: /^AIKIT-XAI status=auth cli=copilot model=fake-ok exit=69 .* action=stop$/,
        check: (r, ctx) => {
          const tail = statusTail(r.stderr || '');
          if (!tail) return 'no status tail';
          if (tail.rule !== 'text-not-logged-in') return `rule=${tail.rule}`;
          if (tail.pattern !== 'unverified') return `pattern=${tail.pattern}`;
          if (tail.attempts !== '1') return `attempts=${tail.attempts}`;
          const report = (r.stderr || '').split('\n').find((l) => l.startsWith('cross-ai: report '));
          if (!report) return 'missing report line';
          if ((r.stderr || '').includes('pattern=verified')) return 'a copilot pattern read verified';
          return ctx.calls.length === 1 ? null : `calls=${ctx.calls.length}`;
        },
      },
      {
        name: 'pure-argv-prompt-guard',
        pure: () => {
          const reserve = Buffer.byteLength(`${RESUME_MSG}\n\n`);
          const room = ARGV_PROMPT_MAX - reserve;
          if (argvPromptProblem('a'.repeat(room))) return 'exact limit refused';
          if (!argvPromptProblem('a'.repeat(room + 1))) return 'one byte over accepted';
          const multi = '\u00e9'.repeat(Math.floor(room / 2));
          const fit = argvPromptProblem(multi);
          if (Buffer.byteLength(multi) <= room && fit) return 'multi-byte within limit refused';
          const over = argvPromptProblem(multi + '\u00e9');
          if (Buffer.byteLength(multi + '\u00e9') > room && !over) return 'multi-byte over limit accepted';
          const dash = argvPromptProblem('-' + 'a'.repeat(room - 1));
          if (!dash) return 'leading-dash newline not counted';
          return null;
        },
      },
      {
        name: 'copilot-oversize',
        args: ['--runtime', 'copilot', '--model', 'fake-ok'],
        stdin: 'x'.repeat(110000),
        env: { COPILOT_GITHUB_TOKEN: 'github_pat_' + 'a'.repeat(40) },
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
        check: (r, ctx) => {
          if (ctx.calls.length) return `spawned: ${ctx.calls.join('|')}`;
          const line = (r.stderr || '').split('\n').find((l) => l.includes('takes the prompt on argv'));
          if (!line) return 'missing size refusal';
          return line.includes(`over ${ARGV_PROMPT_MAX}`) ? null : line;
        },
      },
      {
        name: 'copilot-large-prompt',
        args: ['--runtime', 'copilot', '--model', 'fake-ok'],
        stdin: 'y'.repeat(90000),
        env: { COPILOT_GITHUB_TOKEN: 'github_pat_' + 'a'.repeat(40) },
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=copilot model=fake-ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          c.seen = path.join(c.tmp, 'copilot-seen-large.json');
          c.env.FAKE_COPILOT_SEEN = c.seen;
          return null;
        },
        check: (_r, ctx) => {
          const seen = JSON.parse(fs.readFileSync(ctx.seen, 'utf8'));
          // The harness writes the stdin as given, and the runner appends one newline of its
          // own only when the stdin has none, then the exec preamble.
          const want = Buffer.byteLength('y'.repeat(90000) + EXEC_PREAMBLE);
          return seen.promptBytes === want ? null : `promptBytes=${seen.promptBytes} want=${want}`;

        },
      },
      {
        name: 'copilot-none-profile-refused',
        args: ['--runtime', 'copilot', '--tools-profile', 'none', '--model', 'fake-ok'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
        check: (r) => ((r.stderr || '').includes('copilot has no tools profile none') ? null : 'missing refusal'),
      },
      {
        name: 'copilot-review-widen-refused',
        args: ['--runtime', 'copilot', '--mode', 'review', '--tools-profile', 'exec', '--model', 'fake-ok'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
        check: (r) => ((r.stderr || '').includes('review mode allows only the review or none') ? null : 'missing refusal'),
      },
      {
        name: 'copilot-review-extra-refused',
        config: { extraArgs: { copilot: ['--available-tools=bash'] }, retry: { max_retries: 1 } },
        args: ['--runtime', 'copilot', '--mode', 'review', '--model', 'fake-ok'],
        env: { COPILOT_GITHUB_TOKEN: 'github_pat_' + 'a'.repeat(40) },
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
        check: async (r, ctx) => {
          if (ctx.calls.length) return `spawned: ${ctx.calls.join('|')}`;
          if (!(r.stderr || '').includes('review argv for copilot holds --available-tools=bash')) {
            return 'element not named';
          }
          const copy = writeCopy(ctx.tmp, 'copilot-extra-allow', {
            extraArgs: { copilot: ['--allow-tool', 'shell'] }, retry: { max_retries: 1 },
          });
          const got = await runCaseProcess({
            args: ['--runtime', 'copilot', '--mode', 'review', '--model', 'fake-ok'],
          }, { ...ctx, copy });
          if (got.status !== 2) return `allow-tool exit ${got.status}`;
          return (got.stderr || '').includes('review argv for copilot holds --allow-tool')
            ? null : 'allow-tool element not named';
        },
      },
      {
        name: 'copilot-transient-new-sessions',
        args: ['--runtime', 'copilot', '--model', 'fake-event400'],
        config: { retry: { max_retries: 2, session_resets: 1 } },
        env: { COPILOT_GITHUB_TOKEN: 'github_pat_' + 'a'.repeat(40) },
        exit: 75,
        status: /^AIKIT-XAI status=transient cli=copilot model=fake-event400 exit=75 .* action=stop$/,
        check: (_r, ctx) => {
          const calls = ctx.calls.filter((l) => l.startsWith('copilot '));
          if (calls.length !== 3) return `calls=${calls.length}`;
          return calls.every((l) => l === 'copilot event400') ? null : `calls=${calls.join('|')}`;
        },
      },
      {
        name: 'copilot-dash-prompt',
        args: ['--runtime', 'copilot', '--model', 'fake-ok'],
        stdin: '---\nrest\n',
        env: { COPILOT_GITHUB_TOKEN: 'github_pat_' + 'a'.repeat(40) },
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=copilot model=fake-ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          c.seen = path.join(c.tmp, 'copilot-seen-dash.json');
          c.env.FAKE_COPILOT_SEEN = c.seen;
          return null;
        },
        check: (_r, ctx) => {
          const seen = JSON.parse(fs.readFileSync(ctx.seen, 'utf8'));
          return seen.prompt.startsWith('\n---') ? null : `prompt head=${JSON.stringify(seen.prompt.slice(0, 12))}`;
        },
      },
      {
        name: 'copilot-argv-review',
        args: ['--runtime', 'copilot', '--mode', 'review', '--model', 'fake-ok', '--print-argv'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const line = (r.stdout || '').split('\n').find((l) => l.startsWith('copilot\t'));
          if (!line) return 'missing argv line';
          const argv = JSON.parse(line.split('\t')[2]);
          const tail = ['--allow-all-tools', '--available-tools=view,grep,glob',
            '--excluded-tools=bash,create,edit,apply_patch', '--deny-tool=shell',
            '--deny-tool=write', '--disable-builtin-mcps'];
          const head = ['-p', '<prompt>', '-s', '--no-ask-user', '--model', 'fake-ok'];
          const want = [...head, ...tail];
          return JSON.stringify(argv) === JSON.stringify(want) ? null : `argv=${JSON.stringify(argv)}`;
        },
      },

    ];

    const only = (process.env.AIKIT_XAI_SELFTEST_CASES || '').split(',').filter(Boolean);
    const selected = only.length ? cases.filter((c) => only.includes(c.name)) : cases;
    if (selected.length !== (only.length || cases.length)) {
      process.stderr.write(`self-test: unknown case in AIKIT_XAI_SELFTEST_CASES=${only.join(',')}\n`);
      return 2;
    }
    let failed = false;
    for (const c of selected) {
      const reason = await runSelfTestCase(tmp, c);
      if (reason) {
        failed = true;
        process.stderr.write(`self-test FAIL ${c.name}: ${reason}\n`);
      }
    }
    if (failed) return 1;
    process.stdout.write('self-test ok\n');
    return 0;
  } finally {
    reapUnder(tmp, []);
    fs.rmSync(tmp, { recursive: true, force: true });
    selfTestRoot = null;
  }
}

async function main(argv) {
  runStartedMs = Date.now();
  finished = false;
  liveFields = {
    cli: '-', model: '-', cli_rc: '-', out: 0, tree: 'clean',
    route: 'unknown', rule: '-', pattern: 'none',
  };
  let o;
  try { o = parseArgs(argv); } catch (e) {
    log(`cross-ai: ${e.message}`);
    return reportAndFinish('usage', { ...liveFields, tree: 'unknown', exit: 2 });
  }
  OVERLAY_IDS = new Set();
  // The self-test never reads the owner's real overlay; each case builds its own.
  if (o.selfTest) return blackBoxSelfTest();
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
  const rt = RUNTIMES[name];
  if (o.model !== null && o.models[name] !== undefined) {
    log(`cross-ai: --model wins; ignored --model-${name} ${o.models[name]}`);
  }
  const model = o.model ?? o.models[name] ?? CONFIG.models[name];
  if (model && !rt.modelId.test(model)) {
    log(`cross-ai: ${name} model ${model} must match ${rt.modelId.source}`);
    return reportAndFinish('usage', { ...liveFields, cli: name, model, tree: 'unknown', exit: 2 });
  }
  const c = {
    name, rt, model,
    bin: resolveBin(rt, process.env.PATH || ''),
  };
  // Baked per-runner effort (the plan's selection); --codex-effort still wins for codex.
  const effort = CONFIG.effort || {};
  const knobs = {
    codexEffort: o.codexEffort ?? (CODEX_EFFORTS.has(effort.codex) ? effort.codex : null),
    piThinking: PI_THINKING.has(effort.pi) ? effort.pi : null,
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
  const resolved = resolveRetry(process.cwd(), process.env);
  if (o.codexSandbox && o.mode !== 'exec') {
    log('cross-ai: --codex-sandbox applies to exec mode only; review already runs read-only');
  }
  if (o.printArgv) {
    const ctx = {
      cwd: process.cwd(), sid: '<sid>', outFile: '<tmp>/last-message.md',
      codexEffort: knobs.codexEffort, codexServiceTier: o.codexServiceTier, cursorMode: o.cursorMode,
      piThinking: knobs.piThinking, codexSandbox: o.mode === 'exec' ? o.codexSandbox : null,
      profileFlags, promptArg: '<prompt>',
    };
    const formula = rt[o.mode];
    const argvOut = (c.model && typeof formula === 'function')
      ? withExtra(name, formula(c.model, ctx)) : null;
    process.stdout.write(`${name}\t${c.bin || 'MISSING'}\t${argvOut ? JSON.stringify(argvOut) : 'NO MODEL'}\n`);
    if (c.model && argvOut) {
      const rung1 = sameSessionArgv(name, rt, c.model, ctx, '<sid>', o.mode);
      if (rung1) log(`cross-ai: rung1 ${name} argv=${JSON.stringify(rung1.argv)}`);
      else log(`cross-ai: rung1 ${name} unavailable`);
      const rung2 = newSessionArgv(name, rt, c.model, ctx, o.mode, '<prompt>');
      log(`cross-ai: rung2 ${name} argv=${JSON.stringify(rung2.argv)}`);
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
  let body = raw;
  if (o.prependFile) {
    let prepended;
    try {
      prepended = fs.readFileSync(path.resolve(process.cwd(), o.prependFile), 'utf8');
    } catch {
      log(`cross-ai: --prepend-file unreadable: ${o.prependFile}`);
      return reportAndFinish('usage', { ...liveFields, tree: 'unknown', exit: 2 });
    }
    // The guidance file's stamp lines are bookkeeping for a human editor, not prompt text.
    body = `${prepended.replace(/^(?:<!--[^\n]*-->\r?\n)+/, '')}\n\n${raw}`;
  }
  const prompt = body + (o.preamble ? (o.mode === 'exec' ? EXEC_PREAMBLE : REVIEW_PREAMBLE) : '');
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
  if (aborting) {
    return reportAndFinish('signal', { ...liveFields, exit: 128 + aborting }, 'signal');
  }
  const before = noTree ? null : await treeState(process.cwd(), runDeadline);
  if (aborting) {
    return reportAndFinish('signal', { ...liveFields, exit: 128 + aborting }, 'signal');
  }
  if (!noTree && before === null) {
    return reportAndFinish(gitFailStatus(), {
      ...liveFields, cli_rc: '-', tree: 'unknown', exit: 1,
    });
  }
  // The review argv is known before any spawn: a widening extra is a usage error, not a run.
  if (o.mode === 'review' && c.model) {
    const probe = {
      cwd: process.cwd(), sid: '<sid>', outFile: '<tmp>/last-message.md',
      cursorMode: o.cursorMode, piThinking: knobs.piThinking, profileFlags,
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
  const listEnv = childEnv(c.rt.env, process.env);
  const listing = await listModels(c.rt, c.bin, listEnv, runDeadline);
  if (listing.ok) {
    const listed = c.rt.modelSuffix ? c.model.replace(c.rt.modelSuffix, '') : c.model;
    if (listed !== c.model) {
      log(`cross-ai: ${c.name} preflight checks ${listed}; the suffix ${c.model.slice(listed.length)} is not validated`);
    }
    if (!listing.ids.includes(listed)) {
      log(`cross-ai: ${c.name} bad_model (${c.model} not in model list)`);
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
  const r = await runCli(c.name, c.rt, c.bin, c.model, o.mode, prompt, {
    beforeSig: noTree ? null : stateSig(before), codexEffort: knobs.codexEffort,
    piThinking: knobs.piThinking, codexServiceTier: o.codexServiceTier,
    cursorMode: o.cursorMode, codexSandbox: o.mode === 'exec' ? o.codexSandbox : null,
    route: liveFields.route, retry: resolved.retry, capS: resolved.capS,
    profileFlags,
  });
  liveFields.out = r.outBytes || 0;
  liveFields.cli_rc = r.cli_rc ?? '-';
  const counted = {
    attempts: r.attempts || 0, cycles: r.cycles || 0,
    retryAfterS: r.retryAfterS, cycle: r.cycle, reportDone: r.reportDone,
    firstFailureMs: r.firstFailureMs, lastFailureMs: r.lastFailureMs,
    dueAtMs: r.dueAtMs,
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

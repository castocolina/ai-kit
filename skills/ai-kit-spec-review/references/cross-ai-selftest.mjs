// ai-kit cross-ai self-test harness (38-08). cross-ai.mjs loads this file only for
// --self-test and --self-test-list; a rendered project copy does not carry it.
import { spawn, spawnSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import vm from 'node:vm';
import os from 'node:os';
import path from 'node:path';
import { StringDecoder } from 'node:string_decoder';
import { fileURLToPath, pathToFileURL } from 'node:url';
import {
  ARGV_PROMPT_MAX,
  CLAUDE_EXEC_FORMULA_RECORD,
  CLI_NAME_RE,
  CONFIG,
  CONTEXT_RE,
  CURSOR_MODEL_ID,
  EXEC_PREAMBLE,
  FINDING_CODES,
  HERDR_BIN,
  HERDR_VERBS,
  HOST_PATH_SAFE,
  IDLE_DEFAULT_S,
  IDLE_MAX_S,
  KEY_SHAPES,
  LEVEL_RE,
  MODEL_ID,
  MODEL_ID_FLOOR,
  OPENCODE_MODEL_ID,
  PATTERNS,
  PI_MODEL_ID,
  RESUME_MSG,
  RETRY_DEFAULTS,
  RUNNER_FILE,
  RUNTIMES,
  RUNTIME_ID_RE,
  SESSION_ID_RE,
  SETTING_NAMES,
  SETTING_REASONS,
  SETTING_STATES,
  SKILL_NAME_RE,
  SKILL_PROSE,
  TABLE,
  addFinding,
  aiKitConfigDir,
  argvFileAllowed,
  argvFileRow,
  argvPromptProblem,
  capCodePoints,
  checkGroup,
  checkoutRoot,
  clampAttemptTimeout,
  clampCapS,
  classifyStop,
  clearStaleLock,
  composePrompt,
  confirmReport,
  current,
  cycleFilePath,
  eventsWithRaw,
  extractEvents,
  findingDetail,
  findingLines,
  finish,
  groupMembers,
  hardWaitFor,
  idleBudgetNote,
  killGroup,
  ladderNext,
  ladderStop,
  launcherVerified,
  liveCheck,
  liveMatch,
  lockGroupAlive,
  lockPath,
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
  parseTomlSubset,
  pidAlive,
  planArgvFile,
  planIdle,
  planSettings,
  planSkills,
  procGroup,
  procSession,
  procStartTime,
  promptFiles,
  providerAdmits,
  pushCapped,
  readCallFile,
  readCycleState,
  readLockOnce,
  readOr,
  redactSecrets,
  redactedValues,
  removeRetryBlock,
  replaceCopies,
  reportLines,
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
  taskDigest,
  upsertTomlKeys,
  upstreamFields,
  upstreamOf,
  validateRetryKey,
  validateRow,
  which,
  writeCycleState,
} from './cross-ai.mjs';

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
    model: 'fake/my-coding',
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
    kind: 'logic',
    pure: () => pureClassify(entry),
  }));
  const pinned = CLASSIFY_CASES.find((entry) => entry.name === 'edge-billing-and-quota');
  const twice = CLASSIFY_CASES.find((entry) => entry.name === 'opencode-monthly-limit-router');
  return [
    ...generated,
    {
      name: 'pure-classify-order-mutation',
      kind: 'logic',
      pure: () => {
        const forward = classifyOne(pinned);
        const reversed = classifyOne(pinned, [...PATTERNS].reverse());
        if (reversed.status === forward.status) return `reversal kept status ${forward.status}`;
        return null;
      },
    },
    {
      name: 'pure-classify-idempotent',
      kind: 'logic',
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
      kind: 'logic',
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
      kind: 'logic',
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
      kind: 'logic',
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
      kind: 'logic',
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
      kind: 'logic',
      pure: () => {
        const routerRow = { route: 'router' };
        if (!routeAdmits(routerRow, 'router') || routeAdmits(routerRow, 'unknown') ||
          routeAdmits(routerRow, 'router-inferred')) return 'route router';
        const unknownRow = { route: 'unknown' };
        if (routeAdmits(unknownRow, 'router') || !routeAdmits(unknownRow, 'unknown') ||
          !routeAdmits(unknownRow, 'router-inferred')) return 'route unknown';
        const row = { provider: 'fake' };
        if (!providerAdmits(row, 'unknown', 'fake/coding-5')) return 'own provider model refused';
        if (providerAdmits(row, 'unknown', 'placeholder-model-1')) return 'other provider admitted';
        if (!providerAdmits(row, 'router', 'placeholder-model-1')) return 'router lane refused';
        return null;
      },
    },
    {
      name: 'pure-overlay-regex-timeout',
      kind: 'runtime',
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
        setLog((line) => logs.push(line));
        try {
          setOverlayIds(new Set([row.id]));
          setTable(mergeCatalog(PATTERNS, [row]));
          const first = classifyStop({ cli: 'pi', route: 'unknown', stderr: text });
          const second = classifyStop({ cli: 'pi', route: 'unknown', stderr: text });
          const elapsed = Date.now() - started;
          if (elapsed >= scaledMs(1000)) return `elapsed ${elapsed}`;
          const notices = logs.filter((line) => line === 'cross-ai: overlay disabled: match exceeded 50 ms');
          if (notices.length !== 1) return `notices ${notices.length}: ${logs.join('|')}`;
          if (first.rule === row.id || second.rule === row.id) return `matched overlay ${first.rule}`;
          return null;
        } finally {
          setLog(real);
          setOverlayIds(new Set());
          setTable(mergeCatalog(PATTERNS, []));
        }
      },
    },
    {
      name: 'pure-overlay-budget',
      kind: 'runtime',
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
        setLog((line) => logs.push(line));
        const started = Date.now();
        try {
          setOverlayIds(new Set(rows.map((row) => row.id)));
          setTable(mergeCatalog(PATTERNS, rows));
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
          setLog(real);
          setOverlayIds(new Set());
          setTable(mergeCatalog(PATTERNS, []));
        }
      },
    },
    {
      name: 'pure-overlay-call-budget',
      kind: 'runtime',
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
        setLog((line) => logs.push(line));
        const started = Date.now();
        try {
          setOverlayIds(new Set([row.id]));
          setTable(mergeCatalog(PATTERNS, [row]));
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
          setLog(real);
          setOverlayIds(new Set());
          setTable(mergeCatalog(PATTERNS, []));
        }
      },
    },
    {
      // Live matching sees one line; a multi-line fixture is out of scope because post-hoc
      // matching sees the whole text.
      name: 'pure-live-agrees-posthoc',
      kind: 'logic',
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
      kind: 'logic',
      pure: () => {
        const got = redactSecrets('{"message":"x","token":"abc","retry_after":120,"reset_at":"2026-10-23T04:01:04.472Z"}');
        return got === '{"message":"x","token":"<redacted>","retry_after":120,"reset_at":"2026-10-23T04:01:04.472Z"}' ? null : got;
      },
    },
    {
      name: 'pure-redact-shapes',
      kind: 'logic',
      pure: () => {
        const source = 'conn:ab12cd34 12345678-1234-abcd-1234-1234567890ab "connectionId":"x1" account_id=x2 "requestId": "x3" ghp_' + 'a'.repeat(36) + ' github_pat_' + 'b'.repeat(40) + ' retry_after":340954 reset_at":"2026-10-23T04:01:04.472Z"';
        const got = redactSecrets(source);
        for (const secret of ['ab12cd34', '12345678-1234-abcd-1234-1234567890ab', 'x1', 'x2', 'x3', 'ghp_', 'github_pat_']) if (got.includes(secret)) return `leaked ${secret}`;
        return got.includes('340954') && got.includes('2026-10-23') ? null : 'retry fields lost';
      },
    },
    {
      name: 'pure-redact-escaped-json',
      kind: 'logic',
      pure: () => {
        const input = '{"error":{"response":{"body":"{\\"accountId\\":\\"acct-123\\",\\"api_key\\":\\"sentinel\\",\\"requestId\\": \\"req-9\\",\\"retry_after\\":120}"}}}';
        const got = redactSecrets(input);
        for (const secret of ['acct-123', 'sentinel', 'req-9']) if (got.includes(secret)) return `leaked ${secret}`;
        return got.includes('retry_after') ? null : 'retry_after lost';
      },
    },
    {
      name: 'pure-redact-quoted-values',
      kind: 'logic',
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
      kind: 'logic',
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
      kind: 'logic',
      pure: () => {
        const raw = ocError({ message: 'first', response: { body: '{"message":"nested"}' } });
        const got = eventsWithRaw('opencode', raw);
        return got.events.length === 3 && got.eventRaw.every((line) => line === raw) ? null : JSON.stringify(got);
      },
    },
    {
      // Each event keeps its own stdout line as its raw text, never the whole multi-line output.
      name: 'pure-events-with-raw-per-line',
      kind: 'logic',
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
      kind: 'logic',
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
      kind: 'logic',
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
      kind: 'logic',
      pure: () => {
        const out = [];
        const saved = log;
        setLog((text) => { out.push(text); });
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
          setLog(saved);
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
      kind: 'logic',
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
      kind: 'logic',
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
      kind: 'logic',
      pure: () => {
        const once = redactSecrets('{"accountId":"acct-77","token":"secret"}');
        return redactSecrets(once) === once ? null : redactSecrets(once);
      },
    },
    {
      // Each KEY_SHAPES row redacts its own synthetic sample, built here from a prefix and
      // filler; a token whose body holds another shape, or a key glued before a private-key
      // block, becomes one marker; two keys joined by a comma stay two markers; a Bearer value
      // holding a key shape loses its whole value; a key rule and a shape leave one marker in
      // a quoted JSON value, key and quote kept.
      name: 'pure-redact-key-shapes',
      kind: 'logic',
      pure: () => {
        const samples = {
          github_token: 'ghp_' + 'x'.repeat(36),
          github_pat: 'github_pat_' + 'x'.repeat(40),
          google_api_key: 'AIza' + 'x'.repeat(35),
          slack_token: 'xoxb-' + 'x'.repeat(24),
          pem_private_key: '-----BEGIN ' + 'RSA PRIVATE KEY' + '-----',
          aws_access_key_id: 'AKIA' + 'X'.repeat(16),
          gitlab_token: 'glpat-' + 'x'.repeat(20),
          xai_api_key: 'xai-' + 'x'.repeat(32),
          jwt: 'eyJ' + 'x'.repeat(12) + '.eyJ' + 'x'.repeat(12) + '.' + 'x'.repeat(12),
          stripe_key: 'sk_live_' + 'x'.repeat(24),
          huggingface_token: 'hf_' + 'x'.repeat(34),
          npm_token: 'npm_' + 'x'.repeat(36),
          groq_key: 'gsk_' + 'x'.repeat(52),
          sk_rk_key: 'sk-' + 'x'.repeat(24),
        };
        for (const [name, sample] of Object.entries(samples)) {
          if (redactSecrets(`note ${sample} end`) !== 'note <redacted> end') return `${name} not redacted`;
        }
        const rows = KEY_SHAPES.map(([name]) => name).join(',');
        if (rows !== Object.keys(samples).join(',')) return 'KEY_SHAPES rows and samples differ';
        const nested = {
          gitlab_token: 'glpat-' + 'a'.repeat(8) + '-' + 'AKIA' + 'X'.repeat(16) + 'z'.repeat(64),
          slack_token: 'xoxb-' + '1'.repeat(12) + '-ghp_' + 'b'.repeat(36) + '-' + 'c'.repeat(30),
        };
        for (const [name, sample] of Object.entries(nested)) {
          if (redactSecrets(`note ${sample} end`) !== 'note <redacted> end') return `nested ${name} left a residue`;
        }
        const pemLabel = 'RSA PRIVATE KEY';
        const pem = '-----BEGIN ' + pemLabel + '-----\n' + 'MIIB' + 'a'.repeat(60) + '\n-----END ' + pemLabel + '-----';
        if (redactSecrets(`note ${'sk-' + 'a'.repeat(8) + pem} end`) !== 'note <redacted> end') return 'key glued before a PEM block left a residue';
        const escaped = redactSecrets(`{"a":"x\\n${samples.github_token}"}`);
        if (escaped !== '{"a":"x\\n<redacted>"}') return 'key after a JSON \\n escape not redacted';
        const open = '-----BEGIN ' + pemLabel + '-----\n' + ('MIIB' + 'a'.repeat(60) + '\n').repeat(20);
        if (redactSecrets(`note ${open} end`) !== 'note <redacted> end') return 'unclosed PEM body left a residue';
        const pair = samples.github_token + ','+ samples.xai_api_key;
        if (redactSecrets(`note ${pair} end`) !== 'note <redacted>,<redacted> end') return 'two keys joined by a comma did not give two markers';
        const bearer = redactSecrets('Bearer abc-' + 'AKIA' + 'Z'.repeat(16) + 'q'.repeat(64));
        if (bearer !== 'Bearer <redacted>') return 'Bearer value left a suffix';
        const keyed = redactSecrets(`{"token":"${samples.aws_access_key_id}"}`);
        const bare = redactSecrets(`{"note":"${samples.jwt}"}`);
        return keyed === '{"token":"<redacted>"}' && bare === '{"note":"<redacted>"}' ? null : 'quoted value lost its key or quote';
      },
    },
    {
      name: 'pure-upstream-cap',
      kind: 'logic',
      pure: () => {
        const capped = capCodePoints('😀'.repeat(2500), 2000);
        return Array.from(capped).length === 2000 && !/[\\uD800-\\uDBFF]$/.test(capped) ? null : `codepoints=${Array.from(capped).length}`;
      },
    },
    {
      name: 'pure-upstream-fields',
      kind: 'logic',
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

// A case's state file, resolved inside the case's own XDG state dir. Router by default: the
// Phase 25 fixtures all sit on confirmed router lanes.
function caseCycleFile(ctx, cli, model, kind = 'router') {
  const home = path.join(ctx.env.XDG_STATE_HOME);
  return cycleFilePath(cli, model, kind, ctx.repo, home);
}

function hermeticEnv(tmp, extra = {}) {
  const home = extra.HOME || path.join(tmp, 'home');
  // A runner temp folder a case leaves behind stays inside the self-test root, never in /tmp.
  const tmpdir = extra.TMPDIR || path.join(tmp, 'tmpdir');
  fs.mkdirSync(tmpdir, { recursive: true });
  const base = {
    TMPDIR: tmpdir,
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
  const src = fs.readFileSync(RUNNER_FILE, 'utf8');
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
const recordSession = (cli, id, input) => { if (process.env.FAKE_SESSIONS) fs.appendFileSync(process.env.FAKE_SESSIONS, cli + ' ' + (id || '-') + ' ' + (String(input || '').startsWith('You were interrupted') ? 'resume-note' : 'prompt') + '\n'); };
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
  'hang', 'hangonce', 'gcescape', 'outer-race', 'stubborn', 'slowok', 'lockhold', 'big', 'sentinelsplit',
  'limit-mid', 'limit-partial', 'limit-flood', 'limit-partial-flood', 'auth-then-noise',
  'transient-hang', 'bare-429-hang', 'retry-notice', 'retry-notice-429', 'slowquota',
  'capclamp', 'reason-code-hang', 'slow-lines', 'router-stop-hang', 'ticker',
]);
let stdinBuf = '';
const FAKE_MODES = {
  // Hosted only: kills the launcher shell so it never writes rc; under a node parent it exits 3.
  killparent: () => {
    let comm = '';
    try { comm = fs.readFileSync('/proc/' + process.ppid + '/comm', 'utf8').trim(); } catch { /* unavailable */ }
    if (!['sh', 'dash', 'bash'].includes(comm)) process.exit(3);
    process.kill(process.ppid, 'SIGKILL');
  },
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
  lockpeek: () => {
    const dir = (process.env.XDG_STATE_HOME || '') + '/ai-kit/spec/locks';
    const names = fs.readdirSync(dir).filter((n) => n.endsWith('.json'));
    const mode = (p) => (fs.statSync(p).mode & 0o777).toString(8);
    const one = names.length === 1 ? dir + '/' + names[0] : null;
    let pgid = process.pid;
    try { const st = fs.readFileSync('/proc/self/stat', 'utf8'); pgid = Number(st.slice(st.lastIndexOf(')') + 1).trim().split(/\s+/)[2]); } catch { pgid = process.pid; }
    fs.writeFileSync((process.env.HOME || '.') + '/lock.seen', JSON.stringify({ names, dir: mode(dir), file: one ? mode(one) : '-', rec: one ? JSON.parse(fs.readFileSync(one, 'utf8')) : null, pgid }));
    fs.appendFileSync('a.txt', 'lockpeek\n');
    process.stdout.write('# Summary\nok');
  },
  lockhold: () => {
    const t0 = Date.now();
    const tick = () => { if (fs.existsSync((process.env.HOME || '.') + '/lock-release') || Date.now() - t0 > 20000) { fs.appendFileSync('a.txt', 'hold\n'); process.stdout.write('# Summary\nok'); process.exit(0); } else setTimeout(tick, 50); };
    tick();
  },
  ticker: () => {
    // Each stream alone is silent for 2.4 s; together the gap is never over 1.2 s.
    const parts = ['tick\n', Buffer.from([0xE2]), 'tick\n', Buffer.from([0x82, 0xAC, 0x0A])];
    [1200, 2400, 3600, 4800].forEach((ms, i) => setTimeout(() => (i % 2 ? process.stdout : process.stderr).write(parts[i]), ms));
    setTimeout(() => { fs.appendFileSync('a.txt', 'tick\n'); process.stdout.write('# Summary\nok'); process.exit(0); }, 4900);
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
  gcleft: () => {
    const gc = spawn(process.execPath, ['-e', 'setInterval(() => {}, 1 << 30)'], { stdio: 'ignore' });
    recordGc(gc.pid);
    gc.unref();
    fs.appendFileSync('a.txt', 'gl\n');
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
let input = ''; process.stdin.on('data', (d) => { input += d; }).on('end', () => {
  const given = argOf('--resume');
  recordSession('cursor-agent', given, input);
  if (given.startsWith('rejected-')) { process.stderr.write('fake-session: no session ' + given + '\n'); process.exit(7); }
  if (given.startsWith('rejected503-')) { process.stderr.write('503 Service Unavailable\n'); console.log(JSON.stringify({ type: 'result', is_error: true, result: '503 Service Unavailable', session_id: given })); process.exit(1); }
  if (process.env.FAKE_SESSION_MODE === 'badsid-503') { process.stderr.write('503 Service Unavailable\n'); console.log(JSON.stringify({ type: 'result', is_error: true, result: '503 Service Unavailable', session_id: 'bad id!' })); process.exit(1); }
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
  console.log(JSON.stringify({ type: 'result', subtype: 'success', is_error: false, result: '## Summary\nok', session_id: given || 'c1' }));
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
let input = '';
process.stdin.on('data', (d) => { input += d; }).on('end', () => {
  const given = argOf('--session');
  recordSession('opencode', given, input);
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
  if (process.env.FAKE_OPENCODE_MODE === 'plan-reminder') {
    // opencode 2.3.0 plan agent: a tool step, the answer, then a reply to its injected
    // plan-mode reminder (a synthetic user turn the json stream does not show).
    const ev = (type, msg, part) => JSON.stringify({ type, sessionID: 'ses_2', part: { messageID: msg, ...part } });
    const lines = [
      ev('step_start', 'm1', { id: 's1', type: 'step-start' }),
      ev('text', 'm1', { id: 'p1', type: 'text', text: 'Reading the plan.' }),
      ev('step_finish', 'm1', { id: 'f1', type: 'step-finish', reason: 'tool-calls' }),
      ev('step_start', 'm2', { id: 's2', type: 'step-start' }),
      ev('text', 'm2', { id: 'p2', type: 'text', text: '## Summary\nverdict' }),
      ev('step_finish', 'm2', { id: 'f2', type: 'step-finish', reason: 'stop' }),
      ev('step_start', 'm3', { id: 's3', type: 'step-start' }),
      ev('text', 'm3', { id: 'p3', type: 'text', text: 'Plan mode is active.' }),
      ev('step_finish', 'm3', { id: 'f3', type: 'step-finish', reason: 'stop' }),
    ];
    for (const l of lines) console.log(l);
    process.exit(0);
  }
  const turnModes = {
    // A stop step, background_wait, then the agent continues and answers.
    'background-wait': [['step_start', 'm1'], ['text', 'm1', 'Waiting for the job.'], ['step_finish', 'm1', 'stop'], ['background_wait'], ['step_start', 'm2'], ['text', 'm2', '## Summary\nfinal'], ['step_finish', 'm2', 'stop']],
    // A complete answer, then an error on the injected reminder turn and exit 1.
    'late-error': [['text', 'm1', '## Summary\nverdict'], ['step_finish', 'm1', 'stop'], ['error'] ],
    // The ending step ran out of tokens.
    'length': [['text', 'm1', '## Summary\ncut off'], ['step_finish', 'm1', 'length']],
    // The ending step has no text of its own; the earlier message must not be returned.
    'no-text': [['text', 'm1', 'Reading the plan.'], ['step_finish', 'm1', 'tool-calls'], ['step_start', 'm2'], ['step_finish', 'm2', 'stop']],
  };
  const turnMode = turnModes[process.env.FAKE_OPENCODE_MODE];
  if (turnMode) {
    for (const [type, msg, extra] of turnMode) {
      if (type === 'error') console.log(JSON.stringify({ type, sessionID: 'ses_3', error: { type: 'provider.quota', status: 429, message: 'rate limited' } }));
      else if (type === 'background_wait') console.log(JSON.stringify({ type, sessionID: 'ses_3' }));
      else if (type === 'text') console.log(JSON.stringify({ type, sessionID: 'ses_3', part: { id: 'p' + msg, messageID: msg, type, text: extra } }));
      else console.log(JSON.stringify({ type, sessionID: 'ses_3', part: { id: type + msg, messageID: msg, type: type.replace('_', '-'), reason: extra } }));
    }
    process.exit(process.env.FAKE_OPENCODE_MODE === 'late-error' ? 1 : 0);
  }
  const lines = [
    JSON.stringify({ type: 'text', sessionID: given || 'ses_1', part: { id: 'p1', messageID: 'm1', type: 'text', text: 'Plan first.' } }),
    JSON.stringify({ type: 'tool_use', sessionID: given || 'ses_1', part: { type: 'tool', tool: 'bash' } }),
    JSON.stringify({ type: 'text', sessionID: given || 'ses_1', part: { id: 'p2', messageID: 'm2', type: 'text', text: '## Summary\ndone' } }),
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
const mcpCount = (file) => { try { return Object.keys(JSON.parse(fs.readFileSync(file, 'utf8')).mcpServers || {}).length; } catch { return -1; } };
recordSession('copilot', argOf('--session-id'), argOf('-p'));
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
    mcpCount: argOf('--additional-mcp-config') ? mcpCount(argOf('--additional-mcp-config').slice(1)) : null,
  }));
}
if (process.env.FAKE_SKILL_EDIT) fs.appendFileSync(process.env.FAKE_SKILL_EDIT, 'edited\n');
if (!tokens.length) {
  process.stderr.write('Error: not logged in. Run copilot login or set COPILOT_GITHUB_TOKEN.\n');
  process.exit(1);
}
if (mode === 'event400') {
  process.stderr.write('[400]: event: error\n');
  process.exit(1);
}
if (mode !== 'readonly') fs.appendFileSync('a.txt', 'ok-line\n');
process.stderr.write('copilot: using token ' + process.env[tokens[0]] + '\n');
process.stdout.write('# Summary\nok');
`);
}

function writeFakeClaude(binDir) {
  writeExe(binDir, 'claude', "import { spawnSync } from 'node:child_process';\n", String.raw`
log('claude ' + argOf('--model'));
const mcpCount = (file) => { try { return Object.keys(JSON.parse(fs.readFileSync(file, 'utf8')).mcpServers || {}).length; } catch { return -1; } };
let input = '';
process.stdin.on('data', (d) => { input += d; }).on('end', () => {
  if (process.env.FAKE_CLAUDE_SEEN) fs.writeFileSync(process.env.FAKE_CLAUDE_SEEN, JSON.stringify({ argv: process.argv.slice(2), stdin: input, mcpCount: argOf('--mcp-config') ? mcpCount(argOf('--mcp-config')) : null }));
  const given = argOf('--resume');
  recordSession('claude', given, input);
  if (argOf('--model') === 'fake-auth') {
    process.stderr.write('401 unauthorized\n');
    console.log(JSON.stringify({ type: 'result', is_error: true, result: '401 unauthorized' }));
    process.exit(1);
  }
  const execute = argOf('--permission-mode') !== 'plan';
  if (execute) {
    fs.appendFileSync('a.txt', 'claude\n');
    spawnSync('git', ['add', 'a.txt']);
    spawnSync('git', ['commit', '-q', '-m', 'fake claude execute']);
  }
  const result = { type: 'result', result: execute ? '## Summary\nok' : 'ok', is_error: false };
  if (process.env.FAKE_SESSION_MODE !== 'nosid') result.session_id = given || 'x';
  console.log(JSON.stringify(result));
  process.exit(0);
});
`);
}

function writeFakeDeclared(binDir) {
  writeExe(binDir, 'placeholder-cli-1', '', String.raw`
let stdin = '';
process.stdin.on('data', (d) => { stdin += d; }).on('end', () => {
  const argv = process.argv.slice(2);
  log('declared ' + JSON.stringify(argv));
  if (process.env.FAKE_DECLARED_SEEN) fs.writeFileSync(process.env.FAKE_DECLARED_SEEN, JSON.stringify({ argv, stdin }));
  const chosen = argOf('--model');
  if (chosen === 'fake-crash') { process.stderr.write('placeholder failure ' + (process.env.AIKIT_XAI_SENTINEL || '') + '\n'); process.exit(7); }
  if (chosen === 'fake-edit-then-ok' && !fs.readFileSync('ign/argv.json', 'utf8').includes('changed-command')) {
    fs.writeFileSync('ign/argv.json', '["changed-command"]');
    process.stderr.write('circuit_open\n'); process.exit(1);
  }
  if (chosen !== 'fake-review') fs.appendFileSync('a.txt', 'declared\n');
  process.stdout.write('# Summary\nok');
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
const dash = sub.lastIndexOf('-');
const resumeId = sub[1] === 'resume' && dash > 0 ? sub[dash - 1] : '';
if (sub[0] === 'exec' && sub[1] === 'resume') log('codex-resume ' + argOf('-m'));
log('codex ' + argOf('-m'));
let input = '';
process.stdin.on('data', (d) => { input += d; }).on('end', () => {
  recordSession('codex', resumeId, input);
  const model = argOf('-m');
  if (model !== 'fake-event400-codex') fs.appendFileSync('a.txt', 'cx\n');
  if (outFile) fs.writeFileSync(outFile, '## Summary\nok');
  console.log(JSON.stringify({ type: 'thread.started', thread_id: resumeId || 't1' }));
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

function writeFakeHerdr(binDir) {
  writeExe(binDir, HERDR_BIN, "import { spawn } from 'node:child_process';\nimport path from 'node:path';\n", String.raw`
const home = process.env.HOME || '.';
const hlog = (line) => fs.appendFileSync(path.join(home, 'herdr.log'), line + '\n');
const args = process.argv.slice(2);
hlog('argv ' + JSON.stringify(args));
const lock = path.join(home, 'herdr-state.lock');
let held = false;
for (let i = 0; i < 400; i++) {
  try { fs.mkdirSync(lock); held = true; break; } catch { Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 5); }
}
const unlock = () => { if (held) { try { fs.rmdirSync(lock); } catch { /* not held */ } held = false; } };
process.on('exit', unlock);
const fail = process.env.FAKE_HERDR_FAIL || '';
const stateFile = path.join(home, 'herdr-state.json');
let state = { next: 1, tabs: { t0: { label: 'aikit:review:pi:000000000000', pane: 'p0', cwd: home, pgid: null, dir: null, closed: false } } };
try { state = JSON.parse(fs.readFileSync(stateFile, 'utf8')); } catch { /* new state */ }
const save = () => fs.writeFileSync(stateFile, JSON.stringify(state));
const mode = (p) => { try { return (fs.statSync(p).mode & 0o777).toString(8); } catch { return '-'; } };
const verb = args[0] + ' ' + args[1];
if (verb === 'tab create') {
  if (fail === 'create') { console.error('{"error":"fake create failure"}'); process.exit(1); }
  const id = 't' + state.next, pane = 'p' + state.next++;
  state.tabs[id] = { label: argOf('--label'), pane, cwd: argOf('--cwd'), pgid: null, dir: null, closed: false };
  save();
  if (fail === 'create-lost') { console.log('not json'); process.exit(0); }
  console.log(JSON.stringify({ result: { tab: { tab_id: id, label: argOf('--label') }, root_pane: { pane_id: pane } } }));
} else if (verb === 'pane run') {
  if (fail === 'run') { console.error('{"error":"fake pane run failure"}'); process.exit(1); }
  if (fail === 'run-lost') { unlock(); process.kill(process.pid, 'SIGKILL'); }
  if (fail === 'nolaunch') { hlog('nolaunch'); process.exit(0); }
  const tab = Object.values(state.tabs).find((t) => t.pane === args[2]);
  if (!tab || tab.closed) { console.error('{"error":"fake pane run failure"}'); process.exit(1); }
  const m = /^sh (\/[A-Za-z0-9._\/-]+)$/.exec(args[3] || '');
  if (!m) { hlog('typed-line-rejected'); process.exit(1); }
  const dir = path.dirname(m[1]);
  hlog('modes dir=' + mode(dir) + ' env=' + mode(path.join(dir, 'env')) + ' prompt=' + mode(path.join(dir, 'prompt')) + ' run=' + mode(path.join(dir, 'run.json')) + ' launch=' + mode(m[1]));
  const rec = JSON.parse(fs.readFileSync(path.join(dir, 'run.json'), 'utf8'));
  hlog('record tab=' + rec.tab_id + ' pane=' + rec.pane_id);
  const child = spawn('/bin/sh', [m[1]], { cwd: tab.cwd, detached: true, stdio: 'ignore', env: process.env });
  recordPid('launcher', child.pid); child.unref();
  tab.pgid = child.pid; tab.dir = dir; tab.closed = process.env.FAKE_HERDR_PRECLOSED === '1'; save();
  if (fail === 'run-after') { console.error('{"error":"fake pane run failure"}'); process.exit(1); }
} else if (verb === 'tab close') {
  const tab = state.tabs[args[2]];
  hlog('close ' + args[2] + ' dir=' + (tab && tab.dir ? (fs.existsSync(tab.dir) ? 'present' : 'gone') : '-') + (tab && tab.closed ? ' already-closed' : ''));
  if (fail === 'close') { console.error('{"error":"fake close failure"}'); process.exit(1); }
  if (tab && !tab.closed && tab.pgid) { try { process.kill(-tab.pgid, 'SIGHUP'); } catch { /* gone */ } }
  if (tab) tab.closed = true;
  save(); console.log('{"result":{"type":"ok"}}');
} else { hlog('unknown-verb ' + verb); process.exit(2); }
`);
}

const STATUS_HEAD_RE = new RegExp(
  '^(.* action=stop)(?: (route=\\S+ rule=\\S+ pattern=\\S+))?' +
  '(?: (attempts=\\S+ cycles=\\S+))?(?: (session=\\S+ applied=\\S+ ignored=\\S+ unknown=\\S+ escalate=\\S+))?(?: (coverage=\\S+ findings=\\S+))?(?: (retry_after_s=\\S+ cycle=\\S+))?(?: upstream=\\S+)?$',
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

// Writes one config fixture (TOML text) for a self-test case, creating its folder first.
function writeCaseFile(file, text) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, text);
}
// The TOML subset sample for the values and CRLF cases: runner tables, a scope table, opaque
// [lanes] and [[lanes.review]] tables, and a string-final array.
const TOML_SAMPLE_TEXT = '# top\n[runner]\nmigrated_from = [".planning/config.json", "a,b]"]\n' +
  '[runner.retry]\nbase_s = 0.5\nfactor = 2\nhard_waits_s = [600, 900,]\nflag = true\n' +
  'name = "x\\"y" # note\n[runner.retry.scopes."p/workstreams/w"]\nmax_retries = 4\n' +
  '[lanes]\nstrategy = "local-only"\n[[lanes.review]]\nkey = "k"\nextra = { a = [1, 2] }\n' +
  '[lanes.policy]\nladder = ["a", "b"]\n';
const TOML_SAMPLE_OBJ = '{"runner":{"migrated_from":[".planning/config.json","a,b]"],"retry":' +
  '{"base_s":0.5,"factor":2,"hard_waits_s":[600,900],"flag":true,"name":"x\\"y",' +
  '"scopes":{"p/workstreams/w":{"max_retries":4}}}}}';

function retryLine(r, fragment) {
  const lines = (r.stderr || '').split('\n').filter((l) => l.startsWith('cross-ai: retry '));
  if (lines.length !== 1) return `retry lines=${lines.length}`;
  return lines[0].includes(fragment) ? null : lines[0];
}

function hostFilesDigest(home) {
  const lines = [];
  for (const rel of ['.claude', '.claude.json', '.agents', '.copilot', '.cursor', '.pi', '.codex', path.join('.config', 'opencode')]) {
    const root = path.join(home, rel);
    if (!fs.existsSync(root)) continue;
    const files = fs.statSync(root).isDirectory()
      ? fs.readdirSync(root, { withFileTypes: true, recursive: true }).filter((e) => e.isFile()).map((e) => path.join(e.parentPath || e.path, e.name))
      : [root];
    for (const file of files) {
      const stat = fs.statSync(file);
      if (stat.isFile()) lines.push(`${path.relative(home, file)}\t${crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex')}\t${stat.mtimeMs}\t${stat.size}`);
    }
  }
  return lines.sort().join('\n');
}

function statusTail(stderr) {
  const line = stderr.split('\n').filter((l) => l.startsWith('AIKIT-XAI ')).pop() || '';
  const parts = STATUS_HEAD_RE.exec(line);
  if (!parts || !parts[2]) return null;
  const tail = [parts[2], parts[3], parts[4], parts[5], parts[6]].filter(Boolean).join(' ');
  const tok = Object.fromEntries(tail.split(' ').map((t) => t.split('=')));
  return {
    route: tok.route, rule: tok.rule, pattern: tok.pattern,
    attempts: tok.attempts, cycles: tok.cycles,
    retry_after_s: tok.retry_after_s, cycle: tok.cycle,
    session: tok.session, applied: tok.applied, ignored: tok.ignored, unknown: tok.unknown, escalate: tok.escalate,
    coverage: tok.coverage, findings: tok.findings,
  };
}

function sessionRows(ctx) { return readOr(ctx.env.FAKE_SESSIONS, '').trim().split('\n').filter(Boolean).map((l) => l.split(' ')); }

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

// Scratch folders for the migration pure cases: a work folder and a home folder under one root that
// the case removes in its finally.
function migrationScratch() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'xai-mig-'));
  const work = path.join(root, 'work');
  const home = path.join(root, 'home');
  fs.mkdirSync(work, { recursive: true });
  fs.mkdirSync(home, { recursive: true });
  return { root, work, home };
}

// Runs fn with the log lines collected (not printed); the caller's log is restored in finally.
function collectLog(fn) {
  const saved = log;
  const lines = [];
  setLog((line) => { lines.push(line); });
  try {
    return { result: fn(), lines };
  } finally {
    setLog(saved);
  }
}

// Makes the first fs.renameSync whose target matches run `after` once the real rename has landed:
// a concurrent publish that replaces our file right after it. Returns the restore function.
function patchRenameOnce(match, after) {
  const savedRename = fs.renameSync;
  let fired = false;
  fs.renameSync = (from, to) => {
    savedRename(from, to);
    if (!fired && match(String(to))) {
      fired = true;
      after();
    }
  };
  return () => { fs.renameSync = savedRename; };
}

function plantLock(c, overrides = {}) {
  const root = fs.realpathSync(c.repo);
  c.lockFile = lockPath(root, c.env.XDG_STATE_HOME);
  writeCycleState(c.lockFile, { version: 1, run_id: 'planted-run', pid: process.pid,
    pid_start: procStartTime(process.pid), host_name: os.hostname(),
    started_ms: Date.UTC(2026, 10, 21), cli: 'pi', model: 'fake/planted', role: 'execute', root,
    child_pgid: null, child_start: null, baseline: null, launcher_pgid: null, token: null, tab_id: null, ...overrides });
  c.planted = fs.readFileSync(c.lockFile);
  return null;
}
function deadPid() { return spawnSync(process.execPath, ['-e', '']).pid; }
function plantLiveLock(c) { return plantLock(c); }
function plantedUnchanged(c) {
  return fs.existsSync(c.lockFile) && fs.readFileSync(c.lockFile).equals(c.planted);
}

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
  const tmpdir = path.join(tmp, `tmp-${spec.name}`);
  const env = hermeticEnv(tmp, {
    TMPDIR: tmpdir,
    HOME: home, XDG_CONFIG_HOME: path.join(home, '.config'),
    XDG_STATE_HOME: path.join(home, '.local', 'state', spec.name),
    FAKE_CALLS: calls, FAKE_PIDS: pidFile,
    FAKE_SIDS: path.join(tmp, `sids-${spec.name}.log`),
    FAKE_SESSIONS: path.join(tmp, `sessions-${spec.name}.log`),
    AIKIT_XAI_SENTINEL: 'sk-aikit-SENTINEL-' + process.pid,
    AIKIT_XAI_BEARER: 'brtok-' + process.pid,
    ...(spec.fakeOpencodeMode ? { FAKE_OPENCODE_MODE: spec.fakeOpencodeMode } : {}),
    ...(spec.env || {}),
  });
  const c = { tmp, repo, home, calls, pidFile, copy, env, tmpdir };
  let reason;
  try {
    reason = (spec.setup && spec.setup(c)) || await checkCase(spec, c);
  } finally {
    reapUnder(repo, [pidFile]);
  }
  // Every runner exit path drops its temp folders; only a case that kills the runner on
  // purpose (keepsTmp) may leave one.
  const left = spec.keepsTmp ? [] : fs.readdirSync(tmpdir);
  if (!reason && left.length) reason = `left in TMPDIR: ${left.join(',')}`;
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

async function blackBoxSelfTest(listOnly = false) {
  setOverlayIds(new Set());
  setTable(mergeCatalog(PATTERNS, []));
  const gitBin = which('git');
  if (!gitBin) {
    process.stderr.write('self-test: git not found\n');
    return 1;
  }
  selfTestLoadFactor = loadFactor(measuredLoadPerCpu());
  process.stderr.write(`self-test load factor ${selfTestLoadFactor}\n`);
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'xai-st-'));
  selfTestRoot = tmp;
  setSelfTestHook(selfTestAbort);
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
    writeFakeDeclared(binDir);
    for (const name of fs.readdirSync(binDir)) {
      if (name === 'codex') continue;
      const src = path.join(binDir, name);
      const dst = path.join(binNoCodex, name);
      if (!fs.existsSync(dst)) fs.symlinkSync(src, dst);
    }

    const herdrDir = path.join(tmp, 'bin-herdr');
    fs.mkdirSync(herdrDir, { recursive: true });
    writeFakeHerdr(herdrDir);
    const hostedPath = [path.join(tmp, 'bin'), herdrDir].join(path.delimiter);

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

    const noFormula = (id) => `cross-ai: no formula for ${id} in the runner; pass --argv-file, or use a runtime it has a formula for`;
    const advisory = (rt, re) => `cross-ai: note: model id shape is unusual for ${rt} (seed shape: ${re.source})`;
    const keyId = ['sk', 'aikit', 'SENTINEL', String(process.pid)].join('-');
    const skillBody = (n) => `# placeholder skill ${n}\n\nUse the word placeholder-token-${n}.\n`;
    const expectSkillBlock = (dir, n, body) => `<skill name="placeholder-skill-${n}" path="${fs.realpathSync(dir)}" sha256="${crypto.createHash('sha256').update(Buffer.from(body, 'utf8')).digest('hex')}">\n${body}\n</skill>\n`;
    const makeSkill = (c, n) => {
      const dir = path.join(c.tmp, 'skills', `placeholder-skill-${n}`);
      fs.mkdirSync(dir, { recursive: true });
      fs.writeFileSync(path.join(dir, 'SKILL.md'), skillBody(n));
      return dir;
    };
    const hostedUsable = (c) => HOST_PATH_SAFE.test(path.resolve(c.env.XDG_STATE_HOME));
    // A TMPDIR with a space makes every case's state home unsafe: the hosted cases then run headless once (host_failed).
    const hostedHere = HOST_PATH_SAFE.test(path.resolve(tmp));
    const hostFailedOnly = (r, c) => r.stderr.includes('cross-ai: setting host=herdr ignored reason=host_failed') && !fs.existsSync(path.join(c.home, 'herdr.log')) ? null : 'expected host_failed and no herdr call';
    const statusFields = (r) => {
      const line = r.stderr.split('\n').filter((s) => s.startsWith('AIKIT-XAI ')).at(-1) || '';
      const fields = Object.fromEntries(line.split(' ').slice(1).map((s) => s.split('=')));
      const selected = {};
      for (const key of 'status cli model exit cli_rc out tree route rule pattern attempts cycles session unknown escalate'.split(' ')) selected[key] = fields[key];
      for (const key of ['applied', 'ignored']) selected[key] = (fields[key] || '-').split(',').filter((s) => s !== 'host' && s !== '-').join(',') || '-';
      return JSON.stringify(selected);
    };
    const hostLogProblem = (c, tabs, closeTail = '') => {
      const text = readOr(path.join(c.home, 'herdr.log'), '');
      const lines = text.split('\n');
      const calls = lines.filter((s) => s.startsWith('argv ')).map((s) => JSON.parse(s.slice(5)));
      const verbs = calls.map((a) => a.slice(0, 2).join(' '));
      if (verbs.some((v) => !HERDR_VERBS.includes(v))) return `herdr verbs ${verbs}`;
      if (calls.some((a) => a.includes('t0') || a.includes('p0'))) return 'the foreign tab t0 was touched';
      if (verbs.filter((v) => v === 'tab create').length !== tabs) return `tab create count ${verbs.filter((v) => v === 'tab create').length}`;
      if (text.includes(c.env.AIKIT_XAI_SENTINEL)) return 'a key reached herdr';
      for (let i = 1; i <= tabs; i++) for (const line of [`record tab=t${i} pane=p${i}`, 'modes dir=700 env=600 prompt=600 run=600 launch=600', `close t${i} dir=present${closeTail}`]) if (!lines.includes(line)) return `herdr log lacks: ${line}`;
      const dir = path.join(c.env.XDG_STATE_HOME, 'ai-kit', 'spec', 'host');
      if (fs.existsSync(dir) && fs.readdirSync(dir).length) return `run dirs left: ${fs.readdirSync(dir)}`;
      return null;
    };
    const hostPairCheck = (both, c, extra) => {
      const lines = (r, prefix) => r.stderr.split('\n').filter((s) => s.startsWith(prefix));
      if (!both.again.stderr.includes('cross-ai: setting host=none applied')) return 'headless run lacks host=none';
      if (both.first.stdout !== both.again.stdout) return 'stdout differs';
      if (JSON.stringify(both.calls1) !== JSON.stringify(both.calls2)) return `lane calls differ: ${both.calls1} | ${both.calls2}`;
      if (JSON.stringify(lines(both.first, 'cross-ai: argv=')) !== JSON.stringify(lines(both.again, 'cross-ai: argv='))) return 'argv lines differ';
      const settings = (r) => lines(r, 'cross-ai: setting ').filter((s) => !s.startsWith('cross-ai: setting host='));
      if (JSON.stringify(settings(both.first)) !== JSON.stringify(settings(both.again))) return 'settings lines differ';
      if (statusFields(both.first) !== statusFields(both.again)) return `status fields differ: ${statusFields(both.first)} | ${statusFields(both.again)}`;
      if (both.first.stderr.includes(c.env.AIKIT_XAI_SENTINEL) || both.again.stderr.includes(c.env.AIKIT_XAI_SENTINEL)) return 'a key reached stderr';
      for (const name of extra.dead || []) for (const pid of recordedPids(c.pidFile)[name] || []) if (pidLingers(pid)) return `${name} ${pid} still alive`;
      if (!hostedUsable(c)) return hostFailedOnly(both.first, c);
      if (!both.first.stderr.includes('cross-ai: setting host=herdr applied')) return 'hosted run lacks host=herdr';
      if (!lines(both.first, 'cross-ai: host herdr tab=t1 label=aikit:execute:pi:').length) return 'no host line';
      return hostLogProblem(c, 1, extra.closeTail || '');
    };
    const hostPair = (name, model, exit, status, extra = {}) => {
      const base = ['--runtime', 'pi', '--model', model, '--session-id', 'placeholder-sid-' + name, ...(extra.args || [])];
      return { name, kind: 'runtime', args: [...base, '--host', 'auto'], env: { HERDR_ENV: '1', PATH: hostedPath, ...(extra.env || {}) }, exit, status, second: { args: [...base, '--host', 'none'], exit, status }, check: (both, c) => hostPairCheck(both, c, extra) };
    };
    const keptRecords = (c) => {
      const root = path.join(c.env.XDG_STATE_HOME, 'ai-kit', 'spec', 'host');
      if (!fs.existsSync(root)) return [];
      const records = [];
      for (const name of fs.readdirSync(root)) {
        const folder = path.join(root, name);
        const files = fs.readdirSync(folder);
        if (files.length !== 1 || files[0] !== 'run.json') return `extra files in ${folder}`;
        records.push(JSON.parse(fs.readFileSync(path.join(folder, 'run.json'), 'utf8')));
      }
      return records.sort((a, b) => (a.tab_id || '').localeCompare(b.tab_id || ''));
    };
    const fakeTabs = (c) => JSON.parse(readOr(path.join(c.home, 'herdr-state.json'), '{"tabs":{}}')).tabs;
    const hostCalls = (c) => readOr(path.join(c.home, 'herdr.log'), '').split('\n').filter((s) => s.startsWith('argv ')).map((s) => JSON.parse(s.slice(5)));
    const hostSafety = (calls) => {
      const verbs = calls.map((a) => a.slice(0, 2).join(' '));
      if (verbs.some((v) => !HERDR_VERBS.includes(v))) return `herdr verbs ${verbs}`;
      if (calls.some((a) => a.includes('t0') || a.includes('p0'))) return 'the foreign tab t0 was touched';
      return null;
    };
    const cases = [
      {
        name: 'ok',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 cli_rc=0 elapsed=\d+s out=\d+ tree=dirty action=stop$/,
        check: (r) => (r.stdout.includes('# Summary') ? null : 'stdout missing # Summary'),
      },
      {
        name: 'empty_stdin',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: '',
        exit: 2,
        status: /^AIKIT-XAI status=empty_stdin .* action=stop$/,
      },
      {
        name: 'no_model',
        kind: 'logic',
        args: ['--prefer', 'pi'],
        exit: 2,
        status: /^AIKIT-XAI status=no_model .* action=stop$/,
      },
      // U-4: a model id must not read as an option or carry shell/space characters.
      ...['--yolo', 'a b', 'x;rm'].map((model, i) => ({
        name: `bad-model-id-${i}`,
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', model],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* action=stop$/,
      })),
      ...['--yolo', 'a b', 'x;rm'].map((model, i) => ({
        name: `bad-model-flag-${i}`,
        kind: 'logic',
        args: ['--runtime', 'pi', '--model', model],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* action=stop$/,
      })),
      {
        name: 'model-flag-cursor-bracket',
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        // One case, three runtimes: the model flag works for opencode, codex and claude review.
        name: 'model-flag-each',
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
        args: ['--runtime', 'pi', '--model', 'fake/ok', '--model-pi', 'fake/other', '--print-argv'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          if (!(r.stderr || '').includes('cross-ai: --model' + ' wins; ignored --model-pi fake/other')) {
            return 'missing model-wins note';
          }
          const line = (r.stdout || '').split('\n').find((l) => l.startsWith('pi\t'));
          const argv = JSON.parse(line.split('\t')[2]);
          if (!argv.includes('fake/ok')) return `argv=${JSON.stringify(argv)}`;
          return argv.includes('fake/other') ? 'alias model reached argv' : null;
        },
      },
      {
        name: 'model-unusual-pi-bare',
        kind: 'logic',
        args: ['--runtime', 'pi', '--model', 'fake-bare', '--print-argv'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const lines = (r.stderr || '').split('\n');
          if (!lines.includes(advisory('pi', PI_MODEL_ID))) return 'missing advisory';
          return lines.some((line) => line.includes('must match')) ? 'unexpected refusal' : null;
        },
      },
      {
        name: 'model-unusual-bracket-pi',
        kind: 'logic',
        args: ['--runtime', 'pi', '--model', 'fake/ok[x=1]', '--print-argv'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => (r.stderr || '').split('\n').includes(advisory('pi', PI_MODEL_ID)) && (r.stdout || '').split('\n').some((l) => l.startsWith('pi\t') && l.includes('fake/ok[x=1]')) ? null : 'missing advisory or argv',
      },
      {
        // 25.1 WR-05: a colon that is not a thinking level is part of pi's model id.
        name: 'model-pi-colon-id',
        kind: 'logic',
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
        kind: 'logic',
        // An id with two slashes and a tag; built from invented parts because no allowed literal has a second slash (HUB-09).
        args: ['--runtime', 'opencode', '--model', ['fake', 'org', 'model:free'].join('/'), '--print-argv'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => ((r.stdout || '').split('\n').some((l) => l.startsWith('opencode\t') && l.includes(['fake', 'org', 'model:free'].join('/'))) ? null : 'two-slash id missing from argv'),
      },
      {
        name: 'model-unusual-opencode-two-variants',
        kind: 'logic',
        args: ['--runtime', 'opencode', '--model', 'fake/ok#a#b', '--print-argv'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => (r.stderr || '').split('\n').includes(advisory('opencode', OPENCODE_MODEL_ID)) && (r.stdout || '').includes('fake/ok#a#b') ? null : 'missing advisory or argv',
      },
      {
        name: 'model-usual-shape-no-advisory', kind: 'logic',
        args: ['--runtime', 'pi', '--model', 'fake/ok', '--print-argv'], exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => (r.stderr || '').split('\n').some((l) => l.startsWith('cross-ai: note: model id shape')) ? 'unexpected advisory' : null,
      },
      {
        name: 'model-unusual-shape-spawns', kind: 'logic',
        args: ['--runtime', 'claude', '--mode', 'review', '--model', 'fake-ok[x=1]'], exit: 0,
        status: /^AIKIT-XAI status=ok cli=claude model=fake-ok\[x=1\] exit=0 .* tree=clean action=stop$/,
        check: (r, ctx) => (r.stderr || '').split('\n').includes(advisory('claude', MODEL_ID)) && ctx.calls.includes('claude fake-ok[x=1]') ? null : 'missing advisory or call',
      },
      {
        name: 'model-cli-flag-floor', kind: 'logic',
        args: ['--runtime', 'claude', '--mode', 'review', '--model-claude', 'fake-ok[x=1]', '--print-argv'], exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => (r.stderr || '').split('\n').includes(advisory('claude', MODEL_ID)) ? null : 'missing advisory',
      },
      {
        name: 'model-advisory-no-key', kind: 'logic',
        args: ['--runtime', 'pi', '--model', keyId, '--print-argv'], exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const lines = (r.stderr || '').split('\n').filter((l) => l.startsWith('cross-ai: note:'));
          return lines.includes(advisory('pi', PI_MODEL_ID)) && !lines.some((l) => l.includes(keyId)) ? null : 'missing or leaking advisory';
        },
      },
      ...['fake-ok\x07', 'fake-ok\u00e9', 'fake-\tok'].map((value, i) => ({
        name: `model-floor-refuses-${i}`, kind: 'logic',
        args: ['--runtime', 'claude', '--mode', 'review', '--model', value], exit: 2,
        status: /^AIKIT-XAI status=usage .* action=stop$/,
        check: (r) => (r.stderr || '').split('\n').includes(`cross-ai: ${'--model'} must match ${MODEL_ID_FLOOR.source}`) ? null : 'missing floor refusal',
      })),
      {
        name: 'pure-model-id-floor', kind: 'logic', pure: () => {
          const accept = ['a', 'fake-ok', 'fake/ok', 'fake/ok:free', 'fake/ok:high', 'fake/ok#fast', 'fake-ok[effort=high]'];
          const refuse = ['', '-x', '--yolo', 'a b', 'a\tb', 'x;rm', 'a$b', "a'b", 'a`b', 'a\x07', 'a\u00e9', 'a[x=1][y=2]', 'a[x y]'];
          for (const id of accept) if (!MODEL_ID_FLOOR.test(id)) return `floor refused ${id}`;
          for (const id of refuse) if (MODEL_ID_FLOOR.test(id)) return `floor accepted ${id}`;
          return MODEL_ID_FLOOR.source === CURSOR_MODEL_ID.source ? null : 'floor differs from the superset charset';
        },
      },
      {
        name: 'model-config-floor-refuses', kind: 'logic', config: { models: { pi: 'a b' } },
        args: ['--runtime', 'pi', '--print-argv'], exit: 2, status: /^AIKIT-XAI status=usage .* action=stop$/,
        check: (r) => (r.stderr || '').split('\n').includes(`cross-ai: the model for pi must match ${MODEL_ID_FLOOR.source}`) && !(r.stderr || '').includes('a b') ? null : 'missing or leaking refusal',
      },
      {
        name: 'model-config-valid', kind: 'logic', config: { models: { pi: 'fake-ok' } },
        args: ['--runtime', 'pi', '--print-argv'], exit: 0, status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => (r.stderr || '').split('\n').includes(advisory('pi', PI_MODEL_ID)) ? null : 'missing advisory',
      },
      {
        name: 'model-config-empty-no-model', kind: 'logic', config: { models: { pi: '' } },
        args: ['--runtime', 'pi'], exit: 2, status: /^AIKIT-XAI status=no_model .* action=stop$/,
      },
      {
        name: 'model-unusual-shape-spawns-copilot', kind: 'logic', env: { COPILOT_GITHUB_TOKEN: 'fake-token' },
        args: ['--runtime', 'copilot', '--model', 'fake-ok[x=1]'], exit: 0, status: /^AIKIT-XAI status=ok cli=copilot .* action=stop$/,
        check: (r, ctx) => (r.stderr || '').split('\n').includes(advisory('copilot', MODEL_ID)) && ctx.calls.includes('copilot ok[x=1]') ? null : 'missing advisory or call',
      },
      ...[['pi', 'fake-unlisted', PI_MODEL_ID], ['codex', 'fake-unlisted[x=1]', MODEL_ID]].map(([rt, id, re]) => ({
        name: `model-unusual-shape-listing-${rt}`, kind: 'logic', args: ['--runtime', rt, '--model', id], exit: 69,
        status: /^AIKIT-XAI status=bad_model .* action=stop$/,
        check: (r) => (r.stderr || '').split('\n').includes(advisory(rt, re)) && !(r.stderr || '').includes('must match') ? null : 'missing advisory or unexpected refusal',
      })),
      {
        name: 'model-other-runtime-not-checked',
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
        pure: () => {
          const accept = [
            [PI_MODEL_ID, 'fake/ok:high'], [PI_MODEL_ID, 'fake/my-coding:high'],
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
        kind: 'logic',
        args: ['--prefer', 'pi,nosuchcli', '--model-pi', 'fake/ok', '--print-argv'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => ((r.stderr || '').includes(
          'cross-ai: --prefer reads only its first entry (pi); ignored: nosuchcli') ? null : 'missing notice'),
      },
      {
        name: 'gate-runtime-no-formula', kind: 'logic',
        args: ['--runtime', 'placeholder-cli-1', '--model', 'fake-ok'], exit: 2,
        status: /^AIKIT-XAI status=usage .* action=stop$/,
        check: (r, ctx) => {
          const lines = (r.stderr || '').split('\n');
          return lines.includes(noFormula('placeholder-cli-1')) && !lines.some((line) => line.includes('known:')) && ctx.calls.length === 0 ? null : 'missing refusal or unexpected call';
        },
      },
      {
        name: 'gate-classify-unknown-cli', kind: 'logic',
        files: { 'cases.json': [{ name: 'g', cli: 'placeholder-cli-1', stderr: 'circuit_open' }] },
        args: ['--classify-only', 'cases.json'], exit: 0, status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => (r.stdout || '').split('\n')[0] === JSON.stringify({ name: 'g', status: 'transient', rule: 'omniroute-circuit-open', pattern: 'unverified', route: 'unknown' }) ? null : 'unexpected classification',
      },
      {
        name: 'gate-classify-bad-cli', kind: 'logic',
        files: { 'cases.json': [{ name: 'b', cli: 'a b', stderr: 'x' }] },
        args: ['--classify-only', 'cases.json'], exit: 2, status: /^AIKIT-XAI status=usage .* action=stop$/,
        check: (r) => (r.stderr || '').split('\n').includes(`cross-ai: --classify-only cli must match ${RUNTIME_ID_RE.source}`) ? null : 'missing refusal',
      },
      ...[
        ['runtime-case-sensitive', ['--runtime', 'Claude', '--model', 'fake-ok'], null, [noFormula('Claude')]],
        ['prefer-no-formula', ['--prefer', 'placeholder-cli-1,pi', '--model', 'fake-ok'], null, ['cross-ai: --prefer reads only its first entry (placeholder-cli-1); ignored: pi', noFormula('placeholder-cli-1')]],
        ['config-runtime-no-formula', ['--model', 'fake-ok'], { runtime: 'placeholder-cli-1' }, [noFormula('placeholder-cli-1')]],
        ['config-prefer-no-formula', ['--model', 'fake-ok'], { prefer: ['placeholder-cli-1', 'pi'] }, ['cross-ai: CONFIG.prefer reads only its first entry (placeholder-cli-1); ignored: pi', noFormula('placeholder-cli-1')]],
        ['runtime-charset', ['--runtime', 'x;y', '--model', 'fake-ok'], null, [`cross-ai: --runtime must match ${RUNTIME_ID_RE.source}`]],
        ['config-runtime-charset', ['--model', 'fake-ok'], { runtime: 'a b' }, [`cross-ai: CONFIG.runtime must match ${RUNTIME_ID_RE.source}`]],
        ['cli-name-charset', ['--runtime', 'pi', '--model', 'fake/ok', '--model-Bad', 'fake-ok'], null, [`cross-ai: --model-Bad: the cli name must match ${CLI_NAME_RE.source}`]],
      ].map(([suffix, args, config, expected]) => ({
        name: `gate-${suffix}`, kind: 'logic', args, ...(config ? { config } : {}), exit: 2,
        status: /^AIKIT-XAI status=usage .* action=stop$/,
        check: (r, ctx) => {
          const lines = (r.stderr || '').split('\n');
          if (!expected.every((line) => lines.includes(line))) return 'missing refusal';
          if (lines.some((line) => line.includes('known:'))) return 'unexpected known list';
          return ctx.calls.length ? 'unexpected call' : null;
        },
      })),
      {
        name: 'gate-any-cli-name-read-only-selected', kind: 'logic',
        args: ['--runtime', 'pi', '--model-pi', 'fake/ok', '--model-placeholder-cli-1', 'fake-ok', '--route-placeholder-cli-1', 'router', '--print-argv'],
        exit: 0, status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const line = (r.stdout || '').split('\n').find((l) => l.startsWith('pi\t'));
          return line && line.includes('fake/ok') && !line.includes('fake-ok') ? null : 'unexpected argv';
        },
      },
      {
        name: 'argv-file-exec-ok', kind: 'logic',
        // A key the caller wrote into the argv file reaches the child raw but no printed line.
        files: { 'argv.json': ['placeholder-cli-1', '--model', '{model}', '--effort={effort}', '--api-key', 'sk-' + 'b'.repeat(24)] },
        env: { FAKE_DECLARED_SEEN: path.join(tmp, 'declared-exec-ok.json') },
        args: ['--runtime', 'placeholder-cli-1', '--role', 'execute', '--argv-file', 'argv.json', '--model', 'fake-ok', '--effort', 'high', '--context', '1m'],
        exit: 0, status: /^AIKIT-XAI status=ok cli=placeholder-cli-1 model=fake-ok exit=0 .* tree=dirty action=stop$/,
        check: (r, ctx) => {
          const seen = JSON.parse(fs.readFileSync(ctx.env.FAKE_DECLARED_SEEN, 'utf8'));
          if (JSON.stringify(seen.argv) !== JSON.stringify(['--model', 'fake-ok', '--effort=high', '--api-key', 'sk-' + 'b'.repeat(24)])) return 'argv';
          if (`${r.stdout || ''}${r.stderr || ''}`.includes('b'.repeat(24)) || !(r.stderr || '').includes('"--api-key","<redacted>"')) return 'key printed';
          if (!seen.stdin.startsWith('prompt\n') || seen.argv.some((el) => el.includes('prompt'))) return 'stdin';
          const lines = (r.stderr || '').split('\n');
          for (const line of ['cross-ai: setting model=fake-ok applied', 'cross-ai: setting effort=high applied', 'cross-ai: setting context=1m ignored reason=no_slot']) if (!lines.includes(line)) return `missing ${line}`;
          if (lines.some((line) => line.startsWith('cross-ai: setting provider=') && line !== 'cross-ai: setting provider=- unknown')) return 'provider';
          return ctx.calls.filter((line) => line.startsWith('declared ')).length === 1 ? null : 'call count';
        },
      },
      {
        name: 'argv-file-print-argv', kind: 'logic',
        files: { 'argv.json': ['placeholder-cli-1', '--model', '{model}', '--effort={effort}', 'https://example.invalid/x?token=' + 'c'.repeat(20)] },
        args: ['--runtime', 'placeholder-cli-1', '--role', 'execute', '--argv-file', 'argv.json', '--model', 'fake-ok', '--effort', 'high', '--print-argv'],
        exit: 0, status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const line = (r.stdout || '').split('\n').find((s) => s.startsWith('placeholder-cli-1\t'));
          if (line !== `placeholder-cli-1\t${path.join(tmp, 'bin', 'placeholder-cli-1')}\t["--model","fake-ok","--effort=high","https://example.invalid/x?token=<redacted>"]`) return 'argv';
          if ((r.stderr || '').includes('c'.repeat(20)) || !(r.stderr || '').includes('cross-ai: rung2 placeholder-cli-1 argv=')) return 'rung2 key';
          return (r.stderr || '').split('\n').includes('cross-ai: rung1 placeholder-cli-1 unavailable') ? null : 'rung1';
        },
      },
      ...[
        { suffix: 'outside', setup: (c) => { fs.writeFileSync(path.join(c.tmp, 'outside-argv.json'), '["placeholder-cli-1"]'); return null; }, args: ['--runtime', 'placeholder-cli-1', '--role', 'execute', '--argv-file', '../outside-argv.json', '--model', 'fake-ok'], text: '--argv-file must name a file inside the working directory: ../outside-argv.json' },
        { suffix: 'symlink', setup: (c) => { const target = path.join(c.tmp, 'symlink-target.json'); fs.writeFileSync(target, '["placeholder-cli-1"]'); fs.symlinkSync(target, path.join(c.repo, 'argv.json')); return null; }, text: '--argv-file must name a file inside the working directory: argv.json' },
        { suffix: 'oversize', files: ['placeholder-cli-1', 'x'.repeat(70000)], text: '--argv-file is over 65536 bytes: argv.json' },
        { suffix: 'invalid-utf8', setup: (c) => { fs.writeFileSync(path.join(c.repo, 'argv.json'), Buffer.from([0x5b, 0x22, 0xff, 0x22, 0x5d])); return null; }, text: '--argv-file is not valid UTF-8: argv.json' },
        { suffix: 'bom', setup: (c) => { fs.writeFileSync(path.join(c.repo, 'argv.json'), '\uFEFF["placeholder-cli-1"]'); return null; }, text: '--argv-file starts with a byte-order mark: argv.json' },
        { suffix: 'bad-json', setup: (c) => { fs.writeFileSync(path.join(c.repo, 'argv.json'), '["placeholder-cli-1",'); return null; }, text: '--argv-file is not strict JSON: argv.json', exact: true },
        { suffix: 'duplicate-key', setup: (c) => { fs.writeFileSync(path.join(c.repo, 'argv.json'), '["placeholder-cli-1",{"a":1,"a":2}]'); return null; }, text: '--argv-file is not strict JSON: argv.json', exact: true },
        { suffix: 'not-array', files: { command: 'placeholder-cli-1' }, text: '--argv-file must hold a JSON array of strings' },
        { suffix: 'empty-array', files: [], text: '--argv-file holds an empty array; the first element is the command' },
        { suffix: 'non-string', files: ['placeholder-cli-1', 3], text: '--argv-file element 1 is not a string' },
        { suffix: 'empty-element', files: ['placeholder-cli-1', ''], text: '--argv-file element 1 is empty' },
        { suffix: 'nul-element', files: ['placeholder-cli-1', 'a\u0000b'], text: '--argv-file element 1 holds a NUL character' },
        { suffix: 'unknown-placeholder', files: ['placeholder-cli-1', '-p', '{prompt}'], text: '--argv-file element 2 holds an unknown placeholder (only {model}, {effort} and {session})' },
        { suffix: 'command-placeholder', files: ['{model}', '-p'], text: '--argv-file element 0 is the command and holds no placeholder' },
        { suffix: 'effort-unset', files: ['placeholder-cli-1', '--effort', '{effort}'], text: '--argv-file holds {effort} and the call names no effort (pass --effort)' },
        { suffix: 'session-unset', files: ['placeholder-cli-1', '--session', '{session}'], text: '--argv-file holds {session} and the call names no session id (pass --session-id)' },
        { suffix: 'known-runtime', files: ['placeholder-cli-1'], args: ['--runtime', 'pi', '--role', 'execute', '--argv-file', 'argv.json', '--model', 'fake/ok'], text: '--argv-file needs a runtime with no execute formula in the runner; pi has one' },
      ].map((row) => ({
        name: `argv-file-refuse-${row.suffix}`, kind: 'logic',
        args: row.args || ['--runtime', 'placeholder-cli-1', '--role', 'execute', '--argv-file', 'argv.json', '--model', 'fake-ok'],
        ...(row.files ? { files: { 'argv.json': row.files } } : {}), ...(row.setup ? { setup: row.setup } : {}),
        exit: 2, status: /^AIKIT-XAI status=usage .* action=stop$/,
        check: (r, ctx) => {
          const lines = (r.stderr || '').split('\n');
          if (!lines.some((line) => row.exact ? line === `cross-ai: ${row.text}` : line.includes(`cross-ai: ${row.text}`))) return 'missing refusal';
          return ctx.calls.some((line) => line.startsWith('declared ')) ? 'unexpected call' : null;
        },
      })),
      {
        name: 'pure-argv-file-allowed', kind: 'logic', pure: () => {
          const row = { exec: null, review: () => [] };
          return argvFileAllowed(undefined, 'exec') && argvFileAllowed(row, 'exec') && !argvFileAllowed(row, 'review') ? null : 'formula eligibility';
        },
      },
      {
        name: 'pure-argv-file-slot-proof', kind: 'logic', pure: () => {
          const declared = { argv: ['placeholder-cli-1', '--effort={effort}', '-x', 'high'], slots: { model: false, effort: true, session: false } };
          const plan = { model: 'fake-ok', adds: { session: [], effort: [], context: [], skills: [], mcp: [] }, sessionId: null, resume: false, report: [{ name: 'model', value: 'fake-ok', state: 'applied', proof: ['fake-ok'] }, { name: 'effort', value: 'high', state: 'ignored', reason: 'no_form' }], provider: null };
          const out = planArgvFile(plan, argvFileRow(declared));
          const effort = out.report.find((entry) => entry.name === 'effort');
          const modelEntry = out.report.find((entry) => entry.name === 'model');
          if (effort.state !== 'applied' || JSON.stringify(effort.proof) !== '["--effort=high"]') return 'effort proof';
          if (modelEntry.state !== 'ignored' || modelEntry.reason !== 'no_slot' || 'proof' in modelEntry) return 'model proof';
          try { confirmReport(out.report, ['--effort=high', '-x', 'high'], ''); } catch { return 'valid proof rejected'; }
          try { confirmReport(out.report, ['--effort=low', '-x', 'high'], ''); } catch { return null; }
          return 'unrelated argument proved slot';
        },
      },
      {
        name: 'argv-file-review-ok', kind: 'logic',
        files: { 'argv.json': ['placeholder-cli-1', '--model', '{model}', '--session', '{session}'] },
        env: { FAKE_DECLARED_SEEN: path.join(tmp, 'declared-review-ok.json') },
        args: ['--runtime', 'placeholder-cli-1', '--role', 'review', '--argv-file', 'argv.json', '--model', 'fake-review', '--effort', 'high', '--session-id', 'placeholder-sid-1'],
        exit: 0, status: /^AIKIT-XAI status=ok cli=placeholder-cli-1 model=fake-review exit=0 .* tree=clean action=stop$/,
        check: (r, ctx) => {
          const seen = JSON.parse(fs.readFileSync(ctx.env.FAKE_DECLARED_SEEN, 'utf8'));
          if (JSON.stringify(seen.argv) !== JSON.stringify(['--model', 'fake-review', '--session', 'placeholder-sid-1'])) return 'argv';
          const lines = (r.stderr || '').split('\n');
          if (!lines.includes('cross-ai: setting effort=high ignored reason=no_slot') || !lines.includes('cross-ai: setting session=placeholder-sid-1 applied')) return 'settings';
          return lines.filter((line) => line.startsWith('AIKIT-XAI ')).at(-1)?.includes(' session=placeholder-sid-1 ') ? null : 'session';
        },
      },
      {
        name: 'argv-file-review-tree-check', kind: 'logic', files: { 'argv.json': ['placeholder-cli-1', '--model', '{model}'] },
        args: ['--runtime', 'placeholder-cli-1', '--role', 'review', '--argv-file', 'argv.json', '--model', 'fake-ok'],
        exit: 1, status: /^AIKIT-XAI status=contract_violation cli=placeholder-cli-1 .* tree=dirty action=stop$/,
      },
      {
        name: 'argv-file-crash-redacted', kind: 'logic', files: { 'argv.json': ['placeholder-cli-1', '--model', '{model}'] },
        args: ['--runtime', 'placeholder-cli-1', '--role', 'execute', '--argv-file', 'argv.json', '--model', 'fake-crash'],
        exit: 1, status: /^AIKIT-XAI status=crash cli=placeholder-cli-1 model=fake-crash exit=1 cli_rc=7 .* tree=clean action=stop$/,
        check: (r, ctx) => {
          const stderr = r.stderr || ''; const line = stderr.split('\n').filter((s) => s.startsWith('AIKIT-XAI ')).at(-1);
          if (!line?.includes(' pattern=unverified') || !stderr.includes('placeholder failure') || stderr.includes('sk-aikit-SENTINEL-' + process.pid)) return 'redaction or pattern';
          return ctx.calls.filter((s) => s.startsWith('declared ')).length === 1 ? null : 'call count';
        },
      },
      {
        name: 'argv-file-same-argv-twice', kind: 'logic', files: { 'argv.json': ['placeholder-cli-1', '--model', '{model}'] },
        args: ['--runtime', 'placeholder-cli-1', '--role', 'review', '--argv-file', 'argv.json', '--model', 'fake-review'],
        exit: 0, status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        second: { exit: 0, status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/ },
        check: (both) => {
          const first = both.calls1.filter((s) => s.startsWith('declared ')); const second = both.calls2.filter((s) => s.startsWith('declared '));
          if (first.length !== 1 || second.length !== 1 || first[0] !== second[0]) return 'argv changed';
          return fs.readFileSync(path.join(both.repo, 'argv.json'), 'utf8') === JSON.stringify(['placeholder-cli-1', '--model', '{model}']) ? null : 'file changed';
        },
      },
      {
        name: 'argv-file-read-once', kind: 'logic',
        setup: (c) => {
          fs.writeFileSync(path.join(c.repo, '.gitignore'), 'ign/\n');
          fs.mkdirSync(path.join(c.repo, 'ign'));
          fs.writeFileSync(path.join(c.repo, 'ign', 'argv.json'), JSON.stringify(['placeholder-cli-1', '--model', '{model}', '--session={session}']));
          for (const args of [['add', '.gitignore'], ['commit', '-q', '-m', 'ignore']]) {
            const g = spawnSync('git', args, { cwd: c.repo, env: c.env, encoding: 'utf8' });
            if (g.status !== 0) return `setup git ${args.join(' ')}: ${g.stderr}`;
          }
          return null;
        },
        args: ['--runtime', 'placeholder-cli-1', '--role', 'execute', '--argv-file', 'ign/argv.json', '--model', 'fake-edit-then-ok', '--session-id', 'placeholder-sid-2'],
        exit: 0, status: /^AIKIT-XAI status=ok cli=placeholder-cli-1 model=fake-edit-then-ok exit=0 .* tree=dirty action=stop$/,
        check: (r, ctx) => {
          const calls = ctx.calls.filter((s) => s.startsWith('declared ')); const lines = (r.stderr || '').split('\n');
          if (calls.length !== 2 || calls.some((s) => s !== 'declared ["--model","fake-edit-then-ok","--session=placeholder-sid-2"]')) return 'retry argv';
          if (lines.some((s) => s.includes('no fresh session is started')) || !lines.filter((s) => s.startsWith('AIKIT-XAI ')).at(-1)?.includes(' session=placeholder-sid-2 ')) return 'session';
          return fs.readFileSync(path.join(ctx.repo, 'ign', 'argv.json'), 'utf8') === '["changed-command"]' ? null : 'file not changed';
        },
      },
      {
        name: 'argv-file-session-no-slot', kind: 'logic', files: { 'argv.json': ['placeholder-cli-1', '--model', '{model}'] },
        args: ['--runtime', 'placeholder-cli-1', '--role', 'review', '--argv-file', 'argv.json', '--model', 'fake-review', '--session-id', 'placeholder-sid-3'],
        exit: 0, status: /^AIKIT-XAI status=ok cli=placeholder-cli-1 model=fake-review exit=0 .* tree=clean action=stop$/,
        check: (r) => {
          const lines = (r.stderr || '').split('\n'); const line = lines.filter((s) => s.startsWith('AIKIT-XAI ')).at(-1) || '';
          return lines.includes('cross-ai: setting session=placeholder-sid-3 ignored reason=no_slot') && line.includes(' session=- ') && !line.includes(' session=placeholder-sid-3') ? null : 'session';
        },
      },
      {
        name: 'argv-file-constructor-no-model', kind: 'logic', files: { 'argv.json': ['placeholder-cli-1', '--model', '{model}'] },
        args: ['--runtime', 'constructor', '--role', 'review', '--argv-file', 'argv.json'], exit: 2, status: /^AIKIT-XAI status=no_model .* action=stop$/,
        check: (r) => (r.stderr || '').includes('internal error') ? 'internal error' : null,
      },
      {
        name: 'argv-file-constructor-model', kind: 'logic', files: { 'argv.json': ['placeholder-cli-1', '--model', '{model}'] },
        args: ['--runtime', 'constructor', '--role', 'review', '--argv-file', 'argv.json', '--model', 'fake-review'],
        exit: 0, status: /^AIKIT-XAI status=ok cli=constructor model=fake-review exit=0 .* tree=clean action=stop$/,
      },
      ...[['gate-runtime-constructor', ['--runtime', 'constructor']],
        ['gate-runtime-constructor-model', ['--runtime', 'constructor', '--model-constructor', 'fake-ok']]].map(([name, args]) => ({
        name, kind: 'logic', args, exit: 2, status: /^AIKIT-XAI status=usage .* action=stop$/,
        check: (r, ctx) => {
          const lines = (r.stderr || '').split('\n');
          return lines.includes(noFormula('constructor')) && !lines.some((line) => line.includes('internal error')) && ctx.calls.length === 0 ? null : 'missing refusal or unexpected call';
        },
      })),
      {
        name: 'pure-own-value', kind: 'logic',
        pure: () => parseArgs(['--runtime', 'constructor']).models.constructor === undefined
          && parseArgs(['--route-pi', 'router']).routes.constructor === undefined
          && ownValue({}, 'constructor') === undefined && ownValue({ pi: 'x' }, 'pi') === 'x'
          && ownValue(null, 'pi') === undefined ? null : 'own-value lookup failed',
      },
      {
        // With HOME and XDG_CONFIG_HOME unset there is no user layer (C1-3): neither the account
        // home nor the working folder's .config/ai-kit is read, and os.homedir is never called.
        name: 'pure-retry-user-config-without-home',
        kind: 'logic',
        pure: () => {
          const root = fs.mkdtempSync(path.join(os.tmpdir(), 'xai-home-'));
          const home = path.join(root, 'home');
          const work = path.join(root, 'work');
          for (const [dir, base] of [[home, 3], [work, 7]]) {
            writeCaseFile(path.join(dir, '.config', 'ai-kit', 'config.toml'),
              `[runner.retry]\nbase_s = ${base}\n`);
          }
          const savedHome = os.homedir;
          const savedLog = log;
          const savedCwd = process.cwd();
          const lines = [];
          os.homedir = () => { throw new Error('ambient home lookup'); };
          setLog((line) => { lines.push(line); });
          try {
            process.chdir(work);
            const got = resolveRetry(work, {}).retry.base_s;
            if (got === 3 || got === 7) return `base_s=${got} read from an ambient home`;
            return lines.some((l) => l.includes('the user config layer is skipped'))
              ? null : 'no skipped-layer notice';
          } finally {
            process.chdir(savedCwd);
            os.homedir = savedHome;
            setLog(savedLog);
            fs.rmSync(root, { recursive: true, force: true });
          }
        },
      },
      {
        // A CLI that cannot be executed at spawn time (its interpreter is gone) is not_installed
        // with exit 127, as when it is missing from PATH, never a crash.
        name: 'spawn-enoent-not-installed',
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
            kind: 'logic',
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
              // A scratch path under a TMPDIR that holds a space is a legitimate token; any other
              // whitespace token means an argv element was split or joined.
              if (argv.some((t) => /\s/.test(t.startsWith(os.tmpdir()) ? t.slice(os.tmpdir().length) : t))) return 'whitespace token';
              return null;
            },
          },
          {
            name: `argv-review-${rt}`,
            kind: 'logic',
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
        kind: 'logic',
        args: ['--prefer', 'cursor', '--model-cursor', 'fake-ok-cursor'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=dirty action=stop$/,
        check: (r) => (r.stdout === '## Summary\nok\n' ? null : `stdout=${JSON.stringify(r.stdout)}`),
      },
      {
        name: 'parser-opencode',
        kind: 'logic',
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
        name: 'parser-opencode-plan-reminder',
        kind: 'logic',
        fakeOpencodeMode: 'plan-reminder',
        args: ['--prefer', 'opencode', '--model-opencode', 'fake/ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=dirty action=stop$/,
        check: (r) => (r.stdout === '## Summary\nverdict\n' ? null : `stdout=${JSON.stringify(r.stdout)}`),
      },
      {
        name: 'parser-opencode-background-wait',
        kind: 'logic',
        fakeOpencodeMode: 'background-wait',
        args: ['--prefer', 'opencode', '--model-opencode', 'fake/ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=dirty action=stop$/,
        check: (r) => (r.stdout === '## Summary\nfinal\n' ? null : `stdout=${JSON.stringify(r.stdout)}`),
      },
      {
        name: 'parser-opencode-late-error',
        kind: 'logic',
        fakeOpencodeMode: 'late-error',
        args: ['--prefer', 'opencode', '--model-opencode', 'fake/ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=dirty action=stop$/,
        check: (r) => {
          if (r.stdout !== '## Summary\nverdict\n') return `stdout=${JSON.stringify(r.stdout)}`;
          const n = (r.stderr || '').split('\n').filter((l) => l.startsWith('cross-ai: opencode failed after the answer (')).length;
          return n === 1 ? null : `late-error stderr lines=${n}`;
        },
      },
      {
        name: 'parser-opencode-step-length',
        kind: 'logic',
        fakeOpencodeMode: 'length',
        args: ['--prefer', 'opencode', '--model-opencode', 'fake/ok'],
        exit: 1,
        status: /^AIKIT-XAI status=crash /,
        check: (r) => (r.stdout === '' ? null : `stdout=${JSON.stringify(r.stdout)}`),
      },
      {
        name: 'parser-opencode-no-turn-text',
        kind: 'logic',
        fakeOpencodeMode: 'no-text',
        args: ['--prefer', 'opencode', '--model-opencode', 'fake/ok'],
        exit: 1,
        status: /^AIKIT-XAI status=empty_answer /,
        check: (r) => (r.stdout === '' ? null : `stdout=${JSON.stringify(r.stdout)}`),
      },
      {
        name: 'parser-codex',
        kind: 'logic',
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
        kind: 'logic',
        args: ['--prefer', 'codex', '--model-codex', 'fake-retry-codex'],
        config: { prefer: ['codex'] },
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=codex model=fake-retry-codex exit=0 .* tree=dirty action=stop$/,
      },
      {
        name: 'parser-pi-ansi',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ansi'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=dirty action=stop$/,
        check: (r) => (r.stdout === 'Done.\n\n## Summary\nC# is fine. Use ## inline\n' ? null : `stdout=${JSON.stringify(r.stdout)}`),
      },
      {
        name: 'quote',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/quote'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/quote exit=0 cli_rc=0 elapsed=\d+s out=\d+ tree=dirty action=stop$/,
      },
      {
        name: 'okwarn',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/okwarn'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/okwarn exit=0 cli_rc=0 elapsed=\d+s out=\d+ tree=dirty action=stop$/,
        check: (r) => (r.stdout === '# Summary\nok\n' ? null : `stdout=${JSON.stringify(r.stdout)}`),
      },
      {
        // WR-01: a large answer and stderr through pipes arrive whole, status line last.
        name: 'big-pipe',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/big'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/big exit=0 .* tree=dirty action=stop$/,
        check: (r) => (r.stdout === `# Summary\n${'y'.repeat(300000)}\n` ? null : `stdout ${r.stdout.length} bytes`),
      },
      {
        // WR-02: the stderr reader goes away mid-run; the runner must still finish the run.
        name: 'stderr-closed',
        kind: 'runtime',
        args: ['--prefer', 'pi', '--model-pi', 'fake/slowok'],
        config: { heartbeatS: 1 },
        closeStderr: (c) => fs.existsSync(path.join(c.repo, 'started')),
        exit: 0,
        check: (r) => (r.stdout === '# Summary\nok\n' ? null : `stdout=${JSON.stringify(r.stdout)}`),
      },
      {
        name: 'empty-auth',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/emptyauth'],
        exit: 69,
        status: /^AIKIT-XAI status=auth cli=pi model=fake\/emptyauth exit=69 cli_rc=0 .* tree=clean action=stop$/,
      },
      {
        name: 'billing',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/billing'],
        exit: 69,
        status: /^AIKIT-XAI status=billing cli=pi model=fake\/billing exit=69 cli_rc=1 elapsed=\d+s out=\d+ tree=clean action=stop$/,
      },
      {
        name: 'billing-router',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/billing'],
        config: { routerBacked: { pi: true } },
        exit: 75,
        status: /^AIKIT-XAI status=quota cli=pi model=fake\/billing exit=75 cli_rc=1 elapsed=\d+s out=\d+ tree=clean action=stop$/,
      },
      {
        // routerBacked covers only the CLI's pinned model: a direct model on it stops on billing.
        name: 'billing-unpinned-model-on-router-cli',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/billing'],
        config: { routerBacked: { pi: true }, models: { pi: 'fake/pinned-router' } },
        exit: 69,
        status: /^AIKIT-XAI status=billing cli=pi model=fake\/billing exit=69 .* action=stop$/,
        check: (r) => ((r.stderr || '').includes('action=stop route=unknown ') ? null
          : 'route was not unknown'),
      },
      {
        name: 'billing-403-router',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/spend403'],
        config: { routerBacked: { pi: true } },
        exit: 75,
        status: /^AIKIT-XAI status=quota cli=pi model=fake\/spend403 exit=75 cli_rc=1 .* tree=clean action=stop$/,
      },
      {
        name: 'billing-free-tier',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/freetier'],
        exit: 69,
        status: /^AIKIT-XAI status=billing cli=pi model=fake\/freetier exit=69 cli_rc=1 .* tree=clean action=stop$/,
      },
      {
        name: 'auth',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/auth'],
        exit: 69,
        status: /^AIKIT-XAI status=auth cli=pi model=fake\/auth exit=69 cli_rc=1 elapsed=\d+s out=\d+ tree=clean action=stop$/,
      },
      {
        name: 'perm',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/perm'],
        exit: 69,
        status: /^AIKIT-XAI status=permission_blocked cli=pi model=fake\/perm exit=69 cli_rc=1 elapsed=\d+s out=\d+ tree=clean action=stop$/,
      },
      {
        name: 'quota',
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'runtime',
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
        kind: 'runtime',
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
        kind: 'runtime',
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
        kind: 'logic',
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
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/stderr-then-ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/stderr-then-ok exit=0 .* action=stop$/,
      },
      {
        // An unwritable state dir keeps the quota class: a bare 75, never a crash.
        name: 'quota-state-unwritable',
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'runtime',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
        setup: (c) => {
          writeCaseFile(path.join(c.repo, '.aikit', 'config.toml'), '[runner.retry]\nhard_waits_s = [60]\n');
          return null;
        },
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
        args: ['--prefer', 'pi,cursor', '--model-pi', 'fake/gitfailquota', '--model-cursor', 'fake-ok-cursor'],
        exit: 1,
        status: new RegExp('^AIKIT-XAI status=git_error cli=pi model=fake/gitfailquota ' +
          'exit=1 cli_rc=1 .* tree=unknown action=stop$'),
        check: (_r, ctx) => (ctx.calls.some((l) => l.startsWith('cursor-agent')) ? 'cursor ran' : null),
      },
      {
        name: 'upstream-opencode-event',
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'runtime',
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
        kind: 'logic',
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
        kind: 'runtime',
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
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/crash'],
        exit: 1,
        status: /^AIKIT-XAI status=crash .* action=stop$/,
        check: (r) => (r.stderr || '').includes('upstream=-') && !(r.stderr || '').includes('cross-ai: upstream ')
          ? null : 'empty upstream should have no trailer',
      },
      {
        name: 'crash',
        kind: 'logic',
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
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/nochange'],
        exit: 1,
        status: /^AIKIT-XAI status=no_change cli=pi model=fake\/nochange exit=1 cli_rc=0 elapsed=\d+s out=\d+ tree=clean action=stop$/,
      },
      {
        name: 'empty',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/empty'],
        exit: 1,
        status: /^AIKIT-XAI status=empty_answer cli=pi model=fake\/empty exit=1 cli_rc=0 elapsed=\d+s out=\d+ tree=clean action=stop$/,
      },
      {
        name: 'upstream-cursor-result',
        kind: 'logic',
        args: ['--prefer', 'cursor', '--model-cursor', 'fake-err-cursor'],
        exit: 69,
        status: /^AIKIT-XAI status=auth .* action=stop$/,
        check: (r) => (r.stderr || '').includes('cross-ai: upstream body=') &&
          JSON.parse((r.stderr || '').split('\n').find((line) => line.startsWith('cross-ai: upstream body=')).split('=').slice(1).join('=')).includes('"is_error":true')
          ? null : 'cursor error event was not passed through',
      },
      {
        name: 'cursor-error',
        kind: 'logic',
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
        kind: 'logic',
        args: ['--prefer', 'pi,cursor', '--model-pi', 'fake/dirtycrash', '--model-cursor', 'fake-ok-cursor'],
        exit: 1,
        status: /^AIKIT-XAI status=crash cli=pi model=fake\/dirtycrash exit=1 cli_rc=7 elapsed=\d+s out=\d+ tree=dirty action=stop$/,
        check: (_r, ctx) => (ctx.calls.some((l) => l.startsWith('cursor-agent')) ? 'cursor ran after dirty crash' : null),
      },
      {
        name: 'no-change-no-fallback',
        kind: 'logic',
        args: ['--prefer', 'pi,cursor', '--model-pi', 'fake/nochange', '--model-cursor', 'fake-ok-cursor'],
        exit: 1,
        status: /^AIKIT-XAI status=no_change cli=pi model=fake\/nochange exit=1 cli_rc=0 elapsed=\d+s out=\d+ tree=clean action=stop$/,
        check: (_r, ctx) => (ctx.calls.some((l) => l.startsWith('cursor-agent')) ? 'cursor ran' : null),
      },
      {
        name: 'reedit',
        kind: 'logic',
        setup: (ctx) => { fs.writeFileSync(path.join(ctx.repo, 'dirty.txt'), 'seed\n'); return null; },
        args: ['--prefer', 'pi', '--model-pi', 'fake/reedit'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/reedit exit=0 cli_rc=0 elapsed=\d+s out=\d+ tree=dirty action=stop$/,
      },
      {
        name: 'hang',
        kind: 'runtime',
        args: ['--prefer', 'pi', '--model-pi', 'fake/hang', '--timeout', '2'],
        exit: 124,
        status: /^AIKIT-XAI status=timeout cli=pi model=fake\/hang exit=124 cli_rc=.* elapsed=\d+s out=\d+ tree=.* action=stop$/,
        check: (_r, ctx) => deadCheck(ctx, ['gc']),
      },
      {
        // SPEC R4: a terminal usage-limit line, then the child stays alive. Stopped at the grace.
        name: 'live-limit-kill',
        kind: 'runtime',
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
        kind: 'runtime',
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
        kind: 'logic',
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
        kind: 'runtime',
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
        kind: 'runtime',
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
        kind: 'runtime',
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
        kind: 'runtime',
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
        kind: 'logic',
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
        kind: 'runtime',
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
        kind: 'runtime',
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
        kind: 'logic',
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
        kind: 'runtime',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'runtime',
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
        kind: 'runtime',
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
        kind: 'runtime',
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
        kind: 'runtime',
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
        kind: 'runtime',
        args: ['--prefer', 'pi', '--model-pi', 'fake/limit-flood', '--timeout', '60'],
        exit: 75,
        status: /^AIKIT-XAI status=quota cli=pi model=fake\/limit-flood exit=75 .* action=stop$/,
        check: (_r, ctx) => deadCheck(ctx, ['pi']),
      },
      {
        // turn.failed carrying limit text is terminal; the grace stops the child.
        name: 'live-codex-turn-failed',
        kind: 'runtime',
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
        kind: 'runtime',
        args: ['--prefer', 'codex', '--model-codex', 'fake-error-then-ok-codex', '--timeout', '60'],
        config: { prefer: ['codex'] },
        exit: 0,
        status: new RegExp('^AIKIT-XAI status=ok cli=codex model=fake-error-then-ok-codex ' +
          'exit=0 .* action=stop$'),
      },
      {
        // A bare codex error is never terminal, so the deadline passes and post-hoc labels quota.
        name: 'post-hoc-timeout-codex-error',
        kind: 'runtime',
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
        kind: 'logic',
        args: ['--prefer', 'codex', '--model-codex', 'x'],
        env: { PATH: `${path.join(tmp, 'bin-nocodex')}` },
        exit: 127,
        status: /^AIKIT-XAI status=not_installed .* exit=127 .* action=stop$/,
      },
      {
        name: 'sigterm-hang',
        kind: 'runtime',
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
        kind: 'runtime',
        args: ['--prefer', 'pi', '--model-pi', 'fake/stubborn', '--timeout', '60'],
        signal: { when: (c) => fs.existsSync(path.join(c.repo, 'cli.ready')), sig: 'SIGTERM', withinMs: SELF_TEST_SIGNAL_EXIT_MS },
        exit: 143,
        status: /^AIKIT-XAI status=signal cli=pi model=fake\/stubborn exit=143 .* tree=dirty action=stop$/,
        check: (_r, ctx) => deadCheck(ctx, ['pi']),
      },
      {
        name: 'sigterm-twice',
        kind: 'runtime',
        args: ['--prefer', 'pi', '--model-pi', 'fake/stubborn', '--timeout', '60'],
        signal: { when: (c) => fs.existsSync(path.join(c.repo, 'cli.ready')), sig: 'SIGTERM', again: 'SIGINT', withinMs: SELF_TEST_SIGNAL_EXIT_MS },
        exit: 143,
        status: /^AIKIT-XAI status=signal cli=pi model=fake\/stubborn exit=143 .* action=stop$/,
        check: (_r, ctx) => deadCheck(ctx, ['pi']),
      },
      {
        name: 'sigterm-backoff',
        kind: 'runtime',
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
        kind: 'runtime',
        args: ['--prefer', 'pi', '--model-pi', 'fake/hang', '--timeout', '60'],
        signal: { when: (c) => fs.existsSync(path.join(c.repo, 'gc.pid')), sig: 'SIGKILL' },
        exit: 0,
        status: /^$/,
        expectFailure: true,
        // SIGKILL skips every cleanup, so the runner's cross-ai-* folder stays (in the case
        // TMPDIR, which proves the containment).
        keepsTmp: true,
        afterReap: (c) => {
          const dead = deadCheck(c, ['pi', 'gc']);
          if (dead) return dead;
          if (!fs.readdirSync(c.tmpdir).some((n) => n.startsWith('cross-ai-'))) return 'no cross-ai- folder in the case TMPDIR';
          const left = pidsUnder(c.repo);
          return left.length ? `survivors ${left.join(',')}` : null;
        },
      },
      {
        name: 'gcescape',
        kind: 'runtime',
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
        kind: 'runtime',
        args: ['--prefer', 'pi', '--model-pi', 'fake/gcpipe', '--timeout', '60'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/gcpipe exit=0 .* action=stop$/,
        check: (_r, ctx) => (ctx.elapsedMs >= scaledMs(15000) ? `elapsed ${ctx.elapsedMs}` : deadCheck(ctx, ['gc'])),
      },
      {
        name: 'gcterm',
        kind: 'runtime',
        args: ['--prefer', 'pi', '--model-pi', 'fake/gcterm', '--timeout', '60'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/gcterm exit=0 .* action=stop$/,
        check: (_r, ctx) => (ctx.elapsedMs >= scaledMs(15000) ? `elapsed ${ctx.elapsedMs}` : deadCheck(ctx, ['gc'])),
      },
      {
        name: 'git-before-fail',
        kind: 'logic',
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
        kind: 'logic',
        args: ['--prefer', 'pi,cursor', '--model-pi', 'fake/gitfail', '--model-cursor', 'fake-ok-cursor'],
        exit: 1,
        status: new RegExp('^AIKIT-XAI status=git_error cli=pi model=fake/gitfail exit=1 cli_rc=0' +
          ' elapsed=\\d+s out=\\d+ tree=unknown action=stop$'),
        check: (_r, ctx) => (ctx.calls.some((l) => l.startsWith('cursor-agent')) ? 'cursor ran' : null),
      },
      {
        name: 'git-hang',
        kind: 'runtime',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
        setup: nestedRepoSetup,
        args: ['--prefer', 'pi', '--model-pi', 'fake/subedit'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/subedit exit=0 .* tree=dirty action=stop$/,
      },
      {
        // U-3: an edit only to a gitignored file still reads dirty.
        name: 'ignored-edit',
        kind: 'logic',
        setup: ignoredFileSetup,
        args: ['--prefer', 'pi', '--model-pi', 'fake/ignorededit'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ignorededit exit=0 .* tree=dirty action=stop$/,
      },
      {
        // ...but a write inside a fully ignored dir (a cache) does not.
        name: 'ignored-dir-write',
        kind: 'logic',
        setup: ignoredFileSetup,
        args: ['--mode', 'review', '--prefer', 'pi', '--model-pi', 'fake/cachewrite'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/cachewrite exit=0 .* tree=clean action=stop$/,
      },
      {
        name: 'ignored-review-ok',
        kind: 'logic',
        setup: ignoredFileSetup,
        args: ['--mode', 'review', '--prefer', 'pi', '--model-pi', 'fake/review-ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/review-ok exit=0 .* tree=clean action=stop$/,
      },
      {
        name: 'submodule-review-ok',
        kind: 'logic',
        setup: nestedRepoSetup,
        args: ['--mode', 'review', '--prefer', 'pi', '--model-pi', 'fake/review-ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/review-ok exit=0 .* tree=clean action=stop$/,
      },
      {
        name: 'unborn-head-l10n',
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok:high'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok:high exit=0 .* tree=dirty action=stop$/,
        check: (r) => ((r.stderr || '').includes('suffix :high is not validated') ? null : 'missing suffix note'),
      },
      {
        name: 'model-suffix-opencode',
        kind: 'logic',
        args: ['--prefer', 'opencode', '--model-opencode', 'fake/ok#high'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=opencode model=fake\/ok#high exit=0 .* tree=dirty action=stop$/,
      },
      {
        name: 'model-suffix-bad-base',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/missing:high'],
        exit: 69,
        status: /^AIKIT-XAI status=bad_model cli=pi model=fake\/missing:high exit=69 .* action=stop$/,
      },
      {
        name: 'bad-model-only',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/missing'],
        exit: 69,
        status: /^AIKIT-XAI status=bad_model cli=pi model=fake\/missing exit=69 .* action=stop$/,
      },
      {
        name: 'list-broken',
        kind: 'logic',
        env: { FAKE_PI_LIST: 'broken' },
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* action=stop$/,
        check: (r) => ((r.stderr || '').includes('model list unavailable (unparseable)') ? null : 'missing unparseable note'),
      },
      {
        name: 'list-fail',
        kind: 'logic',
        env: { FAKE_PI_LIST: 'fail' },
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* action=stop$/,
        check: (r) => ((r.stderr || '').includes('model list unavailable (exit 1)') ? null : 'missing exit 1 note'),
      },
      {
        name: 'list-zero',
        kind: 'logic',
        env: { FAKE_CURSOR_LIST: 'empty' },
        args: ['--prefer', 'cursor', '--model-cursor', 'fake-ok-cursor'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=cursor model=fake-ok-cursor exit=0 .* action=stop$/,
        check: (r) => ((r.stderr || '').includes('model list unavailable (no ids)') ? null : 'missing no ids note'),
      },
      {
        name: 'print-argv-no-preflight',
        kind: 'logic',
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
        // WR-53: --print-argv runs no retry migration and changes no file in the project or the user dir.
        name: 'print-argv-no-migration',
        kind: 'logic',
        args: ['--print-argv', '--model-pi', 'fake/ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* action=stop$/,
        setup: (c) => {
          c.gsdBytes = '{"workflow": {"cross_ai_retry": {"max_retries": 2}}}';
          c.userBytes = '{"cross_ai_retry": {"max_retries": 3}}\n';
          writeCaseFile(path.join(c.repo, '.planning', 'config.json'), c.gsdBytes);
          writeCaseFile(path.join(c.home, '.config', 'ai-kit', 'cross-ai.json'), c.userBytes);
          return null;
        },
        check: (r, c) => {
          const dir = path.join(c.home, '.config', 'ai-kit');
          if (fs.readFileSync(path.join(c.repo, '.planning', 'config.json'), 'utf8') !== c.gsdBytes) return 'GSD file changed';
          if (fs.readFileSync(path.join(dir, 'cross-ai.json'), 'utf8') !== c.userBytes) return 'cross-ai.json changed';
          if (fs.readdirSync(dir).join(',') !== 'cross-ai.json') return `user dir holds ${fs.readdirSync(dir).join(',')}`;
          if (fs.existsSync(path.join(c.repo, '.aikit'))) return '.aikit created';
          return (r.stderr || '').includes('migrated') ? 'a migration notice was logged' : null;
        },
      },
      {
        name: 'list-hang',
        kind: 'runtime',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'runtime',
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
        kind: 'runtime',
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
        kind: 'runtime',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'runtime',
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
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/event400'],
        setup: (c) => {
          writeCaseFile(path.join(c.repo, '.aikit', 'config.toml'), '[runner.retry]\nmax_retries = 1\nsession_resets = 0\n');
          return null;
        },
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
        pure: () => {
          if (clampCapS(99999) !== 14400) return `capS=${clampCapS(99999)}`;
          return clampCapS(-5) === 0 ? null : `capS=${clampCapS(-5)}`;
        },
      },
      {
        // The caller's hard tier, pure: one wait per cycle from the list, the list's end and a
        // wait past the cap left both stop, and the boundary sits on the wait itself.
        name: 'pure-hard-wait',
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
        args: ['--mode', 'review', '--prefer', 'pi', '--model-pi', 'fake/review-ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/review-ok exit=0 .* tree=clean action=stop$/,
      },
      {
        name: 'review-commit',
        kind: 'logic',
        args: ['--mode', 'review', '--prefer', 'pi', '--model-pi', 'fake/review-commit'],
        exit: 1,
        status: /^AIKIT-XAI status=contract_violation cli=pi model=fake\/review-commit exit=1 .* action=stop$/,
        check: (_r, ctx) => (fs.existsSync(path.join(ctx.home, '.fake-committed')) ? null : 'fake never committed'),
      },
      {
        name: 'review-edit',
        kind: 'logic',
        args: ['--mode', 'review', '--prefer', 'pi', '--model-pi', 'fake/review-edit'],
        exit: 1,
        status: /^AIKIT-XAI status=contract_violation cli=pi model=fake\/review-edit exit=1 .* action=stop$/,
      },
      {
        name: 'review-edit-no-fallback',
        kind: 'logic',
        args: ['--mode', 'review', '--prefer', 'pi,cursor', '--model-pi', 'fake/review-edit', '--model-cursor', 'fake-ok-cursor'],
        exit: 1,
        status: /^AIKIT-XAI status=contract_violation .* action=stop$/,
        check: (_r, ctx) => (ctx.calls.some((l) => l.startsWith('cursor-agent')) ? 'cursor ran' : null),
      },
      {
        name: 'review-gitfail',
        kind: 'logic',
        args: ['--mode', 'review', '--prefer', 'pi', '--model-pi', 'fake/review-gitfail'],
        exit: 1,
        status: new RegExp('^AIKIT-XAI status=git_error cli=pi model=fake/review-gitfail exit=1 ' +
          '.* tree=unknown action=stop$'),
      },
      {
        name: 'review-git-before-fail',
        kind: 'logic',
        setup: (ctx) => { fs.writeFileSync(path.join(ctx.home, '.fake-git-fail'), '1'); return null; },
        args: ['--mode', 'review', '--prefer', 'pi', '--model-pi', 'fake/review-ok'],
        exit: 1,
        status: /^AIKIT-XAI status=git_error .* tree=unknown action=stop$/,
        check: (_r, ctx) => (ctx.calls.some((l) => l.startsWith('pi ')) ? `calls=${ctx.calls.join(',')}` : null),
      },
      {
        name: 'review-flaky-edit',
        kind: 'logic',
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
        kind: 'logic',
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
        name: 'claude-exec-commit',
        kind: 'logic',
        args: ['--runtime', 'claude', '--role', 'execute', '--model', 'fake-ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=claude model=fake-ok exit=0 .* tree=dirty action=stop$/,
        check: (r, ctx) => {
          if ((r.stderr || '').includes('cross-ai: note: claude execute formula is unverified (no live probe record)') !== (CLAUDE_EXEC_FORMULA_RECORD === null)) return 'incorrect note';
          const line = (r.stderr || '').split('\n').find((l) => l.startsWith('cross-ai: argv='));
          if (!line) return 'missing argv';
          const expected = RUNTIMES.claude.exec('fake-ok', { cwd: ctx.repo, adds: { session: [], effort: [], context: [], skills: [], mcp: [] } });
          if (JSON.stringify(JSON.parse(line.slice('cross-ai: argv='.length)).slice(0, expected.length)) !== JSON.stringify(expected)) return 'wrong argv';
          const git = spawnSync('git', ['log', '--format=%s'], { cwd: ctx.repo, env: ctx.env, encoding: 'utf8' });
          return git.stdout.includes('fake claude execute') ? null : 'missing commit';
        },
      },
      {
        // A later --prefer entry is ignored, never started, and never rejects the first.
        name: 'review-only-later-menu-ok',
        kind: 'logic',
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
        kind: 'logic',
        args: ['--prefer', 'constructor', '--model-constructor', 'x'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
      },
      {
        name: 'claude-review-ok',
        kind: 'logic',
        args: ['--prefer', 'claude', '--mode', 'review', '--model-claude', 'fake-ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=claude model=fake-ok exit=0 .* tree=clean action=stop$/,
      },
      {
        name: 'no-preamble-len',
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
          const m = err.match(/cross-ai: rung2 codex argv=(.+)$/m);
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
        kind: 'logic',
        args: ['--print-argv', '--mode', 'exec', '--prefer', 'codex', '--model-codex', 'x',
          '--codex-effort', 'high', '--codex-service-tier', 'flex'],
        config: { prefer: ['codex'] },
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const m = (r.stderr || '').match(/cross-ai: rung1 codex argv=(.+)$/m);
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
        kind: 'logic',
        args: ['--print-argv', '--mode', 'review', '--prefer', 'pi', '--model-pi', 'fake/ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const line = (r.stdout || '').split('\n').find((l) => l.startsWith('pi\t'));
          const first = JSON.parse(line.split('\t')[2]);
          const err = r.stderr || '';
          const one = err.match(/cross-ai: rung1 pi argv=(.+)$/m);
          const two = err.match(/cross-ai: rung2 pi argv=(.+)$/m);
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
        kind: 'logic',
        args: ['--print-argv', '--mode', 'review', '--prefer', 'cursor', '--model-cursor', 'x'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const stdoutLine = (r.stdout || '').split('\n').find((l) => l.startsWith('cursor\t'));
          if (!stdoutLine) return 'missing cursor stdout';
          const review = JSON.parse(stdoutLine.split('\t')[2]);
          const m = (r.stderr || '').match(/cross-ai: rung1 cursor argv=(.+)$/m);
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          fs.mkdirSync(path.join(c.repo, '.aikit'), { recursive: true });
          fs.writeFileSync(path.join(c.repo, '.aikit', 'config.toml'),
            '[runner.retry]\nmax_retries = 1\nsession_resets = 0\n');
          return null;
        },
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
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          writeCaseFile(path.join(c.home, '.config', 'ai-kit', 'config.toml'),
            '[runner.retry]\nmax_retries = 2\nsession_resets = 0\n');
          return null;
        },
        check: (r) => retryLine(r, 'max_retries=2 session_resets=0'),
      },
      {
        // The project key wins where both set it; the user key fills a key the project lacks.
        name: 'retry-config-per-key',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          writeCaseFile(path.join(c.repo, '.aikit', 'config.toml'), '[runner.retry]\nmax_retries = 1\n');
          writeCaseFile(path.join(c.home, '.config', 'ai-kit', 'config.toml'),
            '[runner.retry]\nmax_retries = 3\nsession_resets = 0\n');
          return null;
        },
        check: (r) => retryLine(r, 'max_retries=1 session_resets=0'),
      },
      {
        name: 'retry-config-workstream',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        env: { GSD_WORKSTREAM: 'ws1' },
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          writeCaseFile(path.join(c.repo, '.aikit', 'config.toml'),
            '[runner.retry]\nmax_retries = 2\n\n[runner.retry.scopes."workstreams/ws1"]\nmax_retries = 1\n');
          return null;
        },
        check: (r) => retryLine(r, 'max_retries=1'),
      },
      {
        // A scoped file without the key falls through to the root config.
        name: 'retry-config-workstream-fallback',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        env: { GSD_WORKSTREAM: 'ws1' },
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          writeCaseFile(path.join(c.repo, '.aikit', 'config.toml'),
            '[runner.retry]\nmax_retries = 2\n\n[runner.retry.scopes."workstreams/ws1"]\n');
          return null;
        },
        check: (r) => retryLine(r, 'max_retries=2'),
      },
      {
        name: 'retry-config-refused',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          writeCaseFile(path.join(c.repo, '.aikit', 'config.toml'),
            '[runner.retry]\nbase_s = 61\nmax_retries = "1"\n');
          writeCaseFile(path.join(c.home, '.config', 'ai-kit', 'config.toml'),
            '[runner.retry]\nmax_retries = 1\nsession_resets = 0\n');
          return null;
        },
        check: (r) => {
          const err = r.stderr || '';
          for (const key of ['base_s', 'max_retries']) {
            const line = `cross-ai: config runner.retry.${key} refused (.aikit/config.toml [runner.retry]):`;
            if (!err.includes(line)) return `missing refusal ${key}`;
          }
          return retryLine(r, 'base_s=0') || retryLine(r, 'max_retries=1');
        },
      },
      {
        // A FIFO user retry file is refused by type before any read and the run goes on.
        name: 'retry-config-fifo',
        kind: 'runtime',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* action=stop$/,
        setup: (c) => {
          const dir = path.join(c.home, '.config', 'ai-kit');
          fs.mkdirSync(dir, { recursive: true });
          const made = spawnSync('mkfifo', [path.join(dir, 'config.toml')]);
          return made.status === 0 ? null : 'mkfifo unavailable';
        },
        check: (r) => ((r.stderr || '').includes('not a regular file') ? null : 'missing notice'),
      },
      {
        name: 'retry-config-malformed',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          writeCaseFile(path.join(c.repo, '.aikit', 'config.toml'), '[runner.retry]\nmax_retries =\n');
          return null;
        },
        check: (r) => {
          const notice = 'cross-ai: config .aikit/config.toml line 2: unsupported value; ' +
            'retry keys from the next source';
          if (!(r.stderr || '').includes(notice)) return 'missing malformed notice';
          return retryLine(r, 'base_s=0 factor=1.5 max_retries=5 session_resets=1 hard_waits_s=0,0,0 cap_s=14400');
        },
      },
      {
        name: 'retry-config-unknown-key',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          writeCaseFile(path.join(c.repo, '.aikit', 'config.toml'), '[runner.retry]\ncap_s = 99999\n');
          return null;
        },
        check: (r) => {
          const notice = 'cross-ai: config runner.retry.cap_s refused (.aikit/config.toml [runner.retry]): unknown key';
          if (!(r.stderr || '').includes(notice)) return 'missing unknown-key notice';
          return retryLine(r, 'cap_s=14400');
        },
      },
      {
        name: 'retry-config-caps-clamp',
        kind: 'logic',
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
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
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
          writeCaseFile(path.join(c.repo, '.aikit', 'config.toml'), '[runner.retry]\nmax_retries = 1\n');
          writeCaseFile(path.join(dir, 'config.toml'), '[runner.retry]\nsession_resets = 0\n');
          const stamp = (p) => {
            const st = fs.statSync(p);
            return { bytes: fs.readFileSync(p), mtime: st.mtimeMs };
          };
          c.retryStamp = {
            project: stamp(path.join(c.repo, '.aikit', 'config.toml')),
            user: stamp(path.join(dir, 'config.toml')),
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
            project: stamp(path.join(both.repo, '.aikit', 'config.toml')),
            user: stamp(path.join(dir, 'config.toml')),
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
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        config: { capS: 300, retry: { hard_waits_s: [600] } },
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        // An empty project file: no earlier source supplies hard_waits_s, so only CONFIG is refused.
        setup: (c) => {
          writeCaseFile(path.join(c.repo, '.aikit', 'config.toml'), '');
          return null;
        },
        check: (r) => {
          const notice = 'cross-ai: config retry.hard_waits_s refused (CONFIG):';
          if (!(r.stderr || '').includes(notice)) return 'missing hard_waits_s refusal';
          return retryLine(r, 'hard_waits_s=600,900,1800 cap_s=300');
        },
      },
      {
        // The retry read refuses a symlink out of .aikit; the timeout read still follows a symlink
        // out of .planning (GSD's workflow.cross_ai_timeout, which stays a GSD key).
        name: 'retry-config-outside',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          const outsideToml = path.join(c.tmp, 'outside-config.toml');
          fs.writeFileSync(outsideToml, '[runner.retry]\nmax_retries = 7\n');
          fs.mkdirSync(path.join(c.repo, '.aikit'), { recursive: true });
          fs.symlinkSync(outsideToml, path.join(c.repo, '.aikit', 'config.toml'));
          const outsideJson = path.join(c.tmp, 'outside-config.json');
          fs.writeFileSync(outsideJson, JSON.stringify({ workflow: { cross_ai_timeout: 600 } }));
          fs.mkdirSync(path.join(c.repo, '.planning'), { recursive: true });
          fs.symlinkSync(outsideJson, path.join(c.repo, '.planning', 'config.json'));
          writeCaseFile(path.join(c.home, '.config', 'ai-kit', 'config.toml'),
            '[runner.retry]\nmax_retries = 2\n');
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
        // The subset reader keeps the runner tables and skips every other table as opaque (D-07).
        name: 'pure-toml-subset-values',
        kind: 'logic',
        pure: () => {
          const got = parseTomlSubset(TOML_SAMPLE_TEXT);
          if (got.error) return got.error;
          return JSON.stringify(got.obj) === JSON.stringify(JSON.parse(TOML_SAMPLE_OBJ))
            ? null : JSON.stringify(got.obj);
        },
      },
      {
        // The same text with CRLF line ends parses to the same object (run rule 5).
        name: 'pure-toml-subset-crlf',
        kind: 'logic',
        pure: () => {
          const lf = parseTomlSubset(TOML_SAMPLE_TEXT);
          const crlf = parseTomlSubset(TOML_SAMPLE_TEXT.replace(/\n/g, '\r\n'));
          if (lf.error || crlf.error) return lf.error || crlf.error;
          return JSON.stringify(crlf.obj) === JSON.stringify(lf.obj)
            ? null : 'CRLF text parsed differently';
        },
      },
      {
        // Each text is refused with its reason (C1-4 collisions in both orders, C1-11 header names).
        name: 'pure-toml-subset-refusals',
        kind: 'logic',
        pure: () => {
          const refusals = [
            ['[runner.retry]\nx = { a = 1 }\n', 'unsupported value'],
            ['[[lanes.review]]\ncommand = """a\n', 'multi-line string'],
            ["[runner.retry]\nx = 'a'\n", 'unsupported value'],
            ['[runner.retry]\nd = 1979-05-27\n', 'unsupported value'],
            ['[runner.retry]\nx = [[1]]\n', 'unsupported value'],
            ['[[runner.retry]]\n', 'array of tables outside [lanes]'],
            ['[runner.retry]\nx = 1\nx = 2\n', 'duplicate key x'],
            ['[runner.retry]\n[runner.retry]\n', 'duplicate table runner.retry'],
            ['[runner.retry]\nmax_retries = 9\n[runner]\nretry = 0\n',
              'key retry conflicts with table runner.retry'],
            ['[runner]\nretry = 0\n[runner.retry]\nmax_retries = 9\n',
              'table runner.retry conflicts with key runner.retry'],
            ['[runner]\nretry = [1]\n[runner.retry]\n',
              'table runner.retry conflicts with key runner.retry'],
            ['[runner]\nretry = "x"\n[runner.retry.scopes."p"]\n', 'conflicts with key runner.retry'],
            ["['lanes']\nstrategy = \"x\"\n", 'line 1: unsupported table name'],
            // CR-51: root-level keys that name the runner subtree are refused, in each spelling.
            ['runner.retry.base_s = 9\n[lanes]\n', 'line 1: runner keys outside a [runner] table'],
            ['# c\nrunner = { retry = { base_s = 9 } }\n', 'line 2: runner keys outside a [runner] table'],
            ['"runner".retry.base_s = 9\n', 'runner keys outside a [runner] table'],
            ["'runner'.retry.base_s = 9\n", 'runner keys outside a [runner] table'],
            // IN-51: names that reach Object.prototype are refused.
            ['[runner.__proto__.retry]\nbase_s = 60\n', 'line 1: reserved table name'],
            ['[runner.constructor]\n', 'reserved table name'],
            ['[runner.retry]\nprototype = 1\n', 'line 2: reserved key prototype'],
            // WR-51 / D-07: a multi-line string outside [lanes] stays refused, and one never closed.
            ['[models]\nx = """a\nb"""\n', 'line 2: multi-line string'],
            ["[lanes]\nx = '''a\nb\n", 'multi-line string not closed'],
          ];
          for (const [text, fragment] of refusals) {
            const got = parseTomlSubset(text);
            if (!got.error || !got.error.includes(fragment)) {
              return `${JSON.stringify(text)} gave ${JSON.stringify(got)}, want ${fragment}`;
            }
          }
          // A root key that is not the runner's, and a runner-like key after a header, stay opaque.
          const other = parseTomlSubset('runners = 1\nmodels.x = 2\n[lanes]\nrunner = 3\n');
          if (other.error) return `unrelated root keys refused: ${other.error}`;
          // A super-table defined after its sub-table is valid TOML.
          const ok = parseTomlSubset('[runner.retry]\nbase_s = 1\n[runner]\nmigrated_from = ["a"]\n');
          if (ok.error) return `super-table after sub-table: ${ok.error}`;
          return ok.obj.runner.retry.base_s === 1 ? null : 'base_s not read';
        },
      },
      {
        // WR-51 / D-07: a '''/""" in a comment or a one-line string does not refuse the file, and a
        // multi-line string inside [lanes] is opaque until it closes (its fake headers hide nothing).
        name: 'pure-toml-subset-opaque-strings',
        kind: 'logic',
        pure: () => {
          const texts = [
            '[runner.retry]\nbase_s = 2 # don\'\'\'t\n',
            '[models]\nnote = "x\'\'\'y" # """\n[runner.retry]\nbase_s = 2\n',
            '[[lanes.review]]\ncommand = """\n[runner.retry]\nbase_s = 99\n"""\n[runner.retry]\nbase_s = 2\n',
            "[lanes]\nx = '''\n[runner.retry]\nbase_s = 99\n''' # done\n[runner.retry]\nbase_s = 2\n",
            '[lanes]\nx = """a\\"""b\n[runner.retry]\nbase_s = 99\n"""\n[runner.retry]\nbase_s = 2\n',
          ];
          for (const text of texts) {
            const got = parseTomlSubset(text);
            if (got.error) return `${JSON.stringify(text)} refused: ${got.error}`;
            if (got.obj.runner.retry.base_s !== 2) return `${JSON.stringify(text)} gave ${JSON.stringify(got.obj)}`;
          }
          return null;
        },
      },
      {
        // The one user-dir rule (D-19, D-27): an absolute XDG_CONFIG_HOME, else an absolute HOME,
        // else none; os.homedir is never called (it throws in this case).
        name: 'pure-config-dir-rule',
        kind: 'logic',
        pure: () => {
          const savedHomedir = os.homedir;
          os.homedir = () => { throw new Error('ambient home lookup'); };
          try {
            const rows = [
              [{ XDG_CONFIG_HOME: '/abs/xdg', HOME: '/srv/u' }, '/abs/xdg/ai-kit'],
              [{ XDG_CONFIG_HOME: '/abs/xdg' }, '/abs/xdg/ai-kit'],
              [{ XDG_CONFIG_HOME: 'rel/xdg', HOME: '/srv/u' }, '/srv/u/.config/ai-kit'],
              [{ XDG_CONFIG_HOME: '', HOME: '/srv/u' }, '/srv/u/.config/ai-kit'],
              [{ XDG_CONFIG_HOME: '   ', HOME: '/srv/u' }, '/srv/u/.config/ai-kit'],
              [{ XDG_CONFIG_HOME: '/srv/u/.config', HOME: '/srv/u' }, '/srv/u/.config/ai-kit'],
              [{ HOME: 'rel-home' }, null],
              [{}, null],
              [{ HOME: '' }, null],
              [{ XDG_CONFIG_HOME: 'rel/xdg', HOME: '' }, null],
            ];
            for (const [env, want] of rows) {
              const got = aiKitConfigDir(env);
              if (got !== want) return `${JSON.stringify(env)} gave ${got}, want ${want}`;
            }
            return null;
          } finally {
            os.homedir = savedHomedir;
          }
        },
      },
      {
        // A config.toml with an invalid UTF-8 byte is skipped with one notice (C1-8); the user file fills.
        name: 'retry-config-invalid-utf8',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          fs.mkdirSync(path.join(c.repo, '.aikit'), { recursive: true });
          fs.writeFileSync(path.join(c.repo, '.aikit', 'config.toml'), Buffer.concat([
            Buffer.from('[runner.retry]\n# '), Buffer.from([0xff]), Buffer.from('\nmax_retries = 1\n'),
          ]));
          writeCaseFile(path.join(c.home, '.config', 'ai-kit', 'config.toml'),
            '[runner.retry]\nmax_retries = 4\n');
          return null;
        },
        check: (r) => {
          const notice = 'cross-ai: config .aikit/config.toml not valid UTF-8; retry keys from the next source';
          if (!(r.stderr || '').includes(notice)) return 'missing UTF-8 notice';
          return retryLine(r, 'max_retries=4');
        },
      },
      {
        // Per key: the project value wins for base_s, the user file supplies factor, CONFIG the
        // max_retries and the default fills session_resets.
        name: 'retry-config-precedence',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        config: { retry: { max_retries: 3 } },
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          writeCaseFile(path.join(c.repo, '.aikit', 'config.toml'), '[runner.retry]\nbase_s = 2\n');
          writeCaseFile(path.join(c.home, '.config', 'ai-kit', 'config.toml'),
            '[runner.retry]\nbase_s = 9\nfactor = 2\n');
          return null;
        },
        check: (r) => retryLine(r, 'base_s=2 factor=2 max_retries=3 session_resets=1'),
      },
      {
        // Only the active scope's table is read: GSD_PROJECT=p selects [runner.retry.scopes."p"].
        name: 'retry-config-scope-active-only',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        env: { GSD_PROJECT: 'p' },
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          writeCaseFile(path.join(c.repo, '.aikit', 'config.toml'),
            '[runner.retry]\nmax_retries = 5\n[runner.retry.scopes."other"]\nmax_retries = 9\n' +
            '[runner.retry.scopes."p"]\nmax_retries = 2\n');
          return null;
        },
        check: (r) => retryLine(r, 'max_retries=2'),
      },
      {
        // A value outside the subset skips that file with a notice and the user file fills the key.
        name: 'retry-config-out-of-subset',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          writeCaseFile(path.join(c.repo, '.aikit', 'config.toml'), '[runner.retry]\nmax_retries = { a = 1 }\n');
          writeCaseFile(path.join(c.home, '.config', 'ai-kit', 'config.toml'), '[runner.retry]\nmax_retries = 4\n');
          return null;
        },
        check: (r) => {
          const notice = 'cross-ai: config .aikit/config.toml line 2: unsupported value; retry keys from the next source';
          if (!(r.stderr || '').includes(notice)) return 'missing out-of-subset notice';
          return retryLine(r, 'max_retries=4');
        },
      },
      {
        // Quote-aware headers (C2-2): brackets, an escaped quote and a tab escape in quoted names.
        name: 'pure-toml-subset-bracket-names',
        kind: 'logic',
        pure: () => {
          const text = '[runner.retry.scopes."p[1]"] # c\nmax_retries = 2\n' +
            '[runner.retry.scopes."a\\"b"]\nmax_retries = 3\n' +
            '[runner.retry.scopes."t\\tx"]\nmax_retries = 4\n' +
            '[[lanes."x]y"]]\nkey = "k"\n';
          const got = parseTomlSubset(text);
          if (got.error) return got.error;
          const want = { runner: { retry: { scopes: {
            'p[1]': { max_retries: 2 }, 'a"b': { max_retries: 3 }, 't\tx': { max_retries: 4 },
          } } } };
          if (JSON.stringify(got.obj) !== JSON.stringify(want)) return JSON.stringify(got.obj);
          const names = JSON.stringify(splitTomlName('runner.retry.scopes."p[1]"'));
          return names === JSON.stringify(['runner', 'retry', 'scopes', 'p[1]'])
            ? null : `splitTomlName gave ${names}`;
        },
      },
      {
        // A scope holding brackets (GSD_PROJECT=p[1]) reads back from its quoted table (C2-2).
        name: 'retry-config-bracket-scope',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        env: { GSD_PROJECT: 'p[1]' },
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          writeCaseFile(path.join(c.repo, '.aikit', 'config.toml'),
            '[runner.retry]\nmax_retries = 5\n\n[runner.retry.scopes."p[1]"]\nmax_retries = 2\n');
          return null;
        },
        check: (r) => {
          if ((r.stderr || '').includes('retry keys from the next source')) return 'unexpected refusal notice';
          return retryLine(r, 'max_retries=2');
        },
      },
      {
        // A root GSD block moves into the project config.toml; the GSD file keeps its other keys.
        name: 'retry-migrate-project',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        planningConfig: {
          workflow: { cross_ai_retry: { max_retries: 1, session_resets: 0 }, cross_ai_timeout: 1800 },
        },
        check: (r, c) => {
          const migrated = 'cross-ai: migrated workflow.cross_ai_retry from .planning/config.json ' +
            'to .aikit/config.toml [runner.retry]';
          if (!(r.stderr || '').includes(migrated)) return 'missing migrated notice';
          const read = parseTomlSubset(fs.readFileSync(path.join(c.repo, '.aikit', 'config.toml'), 'utf8'));
          if (read.error) return `config.toml: ${read.error}`;
          const { runner } = read.obj;
          if (runner.retry.max_retries !== 1 || runner.retry.session_resets !== 0) return 'retry values not moved';
          if (JSON.stringify(runner.migrated_from) !== '[".planning/config.json"]') return 'migrated_from not recorded';
          const gsd = JSON.parse(fs.readFileSync(path.join(c.repo, '.planning', 'config.json'), 'utf8'));
          if (JSON.stringify(gsd) !== JSON.stringify({ workflow: { cross_ai_timeout: 1800 } })) {
            return 'GSD file not reduced to its other keys';
          }
          return retryLine(r, 'max_retries=1 session_resets=0');
        },
      },
      {
        name: 'retry-migrate-workstream',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        env: { GSD_WORKSTREAM: 'ws1' },
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        planningConfig: { workflow: { cross_ai_retry: { max_retries: 2 } } },
        workstream: { ws: 'ws1', config: { workflow: { cross_ai_retry: { max_retries: 1 } } } },
        check: (r, c) => {
          const read = parseTomlSubset(fs.readFileSync(path.join(c.repo, '.aikit', 'config.toml'), 'utf8'));
          if (read.error) return `config.toml: ${read.error}`;
          const { runner } = read.obj;
          if (runner.retry.max_retries !== 2) return 'root max_retries not moved';
          if (runner.retry.scopes?.['workstreams/ws1']?.max_retries !== 1) return 'workstream max_retries not moved';
          const want = '[".planning/workstreams/ws1/config.json",".planning/config.json"]';
          if (JSON.stringify(runner.migrated_from) !== want) return 'migrated_from not recorded in order';
          for (const file of ['.planning/config.json', '.planning/workstreams/ws1/config.json']) {
            const doc = JSON.parse(fs.readFileSync(path.join(c.repo, file), 'utf8'));
            if (doc.workflow && Object.hasOwn(doc.workflow, 'cross_ai_retry')) return `${file} still holds the block`;
          }
          return retryLine(r, 'max_retries=1');
        },
      },
      {
        name: 'retry-migrate-user-json',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          c.userJsonText = '{"cross_ai_retry": {"max_retries": 2, "session_resets": 0}}\n';
          writeCaseFile(path.join(c.home, '.config', 'ai-kit', 'cross-ai.json'), c.userJsonText);
          return null;
        },
        check: (r, c) => {
          const dir = path.join(c.home, '.config', 'ai-kit');
          if (fs.existsSync(path.join(dir, 'cross-ai.json'))) return 'cross-ai.json still in place';
          if (fs.readFileSync(path.join(dir, 'cross-ai.json.migrated'), 'utf8') !== c.userJsonText) {
            return 'cross-ai.json.migrated is not the original bytes';
          }
          const read = parseTomlSubset(fs.readFileSync(path.join(dir, 'config.toml'), 'utf8'));
          if (read.error) return `user config.toml: ${read.error}`;
          if (read.obj.runner.retry.max_retries !== 2 || read.obj.runner.retry.session_resets !== 0) {
            return 'user values not moved';
          }
          if (JSON.stringify(read.obj.runner.migrated_from) !== '["cross-ai.json"]') return 'migrated_from not recorded';
          return retryLine(r, 'max_retries=2 session_resets=0');
        },
      },
      {
        // A block a run finds again in a recorded source is ignored; the GSD file keeps its bytes.
        name: 'retry-migrate-readded',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          writeCaseFile(path.join(c.repo, '.aikit', 'config.toml'),
            '[runner]\nmigrated_from = [".planning/config.json"]\n[runner.retry]\nmax_retries = 3\n');
          writeCaseFile(path.join(c.repo, '.planning', 'config.json'),
            '{"workflow": {"cross_ai_retry": {"max_retries": 9}}}');
          c.gsdBytes = fs.readFileSync(path.join(c.repo, '.planning', 'config.json'));
          return null;
        },
        check: (r, c) => {
          const notice = 'cross-ai: .planning/config.json holds workflow.cross_ai_retry again; ignored ' +
            '(already migrated to .aikit/config.toml)';
          if (!(r.stderr || '').includes(notice)) return 'missing re-added notice';
          if (!fs.readFileSync(path.join(c.repo, '.planning', 'config.json')).equals(c.gsdBytes)) {
            return 'GSD file bytes changed';
          }
          return retryLine(r, 'max_retries=3');
        },
      },
      {
        // A second run finds no block and no user JSON to migrate and writes nothing (SPEC R7).
        name: 'retry-migrate-second-run',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        second: {
          args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
          stdin: 'do the thing\n',
          exit: 0,
          status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        },
        setup: (c) => {
          writeCaseFile(path.join(c.repo, '.aikit', 'config.toml'),
            '[runner]\nmigrated_from = [".planning/config.json"]\n\n[runner.retry]\nmax_retries = 1\n');
          writeCaseFile(path.join(c.repo, '.planning', 'config.json'), '{"workflow": {"cross_ai_timeout": 600}}');
          const stamp = (p) => ({ bytes: fs.readFileSync(p), mtime: fs.statSync(p).mtimeMs });
          c.retryStamp = {
            project: stamp(path.join(c.repo, '.aikit', 'config.toml')),
            gsd: stamp(path.join(c.repo, '.planning', 'config.json')),
          };
          return null;
        },
        check: (both) => {
          const stamp = (p) => ({ bytes: fs.readFileSync(p), mtime: fs.statSync(p).mtimeMs });
          const now = {
            project: stamp(path.join(both.repo, '.aikit', 'config.toml')),
            gsd: stamp(path.join(both.repo, '.planning', 'config.json')),
          };
          for (const which of ['project', 'gsd']) {
            if (!both.retryStamp[which].bytes.equals(now[which].bytes)) return `${which} bytes changed`;
            if (both.retryStamp[which].mtime !== now[which].mtime) return `${which} mtime changed`;
          }
          for (const run of [both.first, both.again]) {
            if ((run.stderr || '').split('\n').some((l) => l.startsWith('cross-ai: migrated'))) {
              return 'a run migrated again';
            }
          }
          return retryLine(both.first, 'max_retries=1') || retryLine(both.again, 'max_retries=1');
        },
      },
      {
        // Only the block's own bytes change: CRLF, the spacing and the other keys stay (T-33-10).
        name: 'retry-migrate-keeps-bytes',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          writeCaseFile(path.join(c.repo, '.planning', 'config.json'),
            '{\r\n  "skills": ["a", "b"],\r\n  "workflow": {\r\n    "cross_ai_retry": {\r\n      "max_retries": 1\r\n    },' +
            '\r\n    "cross_ai_timeout": 600\r\n  }\r\n}\r\n');
          return null;
        },
        check: (r, c) => {
          const want = '{\r\n  "skills": ["a", "b"],\r\n  "workflow": {\r\n    "cross_ai_timeout": 600\r\n  }\r\n}\r\n';
          if (fs.readFileSync(path.join(c.repo, '.planning', 'config.json'), 'utf8') !== want) {
            return 'GSD file bytes not kept';
          }
          return retryLine(r, 'max_retries=1');
        },
      },
      {
        // The comma before a last-position block goes with it, so the file stays valid JSON.
        name: 'retry-migrate-last-key',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          writeCaseFile(path.join(c.repo, '.planning', 'config.json'),
            '{\n  "workflow": {\n    "cross_ai_timeout": 600,\n    "cross_ai_retry": {"max_retries": 1}\n  }\n}\n');
          return null;
        },
        check: (r, c) => {
          const want = '{\n  "workflow": {\n    "cross_ai_timeout": 600\n  }\n}\n';
          if (fs.readFileSync(path.join(c.repo, '.planning', 'config.json'), 'utf8') !== want) {
            return 'GSD file bytes not kept';
          }
          return retryLine(r, 'max_retries=1');
        },
      },
      {
        // The GSD file is a symlink: it stays a link and the file it names loses only the block.
        name: 'retry-migrate-symlink',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          writeCaseFile(path.join(c.repo, '.planning', 'real-config.json'),
            '{"workflow": {"cross_ai_retry": {"max_retries": 1}, "cross_ai_timeout": 600}}');
          fs.symlinkSync('real-config.json', path.join(c.repo, '.planning', 'config.json'));
          return null;
        },
        check: (r, c) => {
          if (!fs.lstatSync(path.join(c.repo, '.planning', 'config.json')).isSymbolicLink()) {
            return 'config.json is no longer a symlink';
          }
          const real = JSON.parse(fs.readFileSync(path.join(c.repo, '.planning', 'real-config.json'), 'utf8'));
          if (Object.hasOwn(real.workflow, 'cross_ai_retry')) return 'the linked file still holds the block';
          return retryLine(r, 'max_retries=1');
        },
      },
      {
        // CR-01: a project .aikit/config.toml that links to the user config.toml is never written
        // through: the user file keeps its bytes and the GSD block stays where it is.
        name: 'retry-migrate-project-link',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        planningConfig: { workflow: { cross_ai_retry: { max_retries: 1 } } },
        setup: (c) => {
          const user = path.join(c.home, '.config', 'ai-kit', 'config.toml');
          writeCaseFile(user, '[runner.retry]\nmax_retries = 4\n');
          c.userBytes = fs.readFileSync(user);
          fs.mkdirSync(path.join(c.repo, '.aikit'), { recursive: true });
          fs.symlinkSync(user, path.join(c.repo, '.aikit', 'config.toml'));
          return null;
        },
        check: (r, c) => {
          const user = path.join(c.home, '.config', 'ai-kit', 'config.toml');
          if (!fs.readFileSync(user).equals(c.userBytes)) return 'the user config.toml was written through the link';
          if (!(r.stderr || '').includes('resolves outside')) return 'missing confinement notice';
          const gsd = JSON.parse(fs.readFileSync(path.join(c.repo, '.planning', 'config.json'), 'utf8'));
          return Object.hasOwn(gsd.workflow, 'cross_ai_retry') ? null : 'the GSD block was migrated anyway';
        },
      },
      {
        // CR-51: a root-level runner key is refused with a notice; the migration appends no second
        // runner table and the GSD block stays.
        name: 'retry-migrate-root-runner-key',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        planningConfig: { workflow: { cross_ai_retry: { max_retries: 1 } } },
        setup: (c) => {
          c.projectText = 'runner.retry.base_s = 9\n';
          writeCaseFile(path.join(c.repo, '.aikit', 'config.toml'), c.projectText);
          return null;
        },
        check: (r, c) => {
          if (fs.readFileSync(path.join(c.repo, '.aikit', 'config.toml'), 'utf8') !== c.projectText) {
            return 'config.toml was changed';
          }
          if (!(r.stderr || '').includes('runner keys outside a [runner] table')) return 'missing refusal notice';
          const gsd = JSON.parse(fs.readFileSync(path.join(c.repo, '.planning', 'config.json'), 'utf8'));
          return Object.hasOwn(gsd.workflow, 'cross_ai_retry') ? null : 'the GSD block was migrated anyway';
        },
      },
      {
        // CR-01: the same link while the user config.toml is absent creates no user file.
        name: 'retry-migrate-project-link-dangling',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        planningConfig: { workflow: { cross_ai_retry: { max_retries: 1 } } },
        setup: (c) => {
          const user = path.join(c.home, '.config', 'ai-kit', 'config.toml');
          fs.mkdirSync(path.join(c.repo, '.aikit'), { recursive: true });
          fs.symlinkSync(user, path.join(c.repo, '.aikit', 'config.toml'));
          return null;
        },
        check: (r, c) => {
          if (fs.existsSync(path.join(c.home, '.config', 'ai-kit', 'config.toml'))) {
            return 'a user config.toml was created through the link';
          }
          return null;
        },
      },
      {
        // SEC-W1: a project .aikit that links to the user config folder migrates nothing into it.
        name: 'retry-migrate-aikit-link',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        planningConfig: { workflow: { cross_ai_retry: { max_retries: 1 } } },
        setup: (c) => {
          const dir = path.join(c.home, '.config', 'ai-kit');
          c.userBytes = Buffer.from('[runner.retry]\nbase_s = 4\n');
          writeCaseFile(path.join(dir, 'config.toml'), c.userBytes.toString('utf8'));
          fs.symlinkSync(dir, path.join(c.repo, '.aikit'));
          return null;
        },
        check: (r, c) => {
          if (!fs.readFileSync(path.join(c.home, '.config', 'ai-kit', 'config.toml')).equals(c.userBytes)) {
            return 'the user config.toml was written through the .aikit link';
          }
          if (!(r.stderr || '').includes('.aikit is a link')) return 'missing link notice';
          const gsd = JSON.parse(fs.readFileSync(path.join(c.repo, '.planning', 'config.json'), 'utf8'));
          return Object.hasOwn(gsd.workflow, 'cross_ai_retry') ? null : 'the GSD block was migrated anyway';
        },
      },
      {
        // WR-52: one unusable key or value is named with its value; the valid keys still migrate.
        name: 'retry-migrate-odd-key',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        planningConfig: { workflow: { cross_ai_retry: { base_s: 5, 'my key': 1, max_retries: null } } },
        setup: (c) => {
          writeCaseFile(path.join(c.home, '.config', 'ai-kit', 'cross-ai.json'),
            '{"cross_ai_retry": {"factor": 3, "a.b": 2, "session_resets": {"x": 1}}}\n');
          return null;
        },
        check: (r, c) => {
          const err = r.stderr || '';
          for (const want of ['retry key "my key" not migrated: not a usable key (value 1)',
            'retry key max_retries not migrated: a value outside the TOML subset (null)',
            'retry key "a.b" not migrated: not a usable key (value 2)',
            'retry key session_resets not migrated: a value outside the TOML subset ({"x":1})']) {
            if (!err.includes(want)) return `missing notice: ${want}`;
          }
          const project = parseTomlSubset(fs.readFileSync(path.join(c.repo, '.aikit', 'config.toml'), 'utf8'));
          if (project.error || project.obj.runner.retry.base_s !== 5) return 'project base_s not migrated';
          const gsd = JSON.parse(fs.readFileSync(path.join(c.repo, '.planning', 'config.json'), 'utf8'));
          if (gsd.workflow && Object.hasOwn(gsd.workflow, 'cross_ai_retry')) return 'block not retired';
          const user = parseTomlSubset(fs.readFileSync(path.join(c.home, '.config', 'ai-kit', 'config.toml'), 'utf8'));
          if (user.error || user.obj.runner.retry.factor !== 3) return 'user factor not migrated';
          return retryLine(r, 'base_s=5 factor=3');
        },
      },
      {
        // A project value wins over the GSD block; the conflict is named and the block still goes.
        name: 'retry-migrate-conflict',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        planningConfig: { workflow: { cross_ai_retry: { max_retries: 1, session_resets: 0 } } },
        setup: (c) => {
          writeCaseFile(path.join(c.repo, '.aikit', 'config.toml'), '[runner.retry]\nmax_retries = 3\n');
          return null;
        },
        check: (r, c) => {
          const notice = 'cross-ai: .planning/config.json retry key max_retries not migrated: ' +
            '.aikit/config.toml already sets it';
          if (!(r.stderr || '').includes(notice)) return 'missing conflict notice';
          const read = parseTomlSubset(fs.readFileSync(path.join(c.repo, '.aikit', 'config.toml'), 'utf8'));
          if (read.error) return `config.toml: ${read.error}`;
          if (read.obj.runner.retry.max_retries !== 3 || read.obj.runner.retry.session_resets !== 0) {
            return 'target keys not kept and added';
          }
          const gsd = JSON.parse(fs.readFileSync(path.join(c.repo, '.planning', 'config.json'), 'utf8'));
          if (gsd.workflow && Object.hasOwn(gsd.workflow, 'cross_ai_retry')) return 'block not removed';
          return retryLine(r, 'max_retries=3 session_resets=0');
        },
      },
      {
        // SPEC R8: a repository without .planning/ runs the runner from ai-kit's files only.
        name: 'no-planning-run',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          writeCaseFile(path.join(c.repo, '.aikit', 'config.toml'), '[runner.retry]\nmax_retries = 1\nsession_resets = 0\n');
          return null;
        },
        check: (r, c) => {
          const named = (r.stderr || '').split('\n').find((l) => l.includes('.planning') || l.includes('GSD'));
          if (named) return `a stderr line names GSD: ${named}`;
          if (fs.existsSync(path.join(c.repo, '.planning'))) return '.planning was created';
          return retryLine(r, 'max_retries=1 session_resets=0');
        },
      },
      {
        name: 'pure-json-span-string-final',
        kind: 'logic',
        pure: () => {
          const got = removeRetryBlock('{"a": ["x", "y"], "workflow": {"cross_ai_retry": {"b": 1}, "c": ["p", "q"]}}');
          if (typeof got.text !== 'string') return `removal failed: ${got.error ?? 'no text'}`;
          if (JSON.stringify(JSON.parse(got.text)) !== '{"a":["x","y"],"workflow":{"c":["p","q"]}}') {
            return `wrong result: ${got.text}`;
          }
          return removeRetryBlock('{"workflow": {"c": 1}}').text === null ? null : 'a text without a block was changed';
        },
      },
      {
        name: 'pure-toml-upsert-lines',
        kind: 'logic',
        pure: () => {
          const crlf = '[runner]\r\nmigrated_from = ["a", "b"]\r\n[runner.retry]\r\nbase_s = 1\r\n';
          const one = upsertTomlKeys(crlf, ['runner'], [['migrated_from', ['a', 'b', 'c']]], ['migrated_from']);
          const read = parseTomlSubset(one.text);
          if (read.error) return `replaced key does not parse: ${read.error}`;
          if (JSON.stringify(read.obj.runner.migrated_from) !== '["a","b","c"]') return 'migrated_from not replaced';
          if (/[^\r]\n/.test(one.text)) return 'a line lost its CRLF ending';
          const two = upsertTomlKeys(crlf, ['runner', 'retry'], [['base_s', 2], ['factor', 1.5]]);
          if (JSON.stringify(two.kept) !== '["base_s"]') return `kept ${JSON.stringify(two.kept)}`;
          if (!two.text.includes('base_s = 1\r\nfactor = 1.5\r\n')) return 'factor not inserted after base_s';
          const three = upsertTomlKeys(crlf, ['runner', 'retry', 'scopes', 'w'], [['max_retries', 4]]);
          if (!three.text.endsWith('\r\n[runner.retry.scopes.w]\r\nmax_retries = 4\r\n')) return 'scope table not appended';
          const quoted = upsertTomlKeys('["runner"."retry"]\nbase_s = 1\n', ['runner', 'retry'], [['factor', 2]]);
          if (quoted.text !== '["runner"."retry"]\nbase_s = 1\nfactor = 2\n') {
            return `quoted header: ${JSON.stringify(quoted.text)}`;
          }
          return null;
        },
      },
      {
        // C1-7: a quoted header is the same table, so no duplicate [runner.retry] is appended.
        name: 'retry-migrate-quoted-header',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        planningConfig: { workflow: { cross_ai_retry: { max_retries: 1 } } },
        setup: (c) => {
          writeCaseFile(path.join(c.repo, '.aikit', 'config.toml'), '["runner"."retry"]\nbase_s = 2\n');
          return null;
        },
        check: (r, c) => {
          const text = fs.readFileSync(path.join(c.repo, '.aikit', 'config.toml'), 'utf8');
          const read = parseTomlSubset(text);
          if (read.error) return `config.toml: ${read.error}`;
          if (read.obj.runner.retry.base_s !== 2 || read.obj.runner.retry.max_retries !== 1) {
            return 'quoted table not merged';
          }
          if (text.split(/\r?\n/).includes('[runner.retry]')) return 'a duplicate [runner.retry] header was appended';
          const gsd = JSON.parse(fs.readFileSync(path.join(c.repo, '.planning', 'config.json'), 'utf8'));
          if (gsd.workflow && Object.hasOwn(gsd.workflow, 'cross_ai_retry')) return 'GSD block not removed';
          return retryLine(r, 'base_s=2 ') || retryLine(r, 'max_retries=1 ');
        },
      },
      {
        // C2-2: a scope holding brackets migrates into a quoted table the reader reads back and applies.
        name: 'retry-migrate-bracket-scope',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        env: { GSD_PROJECT: 'p[1]' },
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          writeCaseFile(path.join(c.repo, '.planning', 'p[1]', 'config.json'),
            '{"workflow": {"cross_ai_retry": {"max_retries": 2}}}');
          return null;
        },
        check: (r, c) => {
          const text = fs.readFileSync(path.join(c.repo, '.aikit', 'config.toml'), 'utf8');
          if (!text.split(/\r?\n/).includes('[runner.retry.scopes."p[1]"]')) return 'scope header missing';
          const read = parseTomlSubset(text);
          if (read.error) return `config.toml: ${read.error}`;
          if (read.obj.runner.retry.scopes['p[1]'].max_retries !== 2) return 'scope value not read back';
          if (JSON.stringify(read.obj.runner.migrated_from) !== '[".planning/p[1]/config.json"]') {
            return 'migrated_from not recorded';
          }
          const gsd = JSON.parse(fs.readFileSync(path.join(c.repo, '.planning', 'p[1]', 'config.json'), 'utf8'));
          if (gsd.workflow && Object.hasOwn(gsd.workflow, 'cross_ai_retry')) return 'block not removed';
          const notice = 'cross-ai: migrated workflow.cross_ai_retry from .planning/p[1]/config.json to ' +
            '.aikit/config.toml [runner.retry.scopes."p[1]"]';
          if (!(r.stderr || '').includes(notice)) return 'missing migrated notice';
          if ((r.stderr || '').includes('not migrated')) return 'a not-migrated notice';
          return retryLine(r, 'max_retries=2');
        },
      },
      {
        // C1-8: invalid UTF-8 in the GSD file is never migrated; the bytes stay exactly as they were.
        name: 'retry-migrate-invalid-utf8',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => {
          c.gsdBytes = Buffer.concat([
            Buffer.from('{"note": "'), Buffer.from([0xff]),
            Buffer.from('", "workflow": {"cross_ai_retry": {"max_retries": 1}}}\n'),
          ]);
          writeCaseFile(path.join(c.repo, '.planning', 'config.json'), c.gsdBytes);
          return null;
        },
        check: (r, c) => {
          if (Buffer.compare(fs.readFileSync(path.join(c.repo, '.planning', 'config.json')), c.gsdBytes) !== 0) {
            return 'GSD file bytes changed';
          }
          if (fs.existsSync(path.join(c.repo, '.aikit', 'config.toml'))) return 'config.toml was written';
          const notice = 'cross-ai: .planning/config.json workflow.cross_ai_retry not migrated: not valid UTF-8';
          if (!(r.stderr || '').includes(notice)) return 'missing not-valid-UTF-8 notice';
          if ((r.stderr || '').split('\n').some((l) => l.startsWith('cross-ai: migrated'))) return 'a migration ran';
          return null;
        },
      },
      {
        // C1-8: an invalid byte in the project config.toml is never re-published; the GSD block stays.
        name: 'retry-migrate-invalid-utf8-target',
        kind: 'logic',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        stdin: 'do the thing\n',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        planningConfig: { workflow: { cross_ai_retry: { max_retries: 1 } } },
        setup: (c) => {
          c.tomlBytes = Buffer.concat([Buffer.from('# '), Buffer.from([0xff]), Buffer.from('\n[runner.retry]\nbase_s = 2\n')]);
          writeCaseFile(path.join(c.repo, '.aikit', 'config.toml'), c.tomlBytes);
          return null;
        },
        check: (r, c) => {
          if (Buffer.compare(fs.readFileSync(path.join(c.repo, '.aikit', 'config.toml')), c.tomlBytes) !== 0) {
            return 'config.toml bytes changed';
          }
          const gsd = JSON.parse(fs.readFileSync(path.join(c.repo, '.planning', 'config.json'), 'utf8'));
          if (!gsd.workflow || !Object.hasOwn(gsd.workflow, 'cross_ai_retry')) return 'GSD block was removed';
          const notice = 'workflow.cross_ai_retry not migrated: .aikit/config.toml not valid UTF-8';
          if (!(r.stderr || '').includes(notice)) return 'missing not-valid-UTF-8 notice';
          return null;
        },
      },
      {
        // A stop after the merge and before the GSD file is written leaves that file byte-equal, with no
        // temp file; the next run finishes the migration (SPEC R9, T-33-10).
        name: 'retry-migrate-interrupted',
        kind: 'logic',
        pure: () => {
          const { root, work, home } = migrationScratch();
          try {
            const gsd = path.join(work, '.planning', 'config.json');
            const target = path.join(work, '.aikit', 'config.toml');
            const body = '{"workflow": {"cross_ai_retry": {"max_retries": 1}}}';
            writeCaseFile(gsd, body);
            const savedRename = fs.renameSync;
            fs.renameSync = (from, to) => {
              if (String(to).endsWith('config.json')) throw new Error('interrupted');
              return savedRename(from, to);
            };
            try {
              collectLog(() => migrateRetrySources(work, { HOME: home }));
            } finally {
              fs.renameSync = savedRename;
            }
            if (fs.readFileSync(gsd, 'utf8') !== body) return 'GSD file changed by an interrupted run';
            if (fs.readdirSync(path.join(work, '.planning')).some((f) => f.endsWith('.tmp'))) {
              return 'a temp file was left behind';
            }
            const first = parseTomlSubset(fs.readFileSync(target, 'utf8'));
            if (first.error) return `config.toml after the interruption: ${first.error}`;
            if (first.obj.runner.retry.max_retries !== 1 || first.obj.runner.migrated_from !== undefined) {
              return 'an interrupted run recorded the wrong state';
            }
            collectLog(() => migrateRetrySources(work, { HOME: home }));
            if (Object.hasOwn(JSON.parse(fs.readFileSync(gsd, 'utf8')).workflow, 'cross_ai_retry')) {
              return 'the next run did not remove the block';
            }
            const two = parseTomlSubset(fs.readFileSync(target, 'utf8'));
            if (two.error) return `config.toml after the next run: ${two.error}`;
            if (JSON.stringify(two.obj.runner.migrated_from) !== '[".planning/config.json"]') {
              return 'the next run did not record the source';
            }
            return fs.readFileSync(target, 'utf8').split('max_retries = 1').length - 1 === 1
              ? null : 'max_retries was written more than once';
          } finally {
            fs.rmSync(root, { recursive: true, force: true });
          }
        },
      },
      {
        // A run that lost the race re-reads and finds nothing to do: no byte and no mtime changes (D-25).
        name: 'retry-migrate-race',
        kind: 'logic',
        pure: () => {
          const { root, work, home } = migrationScratch();
          try {
            const gsd = path.join(work, '.planning', 'config.json');
            const target = path.join(work, '.aikit', 'config.toml');
            writeCaseFile(gsd, '{"workflow": {"cross_ai_retry": {"max_retries": 1}}}');
            collectLog(() => migrateRetrySources(work, { HOME: home }));
            const stamp = (p) => ({ bytes: fs.readFileSync(p), mtime: fs.statSync(p).mtimeMs });
            const before = [stamp(gsd), stamp(target)];
            collectLog(() => migrateRetrySources(work, { HOME: home }));
            const after = [stamp(gsd), stamp(target)];
            for (let i = 0; i < before.length; i += 1) {
              if (!before[i].bytes.equals(after[i].bytes)) return `file ${i} bytes changed on the second run`;
              if (before[i].mtime !== after[i].mtime) return `file ${i} mtime changed on the second run`;
            }
            return null;
          } finally {
            fs.rmSync(root, { recursive: true, force: true });
          }
        },
      },
      {
        // C1-5: another run publishes its own values right after ours. Our post-publish re-read sees
        // them, so the GSD block stays; the next run (both scopes) keeps both and both markers.
        name: 'retry-migrate-overwritten',
        kind: 'logic',
        pure: () => {
          const { root, work, home } = migrationScratch();
          try {
            const rootGsd = path.join(work, '.planning', 'config.json');
            const wsGsd = path.join(work, '.planning', 'workstreams', 'ws1', 'config.json');
            const target = path.join(work, '.aikit', 'config.toml');
            writeCaseFile(rootGsd, '{"workflow": {"cross_ai_retry": {"max_retries": 1}}}');
            writeCaseFile(wsGsd, '{"workflow": {"cross_ai_retry": {"max_retries": 2}}}');
            const overwrite = '[runner.retry.scopes."workstreams/ws1"]\nmax_retries = 2\n';
            const rootBody = fs.readFileSync(rootGsd, 'utf8');
            const restore = patchRenameOnce(
              (to) => to.endsWith('config.toml'),
              () => fs.writeFileSync(target, overwrite),
            );
            let first;
            try {
              first = collectLog(() => migrateRetrySources(work, { HOME: home }));
            } finally {
              restore();
            }
            if (fs.readFileSync(rootGsd, 'utf8') !== rootBody) return 'the root block was retired after an overwrite';
            if (fs.readFileSync(target, 'utf8') !== overwrite) return 'config.toml is not the overwrite text';
            if (!first.lines.some((l) => l.includes('changed after the merge'))) return 'missing changed-after-merge notice';
            const one = parseTomlSubset(fs.readFileSync(target, 'utf8'));
            if (one.error) return `config.toml after run 1: ${one.error}`;
            if (one.obj.runner.migrated_from !== undefined) return 'a marker was recorded after an overwrite';
            collectLog(() => migrateRetrySources(work, { HOME: home, GSD_WORKSTREAM: 'ws1' }));
            const read = parseTomlSubset(fs.readFileSync(target, 'utf8'));
            if (read.error) return `config.toml after run 2: ${read.error}`;
            const { retry, migrated_from: marks } = read.obj.runner;
            if (retry.max_retries !== 1) return 'root max_retries lost';
            if (retry.scopes?.['workstreams/ws1']?.max_retries !== 2) return 'workstream max_retries lost';
            const want = '[".planning/workstreams/ws1/config.json",".planning/config.json"]';
            if (JSON.stringify(marks) !== want) return `migrated_from ${JSON.stringify(marks)}`;
            for (const file of [rootGsd, wsGsd]) {
              if (Object.hasOwn(JSON.parse(fs.readFileSync(file, 'utf8')).workflow, 'cross_ai_retry')) {
                return `${file} still holds the block`;
              }
            }
            return null;
          } finally {
            fs.rmSync(root, { recursive: true, force: true });
          }
        },
      },
      {
        // C1-6: a GSD file that changed after its snapshot keeps its block; the next run merges it, the
        // target's own value wins and the key is named (D-14).
        name: 'retry-migrate-snapshot-changed',
        kind: 'logic',
        pure: () => {
          const { root, work, home } = migrationScratch();
          try {
            const gsd = path.join(work, '.planning', 'config.json');
            const target = path.join(work, '.aikit', 'config.toml');
            writeCaseFile(gsd, '{"workflow": {"cross_ai_retry": {"max_retries": 1}}}');
            const rewritten = '{"workflow": {"cross_ai_retry": {"max_retries": 3}}}';
            const restore = patchRenameOnce((to) => to.endsWith('config.toml'), () => fs.writeFileSync(gsd, rewritten));
            let first;
            try {
              first = collectLog(() => migrateRetrySources(work, { HOME: home }));
            } finally {
              restore();
            }
            if (fs.readFileSync(gsd, 'utf8') !== rewritten) return 'the changed source was retired';
            if (!first.lines.some((l) => l.includes('the file changed during the migration'))) {
              return 'missing changed-during-migration notice';
            }
            const one = parseTomlSubset(fs.readFileSync(target, 'utf8'));
            if (one.error) return `config.toml after run 1: ${one.error}`;
            if (one.obj.runner.retry.max_retries !== 1 || one.obj.runner.migrated_from !== undefined) {
              return 'run 1 recorded the wrong state';
            }
            const second = collectLog(() => migrateRetrySources(work, { HOME: home }));
            const conflict = '.planning/config.json retry key max_retries not migrated: .aikit/config.toml already sets it';
            if (!second.lines.some((l) => l.includes(conflict))) return 'missing conflict notice on run 2';
            const two = parseTomlSubset(fs.readFileSync(target, 'utf8'));
            if (two.error) return `config.toml after run 2: ${two.error}`;
            if (two.obj.runner.retry.max_retries !== 1) return 'the target value did not win';
            if (JSON.stringify(two.obj.runner.migrated_from) !== '[".planning/config.json"]') {
              return 'migrated_from not recorded on run 2';
            }
            return Object.hasOwn(JSON.parse(fs.readFileSync(gsd, 'utf8')).workflow, 'cross_ai_retry')
              ? 'the block was kept after run 2' : null;
          } finally {
            fs.rmSync(root, { recursive: true, force: true });
          }
        },
      },
      {
        // C1-6 for the user JSON: a cross-ai.json changed after its snapshot stays in place and is renamed
        // only by the run that finds it unchanged.
        name: 'retry-migrate-user-json-changed',
        kind: 'logic',
        pure: () => {
          const { root, work, home } = migrationScratch();
          try {
            const dir = path.join(home, '.config', 'ai-kit');
            const src = path.join(dir, 'cross-ai.json');
            const toml = path.join(dir, 'config.toml');
            writeCaseFile(src, '{"cross_ai_retry": {"max_retries": 2}}');
            const rewritten = '{"cross_ai_retry": {"max_retries": 4}}';
            const restore = patchRenameOnce((to) => to.endsWith('config.toml'), () => fs.writeFileSync(src, rewritten));
            let first;
            try {
              first = collectLog(() => migrateRetrySources(work, { HOME: home }));
            } finally {
              restore();
            }
            if (fs.readFileSync(src, 'utf8') !== rewritten) return 'cross-ai.json is not the rewritten text';
            if (fs.existsSync(`${src}.migrated`)) return 'cross-ai.json was renamed by run 1';
            if (!first.lines.some((l) => l.includes('the file changed during the migration'))) {
              return 'missing changed-during-migration notice';
            }
            const one = parseTomlSubset(fs.readFileSync(toml, 'utf8'));
            if (one.error) return `user config.toml after run 1: ${one.error}`;
            if (one.obj.runner.retry.max_retries !== 2 || one.obj.runner.migrated_from !== undefined) {
              return 'run 1 recorded the wrong state';
            }
            const second = collectLog(() => migrateRetrySources(work, { HOME: home }));
            if (fs.existsSync(src)) return 'cross-ai.json was not retired by run 2';
            if (fs.readFileSync(`${src}.migrated`, 'utf8') !== rewritten) return 'the renamed copy is not the rewritten text';
            if (!second.lines.some((l) => l.includes('max_retries'))) return 'no max_retries notice on run 2';
            const two = parseTomlSubset(fs.readFileSync(toml, 'utf8'));
            if (two.error) return `user config.toml after run 2: ${two.error}`;
            return JSON.stringify(two.obj.runner.migrated_from) === '["cross-ai.json"]'
              ? null : 'migrated_from not recorded on run 2';
          } finally {
            fs.rmSync(root, { recursive: true, force: true });
          }
        },
      },
      {
        name: 'deadline-default',
        kind: 'logic',
        args: ['--print-argv', '--model-pi', 'fake/ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => ((r.stderr || '').includes('cross-ai: deadline 270s (outer 300s)') ? null : 'deadline line'),
      },
      {
        name: 'deadline-1800',
        kind: 'logic',
        args: ['--print-argv', '--model-pi', 'fake/ok'],
        planningConfig: { workflow: { cross_ai_timeout: 1800 } },
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => ((r.stderr || '').includes('cross-ai: deadline 1770s (outer 1800s)') ? null : 'deadline line'),
      },
      {
        name: 'deadline-config-cap',
        kind: 'logic',
        args: ['--print-argv', '--model-pi', 'fake/ok'],
        planningConfig: { workflow: { cross_ai_timeout: 3600 } },
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => ((r.stderr || '').includes('cross-ai: deadline 1770s (outer 1800s)') ? null : 'deadline line'),
      },
      {
        name: 'deadline-20',
        kind: 'logic',
        args: ['--print-argv', '--model-pi', 'fake/ok'],
        planningConfig: { workflow: { cross_ai_timeout: 20 } },
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => ((r.stderr || '').includes('cross-ai: deadline 16s (outer 20s)') ? null : 'deadline line'),
      },
      {
        name: 'deadline-workstream',
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
        args: ['--print-argv', '--model-pi', 'fake/ok'],
        planningConfig: { workflow: { cross_ai_timeout: 1 } },
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
      },
      {
        name: 'deadline-timeout-cap',
        kind: 'logic',
        args: ['--print-argv', '--timeout', '5', '--model-pi', 'fake/ok'],
        planningConfig: { workflow: { cross_ai_timeout: 1800 } },
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => ((r.stderr || '').includes('cross-ai: deadline 5s (outer 1800s)') ? null : 'deadline line'),
      },
      {
        name: 'deadline-timeout-above-inner',
        kind: 'logic',
        args: ['--print-argv', '--timeout', '5000', '--model-pi', 'fake/ok'],
        planningConfig: { workflow: { cross_ai_timeout: 1800 } },
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => ((r.stderr || '').includes('cross-ai: deadline 1770s (outer 1800s)') ? null : 'deadline line'),
      },
      {
        // D-18: an explicit outer deadline replaces both the GSD lookup and the CONFIG cap.
        name: 'outer-timeout-flag',
        kind: 'logic',
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
        kind: 'logic',
        args: ['--print-argv', '--outer-timeout', '0', '--model-pi', 'fake/ok'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
      },
      {
        name: 'codex-knobs',
        kind: 'logic',
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
        kind: 'logic',
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
        // A level is shape-checked (LEVEL_RE): an uppercase level is refused.
        name: 'codex-effort-bogus',
        kind: 'logic',
        args: ['--codex-effort', 'Bogus', '--prefer', 'codex', '--model-codex', 'x'],
        config: { prefer: ['codex'] },
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
      },
      {
        name: 'reader-call-file-cap', kind: 'logic', pure: () => {
          const { root, work } = migrationScratch();
          const msg = (fn) => { try { fn(); return null; } catch (e) { return e.message; } };
          try {
            const file = path.join(work, 'f.json'); fs.writeFileSync(file, 'a'.repeat(65536));
            const r = readCallFile('--argv-file', 'f.json', { cwd: work, cwdOnly: true });
            if (r.abs !== fs.realpathSync(file) || r.bytes.length !== 65536 || r.text.length !== 65536) return 'cap boundary';
            fs.writeFileSync(file, 'a'.repeat(65537));
            return msg(() => readCallFile('--argv-file', 'f.json', { cwd: work, cwdOnly: true })) === '--argv-file is over 65536 bytes: f.json' ? null : 'cap overflow';
          } finally { fs.rmSync(root, { recursive: true, force: true }); }
        },
      },
      {
        name: 'reader-call-file-utf8', kind: 'logic', pure: () => {
          const { root, work } = migrationScratch();
          const msg = (fn) => { try { fn(); return null; } catch (e) { return e.message; } };
          try {
            fs.writeFileSync(path.join(work, 'bad.json'), Buffer.from([0x5b, 0xff, 0x5d]));
            fs.writeFileSync(path.join(work, 'bom.json'), Buffer.from([0xef, 0xbb, 0xbf, 0x5b, 0x5d]));
            const bytes = Buffer.from('["é"]'); fs.writeFileSync(path.join(work, 'ok.json'), bytes);
            if (msg(() => readCallFile('--argv-file', 'bad.json', { cwd: work })) !== '--argv-file is not valid UTF-8: bad.json') return 'invalid UTF-8';
            if (msg(() => readCallFile('--argv-file', 'bom.json', { cwd: work })) !== '--argv-file starts with a byte-order mark: bom.json') return 'BOM';
            const r = readCallFile('--argv-file', 'ok.json', { cwd: work });
            return r.bytes.equals(bytes) && r.text === '["é"]' ? null : 'UTF-8 roundtrip';
          } finally { fs.rmSync(root, { recursive: true, force: true }); }
        },
      },
      {
        name: 'reader-call-file-place', kind: 'logic', pure: () => {
          const { root, work } = migrationScratch();
          const msg = (fn) => { try { fn(); return null; } catch (e) { return e.message; } };
          try {
            fs.writeFileSync(path.join(root, 'outside.json'), '[]'); fs.symlinkSync(path.join(root, 'outside.json'), path.join(work, 'link.json'));
            fs.mkdirSync(path.join(work, 'dir'));
            for (const p of ['../outside.json', 'link.json']) if (msg(() => readCallFile('--argv-file', p, { cwd: work, cwdOnly: true })) !== `--argv-file must name a file inside the working directory: ${p}`) return `outside ${p}`;
            if (msg(() => readCallFile('--argv-file', 'dir', { cwd: work })) !== '--argv-file must name a regular file: dir') return 'directory';
            if (msg(() => readCallFile('--argv-file', 'nope.json', { cwd: work })) !== '--argv-file unreadable: nope.json') return 'missing';
            if (readCallFile('--argv-file', '../outside.json', { cwd: work }).text !== '[]') return 'outside allowed';
            const file = path.join(work, 'm.json'); fs.writeFileSync(file, '{}');
            for (const mode of [0o640, 0o620, 0o604, 0o602]) {
              fs.chmodSync(file, mode);
              if (msg(() => readCallFile('--mcp-config', 'm.json', { cwd: work, mode: 0o077 })) !== `--mcp-config must not be accessible by group or others (mode ${mode.toString(8)}): m.json`) return `mode ${mode.toString(8)}`;
            }
            fs.chmodSync(file, 0o600);
            return readCallFile('--mcp-config', 'm.json', { cwd: work, mode: 0o077 }).text === '{}' ? null : 'private mode';
          } finally { fs.rmSync(root, { recursive: true, force: true }); }
        },
      },
      {
        name: 'reader-call-file-fifo', kind: 'runtime', pure: () => {
          const { root, work } = migrationScratch();
          const msg = (fn) => { try { fn(); return null; } catch (e) { return e.message; } };
          try {
            if (spawnSync('mkfifo', [path.join(work, 'pipe.json')]).status !== 0) return 'mkfifo unavailable';
            const t0 = Date.now(); const result = msg(() => readCallFile('--argv-file', 'pipe.json', { cwd: work, cwdOnly: true })); const took = Date.now() - t0;
            return result === '--argv-file must name a regular file: pipe.json' && took < scaledMs(2000) ? null : 'FIFO refusal';
          } finally { fs.rmSync(root, { recursive: true, force: true }); }
        },
      },
      {
        name: 'reader-call-file-swap', kind: 'logic', pure: () => {
          const { root, work } = migrationScratch(); const saved = fs.openSync;
          const msg = (fn) => { try { fn(); return null; } catch (e) { return e.message; } };
          try {
            fs.writeFileSync(path.join(work, 'f.json'), 'first'); fs.writeFileSync(path.join(work, 'other.json'), 'second');
            fs.openSync = (...args) => { fs.renameSync(path.join(work, 'other.json'), path.join(work, 'f.json')); return saved(...args); };
            const result = msg(() => readCallFile('--argv-file', 'f.json', { cwd: work, cwdOnly: true })); fs.openSync = saved;
            if (result !== '--argv-file changed while it was opened: f.json') return 'swap';
            return readCallFile('--argv-file', 'f.json', { cwd: work }).text === 'second' ? null : 'stable read';
          } finally { fs.openSync = saved; fs.rmSync(root, { recursive: true, force: true }); }
        },
      },
      {
        name: 'reader-strict-json', kind: 'logic', pure: () => {
          const { root } = migrationScratch();
          const msg = (fn) => { try { fn(); return null; } catch (e) { return e.message; } };
          try {
            for (const [text, key] of [['{"a":1,"a":2}', 'a'], ['{"x":{"b":1,"b":2}}', 'b'], ['{"a":1,"\\u0061":2}', 'a']]) if (msg(() => strictJson(text)) !== `duplicate key "${key}"`) return `duplicate ${key}`;
            for (const text of ['[{"a":1},{"a":2}]', '{"a":{"a":1}}', '{"s":"}{\\\"","t":["{"]}']) if (JSON.stringify(strictJson(text)) !== JSON.stringify(JSON.parse(text))) return 'valid JSON';
            return msg(() => strictJson('{"a":1,}')) ? null : 'invalid JSON';
          } finally { fs.rmSync(root, { recursive: true, force: true }); }
        },
      },
      ...[
        ['vocab-role-mode-disagree', ['--role', 'review', '--mode', 'exec'], '--role and --mode disagree'],
        ['vocab-role-mode-disagree-exec', ['--mode', 'review', '--role', 'execute'], '--role and --mode disagree'],
        ['vocab-role-bad', ['--role', 'exec'], '--role must be review or execute'],
        ['vocab-effort-disagree', ['--effort', 'high', '--codex-effort', 'low'], '--effort and --codex-effort disagree'],
        ['vocab-effort-empty', ['--effort', ''], `--effort must match ${LEVEL_RE.source}`],
        ['vocab-effort-upper', ['--effort', 'High'], `--effort must match ${LEVEL_RE.source}`],
        ['vocab-effort-dash', ['--effort', '-high'], `--effort must match ${LEVEL_RE.source}`],
        ['vocab-effort-space', ['--effort', 'hi gh'], `--effort must match ${LEVEL_RE.source}`],
        ['vocab-effort-17', ['--effort', 'a'.repeat(17)], `--effort must match ${LEVEL_RE.source}`],
        ['vocab-effort-control', ['--effort', 'hi\x07'], `--effort must match ${LEVEL_RE.source}`],
        ['vocab-codex-effort-upper', ['--codex-effort', 'High'], `--codex-effort must match ${LEVEL_RE.source}`],
        ['vocab-context-upper', ['--context', '1M'], `--context must match ${CONTEXT_RE.source}`],
        ['vocab-context-empty', ['--context', ''], `--context must match ${CONTEXT_RE.source}`],
        ['vocab-session-129', ['--session-id', 'a'.repeat(129)], `--session-id must match ${SESSION_ID_RE.source}`],
        ['vocab-session-empty', ['--session-id', ''], `--session-id must match ${SESSION_ID_RE.source}`],
        ['vocab-session-dash', ['--session-id', '-x'], `--session-id must match ${SESSION_ID_RE.source}`],
        ['vocab-host-bad', ['--host', 'herdr'], '--host must be auto or none'],
        ['vocab-escalate-valued', ['--escalate-runtime', 'yes'], 'unknown argument: yes'],
        ['vocab-skill-name-65', ['--skill-name', 'a'.repeat(65)], `--skill-name must match ${SKILL_NAME_RE.source}`],
        ['vocab-skill-path-empty', ['--skill-path', ''], '--skill-path must be a non-empty path without control characters'],
        ['vocab-skill-path-control', ['--skill-path', 'a\nb'], '--skill-path must be a non-empty path without control characters'],
        ['vocab-mcp-config-empty', ['--mcp-config', ''], '--mcp-config must be a non-empty path without control characters'],
        ['vocab-argv-file-empty', ['--argv-file', ''], '--argv-file must be a non-empty path without control characters'],
      ].map(([name, extra, message]) => ({ name, kind: 'logic', args: ['--print-argv', '--runtime', 'pi', '--model', 'fake/ok', ...extra], exit: 2, status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/, check: (r) => ((r.stderr || '').split('\n').includes(`cross-ai: ${message}`) ? null : `stderr lacks the line: ${message}`) })),
      {
        name: 'vocab-role-alias', kind: 'logic', args: ['--print-argv', '--runtime', 'pi', '--model', 'fake/ok', '--role', 'review', '--mode', 'review'], exit: 0, status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        async check (r, ctx) {
          const run = (extra) => runCaseProcess({ args: ['--print-argv', '--runtime', 'pi', '--model', 'fake/ok', ...extra] }, ctx);
          const line = (x) => (x.stdout || '').split('\n').find((s) => s.startsWith('pi\t'));
          const b = await run(['--mode', 'review']); const c = await run(['--role', 'execute']); const d = await run(['--mode', 'exec']);
          return b.status === 0 && c.status === 0 && d.status === 0 && line(r) === line(b) && line(r)?.includes('"--no-mcp"') && line(c) === line(d) && !line(c)?.includes('"--no-mcp"') ? null : 'role alias mismatch';
        },
      },
      {
        name: 'vocab-boundaries-pass', kind: 'logic', args: ['--print-argv', '--runtime', 'pi', '--model', 'fake/ok', '--effort', 'a', '--context', '1', '--session-id', 'a', '--skill-name', 'a'], exit: 0, status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        async check (_r, ctx) { const r = await runCaseProcess({ args: ['--print-argv', '--runtime', 'pi', '--model', 'fake/ok', '--effort', 'a'.repeat(16), '--context', '1' + 'a'.repeat(15), '--session-id', 'a'.repeat(128), '--skill-name', 'a'.repeat(64)] }, ctx); return r.status === 0 ? null : 'upper boundaries'; },
      },
      {
        name: 'vocab-stored-only', kind: 'logic', args: ['--print-argv', '--runtime', 'pi', '--model', 'fake/ok', '--context', '1m', '--escalate-runtime', '--escalate-model', '--host', 'none', '--skill-name', 'placeholder-skill-1'], exit: 0, status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        async check (r, ctx) { const b = await runCaseProcess({ args: ['--print-argv', '--runtime', 'pi', '--model', 'fake/ok'] }, ctx); const line = (x) => (x.stdout || '').split('\n').find((s) => s.startsWith('pi\t')); return b.status === 0 && line(r) === line(b) ? null : 'stored flags changed argv'; },
      },
      {
        name: 'vocab-codex-effort-level', kind: 'logic', args: ['--print-argv', '--runtime', 'codex', '--model', 'fake-ok-codex', '--codex-effort', 'max'], exit: 0, status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        async check (r, ctx) { const b = await runCaseProcess({ args: ['--print-argv', '--runtime', 'codex', '--model', 'fake-ok-codex', '--codex-effort', 'ultra'] }, ctx); const line = (x) => (x.stdout || '').split('\n').find((s) => s.startsWith('codex\t')) || ''; return b.status === 0 && line(r).includes('model_reasoning_effort=max') && line(b).includes('model_reasoning_effort=ultra') ? null : 'codex levels'; },
      },
      {
        name: 'planner-effort-no-form', kind: 'logic', pure: () => {
          const row = { forms: { effort: { kind: 'none', label: { state: 'unknown', source: 'test' } } } };
          const p = planSettings(row, 'exec', { model: 'fake-ok', effort: 'high' });
          if (JSON.stringify(p.report.map(e => [e.name, e.value, e.state, e.reason || null])) !== JSON.stringify([['model','fake-ok','applied',null],['role','execute','applied',null],['effort','high','ignored','no_form']]) || p.adds.effort.length || p.model !== 'fake-ok') return 'no form';
          row.forms.effort = { kind: 'flag', flag: '--effort', label: { state: 'unverified', source: 'test' } };
          if (planSettings(row, 'exec', { model: 'fake-ok', effort: 'high' }).report.at(-1).reason !== 'unverified_form') return 'unverified';
          row.forms.effort.label.state = 'verified';
          const bad = planSettings(row, 'exec', { model: 'fake-ok', configEffort: 'Bad' });
          if (bad.report.at(-1).reason !== 'bad_value' || bad.adds.effort.length) return 'bad value';
          if (SETTING_REASONS.join(',') !== 'no_form,id_carries,unverified_form,mode_forbids,no_slot,recorded_only,no_provider_form,bad_value,no_herdr,host_failed' || SETTING_NAMES.join(',') !== 'model,provider,role,effort,context,session,escalate_runtime,escalate_model,host,skill,mcp' || SETTING_STATES.join(',') !== 'applied,ignored,unknown') return 'lists';
          return bad.report.every(e => SETTING_STATES.includes(e.state) && (!e.reason || SETTING_REASONS.includes(e.reason))) ? null : 'state';
        },
      },
      {
        name: 'planner-confirm-report', kind: 'logic', pure: () => {
          const entry = (proof) => [{ name: 'effort', value: 'high', state: 'applied', proof }];
          const fails = (r, a, mode = 'exec') => { try { confirmReport(r, a, '', mode); return false; } catch { return true; } };
          const e = entry(['--effort', 'high']);
          if (confirmReport(e, ['-p', '--effort', 'high'], '', 'exec') !== e || !fails(e, ['-p', '--effort', 'low']) || !fails(e, ['--effort', 'x', 'high'])) return 'flag';
          if (fails(entry({ slot: 'b' }), ['--model', 'b', 'x']) || fails(entry({ slot: 'b' }), ['-m', 'b']) || !fails(entry({ slot: 'b' }), ['--model', 'a', 'x', 'b'])) return 'slot';
          // 'ake/' sits inside 'fake/ok' but not at its start: only a real prefix match passes.
          if (fails(entry({ slotPrefix: 'fake/' }), ['--model', 'fake/ok']) || !fails(entry({ slotPrefix: 'fake/ok/' }), ['--model', 'fake/other']) || !fails(entry({ slotPrefix: 'ake/' }), ['--model', 'fake/ok'])) return 'prefix';
          if (!fails(entry({ mode: 'review' }), [], 'exec') || fails(entry({ runs: [['exec', 'resume'], ['s-1', '-']] }), ['exec', 'resume', 's-1', '-']) || !fails(entry({ runs: [['exec', 'resume'], ['s-1', '-']] }), ['exec', 'resume'])) return 'mode or runs';
          if (!fails([{ name: 'effort', state: 'applied' }], []) || fails([{ state: 'ignored' }, { state: 'unknown' }], [])) return 'missing proof';
          for (const row of [RUNTIMES.pi, RUNTIMES.claude]) if (planSettings(row, 'review', { model: 'fake-ok', effort: 'high' }).report.some(x => x.state === 'applied' && !x.proof)) return 'planner proof';
          return null;
        },
      },
      {
        name: 'planner-status-group', kind: 'logic', pure: () => {
          const key = 'sk-' + 'a'.repeat(16);
          const report = ['model', 'role', 'effort'].map(name => ({ name, state: 'applied' }));
          report.push({ name: 'skill', value: 'placeholder-skill-1', state: 'applied' }, { name: 'escalate_runtime', state: 'ignored' }, { name: 'provider', state: 'unknown' });
          if (statusGroup(report, 'abc-1', { runtime: true, model: false }) !== 'session=abc-1 applied=model,role,effort,skill:placeholder-skill-1 ignored=escalate_runtime unknown=provider escalate=runtime') return 'group';
          if (statusGroup([], null, {}) !== 'session=- applied=- ignored=- unknown=- escalate=-') return 'empty';
          const redacted = statusGroup([{ name: 'skill', value: key, state: 'applied' }, { name: 'mcp', value: key, state: 'applied' }], 'bad id', { runtime: true, model: true });
          return redacted === 'session=- applied=skill:<redacted>,mcp:<redacted> ignored=- unknown=- escalate=runtime,model' ? null : 'redaction';
        },
      },
      {
        name: 'planner-report-lines', kind: 'logic', pure: () => {
          const r = reportLines([{ name: 'effort', value: '\x07' + 'sk-' + 'a'.repeat(16), state: 'ignored', reason: 'bad_value' }, { name: 'session', value: '00000000-0000-4000-8000-000000000001', state: 'applied' }, { name: 'skill', value: 'placeholder-skill-1', state: 'applied', form: 'path' }]);
          return JSON.stringify(r) === JSON.stringify(['cross-ai: setting effort=<redacted> ignored reason=bad_value', 'cross-ai: setting session=00000000-0000-4000-8000-000000000001 applied', 'cross-ai: setting skill=placeholder-skill-1 applied form=path']) ? null : 'lines';
        },
      },
      {
        name: 'cursor-mode-plan',
        kind: 'logic',
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
        kind: 'logic',
        args: ['--mode', 'exec', '--cursor-mode', 'plan', '--prefer', 'pi', '--model-pi', 'fake/ok'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
      },
      {
        // D-18: a cursor bracket id is preflighted without the suffix, then run whole.
        name: 'cursor-bracket-model',
        kind: 'logic',
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
        // Brackets pass the universal floor for every runtime.
        name: 'cursor-bracket-other-rt',
        kind: 'logic',
        args: ['--print-argv', '--model-pi', 'fake/ok[x=1]'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
      },
      {
        // D-02: a bare `agent` whose real path is not cursor-agent is not cursor.
        name: 'bare-agent-guard',
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'runtime',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
        args: ['--runtime', 'pi', '--mode', 'review', '--tools-profile', 'exec', '--model', 'fake/ok'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
        check: (r) => ((r.stderr || '').includes('review mode allows only the review or none') ? null : 'missing refusal'),
      },
      {
        name: 'profile-unsupported-cursor',
        kind: 'logic',
        args: ['--runtime', 'cursor', '--tools-profile', 'none', '--model', 'fake-ok-cursor'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
        check: (r) => ((r.stderr || '').includes('cursor has no tools profile none') ? null : 'missing refusal'),
      },
      {
        name: 'profile-bad-name',
        kind: 'logic',
        args: ['--tools-profile', 'write'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
      },
      {
        name: 'no-passthrough',
        kind: 'logic',
        args: ['--runtime', 'pi', '--model', 'fake/ok', '--', '--yolo'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
      },
      {
        name: 'no-passthrough-extra-arg',
        kind: 'logic',
        args: ['--runtime', 'pi', '--model', 'fake/ok', '--extra-arg', 'x'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
      },
      {
        // One case, three widening extras: each exits 2 before any fake call.
        name: 'review-extra-args-widen-refused',
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
          mode: 'transient', token: 'event400', exit: 75, status: 'transient', tree: 'clean',
          config: { retry: { max_retries: 1, session_resets: 0 } },
        },
        {
          // A spent hard tier (record at cycle 2) stops on the same lane, still one CLI only.
          mode: 'hard-waits', token: 'event400', exit: 69, status: 'transient', tree: 'clean',
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
        kind: row.mode === 'hang' ? 'runtime' : 'logic',
        ...(row.setup ? { setup: row.setup } : {}),
        args: [
          '--prefer', 'pi,cursor,opencode', '--model-pi', `fake/${row.token || row.mode}`,
          '--model-cursor', 'fake-ok-cursor', '--model-opencode', 'fake/ok',
          ...(row.extra || []),
        ],
        ...(row.config ? { config: row.config } : {}),
        exit: row.exit,
        status: new RegExp(`^AIKIT-XAI status=${row.status} cli=pi model=fake/${row.token || row.mode} ` +
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
        args: ['--runtime', 'pi', '--model-pi', 'fake/ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        check: (_r, ctx) => (ctx.calls.some((l) => l.startsWith('pi ')) ? null : 'pi did not run'),
      },
      {
        name: 'runtime-and-prefer',
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
        config: { runtime: 'pi', prefer: ['cursor'], models: { pi: 'fake/ok', cursor: 'fake-ok-cursor' } },
        args: [],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        check: (_r, ctx) => (ctx.calls.some((l) => l.startsWith('cursor-agent')) ? 'cursor ran' : null),
      },
      {
        name: 'runtime-unknown',
        kind: 'logic',
        args: ['--runtime', 'nosuch'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
      },
      {
        name: 'runtime-none',
        kind: 'logic',
        config: { prefer: null },
        args: [],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
        check: (r) => ((r.stderr || '').includes('no runtime: pass --runtime <id>') ? null : 'missing usage line'),
      },
      {
        name: 'not-installed-first',
        kind: 'logic',
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
        kind: 'logic',
        args: ['--prefer', 'pi,cursor', '--model-cursor', 'fake-ok-cursor'],
        exit: 2,
        status: /^AIKIT-XAI status=no_model cli=pi .* exit=2 .* action=stop$/,
        check: (_r, ctx) => (ctx.calls.length ? `calls=${ctx.calls.join('|')}` : null),
      },
      {
        name: 'prefer-first-claude-exec-runs',
        kind: 'logic',
        args: ['--mode', 'exec', '--prefer', 'claude,pi', '--model-claude', 'fake-ok', '--model-pi', 'fake/ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=claude model=fake-ok exit=0 .* tree=dirty action=stop$/,
        check: (r, ctx) => {
          if (!(r.stderr || '').includes('cross-ai: --prefer reads only its first entry (claude); ignored: pi')) return 'missing ignored note';
          return ctx.calls.some((l) => l.startsWith('pi ')) ? 'pi ran' : null;
        },
      },
      {
        name: 'outer-race',
        kind: 'runtime',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
        args: ['--classify-only', 'missing.json'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* action=stop$/,
      },
      {
        name: 'route-config',
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
        args: ['--prefer', 'pi', '--route-pi', 'maybe'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* action=stop$/,
      },
      {
        name: 'copilot-exec-ok',
        kind: 'logic',
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
        kind: 'logic',
        args: ['--runtime', 'copilot', '--model', 'fake-ok', '--print-argv'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const line = (r.stdout || '').split('\n').find((l) => l.startsWith('copilot\t'));
          if (!line) return 'missing argv line';
          const argv = JSON.parse(line.split('\t')[2]);
          const want = ['-p', '<prompt>', '-s', '--no-ask-user', '--model', 'fake-ok',
            '--session-id', '<sid>', '--allow-all-tools'];
          return JSON.stringify(argv) === JSON.stringify(want) ? null : `argv=${JSON.stringify(argv)}`;
        },
      },
      {
        name: 'copilot-token-passthrough',
        kind: 'logic',
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
        kind: 'logic',
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
        name: 'pure-skill-forms-verified',
        kind: 'logic',
        pure: () => {
          const row = { forms: { skills: { name: { form: '/<name>', label: { state: 'verified', source: 's' } }, path: { flag: '--add-dir', root: '.github/skills', label: { state: 'verified', source: 's' } }, prose: SKILL_PROSE } } };
          const record = (n, p, byName) => ({ name: `placeholder-skill-${n}`, path: p, dirName: `placeholder-skill-${n}`, byName, body: skillBody(n), sha256: crypto.createHash('sha256').update(skillBody(n)).digest('hex') });
          const plan = planSkills(row, [record(1, null, true), record(2, '/x/proj/.github/skills/placeholder-skill-2', false), record(3, '/x/other/placeholder-skill-3', false)]);
          if (plan.report.map((e) => `${e.state}:${e.form}`).join(',') !== 'applied:name,applied:path,applied:prose') return 'forms';
          if (!plan.promptPrefix.startsWith('/placeholder-skill-1\n') || JSON.stringify(plan.adds) !== JSON.stringify(['--add-dir', '/x/proj'])) return 'plan output';
          confirmReport(plan.report, ['-p', '--add-dir', '/x/proj'], composePrompt(plan.promptPrefix, null, 'p', ''));
          try { confirmReport(plan.report, ['-p', '--add-dir', '/x/proj'], 'p'); } catch { return null; }
          return 'missing prompt proof accepted';
        },
      },
      {
        name: 'mcp-review-lanes-applied',
        kind: 'logic',
        env: { COPILOT_GITHUB_TOKEN: 'github_pat_' + 'a'.repeat(40) },
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=claude model=fake-ok exit=0 .* tree=clean action=stop$/,
        setup: (c) => {
          c.key = 'sk-' + 'Q'.repeat(40);
          c.mcpFile = path.join(c.tmp, 'mcp-review.json');
          fs.writeFileSync(c.mcpFile, JSON.stringify({ mcpServers: {
            'placeholder-server-b': { command: 'placeholder-cmd', args: ['--token', c.key], env: { PLACEHOLDER_TOKEN: c.key } },
            'placeholder-server-a': { url: 'https://example.invalid/mcp', headers: { Authorization: `Bearer ${c.key}` } },
          } }));
          fs.chmodSync(c.mcpFile, 0o600);
          for (const [rel, content] of [['.claude.json', '{"mcpServers":{}}\n'], ['.copilot/mcp-config.json', '{"mcpServers":{}}\n'], ['.cursor/mcp.json', '{"mcpServers":{}}\n'], ['.pi/agent/mcp.json', '{"mcpServers":{}}\n'], ['.codex/config.toml', '# synthetic\n'], ['.config/opencode/opencode.jsonc', '{}\n']]) {
            const file = path.join(c.home, rel); fs.mkdirSync(path.dirname(file), { recursive: true }); fs.writeFileSync(file, content);
          }
          c.hostBefore = hostFilesDigest(c.home);
          c.env.FAKE_CLAUDE_SEEN = path.join(c.tmp, 'claude-mcp-seen');
          c.env.FAKE_COPILOT_SEEN = path.join(c.tmp, 'copilot-mcp-seen');
          c.args = ['--runtime', 'claude', '--mode', 'review', '--model', 'fake-ok', '--mcp-config', c.mcpFile];
          return null;
        },
        check: async (r, c) => {
          const seen = JSON.parse(fs.readFileSync(c.env.FAKE_CLAUDE_SEEN, 'utf8'));
          if (JSON.stringify(seen.argv.slice(-3)) !== JSON.stringify(['--mcp-config', c.mcpFile, '--strict-mcp-config']) || seen.mcpCount !== 2) return 'claude MCP argv or count';
          const lines = r.stderr.split('\n');
          const settings = lines.filter((line) => line.startsWith('cross-ai: setting mcp='));
          if (JSON.stringify(settings) !== JSON.stringify(['cross-ai: setting mcp=placeholder-server-b applied', 'cross-ai: setting mcp=placeholder-server-a applied'])) return 'MCP report order';
          const tokens = Object.fromEntries((lines.filter((line) => line.startsWith('AIKIT-XAI ')).pop() || '').split(' ').slice(1).map((t) => t.split('=')));
          if (!tokens.applied?.includes('mcp:placeholder-server-b') || !tokens.applied?.includes('mcp:placeholder-server-a')) return 'status MCP';
          for (const value of [c.key, 'placeholder-cmd', 'example.invalid']) if ((r.stdout + r.stderr + JSON.stringify(seen.argv)).includes(value)) return 'claude value leaked';
          if (hostFilesDigest(c.home) !== c.hostBefore) return 'claude host files changed';
          const copilot = await runCaseProcess({ args: ['--runtime', 'copilot', '--mode', 'review', '--model', 'fake-readonly', '--mcp-config', c.mcpFile] }, c);
          if (copilot.reason || copilot.status !== 0) return 'copilot failed';
          const other = JSON.parse(fs.readFileSync(c.env.FAKE_COPILOT_SEEN, 'utf8'));
          const at = other.argv.indexOf('--additional-mcp-config');
          if (at < 0 || other.argv[at + 1] !== '@' + c.mcpFile || other.argv.indexOf('--disable-builtin-mcps') < 0 || other.argv.indexOf('--disable-builtin-mcps') >= at || other.mcpCount !== 2) return 'copilot MCP argv or count';
          if (copilot.stderr.includes(c.key)) return 'copilot value leaked';
          return hostFilesDigest(c.home) === c.hostBefore ? null : 'copilot host files changed';
        },
      },
      {
        name: 'skill-prose-claude-stdin',
        kind: 'logic',
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=claude model=fake-ok exit=0 .* action=stop$/,
        setup: (c) => {
          c.dir1 = makeSkill(c, 1); c.dir2 = makeSkill(c, 2);
          fs.writeFileSync(path.join(c.repo, 'guide.md'), 'GUIDE\n');
          for (const rel of ['.claude/skills/placeholder-skill-9/SKILL.md', '.agents/skills/placeholder-skill-9/SKILL.md', '.copilot/skills/placeholder-skill-9/SKILL.md', '.claude/settings.json']) {
            const file = path.join(c.home, rel); fs.mkdirSync(path.dirname(file), { recursive: true }); fs.writeFileSync(file, '{}');
          }
          c.hostBefore = hostFilesDigest(c.home);
          c.seen = path.join(c.tmp, 'claude-skill-seen'); c.env.FAKE_CLAUDE_SEEN = c.seen;
          c.args = ['--runtime', 'claude', '--mode', 'review', '--model', 'fake-ok', '--no-preamble', '--prepend-file', 'guide.md', '--skill-path', c.dir2, '--skill-path', c.dir1];
          return null;
        },
        check: (r, c) => {
          const expected = expectSkillBlock(c.dir2, 2, skillBody(2)) + expectSkillBlock(c.dir1, 1, skillBody(1)) + 'GUIDE\n\n\nprompt\n';
          if (JSON.parse(fs.readFileSync(c.seen, 'utf8')).stdin !== expected) return 'stdin differs';
          const lines = r.stderr.split('\n');
          const settings = lines.filter((l) => l.startsWith('cross-ai: setting skill='));
          const blocks = lines.filter((l) => l.startsWith('cross-ai: skill-block '));
          if (settings.length !== 2 || blocks.length !== 2 || !settings[0].includes('placeholder-skill-2') || !settings[1].includes('placeholder-skill-1') || !blocks[0].includes('placeholder-skill-2') || !blocks[1].includes('placeholder-skill-1')) return 'skill report order';
          const tokens = Object.fromEntries((lines.filter((l) => l.startsWith('AIKIT-XAI ')).pop() || '').split(' ').slice(1).map((t) => t.split('=')));
          if (!tokens.applied?.includes('skill:placeholder-skill-2') || !tokens.applied?.includes('skill:placeholder-skill-1')) return 'status skills';
          return hostFilesDigest(c.home) === c.hostBefore ? null : 'host files changed';
        },
      },
      {
        name: 'skill-prose-copilot-argv',
        kind: 'logic',
        env: { COPILOT_GITHUB_TOKEN: 'github_pat_' + 'a'.repeat(40) },
        config: { retry: { max_retries: 2, session_resets: 1 } },
        exit: 75,
        status: /^AIKIT-XAI status=transient cli=copilot model=fake-event400 exit=75 .* action=stop$/,
        setup: (c) => {
          c.dir1 = makeSkill(c, 1); c.dir2 = makeSkill(c, 2);
          c.seen = path.join(c.tmp, 'copilot-skill-seen'); c.env.FAKE_COPILOT_SEEN = c.seen;
          c.env.FAKE_SKILL_EDIT = path.join(c.dir1, 'SKILL.md');
          c.args = ['--runtime', 'copilot', '--model', 'fake-event400', '--no-preamble', '--skill-path', c.dir1];
          return null;
        },
        check: async (_r, c) => {
          if (c.calls.filter((l) => l.startsWith('copilot ')).length !== 3) return 'call count';
          const seen = JSON.parse(fs.readFileSync(c.seen, 'utf8'));
          const prefix = `${RESUME_MSG}\n\n`;
          const prompt = seen.prompt.startsWith(prefix) ? seen.prompt.slice(prefix.length) : seen.prompt;
          if (prompt !== expectSkillBlock(c.dir1, 1, skillBody(1)) + 'prompt\n') return 'retry prompt differs';
          const block = expectSkillBlock(c.dir2, 2, skillBody(2));
          const room = ARGV_PROMPT_MAX - Buffer.byteLength(prefix) - Buffer.byteLength(block);
          const args = ['--runtime', 'copilot', '--model', 'fake-ok', '--no-preamble', '--skill-path', c.dir2];
          const ctx = { ...c, env: { ...c.env, FAKE_SKILL_EDIT: '' } };
          const fit = await runCaseProcess({ args, stdin: 'z'.repeat(room) }, ctx);
          const over = await runCaseProcess({ args, stdin: 'z'.repeat(room + 1) }, ctx);
          if (fit.status !== 0 || over.status !== 2 || !over.stderr.includes(`is over ${ARGV_PROMPT_MAX}`)) return `limits: ${fit.status},${over.status}`;
          return null;
        },
      },
      {
        name: 'pure-argv-prompt-guard',
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
        args: ['--runtime', 'copilot', '--tools-profile', 'none', '--model', 'fake-ok'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
        check: (r) => ((r.stderr || '').includes('copilot has no tools profile none') ? null : 'missing refusal'),
      },
      {
        name: 'copilot-review-widen-refused',
        kind: 'logic',
        args: ['--runtime', 'copilot', '--mode', 'review', '--tools-profile', 'exec', '--model', 'fake-ok'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
        check: (r) => ((r.stderr || '').includes('review mode allows only the review or none') ? null : 'missing refusal'),
      },
      {
        name: 'copilot-review-extra-refused',
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
        kind: 'logic',
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
          const head = ['-p', '<prompt>', '-s', '--no-ask-user', '--model', 'fake-ok', '--session-id', '<sid>'];
          const want = [...head, ...tail];
          return JSON.stringify(argv) === JSON.stringify(want) ? null : `argv=${JSON.stringify(argv)}`;
        },
      },
      {
        name: 'settings-run-lines', kind: 'logic',
        args: ['--runtime', 'pi', '--model', 'fake/ok'], exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        check: (r) => {
          const lines = r.stderr.split('\n');
          if (!lines.includes('cross-ai: setting model=fake/ok applied') ||
              !lines.includes('cross-ai: setting role=execute applied')) return 'missing applied settings';
          const last = lines.reduce((n, line, i) => line.startsWith('cross-ai: setting ') ? i : n, -1);
          const first = lines.findIndex((line) => line.startsWith('cross-ai: cli=pi '));
          if (first < 0 || last >= first) return 'settings not before cli';
          const tail = statusTail(r.stderr);
          if (!tail || tail.escalate !== '-' || tail.unknown === undefined ||
              !tail.applied?.split(',').includes('model') || !tail.applied.split(',').includes('role')) return 'invalid settings status';
          return null;
        },
      },

      {
        name: 'settings-effort-equals-config', kind: 'logic',
        config: { effort: { pi: 'high' } },
        args: ['--runtime', 'pi', '--model', 'fake/ok', '--effort', 'high'], exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        check: (r) => {
          const lines = (r.stderr || '').split('\n').filter((l) => l.startsWith('cross-ai: setting effort='));
          if (lines.length !== 1 || lines[0] !== 'cross-ai: setting effort=high applied') return `effort lines=${JSON.stringify(lines)}`;
          const line = (r.stderr || '').split('\n').find((l) => l.startsWith('cross-ai: argv='));
          if (!line) return 'missing argv';
          const argv = JSON.parse(line.slice('cross-ai: argv='.length));
          const i = argv.indexOf('--thinking');
          return i >= 0 && argv[i + 1] === 'high' && argv.filter((a) => a === '--thinking').length === 1 ? null : `argv=${JSON.stringify(argv)}`;
        },
      },
      {
        name: 'settings-config-effort-claude', kind: 'logic',
        config: { effort: { claude: 'high' } },
        args: ['--runtime', 'claude', '--role', 'review', '--model', 'fake-ok'], exit: 0,
        status: /^AIKIT-XAI status=ok cli=claude model=fake-ok exit=0 .* tree=clean action=stop$/,
        check: (r) => {
          const lines = (r.stderr || '').split('\n');
          if (!lines.includes('cross-ai: setting effort=high applied')) return 'missing effort line';
          const line = lines.find((l) => l.startsWith('cross-ai: argv='));
          if (!line) return 'missing argv';
          const argv = JSON.parse(line.slice('cross-ai: argv='.length));
          const i = argv.indexOf('--effort');
          return i >= 0 && argv[i + 1] === 'high' ? null : `argv=${JSON.stringify(argv)}`;
        },
      },
      {
        name: 'settings-context-not-fed', kind: 'logic',
        args: ['--runtime', 'pi', '--model', 'fake/ok', '--context', '1m'], exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        check: (r) => {
          const lines = (r.stderr || '').split('\n');
          if (!lines.includes('cross-ai: setting context=1m ignored reason=no_form')) return 'missing context line';
          const line = lines.find((l) => l.startsWith('cross-ai: argv='));
          if (!line) return 'missing argv';
          const argv = JSON.parse(line.slice('cross-ai: argv='.length));
          return !argv.includes('--context') && !argv.some((a) => a.includes('1m')) ? null : `argv=${JSON.stringify(argv)}`;
        },
      },
      {
        name: 'settings-status-model-as-called', kind: 'logic',
        args: ['--runtime', 'cursor', '--model', 'fake-ok-cursor', '--effort', 'high'], exit: 0,
        status: /^AIKIT-XAI status=ok cli=cursor model=fake-ok-cursor exit=0 .* tree=dirty action=stop$/,
        check: (r, ctx) => {
          const line = (r.stderr || '').split('\n').find((l) => l.startsWith('cross-ai: argv='));
          if (!line) return 'missing argv';
          const argv = JSON.parse(line.slice('cross-ai: argv='.length));
          const id = 'fake-ok-cursor' + '[effort=high]';
          return argv.includes(id) && ctx.calls.includes('cursor-agent ' + id) ? null : `argv or calls=${JSON.stringify(ctx.calls)}`;
        },
      },
      {
        name: 'escalate-echo-both', kind: 'logic',
        args: ['--runtime', 'pi', '--model', 'fake/ok', '--escalate-runtime', '--escalate-model'], exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        check: (r) => {
          const lines = (r.stderr || '').split('\n');
          for (const key of ['runtime', 'model']) {
            const hits = lines.filter((l) => new RegExp(`^cross-ai: setting escalate_${key}=\\S+ ignored reason=recorded_only$`).test(l));
            if (hits.length !== 1) return `escalate ${key} lines=${hits.length}`;
          }
          const tail = statusTail(r.stderr || '');
          return tail?.escalate === 'runtime,model' && ['escalate_runtime', 'escalate_model'].every((k) => tail.ignored?.split(',').includes(k)) ? null : `tail=${JSON.stringify(tail)}`;
        },
      },
      {
        name: 'escalate-echo-model-only', kind: 'logic',
        args: ['--runtime', 'pi', '--model', 'fake/ok', '--escalate-model'], exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        check: (r) => {
          const tail = statusTail(r.stderr || '');
          return tail?.escalate === 'model' && !(r.stderr || '').split('\n').some((l) => l.startsWith('cross-ai: setting escalate_runtime')) ? null : `tail=${JSON.stringify(tail)}`;
        },
      },
      {
        name: 'escalate-one-spawn', kind: 'logic',
        args: ['--runtime', 'pi', '--model', 'fake/auth', '--escalate-runtime', '--escalate-model'], exit: 69,
        status: /^AIKIT-XAI status=auth cli=pi model=fake\/auth exit=69 .* action=stop$/,
        check: async (r, ctx) => {
          if (ctx.calls.filter((l) => l === 'pi auth').length !== 1) return `calls=${JSON.stringify(ctx.calls)}`;
          const lane = sameLane(ctx, 'pi', 'fake/auth');
          if (lane) return lane;
          const plain = await runCaseProcess({ args: ['--runtime', 'pi', '--model', 'fake/auth'] }, ctx);
          return plain.status === 69 ? null : `plain status=${plain.status}`;
        },
      },
      {
        name: 'status-group-before-retry', kind: 'logic', config: { retry: { ...HARD_TIER_RETRY } },
        args: ['--runtime', 'pi', '--model', 'fake/event400'], exit: 75,
        status: /^AIKIT-XAI status=transient cli=pi model=fake\/event400 exit=75 .* action=stop$/,
        check: (r) => {
          const line = (r.stderr || '').split('\n').filter((l) => l.startsWith('AIKIT-XAI ')).pop() || '';
          if (!/ attempts=\d+ cycles=\d+ session=\S+ applied=\S+ ignored=\S+ unknown=\S+ escalate=\S+ coverage=- findings=- retry_after_s=\d+ cycle=\d+$/.test(line)) return `status=${line}`;
          const tail = statusTail(r.stderr || '');
          return tail?.retry_after_s === '600' && tail.escalate === '-' ? null : `tail=${JSON.stringify(tail)}`;
        },
      },
      {
        name: 'settings-session-first-argv', kind: 'logic',
        args: ['--runtime', 'pi', '--model', 'fake/ok', '--session-id', 'placeholder-sid-1'], exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        check: async (r, ctx) => {
          if (!(r.stderr || '').split('\n').includes('cross-ai: setting session=placeholder-sid-1 applied')) return 'missing session line';
          const rows = () => readOr(ctx.env.FAKE_SIDS, '').split('\n').filter(Boolean).map((l) => l.split(' '));
          if (rows().length !== 1 || rows()[0][0] !== 'placeholder-sid-1') return `sids=${JSON.stringify(rows())}`;
          const cursor = await runCaseProcess({ args: ['--runtime', 'cursor', '--model', 'fake-ok-cursor', '--session-id', 'c1'] }, ctx);
          const lines = (cursor.stderr || '').split('\n');
          const line = lines.find((l) => l.startsWith('cross-ai: argv='));
          if (cursor.status !== 0 || !lines.includes('cross-ai: setting session=c1 applied') || !line) return 'cursor session or status';
          const argv = JSON.parse(line.slice('cross-ai: argv='.length));
          if (JSON.stringify(argv.slice(-2)) !== JSON.stringify(['--resume', 'c1'])) return `cursor argv=${JSON.stringify(argv)}`;
          const pi = await runCaseProcess({ args: ['--runtime', 'pi', '--model', 'fake/ok'] }, ctx);
          const piLine = (pi.stderr || '').split('\n').find((l) => l.startsWith('cross-ai: argv='));
          if (pi.status !== 0 || !piLine) return 'pi status or argv';
          const piArgv = JSON.parse(piLine.slice('cross-ai: argv='.length));
          const i = piArgv.indexOf('--session-id');
          return i >= 0 && rows().length === 2 && rows()[1][0] === piArgv[i + 1] ? null : `sids=${JSON.stringify(rows())}`;
        },
      },
      {
        name: 'session-roundtrip-cursor', kind: 'logic',
        args: ['--runtime', 'cursor', '--model', 'fake-ok-cursor'], exit: 0,
        status: /^AIKIT-XAI status=ok cli=cursor model=fake-ok-cursor exit=0 .* tree=dirty action=stop$/,
        check: async (r, ctx) => {
          if (statusTail(r.stderr || '')?.session !== 'c1') return 'initial session';
          for (let i = 0; i < 2; i++) {
            const next = await runCaseProcess({ args: ['--runtime', 'cursor', '--model', 'fake-ok-cursor', '--session-id', 'c1'] }, ctx);
            if (next.status !== 0 || statusTail(next.stderr || '')?.session !== 'c1' || !(next.stderr || '').includes('"--resume","c1"')) return `resume=${next.status}`;
          }
          const expected = [['cursor-agent', '-', 'prompt'], ['cursor-agent', 'c1', 'prompt'], ['cursor-agent', 'c1', 'prompt']];
          return JSON.stringify(sessionRows(ctx)) === JSON.stringify(expected) && !fs.existsSync(caseCycleFile(ctx, 'cursor', 'fake-ok-cursor', 'other')) ? null : `rows=${JSON.stringify(sessionRows(ctx))}`;
        },
      },
      {
        name: 'session-rejected-no-fresh', kind: 'logic',
        args: ['--runtime', 'cursor', '--model', 'fake-ok-cursor', '--session-id', 'rejected-1'], exit: 1,
        status: /^AIKIT-XAI status=crash cli=cursor model=fake-ok-cursor exit=1 cli_rc=7 .* action=stop$/,
        check: (r, ctx) => statusTail(r.stderr || '')?.session === 'rejected-1' && (r.stderr || '').includes('fake-session: no session rejected-1') && JSON.stringify(sessionRows(ctx)) === JSON.stringify([['cursor-agent', 'rejected-1', 'prompt']]) ? null : `rows=${JSON.stringify(sessionRows(ctx))}`,
      },
      {
        name: 'session-rejected-transient-no-fresh', kind: 'logic', config: { retry: { max_retries: 1 } },
        args: ['--runtime', 'cursor', '--model', 'fake-ok-cursor', '--session-id', 'rejected503-1'], exit: 75,
        status: /^AIKIT-XAI status=transient cli=cursor model=fake-ok-cursor exit=75 .* action=stop$/,
        check: (r, ctx) => JSON.stringify(sessionRows(ctx)) === JSON.stringify([['cursor-agent', 'rejected503-1', 'prompt'], ['cursor-agent', 'rejected503-1', 'resume-note']]) ? null : `rows=${JSON.stringify(sessionRows(ctx))}`,
      },
      {
        // R7: opencode preserves adjacent and maximum-length ids exactly.
        name: 'session-roundtrip-opencode', kind: 'logic', args: ['--runtime', 'opencode', '--model', 'fake/ok'], exit: 0, status: /^AIKIT-XAI status=ok .* action=stop$/,
        check: async (r, ctx) => {
          const minted = sessionRows(ctx)[0]?.[1] !== '-' ? sessionRows(ctx)[0]?.[1] : 'ses_1';
          if (statusTail(r.stderr || '')?.session !== minted) return 'initial id';
          const ids = [minted, 'c1', 'P' + 'a.B:c-9'.repeat(18) + 'z'];
          for (const id of ids) {
            const next = await runCaseProcess({ args: ['--runtime', 'opencode', '--model', 'fake/ok', '--session-id', id] }, ctx);
            if (next.status !== 0 || statusTail(next.stderr || '')?.session !== id) return `resume ${id}`;
          }
          return JSON.stringify(sessionRows(ctx).slice(1).map((row) => row[1])) === JSON.stringify(ids) ? null : 'rows';
        },
      },
      {
        // R7: codex resume passes the thread id before the final dash.
        name: 'session-roundtrip-codex', kind: 'logic', args: ['--runtime', 'codex', '--model', 'fake-ok-codex'], exit: 0, status: /^AIKIT-XAI status=ok .* action=stop$/,
        check: async (r, ctx) => {
          const next = await runCaseProcess({ args: ['--runtime', 'codex', '--model', 'fake-ok-codex', '--session-id', 't1'] }, ctx);
          return statusTail(r.stderr || '')?.session === 't1' && next.status === 0 && statusTail(next.stderr || '')?.session === 't1' && readOr(ctx.env.FAKE_CALLS, '').includes('codex-resume fake-ok-codex') && JSON.stringify(sessionRows(ctx)) === JSON.stringify([['codex', '-', 'prompt'], ['codex', 't1', 'prompt']]) ? null : 'codex roundtrip';
        },
      },
      {
        // R7: chosen pi ids reject empty input and allow concurrent explicit ids.
        name: 'session-chosen-pi', kind: 'logic', args: ['--runtime', 'pi', '--model', 'fake/ok'], exit: 0, status: /^AIKIT-XAI status=ok .* action=stop$/,
        check: async (r, ctx) => {
          const rows = () => readOr(ctx.env.FAKE_SIDS, '').trim().split('\n').filter(Boolean).map((l) => l.split(' '));
          const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
          if (rows().length !== 1 || !uuid.test(rows()[0][0]) || statusTail(r.stderr || '')?.session !== rows()[0][0]) return 'initial id';
          const args = ['--runtime', 'pi', '--model', 'fake/ok', '--session-id'];
          const one = await runCaseProcess({ args: [...args, 'placeholder-sid-1'] }, ctx);
          const empty = await runCaseProcess({ args: [...args, ''] }, ctx);
          // Concurrent executes use separate checkouts while retaining the same session id.
          const repo = path.join(ctx.tmp, 'r-session-chosen-pi-b');
          fs.mkdirSync(repo, { recursive: true });
          spawnSync('git', ['init', '-q'], { cwd: repo, env: ctx.env });
          fs.writeFileSync(path.join(repo, 'a.txt'), 'base\n');
          spawnSync('git', ['add', 'a.txt'], { cwd: repo, env: ctx.env });
          spawnSync('git', ['commit', '-q', '-m', 'init'], { cwd: repo, env: ctx.env });
          const pair = await Promise.all([ctx, { ...ctx, repo }].map((c) => runCaseProcess({ args: [...args, 'placeholder-sid-6'] }, c)));
          return one.status === 0 && statusTail(one.stderr || '')?.session === 'placeholder-sid-1' && empty.status === 2 && pair.every((x) => x.status === 0) && JSON.stringify(rows().slice(1).map((x) => x[0])) === JSON.stringify(['placeholder-sid-1', 'placeholder-sid-6', 'placeholder-sid-6']) ? null : 'pi ids';
        },
      },
      {
        // R7: copilot chosen ids are reported and reused.
        name: 'session-chosen-copilot', kind: 'logic', env: { COPILOT_GITHUB_TOKEN: 'github_pat_' + 'a'.repeat(40) }, args: ['--runtime', 'copilot', '--model', 'fake-ok'], exit: 0, status: /^AIKIT-XAI status=ok .* action=stop$/,
        check: async (r, ctx) => {
          const id = sessionRows(ctx)[0]?.[1];
          if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(id || '') || statusTail(r.stderr || '')?.session !== id || JSON.stringify(sessionRows(ctx)) !== JSON.stringify([['copilot', id, 'prompt']])) return 'initial id';
          const next = await runCaseProcess({ args: ['--runtime', 'copilot', '--model', 'fake-ok', '--session-id', 'placeholder-sid-2'] }, ctx);
          return next.status === 0 && statusTail(next.stderr || '')?.session === 'placeholder-sid-2' && JSON.stringify(sessionRows(ctx)[1]) === JSON.stringify(['copilot', 'placeholder-sid-2', 'prompt']) ? null : 'copilot resume';
        },
      },
      {
        // R7: forbidden codex modes visibly start fresh.
        name: 'session-mode-forbids-codex', kind: 'logic', config: { retry: { max_retries: 0, session_resets: 0 } }, args: ['--runtime', 'codex', '--role', 'review', '--model', 'fake-event400-codex', '--session-id', 'placeholder-sid-3'], exit: 75, status: /^AIKIT-XAI status=transient .* action=stop$/,
        check: async (r, ctx) => {
          const next = await runCaseProcess({ args: ['--runtime', 'codex', '--role', 'execute', '--codex-sandbox', 'workspace-write', '--model', 'fake-ok-codex', '--session-id', 'placeholder-sid-4'] }, ctx);
          return (r.stderr || '').includes('cross-ai: setting session=placeholder-sid-3 ignored reason=mode_forbids') && statusTail(r.stderr || '')?.session === 't1' && next.status === 0 && (next.stderr || '').includes('cross-ai: setting session=placeholder-sid-4 ignored reason=mode_forbids') && statusTail(next.stderr || '')?.session === 't1' && JSON.stringify(sessionRows(ctx)) === JSON.stringify([['codex', '-', 'prompt'], ['codex', '-', 'prompt']]) ? null : 'forbidden mode';
        },
      },
      {
        // R7: explicit ids take precedence over the quota record.
        name: 'session-explicit-beats-last-sid', kind: 'logic', stdin: 'same task\n', config: { retry: { ...HARD_TIER_RETRY } }, args: ['--runtime', 'pi', '--model', 'fake/event400', '--no-preamble', '--session-id', 'placeholder-sid-5'], exit: 75, status: /^AIKIT-XAI status=transient .* action=stop$/,
        setup: (c) => { writePriorRecord(c, 'pi', 'fake/event400', 'other', 'transient', 0, { last_sid: 'old-sid', task_digest: taskDigest('same task\n') }); return null; },
        check: (r, ctx) => {
          const rows = readOr(ctx.env.FAKE_SIDS, '').trim().split('\n').filter(Boolean).map((l) => l.split(' '));
          return rows.length === 1 && rows[0][0] === 'placeholder-sid-5' && readCycleState(caseCycleFile(ctx, 'pi', 'fake/event400', 'other'))?.last_sid === 'placeholder-sid-5' && statusTail(r.stderr || '')?.session === 'placeholder-sid-5' ? null : 'precedence';
        },
      },
      {
        // R7: status reports the last session in rung order.
        name: 'session-last-id-reported', kind: 'logic', config: { retry: { max_retries: 1, session_resets: 1 } }, args: ['--runtime', 'pi', '--model', 'fake/event400'], exit: 75, status: /^AIKIT-XAI status=transient .* action=stop$/,
        check: (r, ctx) => {
          const rows = readOr(ctx.env.FAKE_SIDS, '').trim().split('\n').filter(Boolean).map((l) => l.split(' '));
          return rows.length >= 3 && rows.at(-1)[0] !== rows[0][0] && statusTail(r.stderr || '')?.session === rows.at(-1)[0] ? null : 'last id';
        },
      },
      {
        // R7: pinned copilot retries continue the same chosen session.
        name: 'session-pinned-copilot-retry', kind: 'logic', env: { COPILOT_GITHUB_TOKEN: 'github_pat_' + 'a'.repeat(40) }, config: { retry: { max_retries: 1 } }, args: ['--runtime', 'copilot', '--model', 'fake-event400', '--session-id', 'placeholder-sid-7'], exit: 75,
        status: /^AIKIT-XAI status=transient cli=copilot model=fake-event400 exit=75 .* action=stop$/,
        check: (r, ctx) => JSON.stringify(sessionRows(ctx)) === JSON.stringify([['copilot', 'placeholder-sid-7', 'prompt'], ['copilot', 'placeholder-sid-7', 'resume-note']]) && !(r.stderr || '').includes('next=new refused') && statusTail(r.stderr || '')?.session === 'placeholder-sid-7' ? null : 'pinned retry',
      },
      {
        // R7: key-shaped record ids are neither reused nor displayed.
        name: 'session-record-id-unshown', kind: 'logic', stdin: 'same task\n', config: { retry: { ...HARD_TIER_RETRY } }, args: ['--runtime', 'pi', '--model', 'fake/event400', '--no-preamble'], exit: 75, status: /^AIKIT-XAI status=transient .* action=stop$/,
        setup: (c) => { writePriorRecord(c, 'pi', 'fake/event400', 'other', 'transient', 0, { last_sid: c.env.AIKIT_XAI_SENTINEL, task_digest: taskDigest('same task\n') }); return null; },
        check: (r, ctx) => {
          const rows = readOr(ctx.env.FAKE_SIDS, '').trim().split('\n').filter(Boolean).map((l) => l.split(' '));
          const lines = (r.stderr || '').split('\n').filter((l) => l.startsWith('cross-ai: attempt ') || l.startsWith('AIKIT-XAI '));
          return (r.stderr || '').includes("cross-ai: note: the quota record's session id is outside [A-Za-z0-9._:-] or shaped like a key; it is not reused") && rows.length === 1 && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(rows[0][0]) && readCycleState(caseCycleFile(ctx, 'pi', 'fake/event400', 'other'))?.last_sid === rows[0][0] && lines.every((l) => !l.includes(ctx.env.AIKIT_XAI_SENTINEL)) ? null : 'unshown record id';
        },
      },
      {
        // R7: invalid host and persisted ids are never displayed, saved or resumed.
        name: 'session-host-id-unshown', kind: 'logic', env: { FAKE_SESSION_MODE: 'badsid-503' }, config: { retry: { max_retries: 1, session_resets: 0 } }, args: ['--runtime', 'cursor', '--model', 'fake-ok-cursor', '--no-preamble'], exit: 75,
        status: /^AIKIT-XAI status=transient cli=cursor model=fake-ok-cursor exit=75 .* action=stop$/,
        check: async (r, ctx) => {
          const rows = sessionRows(ctx);
          const note = ' printed a session id outside [A-Za-z0-9._:-] or shaped like a key; session=- and it is not passed back';
          if (rows.length !== 2 || rows.some((x) => x[1] !== '-') || (r.stderr || '').split(note).length !== 2 || (r.stderr || '').split('\n').some((l) => l.startsWith('cross-ai: attempt ') && l.includes('bad')) || statusTail(r.stderr || '')?.session !== '-') return 'host id';
          const file = caseCycleFile(ctx, 'cursor', 'fake-ok-cursor', 'other');
          const saved = readCycleState(file);
          if (!saved || saved.last_sid !== null) return 'saved host id';
          writePriorRecord(ctx, 'cursor', 'fake-ok-cursor', 'other', 'transient', 0, { last_sid: 'bad id!', task_digest: taskDigest('prompt\n') });
          const next = await runCaseProcess({ args: ['--runtime', 'cursor', '--model', 'fake-ok-cursor', '--no-preamble'] }, ctx);
          if (next.status !== 75 || !(next.stderr || '').includes("cross-ai: note: the quota record's session id is outside [A-Za-z0-9._:-] or shaped like a key; it is not reused") || sessionRows(ctx).slice(rows.length).some((x) => x[1] !== '-')) return 'record id';
          const claude = await runCaseProcess({ args: ['--runtime', 'claude', '--role', 'review', '--model', 'fake-ok'] }, { ...ctx, env: { ...ctx.env, FAKE_SESSION_MODE: 'nosid' } });
          if (claude.status !== 0 || statusTail(claude.stderr || '')?.session !== '-') return 'claude missing id';
          const pi = await runCaseProcess({ args: ['--runtime', 'pi', '--model', 'fake/ok', '--session-id', ctx.env.AIKIT_XAI_SENTINEL] }, ctx);
          const line = (pi.stderr || '').split('\n').filter((l) => l.startsWith('AIKIT-XAI ')).pop() || '';
          return pi.status === 0 && !line.includes(ctx.env.AIKIT_XAI_SENTINEL) && statusTail(pi.stderr || '')?.session === '-' ? null : 'pi key-shaped id';
        },
      },
      {
        name: 'claude-exec-resume', kind: 'logic',
        args: ['--runtime', 'claude', '--role', 'execute', '--model', 'fake-ok'], exit: 0,
        status: /^AIKIT-XAI status=ok cli=claude model=fake-ok exit=0 .* tree=dirty action=stop$/,
        check: async (r, ctx) => {
          if (statusTail(r.stderr || '')?.session !== 'x') return 'first session';
          const next = await runCaseProcess({ args: ['--runtime', 'claude', '--role', 'execute', '--model', 'fake-ok', '--session-id', 'x'] }, ctx);
          if (next.status !== 0 || statusTail(next.stderr || '')?.session !== 'x' || !(next.stderr || '').includes('"--resume","x"')) return 'resume';
          return JSON.stringify(sessionRows(ctx)) === JSON.stringify([['claude', '-', 'prompt'], ['claude', 'x', 'prompt']]) ? null : 'session rows';
        },
      },
      {
        name: 'claude-exec-pattern-unverified', kind: 'logic',
        args: ['--runtime', 'claude', '--role', 'execute', '--model', 'fake-auth'], exit: 69,
        status: /^AIKIT-XAI status=auth cli=claude model=fake-auth exit=69 .* action=stop$/,
        check: async (r, ctx) => {
          if (statusTail(r.stderr || '')?.pattern !== (CLAUDE_EXEC_FORMULA_RECORD === null ? 'unverified' : 'verified')) return 'execute pattern';
          const review = await runCaseProcess({ args: ['--runtime', 'claude', '--role', 'review', '--model', 'fake-auth'] }, ctx);
          return review.status === 69 && statusTail(review.stderr || '')?.pattern === 'verified' ? null : 'review pattern';
        },
      },
      {
        name: 'claude-exec-no-model', kind: 'logic',
        args: ['--runtime', 'claude', '--role', 'execute'], exit: 2,
        status: /^AIKIT-XAI status=no_model cli=claude .* exit=2 .* action=stop$/,
      },
      {
        name: 'argv-nul-refused', kind: 'logic',
        args: ['--runtime', 'copilot', '--model', 'fake-ok'], stdin: 'a\u0000b\n', exit: 2,
        status: /^AIKIT-XAI status=usage cli=copilot model=fake-ok exit=2 cli_rc=- elapsed=\d+s out=\d+ tree=clean action=stop$/,
        check: (r, ctx) => {
          if (!(r.stderr || '').includes('cross-ai: argv for copilot holds a NUL byte; refused')) return 'no NUL refusal line';
          return ctx.calls.some((line) => line.startsWith('copilot')) ? 'copilot was spawned' : null;
        },
      },
      hostPair('host-ok', 'fake/ok', 0, /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 cli_rc=0 elapsed=\d+s out=\d+ tree=dirty action=stop$/, { env: { FAKE_HERDR_PRECLOSED: '1' }, closeTail: ' already-closed' }),
      hostPair('host-auth', 'fake/auth', 69, /^AIKIT-XAI status=auth cli=pi model=fake\/auth exit=69 cli_rc=1 elapsed=\d+s out=\d+ tree=clean action=stop$/),
      hostPair('host-empty', 'fake/empty', 1, /^AIKIT-XAI status=empty_answer cli=pi model=fake\/empty exit=1 cli_rc=0 elapsed=\d+s out=\d+ tree=clean action=stop$/),
      hostPair('host-timeout', 'fake/hang', 124, /^AIKIT-XAI status=timeout cli=pi model=fake\/hang exit=124 cli_rc=.* elapsed=\d+s out=\d+ tree=.* action=stop$/, { args: ['--timeout', '2'], dead: ['gc'] }),
      hostPair('host-group-left', 'fake/gcleft', 0, /^AIKIT-XAI status=ok cli=pi model=fake\/gcleft exit=0 cli_rc=0 elapsed=\d+s out=\d+ tree=dirty action=stop$/, { dead: ['gc'] }),
      {
        name: 'host-env-none', kind: 'logic',
        args: ['--runtime', 'pi', '--model', 'fake/ok', '--host', 'auto'],
        env: { HERDR_ENV: '1', PATH: hostedPath, AIKIT_HOST: 'none' }, exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 cli_rc=0 elapsed=\d+s out=\d+ tree=dirty action=stop$/,
        check: (r, c) => !r.stderr.includes('cross-ai: setting host=none applied') ? 'missing host=none' : fs.existsSync(path.join(c.home, 'herdr.log')) ? 'herdr was called' : null,
      },
      {
        name: 'host-no-herdr', kind: 'logic',
        args: ['--runtime', 'pi', '--model', 'fake/ok', '--host', 'auto'],
        env: { PATH: hostedPath, AIKIT_HOST: 'yes' }, exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 cli_rc=0 elapsed=\d+s out=\d+ tree=dirty action=stop$/,
        check: (r, c) => !r.stderr.includes('cross-ai: AIKIT_HOST=yes is not auto or none; ignored') ? 'missing invalid host note' : !r.stderr.includes('cross-ai: setting host=auto ignored reason=no_herdr') ? 'missing no_herdr' : fs.existsSync(path.join(c.home, 'herdr.log')) ? 'herdr was called' : null,
      },
      {
        name: 'host-print-argv', kind: 'logic',
        args: ['--runtime', 'pi', '--model', 'fake/ok', '--host', 'auto', '--print-argv'],
        env: { HERDR_ENV: '1', PATH: hostedPath }, exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r, c) => !r.stderr.includes('cross-ai: setting host=herdr applied') ? 'missing host=herdr' : r.stderr.includes('cross-ai: host herdr tab=') ? 'host tab line present' : fs.existsSync(path.join(c.home, 'herdr.log')) ? 'herdr was called' : null,
      },
      {
        name: 'host-unsafe-path', kind: 'logic',
        args: ['--runtime', 'pi', '--model', 'fake/ok', '--host', 'auto'],
        env: { HERDR_ENV: '1', PATH: hostedPath }, exit: 0,
        setup: (c) => { c.env.XDG_STATE_HOME = path.join(c.tmp, 'state home'); return null; },
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 cli_rc=0 elapsed=\d+s out=\d+ tree=dirty action=stop$/,
        check: (r, c) => {
          if (!r.stderr.includes('cross-ai: host: state home path holds a character outside [A-Za-z0-9._/-]; the lane runs headless')) return 'missing unsafe path note';
          return hostFailedOnly(r, c) || (c.calls.filter((s) => s === 'pi ok').length === 1 ? null : 'pi ok call count');
        },
      },
      {
        name: 'host-overlap', kind: 'runtime',
        args: ['--runtime', 'pi', '--model', 'fake/slowok', '--host', 'auto'],
        env: { HERDR_ENV: '1', PATH: hostedPath }, exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/slowok exit=0 cli_rc=0 elapsed=\d+s out=\d+ tree=dirty action=stop$/,
        setup: (c) => {
          // 38-13: one checkout admits one execute run; the overlap runs on a second checkout.
          const repoB = path.join(c.tmp, 'r-host-overlap-b');
          fs.mkdirSync(repoB, { recursive: true });
          spawnSync('git', ['init', '-q'], { cwd: repoB, env: c.env });
          fs.writeFileSync(path.join(repoB, 'a.txt'), 'base\n');
          spawnSync('git', ['add', 'a.txt'], { cwd: repoB, env: c.env });
          spawnSync('git', ['commit', '-q', '-m', 'init'], { cwd: repoB, env: c.env });
          const out = fs.openSync(path.join(c.home, 'overlap-out.txt'), 'w');
          const err = fs.openSync(path.join(c.home, 'overlap-err.txt'), 'w');
          const child = spawn(process.execPath, [c.copy, '--runtime', 'pi', '--model', 'fake/slowok', '--host', 'auto'], { cwd: repoB, env: c.env, stdio: ['pipe', out, err], detached: true });
          child.stdin.end('prompt\n');
          fs.closeSync(out); fs.closeSync(err);
          caseRunners.add(child);
          c.overlapExit = new Promise((resolve) => child.once('exit', (code) => { caseRunners.delete(child); resolve(code); }));
          return null;
        },
        check: async (r, c) => {
          const err = path.join(c.home, 'overlap-err.txt');
          const deadline = Date.now() + scaledMs(20000);
          let stderr = '';
          while (Date.now() < deadline) {
            stderr = readOr(err, '');
            if (stderr.split('\n').some((s) => s.startsWith('AIKIT-XAI '))) break;
            Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 50);
          }
          const status = statusLineOk(stderr, /^AIKIT-XAI status=ok cli=pi model=fake\/slowok exit=0 cli_rc=0 elapsed=\d+s out=\d+ tree=dirty action=stop$/);
          if (status) return `background: ${status}`;
          const code = await c.overlapExit;
          if (code !== 0) return `background exit ${code}`;
          if (!r.stdout.includes('# Summary') || !readOr(path.join(c.home, 'overlap-out.txt'), '').includes('# Summary')) return 'missing summary';
          if (!hostedUsable(c)) return hostFailedOnly(r, c) || hostFailedOnly({ stderr }, c);
          const labels = [r.stderr, stderr].map((text) => /cross-ai: host herdr tab=\S+ label=(\S+)/.exec(text)?.[1]);
          if (!labels[0] || !labels[1] || labels[0] === labels[1]) return 'host labels missing or equal';
          return hostLogProblem(c, 2);
        },
      },
      {
        name: 'host-signal-guard', kind: 'logic',
        pure: () => {
          const rows = [[100, '5', '5', 100, true], [100, '5', '6', 100, false], [100, '-', '-', 100, false], [100, '5', '5', 99, false], [100, '5', '-', 100, false]];
          for (const [pid, recorded, current, group, expected] of rows) if (launcherVerified(pid, recorded, current, group) !== expected) return `wrong signal guard row: ${[pid, recorded, current, group]}`;
          return null;
        },
      },
      {
        name: 'host-signal', kind: 'runtime',
        args: ['--runtime', 'pi', '--model', 'fake/hang', '--timeout', '60', '--host', 'auto'],
        env: { HERDR_ENV: '1', PATH: hostedPath },
        signal: { when: (c) => fs.existsSync(path.join(c.repo, 'gc.pid')), sig: 'SIGTERM', withinMs: SELF_TEST_SIGNAL_EXIT_MS },
        exit: 143, status: /^AIKIT-XAI status=signal cli=pi model=fake\/hang exit=143 .* action=stop$/,
        check: (r, c) => deadCheck(c, ['pi', 'gc']) || (hostedUsable(c) ? hostLogProblem(c, 1) : hostFailedOnly(r, c)),
      },
      ...[
        { name: 'host-failed-run', kind: 'runtime', fail: 'run', count: 1, message: 'pane run failed (exit 1); the lane runs headless', close: true },
        { name: 'host-run-error-started', kind: 'runtime', fail: 'run-after', count: 1, started: true },
        { name: 'host-run-unclear', kind: 'runtime', fail: 'run-lost', count: 0, message: 'pane run answer unclear (signal SIGKILL); the lane may have started, so it is not rerun', close: true },
        { name: 'host-no-pid', kind: 'runtime', fail: 'nolaunch', count: 0, message: 'the launcher wrote no pid within 5000 ms; not rerun', close: true },
        { name: 'host-create-refused', kind: 'logic', fail: 'create', count: 1, message: 'tab create failed (exit 1); the lane runs headless', noRun: true },
        { name: 'host-create-lost', kind: 'logic', fail: 'create-lost', count: 1, message: 'tab create answer lost (no tab id in its answer); kept the run record for the sweep; the lane runs headless', noRun: true },
      ].map((test) => (hostedHere ? test : { ...test, count: 1 })).map((test) => ({
        name: test.name, kind: test.kind,
        args: ['--runtime', 'pi', '--model', 'fake/ok', '--host', 'auto'],
        env: { HERDR_ENV: '1', PATH: hostedPath, FAKE_HERDR_FAIL: test.fail },
        exit: test.count ? 0 : 1,
        status: test.count ? /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 cli_rc=0 elapsed=\d+s out=\d+ tree=dirty action=stop$/ : /^AIKIT-XAI status=crash cli=pi model=fake\/ok exit=1 cli_rc=- elapsed=\d+s out=\d+ tree=clean action=stop$/,
        check: (r, c) => {
          const count = c.calls.filter((s) => s === 'pi ok').length;
          if (count !== test.count) return `pi ok calls ${count}`;
          if (!hostedUsable(c)) return hostFailedOnly(r, c);
          if (test.message && !r.stderr.includes(`cross-ai: host: ${test.message}`)) return 'missing host message';
          if (test.fail === 'run') {
            if (!r.stderr.includes('cross-ai: setting host=herdr ignored reason=host_failed')) return 'missing host_failed';
            const line = r.stderr.split('\n').filter((s) => s.startsWith('AIKIT-XAI ')).at(-1) || '';
            const ignored = (/ ignored=(\S+)/.exec(line)?.[1] || '').split(',');
            const applied = (/ applied=(\S+)/.exec(line)?.[1] || '').split(',');
            if (!ignored.includes('host') || applied.includes('host')) return 'status host lists';
          }
          if (test.started && (!r.stderr.includes('cross-ai: setting host=herdr applied') || r.stderr.includes('host_failed'))) return 'started host setting';
          const calls = hostCalls(c);
          const safety = hostSafety(calls); if (safety) return safety;
          if (test.close && !calls.some((a) => JSON.stringify(a) === '["tab","close","t1"]')) return 'missing close';
          if (test.noRun && calls.some((a) => ['pane run', 'tab close'].includes(a.slice(0, 2).join(' ')))) return 'unexpected run or close';
          if (test.started) return hostLogProblem(c, 1);
          if (test.fail === 'nolaunch') { const records = keptRecords(c); if (!Array.isArray(records) || records.length) return 'host records remain'; }
          if (test.fail === 'create-lost') {
            const records = keptRecords(c);
            if (!Array.isArray(records) || records.length !== 1 || records[0].tab_id !== null || !records[0].label.startsWith('aikit:execute:pi:')) return 'lost create record';
            if (fakeTabs(c).t1?.closed !== false) return 'lost create tab';
          }
          return null;
        },
      })),
      {
        name: 'host-dead-launcher', kind: 'runtime',
        args: ['--runtime', 'pi', '--model', 'fake/killparent', '--host', 'auto'],
        env: { HERDR_ENV: '1', PATH: hostedPath, FAKE_HERDR_FAIL: 'close' }, exit: 1,
        status: /^AIKIT-XAI status=crash cli=pi model=fake\/killparent exit=1 cli_rc=\S+ elapsed=\d+s out=\d+ tree=.* action=stop$/,
        second: { exit: 1, status: /^AIKIT-XAI status=crash cli=pi model=fake\/killparent exit=1 cli_rc=\S+ elapsed=\d+s out=\d+ tree=.* action=stop$/ },
        check: (both, c) => {
          for (const calls of [both.calls1, both.calls2]) if (calls.filter((s) => s === 'pi killparent').length !== 1) return 'killparent call count';
          if (!hostedUsable(c)) return hostFailedOnly(both.first, c);
          const status = statusLineOk(both.first.stderr, /^AIKIT-XAI status=crash cli=pi model=fake\/killparent exit=1 cli_rc=\S+ elapsed=\d+s out=\d+ tree=.* action=stop$/);
          if (status) return `first: ${status}`;
          const labels = [];
          for (const [i, r] of [both.first, both.again].entries()) {
            const id = `t${i + 1}`;
            if (!r.stderr.includes(' cli_rc=- ') || !r.stderr.includes('failed (exit null SIGKILL')) return 'dead launcher status';
            if (!r.stderr.includes(`cross-ai: host: tab close ${id} failed (exit 1)`)) return 'close failure missing';
            if (!r.stderr.split('\n').some((s) => s.startsWith('cross-ai: host: kept ') && s.endsWith(`/run.json for tab ${id} (close not confirmed)`))) return 'kept message missing';
            labels.push(r.stderr.split('\n').find((s) => s.startsWith('cross-ai: host herdr tab='))?.split(' label=')[1]);
          }
          if (!labels[0] || !labels[1] || labels[0] === labels[1]) return 'labels not distinct';
          const safety = hostSafety(hostCalls(c)); if (safety) return safety;
          const records = keptRecords(c);
          if (!Array.isArray(records) || records.length !== 2 || records[0].tab_id !== 't1' || records[1].tab_id !== 't2') return 'dead launcher records';
          const tabs = fakeTabs(c);
          return tabs.t1?.closed === false && tabs.t2?.closed === false ? null : 'dead launcher tabs';
        },
      },
      {
        // 38 D-22 (backlog 999.21): ok, failure, signal and timeout exits each leave no runner temp folder in the case TMPDIR.
        name: 'temp-dirs-gone',
        kind: 'runtime',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 cli_rc=0 elapsed=\d+s out=\d+ tree=dirty action=stop$/,
        check: async (_r, ctx) => {
          const left = () => fs.readdirSync(ctx.tmpdir).filter((n) => n.startsWith('cross-ai-') || n.startsWith('xai-idx-'));
          let names = left();
          if (names.length) return `ok run left ${names.join(',')}`;
          const gcPid = path.join(ctx.repo, 'gc.pid');
          const runs = [
            ['failure', 69, /^AIKIT-XAI status=auth cli=pi model=fake\/auth exit=69 .* action=stop$/, false, { args: ['--prefer', 'pi', '--model-pi', 'fake/auth'] }],
            ['signal', 143, /^AIKIT-XAI status=signal cli=pi model=fake\/hang exit=143 .* action=stop$/, true, { args: ['--prefer', 'pi', '--model-pi', 'fake/hang', '--timeout', '60'], signal: { when: (cc) => fs.existsSync(path.join(cc.repo, 'gc.pid')), sig: 'SIGTERM' } }],
            ['timeout', 124, /^AIKIT-XAI status=timeout cli=pi model=fake\/hang exit=124 .* action=stop$/, true, { args: ['--prefer', 'pi', '--model-pi', 'fake/hang', '--timeout', '2'] }],
          ];
          for (const [label, want, status, started, spec] of runs) {
            fs.rmSync(gcPid, { force: true });
            const got = await runCaseProcess(spec, ctx);
            if (got.reason) return `${label}: ${got.reason}`;
            if (got.status !== want) return `${label} exit ${got.status} expected ${want}`;
            const bad = statusLineOk(got.stderr || '', status);
            if (bad) return `${label}: ${bad}`;
            if (started && !fs.existsSync(gcPid)) return `${label}: the fake lane never started`;
            names = left();
            if (names.length) return `${label} run left ${names.join(',')}`;
          }
          return null;
        },
      },
      {
        name: 'pure-idle-plan', kind: 'logic', pure: () => {
          const off = { idleS: 0, checkS: 0, pollTree: false, notices: [] };
          const under = 'cross-ai: note: idle timeout 1s is under 60s; a slow, quiet model may be ended';
          const budget = (s, b) => `cross-ai: note: idle timeout ${s}s is not below the attempt budget of ${b}s; it cannot fire before the deadline`;
          const on = (s, tree, notices = []) => ({ idleS: s, checkS: Math.min(60, Math.max(1, Math.floor(s / 10))), pollTree: tree, notices });
          const rows = [
            [null, {}, 'execute', 1740000, off], [null, { idleTimeoutS: 0 }, 'execute', 1740000, off],
            ['default', {}, 'execute', 1740000, on(900, true)], ['default', {}, 'review', 1740000, on(900, false)],
            [0, { idleTimeoutS: 300 }, 'execute', 1740000, off], [null, { idleTimeoutS: 300 }, 'execute', 1740000, on(300, true)],
            [120, { idleTimeoutS: 300 }, 'review', 1740000, on(120, false)], [1, {}, 'execute', 1740000, on(1, true, [under])],
            [86400, {}, 'execute', 1740000, on(86400, true, [budget(86400, 1740)])],
            [1740, {}, 'execute', 1740000, on(1740, true, [budget(1740, 1740)])], [1739, {}, 'execute', 1740000, on(1739, true)],
            [30, {}, 'execute', 20000, on(30, true, ['cross-ai: note: idle timeout 30s is under 60s; a slow, quiet model may be ended', budget(30, 20)])],
            [86400, {}, 'execute', null, on(86400, true)], [1740, {}, 'execute', 1740500, on(1740, true)],
          ];
          for (const bad of [-5, 1.5, 86401, '300', 'default', true]) {
            rows.push([null, { idleTimeoutS: bad }, 'execute', 1740000, { ...off, notices: ['cross-ai: note: CONFIG.idleTimeoutS is not an integer from 0 to 86400; the idle watchdog is off'] }]);
            rows.push([120, { idleTimeoutS: bad }, 'execute', 1740000, on(120, true)]);
          }
          for (const [i, [idleTimeout, config, role, budgetMs, expected]] of rows.entries()) {
            if (JSON.stringify(planIdle({ idleTimeout, budgetMs }, config, role)) !== JSON.stringify(expected)) return `plan ${i + 1}`;
          }
          if (IDLE_DEFAULT_S !== 900 || IDLE_MAX_S !== 86400) return 'constants';
          return idleBudgetNote(1740, 1740999) === budget(1740, 1740) ? null : 'budget note';
        },
      },
      {
        name: 'idle-print-off', kind: 'logic', args: ['--print-argv', '--runtime', 'pi', '--model', 'fake/ok', '--outer-timeout', '1830'], exit: 0, status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        async check (r, ctx) {
          const b = await runCaseProcess({ args: ['--print-argv', '--runtime', 'pi', '--model', 'fake/ok'] }, ctx);
          for (const x of [r, b]) {
            const lines = (x.stderr || '').split('\n');
            if (x.status !== 0 || lines.filter(s => s === 'cross-ai: idle watchdog off').length !== 1 || lines.some(s => s.startsWith('cross-ai: idle watchdog on') || s.startsWith('cross-ai: note: idle timeout'))) return 'off line';
          }
          return null;
        },
      },
      {
        name: 'pure-idle-parse', kind: 'logic', pure: () => {
          for (const [s, expected] of [['1', 1], ['86400', 86400], ['0', 0], ['007', 7], ['default', 'default']]) if (parseArgs(['--idle-timeout', s]).idleTimeout !== expected) return `valid ${s}`;
          if (parseArgs([]).idleTimeout !== null) return 'default';
          for (const s of ['86401', '-1', '', '1.5', 'abc', ' 5', '0x10', '1e3', '+5', '５', 'Default', '99999999999999999999']) {
            try { parseArgs(['--idle-timeout', s]); return `accepted ${s}`; } catch (e) { if (e.message !== '--idle-timeout must be an integer from 0 to 86400 or default') return `error ${s}`; }
          }
          try { parseArgs(['--idle-timeout']); return 'missing accepted'; } catch (e) { return e.message === '--idle-timeout needs a value' ? null : 'missing error'; }
        },
      },
      {
        name: 'idle-print-default', kind: 'logic', args: ['--print-argv', '--runtime', 'pi', '--model', 'fake/ok', '--outer-timeout', '1830', '--idle-timeout', 'default'], exit: 0, status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        async check (r, ctx) {
          const lines = (r.stderr || '').split('\n');
          if (lines.filter(s => s === 'cross-ai: idle watchdog on timeout=900s').length !== 1 || lines.includes('cross-ai: idle watchdog off') || lines.some(s => s.startsWith('cross-ai: note: idle timeout') || s.startsWith('cross-ai: setting idle'))) return 'on line';
          const b = await runCaseProcess({ args: ['--print-argv', '--runtime', 'pi', '--model', 'fake/ok', '--outer-timeout', '1830'] }, ctx);
          const line = x => (x.stdout || '').split('\n').find(s => s.startsWith('pi\t'));
          return b.status === 0 && line(r) && line(r) === line(b) ? null : 'argv changed';
        },
      },
      {
        name: 'idle-print-config', kind: 'logic', config: { idleTimeoutS: 300 }, args: ['--print-argv', '--runtime', 'pi', '--model', 'fake/ok', '--outer-timeout', '1830'], exit: 0, status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        second: { args: ['--print-argv', '--runtime', 'pi', '--model', 'fake/ok', '--outer-timeout', '1830', '--idle-timeout', '0'], exit: 0, status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/ },
        check: both => (both.first.stderr || '').split('\n').includes('cross-ai: idle watchdog on timeout=300s') && (both.again.stderr || '').split('\n').includes('cross-ai: idle watchdog off') ? null : 'config precedence',
      },
      {
        name: 'idle-print-notices', kind: 'logic', args: ['--print-argv', '--runtime', 'pi', '--model', 'fake/ok', '--outer-timeout', '300', '--idle-timeout', '210'], exit: 0, status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        async check (r, ctx) {
          const lines = (r.stderr || '').split('\n');
          if (!lines.includes('cross-ai: deadline 270s (outer 300s)') || !lines.includes('cross-ai: note: idle timeout 210s is not below the attempt budget of 210s; it cannot fire before the deadline') || !lines.includes('cross-ai: idle watchdog on timeout=210s') || lines.some(s => s.includes('under 60s'))) return 'budget note';
          const run = extra => runCaseProcess({ args: ['--print-argv', '--runtime', 'pi', '--model', 'fake/ok', ...extra] }, ctx);
          const b = await run(['--outer-timeout', '300', '--idle-timeout', '209']);
          if (b.status !== 0 || (b.stderr || '').split('\n').some(s => s.startsWith('cross-ai: note: idle timeout'))) return 'below budget';
          const c = await run(['--idle-timeout', '59', '--outer-timeout', '1830']);
          const notes = (c.stderr || '').split('\n').filter(s => s.startsWith('cross-ai: note: idle timeout'));
          if (c.status !== 0 || JSON.stringify(notes) !== JSON.stringify(['cross-ai: note: idle timeout 59s is under 60s; a slow, quiet model may be ended'])) return 'short note';
          const d = await run(['--idle-timeout', '1.5']);
          return d.status === 2 && (d.stderr || '').split('\n').includes('cross-ai: --idle-timeout must be an integer from 0 to 86400 or default') ? null : 'invalid';
        },
      },
      {
        name: 'idle-silent-ended', kind: 'runtime',
        args: ['--runtime', 'pi', '--model', 'fake/hang', '--timeout', '20', '--idle-timeout', '2'],
        config: { heartbeatS: 1 }, exit: 124,
        status: /^AIKIT-XAI status=timeout cli=pi model=fake\/hang exit=124 cli_rc=.* elapsed=\d+s out=\d+ tree=.* action=stop$/,
        check: (r, ctx) => {
          const lines = (r.stderr || '').split('\n');
          if (lines.filter((s) => s === 'cross-ai: idle watchdog: pi printed nothing for 2s; ending its process group').length !== 1) return 'idle line';
          if (!lines.some((s) => s.startsWith('cross-ai: pi running '))) return 'heartbeat';
          if (lines.filter((s) => /^cross-ai: attempt n=1 rung=first cycle=0 session=\S+ status=timeout rule=idle-watchdog pattern=- at=\S+ took=\d+s$/.test(s)).length !== 1) return 'attempt line';
          if (!lines.includes('cross-ai: idle watchdog on timeout=2s')) return 'on line';
          const calls = ctx.calls.filter((s) => s.startsWith('pi ') && s !== 'pi rpc');
          if (calls.length !== 1 || calls[0] !== 'pi hang') return `calls ${calls.join('|')}`;
          return deadCheck(ctx, ['gc']);
        },
      },
      {
        name: 'idle-keeps-printing', kind: 'runtime',
        args: ['--runtime', 'pi', '--model', 'fake/ticker', '--outer-timeout', '1830', '--idle-timeout', '2'],
        exit: 0, status: /^AIKIT-XAI status=ok cli=pi model=fake\/ticker exit=0 .* action=stop$/,
        check: (r, ctx) => {
          if ((r.stderr || '').split('\n').some((s) => s.startsWith('cross-ai: idle watchdog:'))) return 'idle fired';
          const calls = ctx.calls.filter((s) => s.startsWith('pi ') && s !== 'pi rpc');
          return calls.length === 1 && calls[0] === 'pi ticker' ? null : `calls ${calls.join('|')}`;
        },
      },
      {
        name: 'idle-slow-quiet-default', kind: 'runtime',
        args: ['--runtime', 'pi', '--model', 'fake/slowok', '--outer-timeout', '1830', '--idle-timeout', 'default'],
        exit: 0, status: /^AIKIT-XAI status=ok cli=pi model=fake\/slowok exit=0 .* action=stop$/,
        check: (r, ctx) => {
          const lines = (r.stderr || '').split('\n');
          if (!lines.includes('cross-ai: idle watchdog on timeout=900s')) return 'missing on line';
          if (lines.some((s) => s.startsWith('cross-ai: idle watchdog:'))) return 'idle fired';
          const calls = ctx.calls.filter((s) => s.startsWith('pi ') && s !== 'pi rpc');
          return calls.length === 1 && calls[0] === 'pi slowok' ? null : `calls ${calls.join('|')}`;
        },
      },
      {
        name: 'idle-off-never-fires', kind: 'runtime', config: { idleTimeoutS: 0 },
        args: ['--runtime', 'pi', '--model', 'fake/hang', '--timeout', '4'],
        exit: 124, status: /^AIKIT-XAI status=timeout cli=pi model=fake\/hang exit=124 .* action=stop$/,
        check: (r, ctx) => {
          const lines = (r.stderr || '').split('\n');
          if (lines.some((s) => s.startsWith('cross-ai: idle watchdog'))) return 'idle line';
          if (lines.filter((s) => /^cross-ai: attempt n=1 rung=first cycle=0 session=\S+ status=timeout rule=- /.test(s)).length !== 1) return 'attempt line';
          return deadCheck(ctx, ['gc']);
        },
      },
      {
        name: 'idle-then-resume', kind: 'runtime', config: { backoffS: [0, 0] },
        args: ['--runtime', 'pi', '--model', 'fake/hangonce', '--timeout', '120', '--idle-timeout', '2'],
        exit: 0, status: /^AIKIT-XAI status=ok cli=pi model=fake\/hangonce exit=0 .* action=stop$/,
        check: (r, ctx) => {
          const lines = (r.stderr || '').split('\n');
          if (lines.filter((s) => s === 'cross-ai: idle watchdog: pi printed nothing for 2s; ending its process group').length !== 1) return 'idle line';
          if (!lines.some((s) => /^cross-ai: attempt n=1 rung=first cycle=0 session=\S+ status=timeout rule=idle-watchdog pattern=- /.test(s))) return 'attempt line';
          if (!lines.includes('cross-ai: ladder pi next=same why=soft-retry')) return 'ladder line';
          if (!lines.some((s) => s.startsWith('cross-ai: wait ms=0 next=same retry=1'))) return 'wait line';
          const calls = ctx.calls.filter(Boolean);
          if (calls.some((s) => s !== 'pi rpc' && s !== 'pi hangonce') || calls.filter((s) => s === 'pi hangonce').length !== 2) return `calls ${calls.join('|')}`;
          const rows = readOr(ctx.env.FAKE_SIDS, '').trim().split('\n').filter(Boolean).map((l) => l.split(' ')).filter((row) => row[0]);
          if (rows.length !== 2 || rows[0][0] !== rows[1][0] || rows[0][1] !== 'prompt' || rows[1][1] !== 'resume') return `sessions ${JSON.stringify(rows)}`;
          return deadCheck(ctx, ['pi']);
        },
      },
      {
        name: 'idle-loses-to-deadline', kind: 'runtime',
        args: ['--runtime', 'pi', '--model', 'fake/hang', '--timeout', '2', '--idle-timeout', '5'],
        exit: 124, status: /^AIKIT-XAI status=timeout cli=pi model=fake\/hang exit=124 .* action=stop$/,
        check: (r, ctx) => {
          const lines = (r.stderr || '').split('\n');
          if (!lines.some((s) => /^cross-ai: note: idle timeout 5s is not below the attempt budget of \d+s; it cannot fire before the deadline$/.test(s))) return 'budget note';
          if (!lines.includes('cross-ai: note: idle timeout 5s is under 60s; a slow, quiet model may be ended')) return 'short note';
          if (lines.some((s) => s.startsWith('cross-ai: idle watchdog:') || s.includes('rule=idle-watchdog'))) return 'idle fired';
          return deadCheck(ctx, ['gc']);
        },
      },
      {
        name: 'idle-loses-to-limit', kind: 'runtime',
        args: ['--runtime', 'pi', '--model', 'fake/limit-mid', '--timeout', '60', '--idle-timeout', '1'],
        exit: 75, status: /^AIKIT-XAI status=quota cli=pi model=fake\/limit-mid exit=75 .* action=stop$/,
        check: (r, ctx) => {
          if ((r.stderr || '').split('\n').some((s) => s.startsWith('cross-ai: idle watchdog:') || s.includes('rule=idle-watchdog'))) return 'idle fired';
          return deadCheck(ctx, ['pi']);
        },
      },
      {
        name: 'idle-loses-to-signal', kind: 'runtime',
        args: ['--runtime', 'pi', '--model', 'fake/hang', '--timeout', '60', '--idle-timeout', '5'],
        signal: { when: (c) => fs.existsSync(path.join(c.repo, 'gc.pid')), sig: 'SIGTERM' },
        exit: 143, status: /^AIKIT-XAI status=signal cli=pi model=fake\/hang exit=143 .* tree=dirty action=stop$/,
        check: (r, ctx) => {
          if ((r.stderr || '').split('\n').some((s) => s.startsWith('cross-ai: idle watchdog:') || s.includes('rule=idle-watchdog'))) return 'idle fired';
          return deadCheck(ctx, ['gc']);
        },
      },
      {
        name: 'check-group-no-spawn', kind: 'logic',
        args: ['--print-argv', '--runtime', 'pi', '--model', 'fake/ok'], exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const lines = (r.stderr || '').split('\n').filter(Boolean);
          if (!lines.at(-1).endsWith(' escalate=- coverage=- findings=-')) return 'group';
          const tail = statusTail(r.stderr);
          if (tail?.coverage !== '-' || tail.findings !== '-') return 'tail';
          return lines.some((line) => line.startsWith('cross-ai: finding ')) ? 'finding line' : null;
        },
      },
      {
        name: 'pure-finding-format', kind: 'logic', pure: () => {
          try {
            if (JSON.stringify(FINDING_CODES) !== JSON.stringify(['no_commit', 'task_uncovered', 'admits_skipped', 'forbidden_path', 'no_tree_change', 'outside_plan_files', 'uncommitted_edits', 'baseline_replaced', 'coverage_unchecked'])) return 'codes';
            for (const coverage of ['-', '3/3', 'n/a']) if (checkGroup({ coverage, findings: [] }) !== `coverage=${coverage} findings=-`) return 'coverage';
            for (const coverage of ['1/3 x', '0.5', '1/3/4']) if (checkGroup({ coverage, findings: [] }) !== 'coverage=- findings=-') return 'invalid coverage';
            const check = { coverage: '1/3', findings: [{ code: 'outside_plan_files', detail: '2 paths' }, { code: 'task_uncovered', detail: ['b', 'a', 'b'] }, { code: 'outside_plan_files', detail: 'x' }] };
            if (checkGroup(check) !== 'coverage=1/3 findings=task_uncovered,outside_plan_files') return 'group order';
            if (JSON.stringify(findingLines(check)) !== JSON.stringify(['cross-ai: finding reason=task_uncovered detail=a, b', 'cross-ai: finding reason=outside_plan_files detail=2 paths', 'cross-ai: finding reason=outside_plan_files detail=x'])) return 'line order';
            const items = Array.from({ length: 12 }, (_, i) => `p${String(i + 1).padStart(2, '0')}`);
            if (findingDetail(items.slice(0, 10)) !== items.slice(0, 10).join(', ')) return 'cap 10';
            if (findingDetail(items.slice(0, 11)) !== `${items.slice(0, 10).join(', ')} (+1 more)`) return 'cap 11';
            if (findingDetail(items.toReversed()) !== `${items.slice(0, 10).join(', ')} (+2 more)`) return 'cap 12';
            if (['', [], undefined].some((v) => findingDetail(v) !== '-')) return 'empty';
            if (findingDetail('a\x07b\x9bc') !== 'abc' || findingDetail('a\u2028b\u2029c') !== 'abc') return 'controls';
            const key = 'sk-' + 'a'.repeat(16);
            if ([key, '\x07' + key, 'sk-' + 'a'.repeat(4) + '\x07' + 'a'.repeat(12)].some((v) => findingDetail(v) !== '<redacted>')) return 'redact';
            const array = findingDetail(['src/x.ts', '\x07' + key]);
            if (array.includes('sk-') || !array.includes('<redacted>')) return 'redact array';
            addFinding('no_commit', 'x');
            if (JSON.stringify(liveCheck.findings.at(-1)) !== JSON.stringify({ code: 'no_commit', detail: 'x' })) return 'add';
            const count = liveCheck.findings.length;
            try { addFinding('made_up', 'x'); return 'unknown accepted'; } catch (e) { if (e.message !== 'unknown finding code: made_up') return 'unknown error'; }
            if (liveCheck.findings.length !== count) return 'unknown added';
            return null;
          } finally { liveCheck.findings.splice(0); }
        },
      },
      {
        name: 'pure-status-head-re', kind: 'logic', pure: () => {
          const head = 'AIKIT-XAI status=quota cli=pi model=fake/ok exit=75 cli_rc=1 elapsed=1s out=0 tree=clean action=stop route=unknown rule=- pattern=none attempts=1 cycles=0 session=- applied=model ignored=- unknown=- escalate=-';
          const retry = ' retry_after_s=600 cycle=0';
          const line = head + ' coverage=- findings=-' + retry;
          const parts = STATUS_HEAD_RE.exec(line);
          if (parts?.[5] !== 'coverage=- findings=-' || parts[6] !== 'retry_after_s=600 cycle=0') return 'groups';
          const tail = statusTail(line + '\n');
          if (tail?.retry_after_s !== '600' || tail.cycle !== '0' || tail.coverage !== '-' || tail.findings !== '-' || tail.escalate !== '-') return 'tail';
          const old = STATUS_HEAD_RE.exec(head + retry);
          const oldTail = statusTail(head + retry + '\n');
          if (!old || old[5] !== undefined || old[6] !== 'retry_after_s=600 cycle=0' || oldTail?.retry_after_s !== '600' || oldTail.coverage !== undefined) return 'old';
          const populated = statusTail(head + ' coverage=1/3 findings=task_uncovered,outside_plan_files\n');
          return populated?.coverage === '1/3' && populated.findings === 'task_uncovered,outside_plan_files' ? null : 'populated';
        },
      },
      {
        name: 'finding-lines-through-finish', kind: 'logic',
        args: ['--print-argv', '--runtime', 'pi', '--model', 'fake/ok'], exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r, ctx) => {
          const script = "const m = await import(process.argv[2]); m.addFinding('task_uncovered', ['b', 'a']); m.addFinding('no_commit', 'x'); m.finish('crash', { exit: 1 });";
          const child = spawnSync(process.execPath, ['--input-type=module', '-e', script, ctx.repo, pathToFileURL(RUNNER_FILE).href], { cwd: ctx.repo, env: ctx.env, encoding: 'utf8', timeout: scaledMs(20000) });
          const lines = (child.stderr || '').split('\n').filter(Boolean);
          if (child.status !== 0 || lines.length !== 3) return 'lines';
          if (lines[0] !== 'cross-ai: finding reason=no_commit detail=x' || lines[1] !== 'cross-ai: finding reason=task_uncovered detail=a, b') return 'order';
          return lines[2].startsWith('AIKIT-XAI status=crash ') && lines[2].endsWith(' escalate=- coverage=- findings=no_commit,task_uncovered') ? null : 'trailer';
        },
      },
      {
        name: 'lock-held-refuses', kind: 'logic',
        args: ['--runtime', 'pi', '--model', 'fake/ok'], exit: 75,
        status: /^AIKIT-XAI status=locked cli=pi model=fake\/ok exit=75 cli_rc=- elapsed=\d+s out=0 tree=clean action=stop$/,
        setup: (c) => plantLiveLock(c),
        check: (r, c) => {
          if (!r.stderr.split('\n').includes(`cross-ai: run lock held by pid ${process.pid} (lane pi/fake/planted, since 2026-11-21T00:00:00.000Z); not starting`)) return 'missing held line';
          if (r.stderr.split('\n').find((line) => line.startsWith('AIKIT-XAI ')).includes('retry_after_s=')) return 'retry_after_s printed';
          if (c.calls.length) return 'lane or listing called';
          return plantedUnchanged(c) ? null : 'planted record changed';
        },
      },
      {
        name: 'lock-gone-after-failure', kind: 'logic',
        args: ['--runtime', 'pi', '--model', 'fake/empty'], exit: 1,
        status: /^AIKIT-XAI status=empty_answer cli=pi model=fake\/empty exit=1 .* action=stop$/,
        check: (r, c) => {
          const dir = path.join(c.env.XDG_STATE_HOME, 'ai-kit', 'spec', 'locks');
          if (!fs.existsSync(dir)) return 'no locks folder';
          const names = fs.readdirSync(dir).filter((name) => name.endsWith('.json'));
          return names.length ? `lock left: ${names.join(',')}` : null;
        },
      },
      {
        name: 'lock-held-redacts', kind: 'logic',
        args: ['--runtime', 'pi', '--model', 'fake/ok'], exit: 75,
        status: /^AIKIT-XAI status=locked .* action=stop$/,
        setup: (c) => plantLock(c, { model: 'fake/x\u0007' + c.env.AIKIT_XAI_SENTINEL }),
        check: (r, c) => {
          const line = r.stderr.split('\n').find((s) => s.startsWith('cross-ai: run lock held by pid '));
          if (!line) return 'missing held line';
          if (line.includes(c.env.AIKIT_XAI_SENTINEL) || line.includes('\u0007')) return 'key reached the held line';
          if (c.calls.length) return 'lane or listing called';
          return plantedUnchanged(c) ? null : 'planted record changed';
        },
      },
      {
        name: 'lock-not-taken', kind: 'logic',
        args: ['--runtime', 'pi', '--model', 'fake/ok'], exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
        setup: (c) => { c.env.XDG_STATE_HOME = path.join(c.home, 'state-file'); fs.writeFileSync(c.env.XDG_STATE_HOME, ''); return null; },
        check: (r) => r.stderr.split('\n').filter((line) => line === 'cross-ai: run lock not taken (ENOTDIR); running without a lock').length === 1 ? null : 'missing not-taken line',
      },
      {
        name: 'lock-late-usage-no-lock', kind: 'logic',
        args: ['--mode', 'review', '--runtime', 'pi', '--model', 'fake/review-ok'],
        config: { extraArgs: { pi: ['--tools', 'bash'] } }, exit: 2,
        status: /^AIKIT-XAI status=usage .* action=stop$/,
        setup: (c) => plantLiveLock(c),
        check: (r, c) => {
          if (!r.stderr.includes('review argv for pi holds --tools')) return 'missing review argv refusal';
          if (c.calls.length) return 'lane or listing called';
          return plantedUnchanged(c) ? null : 'planted record changed';
        },
      },
      {
        name: 'lock-record-fields', kind: 'logic',
        args: ['--runtime', 'pi', '--model', 'fake/lockpeek'], exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/lockpeek exit=0 .* tree=dirty action=stop$/,
        check: (r, c) => {
          const file = path.join(c.home, 'lock.seen');
          if (!fs.existsSync(file)) return 'lock.seen missing';
          const seen = JSON.parse(fs.readFileSync(file, 'utf8'));
          const rec = seen.rec || {};
          const checks = { names: JSON.stringify(seen.names) === JSON.stringify([path.basename(lockPath(fs.realpathSync(c.repo), c.env.XDG_STATE_HOME))]),
            dir: seen.dir === '700', file: seen.file === '600', version: rec.version === 1,
            run_id: typeof rec.run_id === 'string' && !!rec.run_id, pid: Number.isInteger(rec.pid),
            pid_start: /^(\d+|-)$/.test(rec.pid_start), host_name: rec.host_name === os.hostname(),
            started_ms: Number.isInteger(rec.started_ms), cli: rec.cli === 'pi', model: rec.model === 'fake/lockpeek',
            role: rec.role === 'execute', root: rec.root === fs.realpathSync(c.repo), child_pgid: rec.child_pgid === seen.pgid,
            child_start: /^(\d+|-)$/.test(rec.child_start), baseline: rec.baseline === null };
          for (const [name, ok] of Object.entries(checks)) if (!ok) return `lock field ${name}: ${JSON.stringify(rec[name] ?? seen[name])}`;
          const names = fs.readdirSync(path.dirname(lockPath(fs.realpathSync(c.repo), c.env.XDG_STATE_HOME))).filter((n) => n.endsWith('.json'));
          return names.length ? `lock left: ${names.join(',')}` : null;
        },
      },
      {
        name: 'lock-gone-after-signal', kind: 'runtime',
        args: ['--runtime', 'pi', '--model', 'fake/hang', '--timeout', '60'],
        signal: { when: (c) => fs.existsSync(path.join(c.repo, 'gc.pid')), sig: 'SIGTERM' },
        exit: 143, status: /^AIKIT-XAI status=signal cli=pi model=fake\/hang exit=143 .* action=stop$/,
        check: (r, c) => {
          const dir = path.join(c.env.XDG_STATE_HOME, 'ai-kit', 'spec', 'locks');
          if (!fs.existsSync(dir)) return 'no locks folder';
          const names = fs.readdirSync(dir).filter((n) => n.endsWith('.json'));
          return names.length ? `lock left: ${names.join(',')}` : null;
        },
      },
      {
        name: 'lock-none-usage', kind: 'logic', args: ['--runtime', 'pi', '--model', 'fake/ok', '--no-such-flag'], exit: 2,
        status: /^AIKIT-XAI status=usage .* action=stop$/,
        check: (r, c) => fs.existsSync(path.join(c.env.XDG_STATE_HOME, 'ai-kit', 'spec', 'locks')) ? 'usage took a lock' : null,
      },
      {
        name: 'pure-lock-update-note', kind: 'logic', pure: () => {
          const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'xai-lockup-'));
          try {
            fs.writeFileSync(path.join(dir, 'f'), '');
            const lock = { file: path.join(dir, 'f', 'sub', 'l.json'), runId: 'r', record: {} };
            const { lines } = collectLog(() => { lockUpdate({ child_pgid: 4242 }, lock); lockUpdate({ child_pgid: 4242 }, lock); });
            return JSON.stringify(lines) === JSON.stringify(['cross-ai: note: run lock record not updated (ENOTDIR)']) ? null : `lines ${JSON.stringify(lines)}`;
          } finally { fs.rmSync(dir, { recursive: true, force: true }); }
        },
      },
      {
        name: 'lock-two-at-once', kind: 'runtime', args: ['--runtime', 'pi', '--model', 'fake/lockhold', '--print-argv'], exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: async (r, c) => {
          const dir = path.join(c.env.XDG_STATE_HOME, 'ai-kit', 'spec', 'locks');
          if (fs.existsSync(dir) && fs.readdirSync(dir).some((n) => n.endsWith('.json'))) return 'print-argv took a lock';
          const spec = { args: ['--runtime', 'pi', '--model', 'fake/lockhold'] };
          const runs = [runCaseProcess(spec, c), runCaseProcess(spec, c)];
          const first = await Promise.race(runs);
          fs.writeFileSync(path.join(c.home, 'lock-release'), '');
          const both = await Promise.all(runs);
          for (const run of both) if (run.reason) return `contender: ${run.reason}`;
          if (first.status !== 75) return `first to end exited ${first.status}`;
          const exits = both.map((run) => run.status).sort((a, b) => a - b);
          if (JSON.stringify(exits) !== '[0,75]') return `exits ${exits.join(',')}`;
          const winner = both.find((run) => run.status === 0);
          const loser = both.find((run) => run.status === 75);
          const win = statusLineOk(winner.stderr, /^AIKIT-XAI status=ok cli=pi model=fake\/lockhold exit=0 .* tree=dirty action=stop$/);
          if (win) return `winner: ${win}`;
          const lose = statusLineOk(loser.stderr, /^AIKIT-XAI status=locked cli=pi model=fake\/lockhold exit=75 .* action=stop$/);
          if (lose) return `loser: ${lose}`;
          if (!loser.stderr.split('\n').some((line) => /^cross-ai: run lock held by pid (\d+|-) \(lane .*, since .*\); not starting$/.test(line))) return 'missing held line';
          if (loser.stderr.includes('retry_after_s=')) return 'retry_after_s printed';
          const calls = readOr(path.join(c.tmp, 'calls-lock-two-at-once.log'), '').trim().split('\n').filter(Boolean);
          const held = calls.filter((line) => line === 'pi lockhold').length;
          const rpc = calls.filter((line) => line === 'pi rpc').length;
          if (held !== 1) return `pi lockhold calls ${held}`;
          if (rpc > 1) return `pi rpc calls ${rpc}`;
          const names = fs.readdirSync(dir).filter((n) => n.endsWith('.json'));
          return names.length ? `lock left: ${names.join(',')}` : null;
        },
      },
      {
        name: 'lock-review-note', kind: 'logic', args: ['--mode', 'review', '--runtime', 'pi', '--model', 'fake/review-ok'], exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/review-ok exit=0 .* tree=clean action=stop$/,
        setup: (c) => plantLiveLock(c),
        check: (r, c) => !r.stderr.split('\n').includes('cross-ai: note: an execute run holds this checkout; the tree check may void this review') ? 'missing review note' : plantedUnchanged(c) ? null : 'planted record changed',
      },
      {
        name: 'pure-lock-root', kind: 'logic', pure: () => {
          const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'xai-root-'));
          try {
            const genv = hermeticEnv(dir, { HOME: path.join(dir, 'h'), PATH: process.env.PATH });
            const repo = path.join(dir, 'r');
            const git = (cwd, args) => { const result = spawnSync('git', args, { cwd, env: genv }); if (result.status !== 0) throw new Error(`git ${args.join(' ')}: ${result.stderr}`); };
            git(dir, ['init', '-q', 'r']);
            fs.writeFileSync(path.join(repo, 'a.txt'), 'base');
            git(repo, ['add', 'a.txt']); git(repo, ['commit', '-q', '-m', 'init']);
            const wt = path.join(dir, 'wt');
            git(repo, ['worktree', 'add', '-q', wt]);
            fs.mkdirSync(path.join(repo, 'sub', 'deeper'), { recursive: true });
            fs.mkdirSync(path.join(wt, 'x'));
            fs.symlinkSync(path.join(repo, 'sub'), path.join(dir, 'link'));
            for (const [input, root] of [[path.join(repo, 'sub', 'deeper'), repo], [path.join(dir, 'link'), repo], [repo, repo], [path.join(wt, 'x'), wt]]) {
              const got = checkoutRoot(input);
              if (got !== fs.realpathSync(root)) return `root of ${input}: ${got}`;
            }
            return null;
          } finally { fs.rmSync(dir, { recursive: true, force: true }); }
        },
      },
    {
      name: 'pure-lock-verdict', kind: 'logic', pure: () => {
        const base = { run_id: 'r1', host_name: 'h1', pid: 4242, pid_start: '100', child_pgid: 4343, child_start: '200' };
        const probe = (o) => ({ host: 'h1', alive: () => o.alive, start: () => o.now, groupAlive: () => o.group });
        const rows = [
          ['foreign', { host_name: 'placeholder-host-1' }, {}, null, 'foreign'],
          ['alive', {}, { alive: true, now: '100' }, null, 'held'],
          ['unknown recorded', { pid_start: '-' }, { alive: true, now: '101' }, null, 'held'],
          ['unknown current', {}, { alive: true, now: '-' }, null, 'held'],
          ['reused', {}, { alive: true, now: '101', group: false }, null, 'stale'],
          ['orphan', {}, { alive: false, group: true }, null, 'orphan'],
          ['dead', {}, { alive: false, group: false }, null, 'stale'],
          ['own', {}, {}, 'r1', 'own'],
        ];
        for (const [name, overrides, options, own, expected] of rows) {
          const got = lockVerdict({ ...base, ...overrides }, probe(options), own);
          if (got !== expected) return `verdict ${name}: ${got}`;
        }
        return lockGroupAlive(null, null) || lockGroupAlive(1, null) ? 'verdict invalid group: alive' : null;
      },
    }, {
      name: 'lock-stale-cleared', kind: 'logic',
      args: ['--runtime', 'pi', '--model', 'fake/ok'], exit: 0,
      status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* tree=dirty action=stop$/,
      setup: (c) => { c.deadPid = deadPid(); return plantLock(c, { pid: c.deadPid, pid_start: '1', child_pgid: null }); },
      check: (r, c) => {
        if (!r.stderr.split('\n').includes(`cross-ai: stale run lock from pid ${c.deadPid} (since 2026-11-21T00:00:00.000Z) cleared`)) return 'missing stale line';
        const names = fs.readdirSync(path.dirname(c.lockFile)).filter((n) => n.endsWith('.json') || n.includes('.stale-'));
        return names.length ? `lock left: ${names.join(',')}` : null;
      },
    },
    {
      name: 'lock-orphan-refuses', kind: 'logic', args: ['--runtime', 'pi', '--model', 'fake/ok'], exit: 75,
      status: /^AIKIT-XAI status=locked cli=pi model=fake\/ok exit=75 .* action=stop$/,
      setup: (c) => {
        c.sleeper = spawn(process.execPath, ['-e', 'setTimeout(() => {}, 30000)'], { cwd: c.repo, detached: true, stdio: 'ignore' });
        caseRunners.add(c.sleeper);
        c.deadPid = deadPid();
        return plantLock(c, { pid: c.deadPid, pid_start: '1', child_pgid: c.sleeper.pid, child_start: procStartTime(c.sleeper.pid) });
      },
      check: (r, c) => {
        try { process.kill(-c.sleeper.pid, 'SIGKILL'); } catch { /* gone */ }
        caseRunners.delete(c.sleeper);
        if (!r.stderr.split('\n').includes(`cross-ai: run lock: pid ${c.deadPid} is gone but its child group ${c.sleeper.pid} still runs; not starting`)) return 'missing orphan line';
        return plantedUnchanged(c) ? null : 'planted record changed';
      },
    }, {
      name: 'lock-foreign-refuses', kind: 'logic', args: ['--runtime', 'pi', '--model', 'fake/ok'], exit: 75,
      status: /^AIKIT-XAI status=locked cli=pi model=fake\/ok exit=75 .* action=stop$/,
      setup: (c) => plantLock(c, { host_name: 'placeholder-host-1' }),
      check: (r, c) => {
        if (!r.stderr.split('\n').includes(`cross-ai: run lock held by pid ${process.pid} on host placeholder-host-1 (lane pi/fake/planted, since 2026-11-21T00:00:00.000Z); this host cannot probe it; not starting`)) return 'missing foreign line';
        return plantedUnchanged(c) ? null : 'planted record changed';
      },
    }, {
      name: 'lock-unreadable-refuses', kind: 'runtime', args: ['--runtime', 'pi', '--model', 'fake/ok'], exit: 75,
      status: /^AIKIT-XAI status=locked cli=pi model=fake\/ok exit=75 .* action=stop$/,
      setup: (c) => {
        c.lockFile = lockPath(fs.realpathSync(c.repo), c.env.XDG_STATE_HOME);
        fs.mkdirSync(path.dirname(c.lockFile), { recursive: true, mode: 0o700 });
        fs.writeFileSync(c.lockFile, '');
        const old = new Date(Date.now() - 10000); fs.utimesSync(c.lockFile, old, old);
        return null;
      },
      check: (r, c) => {
        const match = r.stderr.split('\n').map((line) => line.match(/^cross-ai: run lock record .*\.json is unreadable \(age (\d+)s\); not cleared; not starting$/)).find(Boolean);
        if (!match || Number(match[1]) < 10) return 'missing unreadable line';
        return fs.existsSync(c.lockFile) && fs.statSync(c.lockFile).size === 0 ? null : 'record removed';
      },
    }, {
      name: 'lock-invalid-refuses', kind: 'runtime', args: ['--runtime', 'pi', '--model', 'fake/ok'], exit: 75,
      status: /^AIKIT-XAI status=locked cli=pi model=fake\/ok exit=75 .* action=stop$/,
      setup: (c) => {
        c.lockFile = lockPath(fs.realpathSync(c.repo), c.env.XDG_STATE_HOME);
        writeCycleState(c.lockFile, { version: 1, host_name: os.hostname(), started_ms: 0 });
        c.planted = fs.readFileSync(c.lockFile); return null;
      },
      check: (r, c) => {
        if (!r.stderr.split('\n').some((line) => /^cross-ai: run lock record .*\.json is unreadable \(age \d+s\); not cleared; not starting$/.test(line))) return 'missing unreadable line';
        return plantedUnchanged(c) ? null : 'planted record changed';
      },
    }, {
      name: 'lock-unreadable-reread', kind: 'runtime', args: ['--runtime', 'pi', '--model', 'fake/ok'], exit: 0,
      status: /^AIKIT-XAI status=ok cli=pi model=fake\/ok exit=0 .* action=stop$/,
      setup: (c) => {
        c.lockFile = lockPath(fs.realpathSync(c.repo), c.env.XDG_STATE_HOME);
        fs.mkdirSync(path.dirname(c.lockFile), { recursive: true, mode: 0o700 }); fs.writeFileSync(c.lockFile, '');
        c.deadPid = deadPid();
        setTimeout(() => plantLock(c, { pid: c.deadPid, pid_start: '1', child_pgid: null }), 1000);
        return null;
      },
      check: (r, c) => {
        if (!r.stderr.split('\n').includes(`cross-ai: stale run lock from pid ${c.deadPid} (since 2026-11-21T00:00:00.000Z) cleared`)) return 'missing stale line';
        const waited = r.elapsedMs;
        return waited >= 900 ? null : `waited ${waited}ms`;
      },
    }, {
      name: 'lock-review-no-note-stale', kind: 'logic', args: ['--mode', 'review', '--runtime', 'pi', '--model', 'fake/review-ok'], exit: 0,
      status: /^AIKIT-XAI status=ok cli=pi model=fake\/review-ok exit=0 .* tree=clean action=stop$/,
      setup: (c) => plantLock(c, { pid: deadPid(), pid_start: '1', child_pgid: null }),
      check: (r, c) => {
        if (r.stderr.split('\n').includes('cross-ai: note: an execute run holds this checkout; the tree check may void this review')) return 'note printed for a stale record';
        return plantedUnchanged(c) ? null : 'planted record changed';
      },
    }, {
      name: 'pure-lock-start-ps', kind: 'logic', pure: () => {
        const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'xai-ps-'));
        try {
          const bin = path.join(dir, 'bin'); fs.mkdirSync(bin);
          fs.symlinkSync(process.execPath, path.join(bin, 'node'));
          writeExe(bin, 'ps', '', String.raw`if (argOf('-p') === '4242') { process.stdout.write('Sat Nov 21 10:00:00 2026\n'); process.exit(0); } process.exit(1);`);
          const start = lockStartTime(4242, false, { PATH: bin });
          if (start !== 'Sat Nov 21 10:00:00 2026') return `ps start ${start}`;
          const dead = lockStartTime(4343, false, { PATH: bin });
          if (dead !== '-') return `dead pid start ${dead}`;
          fs.mkdirSync(path.join(dir, 'empty'));
          const missing = lockStartTime(4242, false, { PATH: path.join(dir, 'empty') });
          if (missing !== '-') return `ps start ${missing}`;
          return lockStartTime(process.pid, true) === procStartTime(process.pid) ? null : 'proc start differs';
        } finally { fs.rmSync(dir, { recursive: true, force: true }); }
      },
    }, {
      name: 'pure-lock-clear-race', kind: 'logic', pure: () => {
        const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'xai-lock-'));
        try {
          const file = path.join(dir, 'l.json');
          const stale = { version: 1, run_id: 's', pid: 4242, pid_start: '1', host_name: os.hostname(), child_pgid: null, child_start: null };
          const fresh = { ...stale, run_id: 'f' };
          writeCycleState(file, stale); let seen = readLockOnce(file); writeCycleState(file, fresh);
          if (clearStaleLock(file, seen) || JSON.parse(fs.readFileSync(file)).run_id !== 'f' || JSON.stringify(fs.readdirSync(dir)) !== '["l.json"]') return 'race: fresh replaced';
          writeCycleState(file, stale); seen = readLockOnce(file); fs.mkdirSync(file + '.clearing');
          if (clearStaleLock(file, seen) || JSON.parse(fs.readFileSync(file)).run_id !== 's') return 'race: fresh mutex';
          const old = new Date(Date.now() - 11000); fs.utimesSync(file + '.clearing', old, old);
          if (!clearStaleLock(file, seen) || fs.readdirSync(dir).length) return 'race: old mutex';
          writeCycleState(file, stale); seen = readLockOnce(file);
          if (!clearStaleLock(file, seen) || fs.readdirSync(dir).length) return 'race: clear';
          return null;
        } finally { fs.rmSync(dir, { recursive: true, force: true }); }
      },
    }, {
      name: 'lock-stale-race', kind: 'runtime', args: ['--runtime', 'pi', '--model', 'fake/lockhold', '--print-argv'], exit: 0,
      status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
      setup: (c) => plantLock(c, { pid: deadPid(), pid_start: '1', child_pgid: null }),
      check: async (r, c) => {
        const spec = { args: ['--runtime', 'pi', '--model', 'fake/lockhold'] };
        const runs = [runCaseProcess(spec, c), runCaseProcess(spec, c)];
        const first = await Promise.race(runs);
        fs.writeFileSync(path.join(c.home, 'lock-release'), '');
        const both = await Promise.all(runs);
        for (const run of both) if (run.reason) return `contender: ${run.reason}`;
        if (first.status !== 75) return `first to end exited ${first.status}`;
        const exits = both.map((run) => run.status).sort((a, b) => a - b);
        if (JSON.stringify(exits) !== '[0,75]') return `exits ${exits.join(',')}`;
        const loser = both.find((run) => run.status === 75);
        const lose = statusLineOk(loser.stderr, /^AIKIT-XAI status=locked cli=pi model=fake\/lockhold exit=75 .* action=stop$/);
        if (lose) return `loser: ${lose}`;
        const calls = readOr(path.join(c.tmp, 'calls-lock-stale-race.log'), '').trim().split('\n').filter(Boolean);
        const held = calls.filter((line) => line === 'pi lockhold').length;
        const rpc = calls.filter((line) => line === 'pi rpc').length;
        if (held !== 1) return `pi lockhold calls ${held}`;
        if (rpc > 1) return `pi rpc calls ${rpc}`;
        const dir = path.dirname(c.lockFile);
        const names = fs.readdirSync(dir).filter((n) => n.endsWith('.json') || n.endsWith('.clearing') || n.includes('.stale-'));
        return names.length ? `lock left: ${names.join(',')}` : null;
      },
    },
    ];

    const unkinded = cases.filter((c) => c.kind !== 'logic' && c.kind !== 'runtime').map((c) => c.name);
    if (unkinded.length) {
      process.stderr.write(`self-test: case without a logic or runtime kind: ${unkinded.join(',')}\n`);
      return 2;
    }
    const dupes = cases.map((c) => c.name).filter((n, i, all) => all.indexOf(n) !== i);
    if (dupes.length) {
      process.stderr.write(`self-test: duplicate case name: ${[...new Set(dupes)].join(',')}\n`);
      return 2;
    }
    if (listOnly) {
      for (const c of cases) process.stdout.write(`${c.name}\t${c.kind}\n`);
      return 0;
    }
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
    setSelfTestHook(null);
  }
}

export { blackBoxSelfTest };

#!/usr/bin/env node
// ai-kit-cross-ai generator=ai-kit-gsd-curated-config template=6 sha256=UNSTAMPED
/*
 * cross-ai.mjs: the GSD `workflow.cross_ai_command` dispatcher (template v6).
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
 *   --prefer pi,cursor,opencode,codex   order to try (default CONFIG.prefer)
 *   --model-<cli> <id>                       model per CLI, e.g. --model-cursor auto
 *   --mode exec|review                       exec = full permissions (default); review = read-only
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
 *   --self-test                              hermetic black-box checks (no real CLIs)
 *
 * CONFIG.effort pins the selected effort per runner: pi --thinking (skipped when the model
 * has a :level suffix) and codex model_reasoning_effort.
 *
 * Live outer timeout reads workflow.cross_ai_timeout the way gsd-tools config-get does:
 * .planning[/$GSD_PROJECT][/workstreams/$GSD_WORKSTREAM]/config.json, then the root config
 * under GSD_WORKSTREAM, else 300.
 * No idle watchdog in this version (D-43); only the overall deadline bounds each child.
 */
import { spawn, spawnSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// <config>
const CONFIG = {
  "backoffS": [
    30,
    60
  ],
  "effort": {},
  "extraArgs": {},
  "heartbeatS": 30,
  "models": {},
  "outerTimeoutS": 1800,
  "prefer": [
    "pi",
    "cursor",
    "opencode"
  ],
  "retries": 2,
  "routerBacked": {},
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
const RESUME_MSG = 'You were interrupted by a transient provider error. Continue the same task from where you stopped: ' +
  'first inspect git status, git diff and git log, do not redo finished steps, finish the remaining steps ' +
  '(verify commands and commits included), then reply with the final report as originally asked.';

// First matching key wins: billing and quota come before auth so a 403 spending-limit or
// free-tier error is not read as an auth failure.
// <patterns>
const PATTERNS = {
  "permission_blocked": "permission denied|requires approval|approval required|workspace trust required|pre-dispatch filters",
  "billing": "spending limit|billing|payment required|\\b402\\b|free ?tier",
  "quota": "quota exceeded|insufficient_quota|usage limit",
  "auth": "\\b40[13]\\b|unauthori[sz]ed|token_expired|invalid_refresh_token|could not be refreshed|not logged in|log ?in required|please (?:log|sign) ?in|invalid api key|requires an opencode API key|credential gate",
  "bad_model": "model not found|unknown model|invalid model",
  "capacity": "overloaded|at capacity|service unavailable|\\b503\\b",
  "transient": "temporarily unavailable|cooling down|is locked|rate.?limit|too many requests|\\b429\\b|\\b50[24]\\b|ECONNRESET|ETIMEDOUT|socket hang up|stream (?:closed|disconnected)"
};
// </patterns>

const STATUS_TABLE = {
  ok: { exit: 0, action: 'stop' },
  no_change: { exit: 1, action: 'fallback' },
  empty_answer: { exit: 1, action: 'fallback' },
  crash: { exit: 1, action: 'fallback' },
  contract_violation: { exit: 1, action: 'stop' },
  usage: { exit: 2, action: 'stop' },
  no_model: { exit: 2, action: 'stop' },
  empty_stdin: { exit: 2, action: 'stop' },
  permission_blocked: { exit: 69, action: 'fallback' },
  bad_model: { exit: 69, action: 'fallback' },
  auth: { exit: 69, action: 'fallback' },
  billing: { exit: 69, action: 'fallback' },
  quota: { exit: 75, action: 'retry-later' },
  capacity: { exit: 75, action: 'retry-later' },
  timeout: { exit: 124, action: 'stop' },
  not_installed: { exit: 127, action: 'fallback' },
  signal: { exit: 128, action: 'stop' },
  git_error: { exit: 1, action: 'stop' },
  git_timeout: { exit: 1, action: 'stop' },
};

const FINALIZE_CAP_MS = 10000;
const KILL_GRACE_MS = 2000;
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
let liveFields = { cli: '-', model: '-', cli_rc: '-', out: 0, tree: 'clean' };
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

function log(text) {
  if (finished || stderrGone) return;
  process.stderr.write(text.endsWith('\n') ? text : `${text}\n`);
}

function finish(status, fields) {
  if (finished) return finishedExit;
  const row = STATUS_TABLE[status] || { exit: 1, action: 'stop' };
  let action = fields.action ?? row.action;
  const tree = fields.tree ?? 'unknown';
  let exit = fields.exit ?? row.exit;
  if (status === 'billing' && fields.cli && CONFIG.routerBacked[fields.cli]) {
    action = 'retry-later';
    exit = 75;
  }
  // Neither another CLI nor a later retry may run over edits this run left (or may have left).
  if ((action === 'fallback' || action === 'retry-later') && tree !== 'clean') action = 'stop';
  const elapsed = fields.elapsed ?? Math.max(0, Math.round((Date.now() - runStartedMs) / 1000));
  const line = `AIKIT-XAI status=${status} cli=${fields.cli ?? '-'} model=${fields.model ?? '-'} ` +
    `exit=${exit} cli_rc=${fields.cli_rc ?? '-'} elapsed=${elapsed}s out=${fields.out ?? 0} ` +
    `tree=${tree} action=${action}`;
  if (!stderrGone) process.stderr.write(`${line}\n`);
  finished = true;
  finishedExit = exit;
  return exit;
}

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
  exitFlushed(finish('crash', { ...liveFields, tree: 'unknown', exit: 1, cli_rc: '-' }));
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
    env: { OPENCODE_DISABLE_AUTOUPDATE: '1', OPENCODE_DISABLE_CLAUDE_CODE_SKILLS: '1' },
  },
  pi: {
    bins: ['pi'],
    list: { argv: PI_RPC_ARGS, input: PI_RPC_REQUEST, parse: parsePiListingIds },
    exec: (m, c) => ['-p', '--model', m, ...piThinkingArgs(m, c), '--session-id', c.sid, '--no-skills', '--no-extensions', '--no-approve', '--offline'],
    review: (m, c) => ['-p', '--model', m, ...piThinkingArgs(m, c), '--session-id', c.sid, '--no-skills', '--no-extensions', '--no-approve', '--offline',
      '--tools', 'read,grep,find,ls'],
    resume: (m, c, sid, mode) => RUNTIMES.pi[mode](m, c),
    parse: (out) => ({ text: out, sessionId: null, error: null }),
    // pi documents --model provider/id[:thinking]; the listing has bare ids.
    modelSuffix: /:(?:off|minimal|low|medium|high|xhigh|max)$/,
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
    env: {},
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

function classify(stderrText, structuredError) {
  const inputs = [stderrText || '', structuredError || ''];
  for (const [key, src] of Object.entries(PATTERNS)) {
    const re = new RegExp(src, 'i');
    for (const text of inputs) {
      if (re.test(text)) return key;
    }
  }
  return null;
}

function tryNextCli(status, tree) {
  return (STATUS_TABLE[status] || STATUS_TABLE.crash).action === 'fallback' && tree === 'clean';
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
  const cfg = parseJson(readOr(cfgPath, ''));
  const wf = cfg && typeof cfg === 'object' && !Array.isArray(cfg) ? cfg.workflow : null;
  if (!wf || typeof wf !== 'object' || Array.isArray(wf) || !Object.hasOwn(wf, 'cross_ai_timeout')) return undefined;
  return wf.cross_ai_timeout;
}
// Same ladder as gsd-core readScopedConfigValue (planning-workspace.cjs), which config-get
// follows: the scoped config's own key, then the root key only under GSD_WORKSTREAM; a
// GSD_PROJECT/GSD_WORKSTREAM with a path separator or `..` reads as absent.
// shortcut: the stored active-workstream pointer is not read (only the env), upgrade when
// GSD starts running cross_ai_command without exporting GSD_WORKSTREAM.
function liveOuterTimeoutS(cwd, env) {
  const ws = (env.GSD_WORKSTREAM || '').trim();
  const project = (env.GSD_PROJECT || '').trim();
  let t;
  if (!/[/\\]|\.\./.test(ws) && !/[/\\]|\.\./.test(project)) {
    const root = path.join(cwd, '.planning');
    const scoped = path.join(root, project, ws ? path.join('workstreams', ws) : '');
    t = ownTimeout(path.join(scoped, 'config.json'));
    if (t === undefined && ws) t = ownTimeout(path.join(root, 'config.json'));
  }
  const n = Number(t);
  return t !== undefined && t !== null && Number.isFinite(n) && n > 0 ? n : GSD_DEFAULT_TIMEOUT_S;
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
function retryArgv(name, rt, model, ctx, sid, mode, prompt) {
  if (mode === 'review') {
    // A fresh run: pi would reopen (resume) an existing --session-id.
    ctx.sid = crypto.randomUUID();
    return { argv: withExtra(name, rt.review(model, ctx)), input: prompt };
  }
  // A sandboxed exec retry is a fresh run: resume's sandbox flag is not verified.
  if (sid && rt.resume && !(mode === 'exec' && ctx.codexSandbox)) {
    return { argv: withExtra(name, rt.resume(model, ctx, sid, mode)), input: RESUME_MSG };
  }
  return { argv: withExtra(name, rt[mode](model, ctx)), input: `${RESUME_MSG}\n\n${prompt}` };
}
function readOr(p, dflt) { try { return fs.readFileSync(p, 'utf8'); } catch { return dflt; } }

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
    let spawnErr = null;
    let code = null;
    let signal = null;
    const outChunks = [];
    const errChunks = [];

    // Caps are read when each wait starts, so a signal mid-finalize shortens what is left.
    const finalize = async (reason) => {
      if (settled) return;
      settled = true;
      if (timer) clearTimeout(timer);
      if (currentFinalize === finalize) currentFinalize = null;
      if (child) {
        killGroup(child, 'SIGTERM');
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
      resolve({
        code, signal, timedOut, spawnErr,
        stdout: Buffer.concat(outChunks).toString('utf8'),
        stderr: Buffer.concat(errChunks).toString('utf8'),
      });
    };

    timer = setTimeout(() => { timedOut = true; finalize('timeout'); }, spawnMs);
    try {
      child = spawn(bin, argv, {
        cwd: opts.cwd, env: opts.env, stdio: ['pipe', 'pipe', 'pipe'], detached: true,
      });
    } catch (e) {
      spawnErr = e;
      finalize('spawn');
      return;
    }
    noteChildPgid('spawn', child.pid);
    current = child;
    currentFinalize = finalize;
    if (opts.input !== undefined) {
      child.stdin.on('error', () => { /* closed early */ });
      child.stdin.end(opts.input);
    } else {
      child.stdin.end();
    }
    child.stdout.on('data', (d) => {
      outChunks.push(d);
      opts.onStdout?.(d);
    });
    child.stderr.on('data', (d) => {
      errChunks.push(d);
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
  return stdout.split('\n').map((l) => l.trim()).filter(Boolean);
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
  return env;
}

function withExtra(cli, argv) {
  const extra = CONFIG.extraArgs[cli];
  return extra && extra.length ? [...argv, ...extra] : argv;
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
      exitFlushed(finish('signal', { ...liveFields, exit: 128 + n, tree: 'unknown' }));
    }, SIGNAL_BUDGET_MS + 200);
  });
}

async function runOnce(bin, argv, input, env, cwd, label) {
  let outBytes = 0;
  let lastBytes = 0;
  const started = Date.now();
  let errTail = '';
  const hb = setInterval(() => {
    log(`cross-ai: ${label} running ${Math.round((Date.now() - started) / 1000)}s, stdout +${outBytes - lastBytes} bytes`);
    lastBytes = outBytes;
  }, CONFIG.heartbeatS * 1000);
  const r = await runChild(bin, argv, {
    cwd, env, input, capMs: budgetMs(Number.POSITIVE_INFINITY, runDeadline), limit: runDeadline,
    onStdout: (d) => { outBytes += d.length; },
    onStderr: (d) => { log(d.toString('utf8')); errTail = (errTail + d.toString('utf8')).slice(-65536); },
  });
  clearInterval(hb);
  return { ...r, stderr: errTail || r.stderr, outBytes };
}

// A signal wakes every sleeper so the backoff never outlives the signal budget.
const sleep = (ms) => new Promise((resolve) => {
  const wake = () => { clearTimeout(t); sleepers.delete(wake); resolve(); };
  const t = setTimeout(wake, ms);
  sleepers.add(wake);
});

async function runCli(name, rt, binPath, model, mode, prompt, opts = {}) {
  const backoff = opts.backoffS || CONFIG.backoffS;
  const beforeSig = opts.beforeSig ?? null;
  const tmp = makeTemp('cross-ai-');
  const ctx = {
    cwd: process.cwd(), sid: crypto.randomUUID(), outFile: path.join(tmp, 'last-message.md'),
    codexEffort: opts.codexEffort, codexServiceTier: opts.codexServiceTier, cursorMode: opts.cursorMode,
    piThinking: opts.piThinking, codexSandbox: opts.codexSandbox,
  };
  const env = childEnv(rt.env, process.env);
  let argv = withExtra(name, rt[mode](model, ctx)); let input = prompt;
  try {
    for (let attempt = 0; ; attempt++) {
      log(`cross-ai: cli=${name} bin=${binPath} mode=${mode} attempt=${attempt + 1} timeout=${Math.round(budgetMs(Number.POSITIVE_INFINITY, runDeadline) / 1000)}s`);
      log(`cross-ai: argv=${JSON.stringify(argv)}`);
      const r = await runOnce(binPath, argv, input, env, ctx.cwd, name);
      if (aborting) return { ok: false, code: 128 + aborting, outBytes: r.outBytes, cli_rc: r.code };
      if (r.timedOut) return { ok: false, code: 124, timedOut: true, outBytes: r.outBytes, cli_rc: r.code };
      if (r.spawnErr) return { ok: false, code: r.spawnErr.code === 'ENOENT' ? 127 : 126, error: String(r.spawnErr), outBytes: 0, cli_rc: null };
      const p = rt.parse(r.stdout, ctx);
      const hit = classify(r.stderr, p.error);
      // stderr noise never overrules a clean exit with an answer; it only names a failure.
      const failed = r.code !== 0 || Boolean(p.error);
      if (!failed && p.text.trim()) {
        return { ok: true, text: normalize(p.text), outBytes: Buffer.byteLength(r.stdout, 'utf8'), cli_rc: 0 };
      }
      if (hit && hit !== 'transient') {
        return { ok: false, status: hit, outBytes: r.outBytes, cli_rc: r.code ?? '-' };
      }
      if (!failed) return { ok: false, status: 'empty_answer', outBytes: r.outBytes, cli_rc: 0 };
      const wait = (backoff[attempt] ?? backoff[backoff.length - 1]) * 1000;
      log(`cross-ai: ${name} failed (exit ${r.code}${r.signal ? ' ' + r.signal : ''}, ${hit || 'crash'}${p.error ? ': ' + p.error.slice(0, 200) : ''})`);
      // Retry only with the wait plus a minute of work left before the deadline.
      const exhausted = hit === 'transient' && (
        attempt >= (opts.retries ?? CONFIG.retries) || runDeadline - Date.now() < wait + 60000
      );
      if (hit !== 'transient' || exhausted) {
        const st = exhausted ? 'capacity' : 'crash';
        return { ok: false, status: st, outBytes: r.outBytes, cli_rc: r.code ?? '-' };
      }
      if (mode === 'review' && beforeSig !== null) {
        const mid = await treeState(ctx.cwd, runDeadline);
        if (mid === null) {
          return {
            ok: false, status: gitFailStatus(), outBytes: r.outBytes, cli_rc: r.code ?? '-',
          };
        }
        if (stateSig(mid) !== beforeSig) {
          return { ok: false, status: 'contract_violation', outBytes: r.outBytes, cli_rc: r.code ?? '-' };
        }
      }
      await sleep(budgetMs(wait, runDeadline));
      if (aborting) return { ok: false, outBytes: r.outBytes, cli_rc: r.code ?? '-' };
      const sid = p.sessionId || (name === 'pi' ? ctx.sid : null);
      const retry = retryArgv(name, rt, model, ctx, sid, mode, prompt);
      argv = retry.argv;
      input = retry.input;
    }
  } finally {
    dropTemp(tmp);
  }
}

const CODEX_EFFORTS = new Set(['minimal', 'low', 'medium', 'high', 'xhigh']);
const PI_THINKING = new Set(['off', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max']);
const CURSOR_MODES = new Set(['ask', 'plan']);
// No leading dash (read as a CLI option) and no shell or space characters (U-4).
const MODEL_ID = /^[A-Za-z0-9][A-Za-z0-9._:/#@+-]*$/;
// Cursor only: one trailing [k=v,...] bracket (D-18). No space, quote, `$` or `;`.
const CURSOR_MODEL_ID = /^[A-Za-z0-9][A-Za-z0-9._:/#@+-]*(?:\[[A-Za-z0-9._=,-]+\])?$/;

function parseArgs(argv) {
  const o = {
    prefer: null, models: {}, mode: 'exec', timeout: null, outerTimeout: null, printArgv: false,
    preamble: true, selfTest: false, codexEffort: null, codexServiceTier: null, cursorMode: null,
    prependFile: null, codexSandbox: null, childPgidFile: null,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]; const v = () => { if (i + 1 >= argv.length) throw new Error(`${a} needs a value`); return argv[++i]; };
    if (a === '--prefer') o.prefer = v().split(',').filter(Boolean);
    else if (a.startsWith('--model-')) {
      const id = v();
      const modelRe = a === '--model-cursor' ? CURSOR_MODEL_ID : MODEL_ID;
      if (!modelRe.test(id)) throw new Error(`${a} must match ${modelRe.source}`);
      o.models[a.slice(8)] = id;
    }
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
  for (const n of [...(o.prefer || []), ...Object.keys(o.models)]) if (!Object.hasOwn(RUNTIMES, n)) throw new Error(`unknown cli: ${n} (known: ${Object.keys(RUNTIMES).join(', ')})`);
  return o;
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
  const cfg = {
    backoffS: [0, 0], effort: {}, extraArgs: {}, heartbeatS: 30, models: {}, outerTimeoutS: 1800,
    prefer: ['pi', 'cursor', 'opencode'], retries: 2, routerBacked: {}, scrubEnv: [...CONFIG.scrubEnv],
    ...override,
  };
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
const STICKY_FAKE = new Set(['hang', 'gcescape', 'outer-race', 'stubborn', 'slowok', 'big']);
let stdinBuf = '';
const FAKE_MODES = {
  ok: () => { fs.appendFileSync('a.txt', 'ok-line\n'); process.stdout.write('# Summary\nok'); },
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
  crash: () => { process.stderr.write('boom\n'); process.exit(7); },
  quote: () => {
    fs.appendFileSync('a.txt', 'q\n');
    process.stdout.write('429 rate limit and billing noted.\n# Summary\nok');
  },
  billing: () => { process.stderr.write('402 payment required\n'); process.exit(1); },
  spend403: () => { process.stderr.write('Error 403: spending limit reached for this team\n'); process.exit(1); },
  freetier: () => { process.stderr.write('403: {"type":"FreeTierError"}\n'); process.exit(1); },
  auth: () => { process.stderr.write('401 unauthorized\n'); process.exit(1); },
  perm: () => { process.stderr.write('permission denied\n'); process.exit(1); },
  quota: () => { process.stderr.write('quota exceeded\n'); process.exit(1); },
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
  flaky: () => {
    const home = process.env.HOME || '';
    const ctr = home + '/.fake-flaky-count';
    let n = 0;
    try { n = Number(fs.readFileSync(ctr, 'utf8')) || 0; } catch { /* first call */ }
    if (n < 1) {
      fs.writeFileSync(ctr, '1');
      process.stderr.write('429 Too Many Requests\n');
      process.exit(1);
    }
    fs.appendFileSync('a.txt', 'ok-line\n');
    process.stdout.write('# Summary\nok');
  },
  overloaded: () => {
    process.stderr.write('429 Too Many Requests\n');
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
  'review-flaky-edit': () => {
    const home = process.env.HOME || '';
    const ctr = home + '/.fake-review-flaky-count';
    let n = 0;
    try { n = Number(fs.readFileSync(ctr, 'utf8')) || 0; } catch { /* first */ }
    if (n < 1) {
      fs.writeFileSync(ctr, '1');
      fs.appendFileSync('a.txt', 'flaky-edit\n');
      process.stderr.write('429 Too Many Requests\n');
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
    for (const id of ['fake-ok-cursor', 'fake-err-cursor', 'composer-2.5']) console.log(id + ' - label');
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
  console.log(JSON.stringify({ models: ['fake-ok-codex', 'fake-retry-codex'].map((slug) => ({ slug, visibility: 'list' })) }));
  process.exit(0);
}
const outFile = argOf('-o');
log('codex ' + argOf('-m'));
process.stdin.on('data', () => {}).on('end', () => {
  fs.appendFileSync('a.txt', 'cx\n');
  if (outFile) fs.writeFileSync(outFile, '## Summary\nok');
  console.log(JSON.stringify({ type: 'thread.started', thread_id: 't1' }));
  if (argOf('-m') === 'fake-retry-codex') {
    console.log(JSON.stringify({ type: 'error', message: 'stream disconnected; retrying 1/5' }));
    console.log(JSON.stringify({ type: 'turn.completed' }));
  }
});
`);
}

function statusLineOk(stderr, pattern) {
  const lines = stderr.split('\n').filter((l) => l.trim());
  const hits = lines.filter((l) => l.startsWith('AIKIT-XAI '));
  if (hits.length !== 1) return `expected one AIKIT-XAI line, got ${hits.length}`;
  if (hits[0] !== lines[lines.length - 1]) return 'AIKIT-XAI line is not last stderr line';
  if (!pattern.test(hits[0])) return `status line mismatch: ${hits[0]}`;
  return null;
}

function pidAlive(pid) {
  try { process.kill(pid, 0); } catch { return false; }
  try { return !/^\d+ \(.*\) Z/.test(fs.readFileSync(`/proc/${pid}/stat`, 'utf8')); } catch { return true; }
}

// A SIGKILLed descendant can outlive the runner by a few ms under load (or sit as an unreaped
// zombie), so "still alive" means alive after a bounded wait, not at the first probe.
function pidLingers(pid, ms = 3000) {
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
    const hard = setTimeout(() => end('case hung past 30s'), 30000);
    child.stdout.on('data', (d) => { stdout += d.toString('utf8'); });
    child.stderr.on('data', (d) => {
      stderr += d.toString('utf8');
    });
    child.stdin.on('error', () => { /* runner exited early */ });
    child.stdin.end(spec.stdin ?? 'prompt\n');
    if (spec.closeStderr) waitFor(() => spec.closeStderr(c), 10000).then(() => child.stderr.destroy());
    if (spec.signal) {
      waitFor(() => spec.signal.when(c), 10000).then((ready) => {
        if (done) return;
        if (!ready) { end('signal precondition never met'); return; }
        sigMs = Date.now();
        try { child.kill(spec.signal.sig); } catch { /* exited */ }
        if (spec.signal.again) setTimeout(() => { try { child.kill(spec.signal.again); } catch { /* exited */ } }, 200);
      });
    }
    child.on('exit', (exitCode) => {
      code = exitCode;
      Promise.race([new Promise((r) => child.on('close', r)), sleep(2000)]).then(() => end(null));
    });
  });
}

async function checkCase(spec, c) {
  const r = await runCaseProcess({ ...spec, args: c.args || spec.args }, c);
  if (r.reason) return r.reason;
  if (r.status !== spec.exit) return `exit ${r.status} expected ${spec.exit}`;
  if (!spec.closeStderr) {
    const err = statusLineOk(r.stderr || '', spec.status);
    if (err) return err;
  }
  if (spec.signal && r.sinceSignalMs > (spec.signal.withinMs ?? 2900)) return `exit ${r.sinceSignalMs}ms after the signal`;
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

async function runSelfTestCase(tmp, spec) {
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
    HOME: home, XDG_CONFIG_HOME: path.join(home, '.config'), FAKE_CALLS: calls, FAKE_PIDS: pidFile, ...(spec.env || {}),
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
  const gitBin = which('git');
  if (!gitBin) {
    process.stderr.write('self-test: git not found\n');
    return 1;
  }
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
        status: /^AIKIT-XAI status=auth cli=pi model=fake\/emptyauth exit=69 cli_rc=0 .* tree=clean action=fallback$/,
      },
      {
        name: 'billing',
        args: ['--prefer', 'pi', '--model-pi', 'fake/billing'],
        exit: 69,
        status: /^AIKIT-XAI status=billing cli=pi model=fake\/billing exit=69 cli_rc=1 elapsed=\d+s out=\d+ tree=clean action=fallback$/,
      },
      {
        name: 'billing-router',
        args: ['--prefer', 'pi', '--model-pi', 'fake/billing'],
        config: { routerBacked: { pi: true } },
        exit: 75,
        status: /^AIKIT-XAI status=billing cli=pi model=fake\/billing exit=75 cli_rc=1 elapsed=\d+s out=\d+ tree=clean action=retry-later$/,
      },
      {
        name: 'billing-403-router',
        args: ['--prefer', 'pi', '--model-pi', 'fake/spend403'],
        config: { routerBacked: { pi: true } },
        exit: 75,
        status: /^AIKIT-XAI status=billing cli=pi model=fake\/spend403 exit=75 cli_rc=1 .* tree=clean action=retry-later$/,
      },
      {
        name: 'billing-free-tier',
        args: ['--prefer', 'pi', '--model-pi', 'fake/freetier'],
        exit: 69,
        status: /^AIKIT-XAI status=billing cli=pi model=fake\/freetier exit=69 cli_rc=1 .* tree=clean action=fallback$/,
      },
      {
        name: 'auth',
        args: ['--prefer', 'pi', '--model-pi', 'fake/auth'],
        exit: 69,
        status: /^AIKIT-XAI status=auth cli=pi model=fake\/auth exit=69 cli_rc=1 elapsed=\d+s out=\d+ tree=clean action=fallback$/,
      },
      {
        name: 'perm',
        args: ['--prefer', 'pi', '--model-pi', 'fake/perm'],
        exit: 69,
        status: /^AIKIT-XAI status=permission_blocked cli=pi model=fake\/perm exit=69 cli_rc=1 elapsed=\d+s out=\d+ tree=clean action=fallback$/,
      },
      {
        name: 'quota',
        args: ['--prefer', 'pi', '--model-pi', 'fake/quota'],
        exit: 75,
        status: /^AIKIT-XAI status=quota cli=pi model=fake\/quota exit=75 cli_rc=1 elapsed=\d+s out=\d+ tree=clean action=retry-later$/,
      },
      {
        name: 'dirty-quota',
        args: ['--prefer', 'pi', '--model-pi', 'fake/dirtyquota'],
        exit: 75,
        status: /^AIKIT-XAI status=quota cli=pi model=fake\/dirtyquota exit=75 cli_rc=1 .* tree=dirty action=stop$/,
      },
      {
        name: 'dirty-billing-router',
        args: ['--prefer', 'pi', '--model-pi', 'fake/dirtybilling'],
        config: { routerBacked: { pi: true } },
        exit: 75,
        status: /^AIKIT-XAI status=billing cli=pi model=fake\/dirtybilling exit=75 cli_rc=1 .* tree=dirty action=stop$/,
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
        name: 'crash',
        args: ['--prefer', 'pi', '--model-pi', 'fake/crash'],
        exit: 1,
        status: /^AIKIT-XAI status=crash cli=pi model=fake\/crash exit=1 cli_rc=7 elapsed=\d+s out=\d+ tree=clean action=fallback$/,
      },
      {
        name: 'nochange',
        args: ['--prefer', 'pi', '--model-pi', 'fake/nochange'],
        exit: 1,
        status: /^AIKIT-XAI status=no_change cli=pi model=fake\/nochange exit=1 cli_rc=0 elapsed=\d+s out=\d+ tree=clean action=fallback$/,
      },
      {
        name: 'empty',
        args: ['--prefer', 'pi', '--model-pi', 'fake/empty'],
        exit: 1,
        status: /^AIKIT-XAI status=empty_answer cli=pi model=fake\/empty exit=1 cli_rc=0 elapsed=\d+s out=\d+ tree=clean action=fallback$/,
      },
      {
        name: 'cursor-error',
        args: ['--prefer', 'cursor', '--model-cursor', 'fake-err-cursor'],
        exit: 69,
        status: /^AIKIT-XAI status=auth cli=cursor model=fake-err-cursor exit=69 cli_rc=0 elapsed=\d+s out=\d+ tree=clean action=fallback$/,
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
        name: 'fallback',
        args: ['--prefer', 'pi,cursor', '--model-pi', 'fake/nochange', '--model-cursor', 'fake-ok-cursor'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=cursor model=fake-ok-cursor exit=0 cli_rc=0 elapsed=\d+s out=\d+ tree=dirty action=stop$/,
        check: (_r, ctx) => {
          const piIdx = ctx.calls.findIndex((l) => l.startsWith('pi '));
          const curIdx = ctx.calls.findIndex((l) => l.startsWith('cursor-agent'));
          if (piIdx < 0 || curIdx < 0 || piIdx > curIdx) return `call order: ${ctx.calls.join('|')}`;
          return null;
        },
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
        name: 'not-installed-codex',
        args: ['--prefer', 'codex', '--model-codex', 'x'],
        env: { PATH: `${path.join(tmp, 'bin-nocodex')}` },
        exit: 127,
        status: /^AIKIT-XAI status=not_installed .* exit=127 .* action=fallback$/,
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
        signal: { when: (c) => fs.existsSync(path.join(c.repo, 'cli.ready')), sig: 'SIGTERM', withinMs: 2900 },
        exit: 143,
        status: /^AIKIT-XAI status=signal cli=pi model=fake\/stubborn exit=143 .* tree=dirty action=stop$/,
        check: (_r, ctx) => deadCheck(ctx, ['pi']),
      },
      {
        name: 'sigterm-twice',
        args: ['--prefer', 'pi', '--model-pi', 'fake/stubborn', '--timeout', '60'],
        signal: { when: (c) => fs.existsSync(path.join(c.repo, 'cli.ready')), sig: 'SIGTERM', again: 'SIGINT', withinMs: 2900 },
        exit: 143,
        status: /^AIKIT-XAI status=signal cli=pi model=fake\/stubborn exit=143 .* action=stop$/,
        check: (_r, ctx) => deadCheck(ctx, ['pi']),
      },
      {
        name: 'sigterm-backoff',
        args: ['--prefer', 'pi', '--model-pi', 'fake/overloaded', '--timeout', '200'],
        config: { backoffS: [20] },
        signal: { when: (c) => readOr(c.calls, '').includes('pi overloaded'), sig: 'SIGTERM', withinMs: 2900 },
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
          if (ctx.elapsedMs >= 10000) return `elapsed ${ctx.elapsedMs}`;
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
        check: (_r, ctx) => (ctx.elapsedMs >= 15000 ? `elapsed ${ctx.elapsedMs}` : deadCheck(ctx, ['gc'])),
      },
      {
        name: 'gcterm',
        args: ['--prefer', 'pi', '--model-pi', 'fake/gcterm', '--timeout', '60'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/gcterm exit=0 .* action=stop$/,
        check: (_r, ctx) => (ctx.elapsedMs >= 15000 ? `elapsed ${ctx.elapsedMs}` : deadCheck(ctx, ['gc'])),
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
        check: (_r, ctx) => (ctx.elapsedMs >= 10000 ? `elapsed ${ctx.elapsedMs}` : null),
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
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=cursor model=fake-ok-cursor exit=0 cli_rc=0 elapsed=\d+s out=\d+ tree=dirty action=stop$/,
        check: (r, ctx) => {
          if (!(r.stderr || '').includes('bad_model')) return 'stderr missing bad_model';
          if (!ctx.calls.includes('pi rpc')) return 'missing pi rpc';
          if (ctx.calls.some((l) => l === 'pi missing')) return 'pi run should not happen';
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
        status: /^AIKIT-XAI status=bad_model cli=pi model=fake\/missing:high exit=69 .* action=fallback$/,
      },
      {
        name: 'bad-model-only',
        args: ['--prefer', 'pi', '--model-pi', 'fake/missing'],
        exit: 69,
        status: /^AIKIT-XAI status=bad_model cli=pi model=fake\/missing exit=69 .* action=fallback$/,
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
          if (ctx.elapsedMs >= 10000) return `elapsed ${ctx.elapsedMs}`;
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
        status: /^AIKIT-XAI status=capacity cli=pi model=fake\/overloaded exit=75 .* action=retry-later$/,
        check: (_r, ctx) => {
          const n = ctx.calls.filter((l) => l === 'pi overloaded').length;
          return n === 3 ? null : `overloaded calls=${n}`;
        },
      },
      {
        name: 'backoff-deadline',
        args: ['--prefer', 'pi', '--model-pi', 'fake/overloaded', '--timeout', '3'],
        config: { backoffS: [30, 60] },
        exit: 75,
        status: /^AIKIT-XAI status=capacity cli=pi model=fake\/overloaded exit=75 cli_rc=1 .* tree=clean action=retry-later$/,
        check: (_r, ctx) => (ctx.elapsedMs < 5000 ? null : `elapsed ${ctx.elapsedMs}ms`),
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
        name: 'claude-exec-usage',
        args: ['--prefer', 'claude', '--mode', 'exec', '--model-claude', 'fake-ok'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
        check: (r) => ((r.stderr || '').includes('claude is review-only') ? null : 'missing review-only line'),
      },
      {
        // IN-09: a review-only CLI anywhere in an exec prefer list is refused before any run.
        name: 'claude-exec-late-usage',
        args: ['--prefer', 'pi,claude', '--mode', 'exec', '--model-pi', 'fake/ok', '--model-claude', 'fake-ok'],
        exit: 2,
        status: /^AIKIT-XAI status=usage .* exit=2 .* action=stop$/,
        check: (_r, ctx) => (ctx.calls.length ? `calls=${ctx.calls.join(',')}` : null),
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
          const m = (r.stderr || '').match(/cross-ai: retry codex argv=(\S+)/);
          if (!m) return 'missing retry line';
          const retryArgv = m[1];
          if (retryArgv !== reviewArgv) return 'retry argv mismatch';
          const parsed = JSON.parse(retryArgv);
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
          const m = (r.stderr || '').match(/cross-ai: retry codex argv=(\S+)/);
          if (!m) return 'missing retry line';
          const parsed = JSON.parse(m[1]);
          if (!parsed.includes('resume')) return 'missing resume';
          if (!parsed.includes('--dangerously-bypass-approvals-and-sandbox')) return 'missing bypass';
          for (const k of ['model_reasoning_effort=high', 'service_tier=flex']) if (!parsed.includes(k)) return `retry argv missing ${k}`;
          return null;
        },
      },
      {
        // SPEC R5: a review retry is a fresh run, so pi gets a new session id.
        name: 'argv-retry-pi-review',
        args: ['--print-argv', '--mode', 'review', '--prefer', 'pi', '--model-pi', 'fake/ok'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=clean action=stop$/,
        check: (r) => {
          const line = (r.stdout || '').split('\n').find((l) => l.startsWith('pi\t'));
          const first = JSON.parse(line.split('\t')[2]);
          const m = (r.stderr || '').match(/cross-ai: retry pi argv=(\S+)/);
          if (!m) return 'missing retry line';
          const retry = JSON.parse(m[1]);
          const sid = (a) => a[a.indexOf('--session-id') + 1];
          if (sid(retry) === sid(first)) return 'retry reuses the session id';
          const same = (a) => JSON.stringify(a.filter((t) => t !== sid(a)));
          return same(retry) === same(first) ? null : 'retry argv differs beyond the session id';
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
          const reviewArgv = stdoutLine.split('\t')[2];
          const m = (r.stderr || '').match(/cross-ai: retry cursor argv=(\S+)/);
          if (!m || m[1] !== reviewArgv) return 'retry mismatch';
          if (JSON.parse(m[1]).includes('--resume')) return 'has resume';
          return null;
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
          const retry = (r.stderr || '').split('\n').find((l) => l.includes('retry codex argv='));
          if (!retry) return 'missing retry argv';
          const retryArgv = JSON.parse(retry.slice(retry.indexOf('[')));
          if (retryArgv.includes('resume')) return 'retry resumed';
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
        name: 'outer-race',
        config: { outerTimeoutS: 10 },
        args: ['--prefer', 'pi', '--model-pi', 'fake/outer-race', '--timeout', '8'],
        exit: 124,
        status: /^AIKIT-XAI status=timeout cli=pi model=fake\/outer-race exit=124 .* tree=unknown action=stop$/,
        check: (r, ctx) => {
          if (ctx.elapsedMs >= 10000) return `elapsed ${ctx.elapsedMs}`;
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
  liveFields = { cli: '-', model: '-', cli_rc: '-', out: 0, tree: 'clean' };
  let o;
  try { o = parseArgs(argv); } catch (e) {
    log(`cross-ai: ${e.message}`);
    return finish('usage', { ...liveFields, tree: 'unknown', exit: 2 });
  }
  if (o.selfTest) return blackBoxSelfTest();
  childPgidFile = o.childPgidFile;
  childPgidBroken = false;
  const order = o.prefer || CONFIG.prefer;
  const models = { ...CONFIG.models, ...o.models };
  const cands = order.map((name) => ({
    name, rt: RUNTIMES[name], model: models[name],
    bin: resolveBin(RUNTIMES[name], process.env.PATH || ''),
  }));
  // Baked per-runner effort (the plan's selection); --codex-effort still wins for codex.
  const effort = CONFIG.effort || {};
  const knobs = {
    codexEffort: o.codexEffort ?? (CODEX_EFFORTS.has(effort.codex) ? effort.codex : null),
    piThinking: PI_THINKING.has(effort.pi) ? effort.pi : null,
  };
  const reviewOnly = o.mode === 'exec' ? cands.find((c) => !c.rt.exec) : null;
  if (reviewOnly) {
    log(`cross-ai: ${reviewOnly.name} is review-only (no exec formula)`);
    return finish('usage', { ...liveFields, tree: 'unknown', exit: 2 });
  }

  const dl = logDeadline(process.cwd(), process.env, o);
  if (dl.error) {
    log(dl.error);
    return finish('usage', { ...liveFields, tree: 'unknown', exit: 2 });
  }
  if (o.codexSandbox && o.mode !== 'exec') {
    log('cross-ai: --codex-sandbox applies to exec mode only; review already runs read-only');
  }
  if (o.printArgv) {
    const ctx = {
      cwd: process.cwd(), sid: '<sid>', outFile: '<tmp>/last-message.md',
      codexEffort: knobs.codexEffort, codexServiceTier: o.codexServiceTier, cursorMode: o.cursorMode,
      piThinking: knobs.piThinking, codexSandbox: o.mode === 'exec' ? o.codexSandbox : null,
    };
    for (const c of cands) {
      const argvOut = c.model ? withExtra(c.name, c.rt[o.mode](c.model, ctx)) : null;
      process.stdout.write(`${c.name}\t${c.bin || 'MISSING'}\t${argvOut ? JSON.stringify(argvOut) : 'NO MODEL'}\n`);
      if (c.model && argvOut) {
        const retry = retryArgv(c.name, c.rt, c.model, ctx, '<sid>', o.mode, '<prompt>');
        log(`cross-ai: retry ${c.name} argv=${JSON.stringify(retry.argv)}`);
      }
    }
    return finish('ok', { ...liveFields, tree: 'clean', exit: 0, out: 0 });
  }
  const raw = readStdin();
  if (!raw || !raw.trim()) {
    log('cross-ai: pipe the prompt on stdin');
    return finish('empty_stdin', { ...liveFields, tree: 'clean', exit: 2 });
  }
  let body = raw;
  if (o.prependFile) {
    let prepended;
    try {
      prepended = fs.readFileSync(path.resolve(process.cwd(), o.prependFile), 'utf8');
    } catch {
      log(`cross-ai: --prepend-file unreadable: ${o.prependFile}`);
      return finish('usage', { ...liveFields, tree: 'unknown', exit: 2 });
    }
    // The guidance file's stamp lines are bookkeeping for a human editor, not prompt text.
    body = `${prepended.replace(/^(?:<!--[^\n]*-->\r?\n)+/, '')}\n\n${raw}`;
  }
  const prompt = body + (o.preamble ? (o.mode === 'exec' ? EXEC_PREAMBLE : REVIEW_PREAMBLE) : '');
  const { outer, inner: innerS, innerDefault } = dl;
  runDeadline = Date.now() + innerS * 1000;
  const marginMs = (outer - innerDefault) * 1000;
  finalizeBy = runDeadline + Math.min(FINALIZE_CAP_MS, Math.floor(marginMs / 2));

  let last = null;
  let sawModel = false;
  // Decided once: a directory with no .git ancestor still dispatches (D-34).
  const noTree = !inGitTree(process.cwd());
  if (noTree) {
    log(`cross-ai: ${process.cwd()} is not inside a git work tree; running without the tree ` +
      'check (tree=unknown); no other CLI runs after one has run');
    if (o.mode === 'review') {
      log('cross-ai: review mode cannot verify the read-only contract outside a git work tree');
    }
  }
  for (const c of cands) {
    if (aborting) break;
    if (!c.bin) { log(`cross-ai: ${c.name} not installed, skipping`); continue; }
    if (!c.model) {
      log(`cross-ai: no model configured for ${c.name} (--model-${c.name}), skipping`);
      last = last || { kind: 'no_model' };
      continue;
    }
    sawModel = true;
    liveFields.cli = c.name;
    liveFields.model = c.model;
    const before = noTree ? null : await treeState(process.cwd(), runDeadline);
    if (aborting) break;
    if (!noTree && before === null) {
      return finish(gitFailStatus(), { ...liveFields, cli_rc: '-', tree: 'unknown', exit: 1 });
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
        // bad_model falls back and nothing ran, so the next CLI may always try.
        last = { status: 'bad_model', cli: c.name, model: c.model, tree: 'clean', cli_rc: '-' };
        log(`cross-ai: ${c.name} bad_model, trying the next CLI`);
        continue;
      }
    } else if (listing.reason !== 'no listing') {
      log(`cross-ai: ${c.name} model list unavailable (${listing.reason}); not preflighted`);
    }
    if (aborting) break;
    // From here until the next snapshot nothing proves the tree clean (CR-03).
    liveFields.tree = 'unknown';
    const r = await runCli(c.name, c.rt, c.bin, c.model, o.mode, prompt, {
      beforeSig: noTree ? null : stateSig(before), codexEffort: knobs.codexEffort,
      piThinking: knobs.piThinking, codexServiceTier: o.codexServiceTier,
      cursorMode: o.cursorMode, codexSandbox: o.mode === 'exec' ? o.codexSandbox : null,
    });
    liveFields.out = r.outBytes || 0;
    liveFields.cli_rc = r.cli_rc ?? '-';
    let after = noTree ? null : await treeState(process.cwd(), finalizeBy);
    // A signal during this snapshot killed its git child: read once more on the signal budget.
    if (!noTree && aborting && after === null) after = await treeState(process.cwd(), finalizeBy);
    const tree = noTree ? 'unknown' : treeLabel(before, after);
    liveFields.tree = tree;
    if (aborting) break;
    if (
      r.status === 'contract_violation' || r.status === 'git_error' || r.status === 'git_timeout'
    ) {
      const treeField = r.status === 'contract_violation' ? tree : 'unknown';
      return finish(r.status, { ...liveFields, tree: treeField, cli_rc: r.cli_rc ?? '-', exit: 1 });
    }
    if (r.timedOut) {
      return finish('timeout', { ...liveFields, tree, exit: 124, cli_rc: r.cli_rc ?? '-' });
    }
    if (o.mode === 'review' && before && after && tree === 'dirty') {
      return finish('contract_violation', { ...liveFields, tree, cli_rc: r.cli_rc ?? '-', exit: 1 });
    }
    if (r.ok) {
      if (!noTree && (after === null || before === null)) {
        return finish(gitFailStatus(), { ...liveFields, tree: 'unknown', cli_rc: 0, exit: 1 });
      }
      if (o.mode === 'exec' && tree === 'clean') {
        last = { status: 'no_change', cli: c.name, model: c.model, tree, cli_rc: 0 };
        log(`cross-ai: ${c.name} answered without repo change, trying the next CLI`);
        continue;
      }
      process.stdout.write(r.text);
      return finish('ok', { ...liveFields, tree, exit: 0, cli_rc: 0, out: r.outBytes || 0 });
    }
    if (!noTree && after === null) {
      return finish(gitFailStatus(), {
        ...liveFields, tree: 'unknown', cli_rc: r.cli_rc ?? '-', exit: 1,
      });
    }
    const status = r.status || 'crash';
    last = { status, cli: c.name, model: c.model, tree, cli_rc: r.cli_rc };
    if (tryNextCli(status, tree)) {
      log(`cross-ai: ${c.name} ${status}, trying the next CLI`);
      continue;
    }
    return finish(status, { ...liveFields, tree, cli_rc: r.cli_rc, cli: c.name, model: c.model });
  }
  if (aborting) return finish('signal', { ...liveFields, exit: 128 + aborting });
  if (!sawModel && last && last.kind === 'no_model') {
    return finish('no_model', { ...liveFields, tree: 'clean', exit: 2 });
  }
  if (!last) {
    log(`cross-ai: none of [${order.join(', ')}] is installed`);
    return finish('not_installed', { ...liveFields, tree: 'clean', exit: 127 });
  }
  if (last.status === 'no_change') {
    return finish('no_change', { ...liveFields, cli: last.cli, model: last.model, tree: last.tree, cli_rc: 0 });
  }
  return finish(last.status || 'crash', {
    ...liveFields, cli: last.cli || '-', model: last.model || '-', tree: last.tree || 'unknown',
    cli_rc: last.cli_rc ?? '-',
  });
}

if (process.argv[1] && fs.realpathSync(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(process.argv.slice(2)).then(
    (code) => exitFlushed(code ?? 0),
    (e) => {
      log(`cross-ai: internal error: ${e && e.stack || e}`);
      exitFlushed(finish('crash', { ...liveFields, tree: 'unknown', exit: 1, cli_rc: '-' }));
    },
  );
}

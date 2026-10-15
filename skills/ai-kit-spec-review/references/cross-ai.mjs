#!/usr/bin/env node
// ai-kit-cross-ai generator=ai-kit-gsd-curated-config template=2 sha256=UNSTAMPED
/*
 * cross-ai.mjs: the GSD `workflow.cross_ai_command` dispatcher (template v2).
 *
 * tree=clean means this CLI run left HEAD and the tree unchanged; dirty changed them;
 * unknown means not a git repo or git failed; with no CLI run it is clean.
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
 *   --timeout <s>                            inner deadline (default: workflow.cross_ai_timeout - margin)
 *   --print-argv                             print the resolved command per CLI and exit (no model call)
 *   --no-preamble                            send the prompt unchanged
 *   --self-test                              hermetic black-box checks (no real CLIs)
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

// <patterns>
const PATTERNS = {
  "permission_blocked": "permission denied|requires approval|approval required|workspace trust required|pre-dispatch filters",
  "auth": "\\b40[13]\\b|unauthori[sz]ed|token_expired|invalid_refresh_token|could not be refreshed|not logged in|log ?in required|please (?:log|sign) ?in|invalid api key|requires an opencode API key|credential gate",
  "billing": "spending limit|billing|payment required|\\b402\\b",
  "bad_model": "model not found|unknown model|invalid model",
  "quota": "quota exceeded|insufficient_quota|usage limit",
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
  unverified: { exit: 1, action: 'stop' },
};

const FINALIZE_CAP_MS = 10000;
const KILL_GRACE_MS = 2000;
const PIPE_DRAIN_MS = 2000;
const SIGNAL_GRACE_MS = 1000;
const GIT_CAP_MS = 10000;
const LIST_CAP_MS = 15000;
const PI_RPC_ARGS = [
  '--mode', 'rpc', '--offline', '--no-session', '--no-extensions',
  '--no-skills', '--no-context-files', '--no-mcp',
];
const PI_RPC_REQUEST = '{"id":"1","type":"get_available_models"}\n';

let runStartedMs = Date.now();
let liveFields = { cli: '-', model: '-', cli_rc: '-', out: 0, tree: 'clean' };
let finished = false;
let runDeadline = 0;
let finalizeBy = 0;
let current = null;
let currentFinalize = null;
let aborting = 0;

function budgetMs(capMs, limit) {
  return Math.max(0, Math.min(capMs, limit - Date.now()));
}

function log(text) {
  if (finished) return;
  process.stderr.write(text.endsWith('\n') ? text : `${text}\n`);
}

function finish(status, fields) {
  const row = STATUS_TABLE[status] || { exit: 1, action: 'stop' };
  let action = fields.action ?? row.action;
  const tree = fields.tree ?? 'unknown';
  if (action === 'fallback' && (tree === 'dirty' || tree === 'unknown')) action = 'stop';
  let exit = fields.exit ?? row.exit;
  if (status === 'billing' && fields.cli && CONFIG.routerBacked[fields.cli]) {
    action = 'retry-later';
    exit = 75;
  }
  const elapsed = fields.elapsed ?? Math.max(0, Math.round((Date.now() - runStartedMs) / 1000));
  const line = `AIKIT-XAI status=${status} cli=${fields.cli ?? '-'} model=${fields.model ?? '-'} ` +
    `exit=${exit} cli_rc=${fields.cli_rc ?? '-'} elapsed=${elapsed}s out=${fields.out ?? 0} ` +
    `tree=${tree} action=${action}`;
  process.stderr.write(`${line}\n`);
  finished = true;
  return exit;
}

function exitFlushed(code) {
  const go = () => process.exit(code);
  const flushFd = (fd) => {
    try { fs.fsyncSync(fd); } catch { /* no fsync on this stream */ }
  };
  flushFd(process.stderr.fd);
  flushFd(process.stdout.fd);
  go();
}

const RUNTIMES = {
  cursor: {
    bins: ['cursor-agent', 'agent'],
    exec: (m, c) => ['-p', '--output-format', 'json', '--model', m, '--trust', '--force', '--sandbox', 'disabled', '--approve-mcps', '--workspace', c.cwd],
    review: (m, c) => ['-p', '--output-format', 'json', '--model', m, '--mode', 'ask', '--trust', '--workspace', c.cwd],
    resume: (m, c, sid, mode) => [...RUNTIMES.cursor[mode](m, c), '--resume', sid],
    parse: (out) => {
      const ev = lastJson(out, (j) => j.type === 'result');
      if (!ev) return { text: '', sessionId: null, error: 'no result event in cursor output' };
      return { text: ev.result || '', sessionId: ev.session_id || null, error: ev.is_error ? (ev.result || 'is_error') : null };
    },
    env: {},
  },
  // opencode 2.0.29 run --help formulas; partial bare profile: opencode still loads
  // ~/.agents/skills and ~/.config/opencode/skills (opencode docs)
  opencode: {
    bins: ['opencode'],
    exec: (m) => ['run', '--model', m, '--auto', '--format', 'json'],
    review: (m) => ['run', '--model', m, '--agent', 'plan', '--format', 'json'],
    resume: (m, c, sid, mode) => [...RUNTIMES.opencode[mode](m, c), '--session', sid],
    parse: parseOpencode,
    env: { OPENCODE_DISABLE_AUTOUPDATE: '1', OPENCODE_DISABLE_CLAUDE_CODE_SKILLS: '1' },
  },
  pi: {
    bins: ['pi'],
    exec: (m, c) => ['-p', '--model', m, '--session-id', c.sid, '--no-skills', '--no-extensions', '--no-approve', '--offline'],
    review: (m, c) => ['-p', '--model', m, '--session-id', c.sid, '--no-skills', '--no-extensions', '--no-approve', '--offline',
      '--tools', 'read,grep,find,ls'],
    resume: (m, c, sid, mode) => RUNTIMES.pi[mode](m, c),
    parse: (out) => ({ text: out, sessionId: null, error: null }),
    env: {},
  },
  // unverified (outside the default prefer)
  codex: {
    bins: ['codex'],
    exec: (m, c) => ['exec', '--dangerously-bypass-approvals-and-sandbox', '--skip-git-repo-check', '-C', c.cwd, '-m', m,
      '--json', '-o', c.outFile, '-'],
    review: (m, c) => ['exec', '--sandbox', 'read-only', '--skip-git-repo-check', '-C', c.cwd, '-m', m, '--json', '-o', c.outFile, '-'],
    resume: (m, c, sid, mode) => ['exec', 'resume', ...(mode === 'exec' ? ['--dangerously-bypass-approvals-and-sandbox'] : []),
      '--skip-git-repo-check', '-m', m, '--json', '-o', c.outFile, sid, '-'],
    parse: (out, c) => {
      let sid = null, error = null;
      for (const j of jsonLines(out)) {
        if (j.type === 'thread.started') sid = j.thread_id || sid;
        if (j.type === 'error' || j.type === 'turn.failed') error = JSON.stringify(j).slice(0, 400);
      }
      let text = '';
      try { text = fs.readFileSync(c.outFile, 'utf8'); } catch { /* no answer written */ }
      return { text, sessionId: sid, error };
    },
    env: {},
  },
};

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
  const row = STATUS_TABLE[status] || STATUS_TABLE.crash;
  if (row.action !== 'fallback' || tree !== 'clean') return false;
  return true;
}

function which(bin, envPath = process.env.PATH || '') {
  if (bin.includes('/')) return isExec(bin) ? bin : null;
  for (const dir of envPath.split(path.delimiter)) {
    const p = path.join(dir || '.', bin);
    if (isExec(p)) return p;
  }
  return null;
}
function isExec(p) { try { fs.accessSync(p, fs.constants.X_OK); return fs.statSync(p).isFile(); } catch { return false; } }

function outerTimeoutS(cwd) {
  const cfg = parseJson(readOr(path.join(cwd, '.planning', 'config.json'), ''));
  const t = Number(cfg && cfg.workflow && cfg.workflow.cross_ai_timeout);
  return Number.isFinite(t) && t > 0 ? t : GSD_DEFAULT_TIMEOUT_S;
}
function innerTimeoutS(outer) { return outer - Math.min(TIMEOUT_MARGIN_S, Math.floor(outer / 5)); }
function readOr(p, dflt) { try { return fs.readFileSync(p, 'utf8'); } catch { return dflt; } }

function stateSig(st) {
  if (!st) return null;
  return `${st.head ?? ''}\t${st.tree ?? ''}`;
}

function treeLabel(before, after) {
  if (!before || !after) return 'unknown';
  return stateSig(before) === stateSig(after) ? 'clean' : 'dirty';
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
  const signalPath = aborting > 0;
  const graceCap = signalPath ? SIGNAL_GRACE_MS : KILL_GRACE_MS;
  const drainCap = signalPath ? SIGNAL_GRACE_MS : PIPE_DRAIN_MS;
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
    let hb = null;

    const finalize = async (reason) => {
      if (settled) return;
      settled = true;
      if (timer) clearTimeout(timer);
      if (hb) clearInterval(hb);
      if (currentFinalize === finalize) currentFinalize = null;
      if (child) killGroup(child, 'SIGTERM');
      if (child && child.exitCode === null && reason !== 'exit') {
        await waitForExit(child, budgetMs(graceCap, finalizeBy));
      }
      if (child) {
        await Promise.all([
          drainStream(child.stdout, budgetMs(drainCap, finalizeBy)),
          drainStream(child.stderr, budgetMs(drainCap, finalizeBy)),
        ]);
        child.stdout?.removeAllListeners('data');
        child.stderr?.removeAllListeners('data');
        child.stdin?.destroy();
        child.stdout?.destroy();
        child.stderr?.destroy();
        killGroup(child, 'SIGKILL');
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

function parseCursorListingIds(stdout) {
  if (typeof stdout !== 'string') return null;
  const ids = [];
  for (const line of stdout.split('\n')) {
    const ln = line.trim();
    if (!ln.includes(' - ')) continue;
    ids.push(ln.split(' - ', 1)[0].trim());
  }
  return ids;
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

function parseListingIds(cli, stdout) {
  if (cli === 'pi') return parsePiListingIds(stdout);
  if (cli === 'opencode') return parseOpencodeListingIds(stdout);
  if (cli === 'cursor') return parseCursorListingIds(stdout);
  if (cli === 'codex') return parseCodexListingIds(stdout);
  return null;
}

async function listModels(cli, binPath, env, limit) {
  if (cli === 'claude') return { ok: false, ids: [], reason: 'no listing' };
  let argv;
  let input;
  if (cli === 'pi') {
    argv = PI_RPC_ARGS;
    input = PI_RPC_REQUEST;
  } else if (cli === 'opencode') {
    argv = ['models'];
  } else if (cli === 'cursor') {
    argv = ['models'];
  } else if (cli === 'codex') {
    argv = ['debug', 'models'];
  } else {
    return { ok: false, ids: [], reason: 'no listing' };
  }
  const r = await runChild(binPath, argv, { cwd: process.cwd(), env, input, capMs: LIST_CAP_MS, limit });
  if (r.timedOut) return { ok: false, ids: [], reason: 'timeout' };
  if (r.spawnErr) return { ok: false, ids: [], reason: 'spawn error' };
  if (r.code !== 0) return { ok: false, ids: [], reason: `exit ${r.code}` };
  const ids = parseListingIds(cli, r.stdout);
  if (ids === null) return { ok: false, ids: [], reason: 'unparseable' };
  if (ids.length === 0) return { ok: false, ids: [], reason: 'no ids' };
  return { ok: true, ids, reason: '' };
}

async function treeState(cwd, limit) {
  const git = which('git', process.env.PATH || '');
  if (!git) return null;
  const headR = await runChild(git, ['rev-parse', 'HEAD'], { cwd, capMs: GIT_CAP_MS, limit });
  if (headR.timedOut || headR.spawnErr) return null;
  let head = null;
  if (headR.code === 0) head = headR.stdout.trim();
  else if (/unborn|unknown revision|bad object/i.test(headR.stderr)) head = null;
  else if (headR.code !== 0) return null;
  const idxDir = fs.mkdtempSync(path.join(os.tmpdir(), 'xai-idx-'));
  const env = { ...process.env, GIT_INDEX_FILE: path.join(idxDir, 'index') };
  try {
    const addR = await runChild(git, ['add', '-A'], { cwd, env, capMs: GIT_CAP_MS, limit });
    if (addR.timedOut || addR.spawnErr || addR.code !== 0) return null;
    const wtR = await runChild(git, ['write-tree'], { cwd, env, capMs: GIT_CAP_MS, limit });
    if (wtR.timedOut || wtR.spawnErr || wtR.code !== 0) return null;
    return { head, tree: wtR.stdout.trim() };
  } finally {
    fs.rmSync(idxDir, { recursive: true, force: true });
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
  process.on(sig, async () => {
    aborting = n;
    if (currentFinalize) await currentFinalize('signal');
    const code = finish('signal', { ...liveFields, exit: 128 + n, tree: liveFields.tree });
    exitFlushed(code);
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

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function runCli(name, rt, binPath, model, mode, prompt, opts = {}) {
  const backoff = opts.backoffS || CONFIG.backoffS;
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'cross-ai-'));
  const ctx = { cwd: process.cwd(), sid: crypto.randomUUID(), outFile: path.join(tmp, 'last-message.md') };
  const env = childEnv(rt.env, process.env);
  let argv = withExtra(name, rt[mode](model, ctx)); let input = prompt;
  try {
    for (let attempt = 0; ; attempt++) {
      log(`cross-ai: cli=${name} bin=${binPath} mode=${mode} attempt=${attempt + 1} timeout=${Math.max(0, Math.round(budgetMs(1000, runDeadline) / 1000))}s`);
      log(`cross-ai: argv=${JSON.stringify(argv)}`);
      const r = await runOnce(binPath, argv, input, env, ctx.cwd, name);
      if (aborting) return { ok: false, code: 128 + aborting, outBytes: r.outBytes, cli_rc: r.code };
      if (r.timedOut) return { ok: false, code: 124, timedOut: true, outBytes: r.outBytes, cli_rc: r.code };
      if (r.spawnErr) return { ok: false, code: r.spawnErr.code === 'ENOENT' ? 127 : 126, error: String(r.spawnErr), outBytes: 0, cli_rc: null };
      const p = rt.parse(r.stdout, ctx);
      const hit = classify(r.stderr, p.error);
      if (hit && hit !== 'transient') {
        return { ok: false, status: hit, outBytes: r.outBytes, cli_rc: r.code ?? '-' };
      }
      if (r.code === 0 && !p.error) {
        if (!p.text.trim()) {
          return { ok: false, status: 'empty_answer', outBytes: r.outBytes, cli_rc: 0 };
        }
        return { ok: true, text: normalize(p.text), outBytes: Buffer.byteLength(r.stdout, 'utf8'), cli_rc: 0 };
      }
      const wait = (backoff[attempt] ?? backoff[backoff.length - 1]) * 1000;
      log(`cross-ai: ${name} failed (exit ${r.code}${r.signal ? ' ' + r.signal : ''}, ${hit || 'crash'}${p.error ? ': ' + p.error.slice(0, 200) : ''})`);
      const exhausted = hit === 'transient' && (
        attempt >= (opts.retries ?? CONFIG.retries) || budgetMs(wait + 60000, runDeadline) <= 0
      );
      if (hit !== 'transient' || exhausted) {
        const st = exhausted ? 'capacity' : 'crash';
        return { ok: false, status: st, outBytes: r.outBytes, cli_rc: r.code ?? '-' };
      }
      await sleep(wait);
      const sid = p.sessionId || (name === 'pi' ? ctx.sid : null);
      if (sid && rt.resume) {
        argv = withExtra(name, rt.resume(model, ctx, sid, mode));
        input = RESUME_MSG;
      } else { input = `${RESUME_MSG}\n\n${prompt}`; }
    }
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

function parseArgs(argv) {
  const o = { prefer: null, models: {}, mode: 'exec', timeout: null, printArgv: false, preamble: true, selfTest: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]; const v = () => { if (i + 1 >= argv.length) throw new Error(`${a} needs a value`); return argv[++i]; };
    if (a === '--prefer') o.prefer = v().split(',').filter(Boolean);
    else if (a.startsWith('--model-')) o.models[a.slice(8)] = v();
    else if (a === '--mode') { o.mode = v(); if (!['exec', 'review'].includes(o.mode)) throw new Error('--mode must be exec or review'); }
    else if (a === '--timeout') { o.timeout = Number(v()); if (!(o.timeout > 0)) throw new Error('--timeout must be > 0'); }
    else if (a === '--print-argv') o.printArgv = true;
    else if (a === '--no-preamble') o.preamble = false;
    else if (a === '--self-test') o.selfTest = true;
    else throw new Error(`unknown argument: ${a}`);
  }
  for (const n of [...(o.prefer || []), ...Object.keys(o.models)]) if (!RUNTIMES[n]) throw new Error(`unknown cli: ${n} (known: ${Object.keys(RUNTIMES).join(', ')})`);
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
    backoffS: [0, 0], extraArgs: {}, heartbeatS: 30, models: {}, outerTimeoutS: 1800,
    prefer: ['pi', 'cursor', 'opencode'], retries: 2, routerBacked: {}, scrubEnv: [...CONFIG.scrubEnv],
    ...override,
  };
  const block = `// <config>\nconst CONFIG = ${JSON.stringify(cfg, null, 2)};\n// </config>`;
  const out = src.replace(/\/\/ <config>[\s\S]*?\/\/ <\/config>/, block);
  const p = path.join(tmp, `runner-${name}.mjs`);
  fs.writeFileSync(p, out);
  return p;
}

function writeGitWrapper(binDir, realGit) {
  const body = `#!/usr/bin/env node
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
const realGit = ${JSON.stringify(realGit)};
const home = process.env.HOME || '';
const sub = process.argv.slice(2);
if (sub[0] === 'write-tree') {
  if (fs.existsSync(path.join(home, '.fake-git-hang'))) { while (true) {} }
  if (fs.existsSync(path.join(home, '.fake-git-fail'))) process.exit(128);
}
const r = spawnSync(realGit, sub, { stdio: 'inherit' });
process.exit(r.status ?? 1);
`;
  const p = path.join(binDir, 'git');
  fs.writeFileSync(p, body);
  fs.chmodSync(p, 0o755);
}

function writeFakePi(binDir) {
  const body = String.raw`#!/usr/bin/env node
import fs from 'node:fs';
import { spawn } from 'node:child_process';
const args = process.argv;
let model = '';
for (let i = 0; i < args.length; i++) if (args[i] === '--model') model = args[++i] || '';
const fakeMode = model.startsWith('fake/') ? model.slice(5) : '';
const calls = process.env.FAKE_CALLS;
const log = (line) => { if (calls) fs.appendFileSync(calls, line + '\n'); };
const STICKY_FAKE = new Set(['hang', 'gcescape']);
const FAKE_MODES = {
  ok: () => { fs.appendFileSync('a.txt', 'ok-line\n'); process.stdout.write('# Summary\nok'); },
  ansi: () => { fs.appendFileSync('a.txt', 'x\n'); process.stdout.write('\x1B[0mDone.## Summary\nC# is fine. Use ## inline'); },
  nochange: () => { process.stdout.write('# Summary\nno edits'); },
  empty: () => {},
  crash: () => { process.stderr.write('boom\n'); process.exit(7); },
  quote: () => {
    fs.appendFileSync('a.txt', 'q\n');
    process.stdout.write('429 rate limit and billing noted.\n# Summary\nok');
  },
  billing: () => { process.stderr.write('402 payment required\n'); process.exit(1); },
  auth: () => { process.stderr.write('401 unauthorized\n'); process.exit(1); },
  perm: () => { process.stderr.write('permission denied\n'); process.exit(1); },
  quota: () => { process.stderr.write('quota exceeded\n'); process.exit(1); },
  dirtycrash: () => { fs.appendFileSync('a.txt', 'd\n'); process.stderr.write('boom\n'); process.exit(7); },
  reedit: () => { fs.appendFileSync('dirty.txt', 'more\n'); process.stdout.write('# Summary\nok'); },
  hang: () => {
    const gc = spawn(process.execPath, ['-e', 'while(true){}'], { stdio: 'ignore' });
    fs.writeFileSync('gc.pid', String(gc.pid));
    setInterval(() => {}, 1 << 30);
  },
  gcpipe: () => {
    const gc = spawn(process.execPath, ['-e', 'while(true){}'], { stdio: 'inherit' });
    fs.writeFileSync('gc.pid', String(gc.pid));
    fs.appendFileSync('a.txt', 'gp\n');
    process.stdout.write('# Summary\nok');
  },
  gcterm: () => {
    const gc = spawn(process.execPath, ['-e', 'process.on("SIGTERM",()=>{});while(true){}'], { stdio: 'inherit' });
    fs.writeFileSync('gc.pid', String(gc.pid));
    fs.appendFileSync('a.txt', 'gt\n');
    process.stdout.write('# Summary\nok');
  },
  gcescape: () => {
    const gc = spawn(process.execPath, ['-e', 'const fs=require("fs");fs.writeFileSync("gc.pid",String(process.pid));setInterval(()=>process.stderr.write("gc-late"+String.fromCharCode(10)),100);setInterval(()=>{},1<<30);'], { detached: true, stdio: ['ignore', 'pipe', 'pipe'] });
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
let stdin = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (d) => { stdin += d; });
process.stdin.on('end', () => {
  const fn = FAKE_MODES[fakeMode];
  if (!fn) process.exit(1);
  fn();
  if (!STICKY_FAKE.has(fakeMode)) process.exit(0);
});
}
`;
  const p = path.join(binDir, 'pi');
  fs.writeFileSync(p, body);
  fs.chmodSync(p, 0o755);
}

function writeFakeCursor(binDir) {
  const body = String.raw`#!/usr/bin/env node
import fs from 'node:fs';
const calls = process.env.FAKE_CALLS;
const sub = process.argv.slice(2);
if (sub[0] === 'models') {
  if (calls) fs.appendFileSync(calls, 'cursor-agent models\n');
  console.log('Available models');
  console.log('');
  if (process.env.FAKE_CURSOR_LIST !== 'empty') {
    for (const id of ['fake-ok-cursor', 'fake-err-cursor']) console.log(id + ' - label');
  }
  process.exit(0);
}
let model = '';
for (let i = 0; i < process.argv.length; i++) if (process.argv[i] === '--model') model = process.argv[++i] || '';
if (calls) fs.appendFileSync(calls, 'cursor-agent ' + model + '\n');
process.stdin.on('data', () => {}).on('end', () => {
  if (model === 'fake-err-cursor') {
    console.log(JSON.stringify({ type: 'result', is_error: true, result: '401 unauthorized', session_id: 'c2' }));
    process.exit(0);
  }
  fs.appendFileSync('a.txt', 'cursor\n');
  console.log(JSON.stringify({ type: 'result', subtype: 'success', is_error: false, result: '## Summary\nok', session_id: 'c1' }));
});
`;
  const p = path.join(binDir, 'cursor-agent');
  fs.writeFileSync(p, body);
  fs.chmodSync(p, 0o755);
}

function writeFakeOpencode(binDir) {
  const body = String.raw`#!/usr/bin/env node
import fs from 'node:fs';
const calls = process.env.FAKE_CALLS;
const sub = process.argv.slice(2);
if (sub[0] === 'models') {
  if (calls) fs.appendFileSync(calls, 'opencode models\n');
  console.log('fake/ok');
  process.exit(0);
}
let model = '';
for (let i = 0; i < process.argv.length; i++) if (process.argv[i] === '--model') model = process.argv[++i] || '';
if (calls) fs.appendFileSync(calls, 'opencode ' + model + '\n');
process.stdin.on('data', () => {}).on('end', () => {
  fs.appendFileSync('a.txt', 'oc\n');
  const lines = [
    JSON.stringify({ type: 'text', sessionID: 'ses_1', part: { id: 'p1', messageID: 'm1', type: 'text', text: 'Plan first.' } }),
    JSON.stringify({ type: 'tool_use', sessionID: 'ses_1', part: { type: 'tool', tool: 'bash' } }),
    JSON.stringify({ type: 'text', sessionID: 'ses_1', part: { id: 'p2', messageID: 'm2', type: 'text', text: '## Summary\ndone' } }),
  ];
  for (const l of lines) console.log(l);
});
`;
  const p = path.join(binDir, 'opencode');
  fs.writeFileSync(p, body);
  fs.chmodSync(p, 0o755);
}

function writeFakeCodex(binDir) {
  const body = String.raw`#!/usr/bin/env node
import fs from 'node:fs';
const calls = process.env.FAKE_CALLS;
const sub = process.argv.slice(2);
if (sub[0] === 'debug' && sub[1] === 'models') {
  if (calls) fs.appendFileSync(calls, 'codex models\n');
  console.log(JSON.stringify({ models: [{ slug: 'fake-ok-codex', visibility: 'list' }] }));
  process.exit(0);
}
let model = '';
let outFile = '';
for (let i = 0; i < process.argv.length; i++) {
  if (process.argv[i] === '-m') model = process.argv[++i] || '';
  if (process.argv[i] === '-o') outFile = process.argv[++i] || '';
}
if (calls) fs.appendFileSync(calls, 'codex ' + model + '\n');
process.stdin.on('data', () => {}).on('end', () => {
  fs.appendFileSync('a.txt', 'cx\n');
  if (outFile) fs.writeFileSync(outFile, '## Summary\nok');
  console.log(JSON.stringify({ type: 'thread.started', thread_id: 't1' }));
});
`;
  const p = path.join(binDir, 'codex');
  fs.writeFileSync(p, body);
  fs.chmodSync(p, 0o755);
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
  try { process.kill(pid, 0); return true; } catch { return false; }
}

function runSelfTestCaseSync(tmp, spec, repo, home, calls, copy, env) {
  const t0 = Date.now();
  const r = spawnSync(process.execPath, [copy, ...(spec.args || [])], {
    cwd: repo, env, input: spec.stdin ?? 'prompt\n', encoding: 'utf8', timeout: 30000,
  });
  const elapsedMs = Date.now() - t0;
  if (r.status !== spec.exit) return `exit ${r.status} expected ${spec.exit}`;
  const err = statusLineOk(r.stderr || '', spec.status);
  if (err) return err;
  const callLines = fs.existsSync(calls) ? fs.readFileSync(calls, 'utf8').trim().split('\n').filter(Boolean) : [];
  if (spec.check) {
    const cErr = spec.check(r, { repo, home, calls: callLines, elapsedMs });
    if (cErr) return cErr;
  }
  return null;
}

function runSelfTestCaseSpawn(tmp, spec, repo, home, calls, copy, env) {
  return new Promise((resolve) => {
    const t0 = Date.now();
    const child = spawn(process.execPath, [copy, ...(spec.args || [])], {
      cwd: repo, env, stdio: ['pipe', 'pipe', 'pipe'],
    });
    child.stdin.write(spec.stdin ?? 'prompt\n');
    child.stdin.end();
    let stderr = '';
    child.stderr.on('data', (d) => { stderr += d.toString('utf8'); });
    const sigAt = setTimeout(() => child.kill('SIGTERM'), 1000);
    const hard = setTimeout(() => {
      try { child.kill('SIGKILL'); } catch { /* gone */ }
      resolve('spawn case hung past 30s');
    }, 30000);
    child.on('exit', (code) => {
      clearTimeout(sigAt);
      clearTimeout(hard);
      const elapsedMs = Date.now() - t0;
      if (code !== spec.exit) return resolve(`exit ${code} expected ${spec.exit}`);
      const err = statusLineOk(stderr, spec.status);
      if (err) return resolve(err);
      if (elapsedMs > 3000) return resolve(`elapsed ${elapsedMs}ms > 3000ms after signal`);
      const callLines = fs.existsSync(calls) ? fs.readFileSync(calls, 'utf8').trim().split('\n').filter(Boolean) : [];
      if (spec.check) {
        const cErr = spec.check({ stderr, status: code }, { repo, home, calls: callLines, elapsedMs });
        if (cErr) return resolve(cErr);
      }
      resolve(null);
    });
  });
}

async function runSelfTestCase(tmp, spec) {
  const repo = path.join(tmp, `r-${spec.name}`);
  fs.mkdirSync(repo, { recursive: true });
  spawnSync('git', ['init', '-q'], { cwd: repo, env: hermeticEnv(tmp, { HOME: path.join(tmp, 'home-git') }) });
  fs.writeFileSync(path.join(repo, 'a.txt'), 'base\n');
  spawnSync('git', ['add', 'a.txt'], { cwd: repo, env: hermeticEnv(tmp, { HOME: path.join(tmp, 'home-git') }) });
  spawnSync('git', ['commit', '-q', '-m', 'init'], { cwd: repo, env: hermeticEnv(tmp, { HOME: path.join(tmp, 'home-git') }) });
  const home = path.join(tmp, `home-${spec.name}`);
  fs.mkdirSync(home, { recursive: true });
  const calls = path.join(tmp, `calls-${spec.name}.log`);
  const copy = writeCopy(tmp, spec.name, spec.config || {});
  const env = hermeticEnv(tmp, { HOME: home, XDG_CONFIG_HOME: path.join(home, '.config'), FAKE_CALLS: calls, ...(spec.env || {}) });
  if (spec.setup) {
    const se = spec.setup({ repo, home, tmp, calls });
    if (se) return se;
  }
  if (spec.spawn) return runSelfTestCaseSpawn(tmp, spec, repo, home, calls, copy, env);
  return runSelfTestCaseSync(tmp, spec, repo, home, calls, copy, env);
}

async function blackBoxSelfTest() {
  const gitBin = which('git');
  if (!gitBin) {
    process.stderr.write('self-test: git not found\n');
    return 1;
  }
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'xai-st-'));
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
    for (const name of fs.readdirSync(binDir)) {
      if (name === 'codex') continue;
      const src = path.join(binDir, name);
      const dst = path.join(binNoCodex, name);
      if (!fs.existsSync(dst)) fs.symlinkSync(src, dst);
    }

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
                pi: ['-p'], cursor: ['--trust', '--force', 'disabled'], opencode: ['--auto'],
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
        check: (_r, ctx) => {
          const pidFile = path.join(ctx.repo, 'gc.pid');
          if (!fs.existsSync(pidFile)) return null;
          const pid = Number(fs.readFileSync(pidFile, 'utf8'));
          return pidAlive(pid) ? 'grandchild still alive' : null;
        },
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
        spawn: true,
        args: ['--prefer', 'pi', '--model-pi', 'fake/hang', '--timeout', '60'],
        exit: 143,
        status: /^AIKIT-XAI status=signal .* exit=143 .* action=stop$/,
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
          const pidFile = path.join(ctx.repo, 'gc.pid');
          if (fs.existsSync(pidFile)) {
            try { process.kill(Number(fs.readFileSync(pidFile, 'utf8')), 'SIGKILL'); } catch { /* esrch */ }
          }
          return null;
        },
      },
      {
        name: 'gcpipe',
        args: ['--prefer', 'pi', '--model-pi', 'fake/gcpipe', '--timeout', '60'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/gcpipe exit=0 .* action=stop$/,
        check: (_r, ctx) => {
          if (ctx.elapsedMs >= 15000) return `elapsed ${ctx.elapsedMs}`;
          const pidFile = path.join(ctx.repo, 'gc.pid');
          if (!fs.existsSync(pidFile)) return null;
          return pidAlive(Number(fs.readFileSync(pidFile, 'utf8'))) ? 'gc alive' : null;
        },
      },
      {
        name: 'gcterm',
        args: ['--prefer', 'pi', '--model-pi', 'fake/gcterm', '--timeout', '60'],
        exit: 0,
        status: /^AIKIT-XAI status=ok cli=pi model=fake\/gcterm exit=0 .* action=stop$/,
        check: (_r, ctx) => {
          if (ctx.elapsedMs >= 15000) return `elapsed ${ctx.elapsedMs}`;
          const pidFile = path.join(ctx.repo, 'gc.pid');
          if (!fs.existsSync(pidFile)) return null;
          return pidAlive(Number(fs.readFileSync(pidFile, 'utf8'))) ? 'gc alive' : null;
        },
      },
      {
        name: 'git-before-fail',
        setup: (ctx) => { fs.writeFileSync(path.join(ctx.home, '.fake-git-fail'), '1'); return null; },
        args: ['--prefer', 'pi,cursor', '--model-pi', 'fake/ok', '--model-cursor', 'fake-ok-cursor'],
        exit: 1,
        status: /^AIKIT-XAI status=unverified cli=pi model=fake\/ok exit=1 cli_rc=- elapsed=\d+s out=0 tree=unknown action=stop$/,
        check: (_r, ctx) => {
          if (ctx.calls.some((l) => l === 'pi ok' || l.startsWith('cursor-agent'))) return `calls=${ctx.calls.join(',')}`;
          return null;
        },
      },
      {
        name: 'git-after-fail',
        args: ['--prefer', 'pi,cursor', '--model-pi', 'fake/gitfail', '--model-cursor', 'fake-ok-cursor'],
        exit: 1,
        status: /^AIKIT-XAI status=unverified cli=pi model=fake\/gitfail exit=1 cli_rc=0 elapsed=\d+s out=\d+ tree=unknown action=stop$/,
        check: (_r, ctx) => (ctx.calls.some((l) => l.startsWith('cursor-agent')) ? 'cursor ran' : null),
      },
      {
        name: 'git-hang',
        setup: (ctx) => { fs.writeFileSync(path.join(ctx.home, '.fake-git-hang'), '1'); return null; },
        args: ['--prefer', 'pi', '--model-pi', 'fake/ok', '--timeout', '3'],
        exit: 1,
        status: /^AIKIT-XAI status=unverified cli=pi model=fake\/ok exit=1 cli_rc=- elapsed=\d+s out=0 tree=unknown action=stop$/,
        check: (_r, ctx) => (ctx.elapsedMs >= 10000 ? `elapsed ${ctx.elapsedMs}` : null),
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
        status: /^AIKIT-XAI status=timeout cli=pi model=fake\/ok exit=124 .* action=stop$/,
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
        check: (_r, ctx) => {
          const flaky = ctx.calls.filter((l) => l === 'pi flaky');
          if (flaky.length !== 2) return `flaky calls=${flaky.length}`;
          const st = spawnSync('git', ['status', '--porcelain'], { cwd: ctx.repo, encoding: 'utf8' });
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

    ];

    let failed = false;
    for (const c of cases) {
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
    fs.rmSync(tmp, { recursive: true, force: true });
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
  const order = o.prefer || CONFIG.prefer;
  const models = { ...CONFIG.models, ...o.models };
  const cands = order.map((name) => ({
    name, rt: RUNTIMES[name], model: models[name],
    bin: RUNTIMES[name].bins.map((b) => which(b, process.env.PATH || '')).find(Boolean) || null,
  }));

  if (o.printArgv) {
    const ctx = { cwd: process.cwd(), sid: '<uuid>', outFile: '<tmp>/last-message.md' };
    for (const c of cands) {
      const argvOut = c.model ? withExtra(c.name, c.rt[o.mode](c.model, ctx)) : null;
      process.stdout.write(`${c.name}\t${c.bin || 'MISSING'}\t${argvOut ? JSON.stringify(argvOut) : 'NO MODEL'}\n`);
    }
    return finish('ok', { ...liveFields, tree: 'clean', exit: 0, out: 0 });
  }
  const raw = readStdin();
  if (!raw || !raw.trim()) {
    log('cross-ai: pipe the prompt on stdin');
    return finish('empty_stdin', { ...liveFields, tree: 'clean', exit: 2 });
  }
  const prompt = raw + (o.preamble ? (o.mode === 'exec' ? EXEC_PREAMBLE : REVIEW_PREAMBLE) : '');
  const outer = outerTimeoutS(process.cwd());
  const innerDefault = innerTimeoutS(outer);
  const innerS = o.timeout ?? innerDefault;
  runDeadline = Date.now() + innerS * 1000;
  const marginMs = (outer - innerDefault) * 1000;
  finalizeBy = runDeadline + Math.min(FINALIZE_CAP_MS, Math.floor(marginMs / 2));

  let last = null;
  let sawModel = false;
  for (const c of cands) {
    if (!c.bin) { log(`cross-ai: ${c.name} not installed, skipping`); continue; }
    if (!c.model) {
      log(`cross-ai: no model configured for ${c.name} (--model-${c.name}), skipping`);
      last = last || { kind: 'no_model' };
      continue;
    }
    sawModel = true;
    liveFields.cli = c.name;
    liveFields.model = c.model;
    const before = await treeState(process.cwd(), runDeadline);
    if (before === null) {
      return finish('unverified', { ...liveFields, cli_rc: '-', tree: 'unknown', exit: 1 });
    }
    const listEnv = childEnv(c.rt.env, process.env);
    const listing = await listModels(c.name, c.bin, listEnv, runDeadline);
    if (listing.ok) {
      if (!listing.ids.includes(c.model)) {
        log(`cross-ai: ${c.name} bad_model (${c.model} not in model list)`);
        last = { status: 'bad_model', cli: c.name, model: c.model, tree: 'clean', cli_rc: '-' };
        if (tryNextCli('bad_model', 'clean')) {
          log(`cross-ai: ${c.name} bad_model, trying the next CLI`);
          continue;
        }
        return finish('bad_model', { ...liveFields, tree: 'clean', cli_rc: '-' });
      }
    } else if (listing.reason !== 'no listing') {
      log(`cross-ai: ${c.name} model list unavailable (${listing.reason}); not preflighted`);
    }
    const r = await runCli(c.name, c.rt, c.bin, c.model, o.mode, prompt);
    liveFields.out = r.outBytes || 0;
    liveFields.cli_rc = r.cli_rc ?? '-';
    const after = await treeState(process.cwd(), finalizeBy);
    const tree = treeLabel(before, after);
    liveFields.tree = tree;
    if (r.timedOut || aborting) {
      return finish('timeout', { ...liveFields, tree, exit: 124, cli_rc: r.cli_rc ?? 124 });
    }
    if (r.ok) {
      if (after === null) {
        return finish('unverified', { ...liveFields, tree: 'unknown', cli_rc: 0, exit: 1 });
      }
      if (tree === 'clean') {
        last = { status: 'no_change', cli: c.name, model: c.model, tree, cli_rc: 0 };
        log(`cross-ai: ${c.name} answered without repo change, trying the next CLI`);
        continue;
      }
      process.stdout.write(r.text);
      return finish('ok', { ...liveFields, tree, exit: 0, cli_rc: 0, out: r.outBytes || 0 });
    }
    const status = r.status || 'crash';
    const treeField = after === null ? 'unknown' : tree;
    liveFields.tree = treeField;
    last = { status, cli: c.name, model: c.model, tree: treeField, cli_rc: r.cli_rc };
    if (tryNextCli(status, treeField)) {
      log(`cross-ai: ${c.name} ${status}, trying the next CLI`);
      continue;
    }
    return finish(status, { ...liveFields, tree: treeField, cli_rc: r.cli_rc, cli: c.name, model: c.model });
  }
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
    (code) => {
      if (finished) exitFlushed(code);
      else exitFlushed(code ?? 0);
    },
    (e) => {
      log(`cross-ai: internal error: ${e && e.stack || e}`);
      exitFlushed(finish('crash', { ...liveFields, tree: 'unknown', exit: 1, cli_rc: '-' }));
    },
  );
}

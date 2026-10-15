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

const TRANSIENT = /temporarily unavailable|cooling down|is locked|rate.?limit|overloaded|too many requests|\b429\b|\b50[234]\b|service unavailable|ECONNRESET|ETIMEDOUT|socket hang up|stream (?:closed|disconnected)/i;
const FATAL = /\b40[123]\b|spending limit|billing|quota exceeded|insufficient_quota|token_expired|invalid_refresh_token|could not be refreshed|not logged in|log ?in required|please (?:log|sign) ?in|unauthori[sz]ed|invalid api key|requires an opencode API key|pre-dispatch filters|credential gate|model not found|unknown model|invalid model/i;

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
};

let runStartedMs = Date.now();
let liveFields = { cli: '-', model: '-', cli_rc: '-', out: 0, tree: 'clean' };

function finish(status, fields) {
  const row = STATUS_TABLE[status] || { exit: 1, action: 'stop' };
  let action = fields.action ?? row.action;
  const tree = fields.tree ?? 'unknown';
  if (action === 'fallback' && (tree === 'dirty' || tree === 'unknown')) action = 'stop';
  if (status === 'billing' && fields.cli && CONFIG.routerBacked[fields.cli]) action = 'retry-later';
  const exit = fields.exit ?? row.exit;
  const elapsed = fields.elapsed ?? Math.max(0, Math.round((Date.now() - runStartedMs) / 1000));
  const line = `AIKIT-XAI status=${status} cli=${fields.cli ?? '-'} model=${fields.model ?? '-'} ` +
    `exit=${exit} cli_rc=${fields.cli_rc ?? '-'} elapsed=${elapsed}s out=${fields.out ?? 0} ` +
    `tree=${tree} action=${action}`;
  process.stderr.write(`${line}\n`);
  return exit;
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

function classify(blob) {
  if (FATAL.test(blob)) return 'fatal';
  if (TRANSIENT.test(blob)) return 'transient';
  return 'other';
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

function gitState(cwd) {
  const head = spawnSync('git', ['rev-parse', 'HEAD'], { cwd, encoding: 'utf8' });
  const st = spawnSync('git', ['status', '--porcelain'], { cwd, encoding: 'utf8' });
  return head.status === 0 && st.status === 0 ? head.stdout + st.stdout : null;
}

function treeAfter(before, cwd) {
  if (before === null) return 'unknown';
  const after = gitState(cwd);
  if (after === null) return 'unknown';
  return before === after ? 'clean' : 'dirty';
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

let current = null;
let aborting = 0;

function killGroup(child, sig) { try { process.kill(-child.pid, sig); } catch { try { child.kill(sig); } catch { /* gone */ } } }

for (const [sig, n] of [['SIGTERM', 15], ['SIGINT', 2], ['SIGHUP', 1]]) {
  process.on(sig, () => {
    aborting = n;
    if (!current) {
      finish('signal', { ...liveFields, exit: 128 + n, tree: 'unknown' });
      process.exit(128 + n);
    }
    killGroup(current, 'SIGTERM');
    setTimeout(() => {
      if (current) killGroup(current, 'SIGKILL');
      finish('signal', { ...liveFields, exit: 128 + n, tree: liveFields.tree });
      process.exit(128 + n);
    }, 2000).unref();
  });
}

function runOnce(bin, argv, input, env, cwd, deadline, label) {
  return new Promise((resolve) => {
    const child = spawn(bin, argv, { cwd, env, stdio: ['pipe', 'pipe', 'pipe'], detached: true });
    current = child;
    const out = []; let outBytes = 0; let errTail = ''; let timedOut = false; let lastBytes = 0;
    const started = Date.now();
    child.stdout.on('data', (d) => { out.push(d); outBytes += d.length; });
    child.stderr.on('data', (d) => { process.stderr.write(d); errTail = (errTail + d).slice(-65536); });
    child.stdin.on('error', () => { /* CLI closed stdin early */ });
    child.stdin.end(input);
    const hb = setInterval(() => {
      process.stderr.write(`cross-ai: ${label} running ${Math.round((Date.now() - started) / 1000)}s, stdout +${outBytes - lastBytes} bytes\n`);
      lastBytes = outBytes;
    }, CONFIG.heartbeatS * 1000);
    const ms = Math.max(0, deadline - Date.now());
    const timer = setTimeout(() => {
      timedOut = true;
      killGroup(child, 'SIGTERM');
      setTimeout(() => killGroup(child, 'SIGKILL'), 5000).unref();
    }, ms);
    const done = (code, signal, spawnErr) => {
      clearInterval(hb); clearTimeout(timer); current = null;
      resolve({ code, signal, timedOut, spawnErr, stdout: Buffer.concat(out).toString('utf8'), stderr: errTail, outBytes });
    };
    child.on('error', (e) => done(null, null, e));
    child.on('close', (code, signal) => done(code, signal, null));
  });
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function runCli(name, rt, binPath, model, mode, prompt, deadline, opts = {}) {
  const backoff = opts.backoffS || CONFIG.backoffS;
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'cross-ai-'));
  const ctx = { cwd: process.cwd(), sid: crypto.randomUUID(), outFile: path.join(tmp, 'last-message.md') };
  const env = childEnv(rt.env, process.env);
  let argv = withExtra(name, rt[mode](model, ctx)); let input = prompt;
  try {
    for (let attempt = 0; ; attempt++) {
      process.stderr.write(`cross-ai: cli=${name} bin=${binPath} mode=${mode} attempt=${attempt + 1} timeout=${Math.round((deadline - Date.now()) / 1000)}s\n`);
      process.stderr.write(`cross-ai: argv=${JSON.stringify(argv)}\n`);
      const r = await runOnce(binPath, argv, input, env, ctx.cwd, deadline, name);
      if (aborting) return { ok: false, code: 128 + aborting, outBytes: r.outBytes, cli_rc: r.code };
      if (r.timedOut) return { ok: false, code: 124, timedOut: true, outBytes: r.outBytes, cli_rc: r.code };
      if (r.spawnErr) return { ok: false, code: r.spawnErr.code === 'ENOENT' ? 127 : 126, error: String(r.spawnErr), outBytes: 0, cli_rc: null };
      const p = rt.parse(r.stdout, ctx);
      if (r.code === 0 && !p.error && p.text.trim()) {
        return { ok: true, text: normalize(p.text), outBytes: Buffer.byteLength(r.stdout, 'utf8'), cli_rc: r.code ?? 0 };
      }
      const blob = `${r.stderr}\n${p.error || ''}\n${r.stdout.slice(-4000)}`;
      const kind = classify(blob);
      const wait = (backoff[attempt] ?? backoff[backoff.length - 1]) * 1000;
      process.stderr.write(`cross-ai: ${name} failed (exit ${r.code}${r.signal ? ' ' + r.signal : ''}, ${kind}${p.error ? ': ' + p.error.slice(0, 200) : ''})\n`);
      if (kind !== 'transient' || attempt >= (opts.retries ?? CONFIG.retries) || deadline - Date.now() < wait + 60000) {
        return { ok: false, code: r.code || 1, kind, outBytes: r.outBytes, cli_rc: r.code };
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

function writeFakePi(binDir) {
  const body = String.raw`#!/usr/bin/env node
import fs from 'node:fs';
const args = process.argv;
let model = '';
for (let i = 0; i < args.length; i++) if (args[i] === '--model') model = args[++i] || '';
const fakeMode = model.startsWith('fake/') ? model.slice(5) : '';
const calls = process.env.FAKE_CALLS;
const log = (line) => { if (calls) fs.appendFileSync(calls, line + '\n'); };
const FAKE_MODES = {
  ok: () => { fs.appendFileSync('a.txt', 'ok-line\n'); process.stdout.write('# Summary\nok'); },
  ansi: () => { fs.appendFileSync('a.txt', 'x\n'); process.stdout.write('\x1B[0mDone.## Summary\nC# is fine. Use ## inline'); },
};
const modeIdx = args.indexOf('--mode');
if (modeIdx >= 0 && args[modeIdx + 1] === 'rpc') {
  log('pi rpc');
  if (process.env.FAKE_PI_LIST === 'broken') { console.log('not json'); process.exit(0); }
  if (process.env.FAKE_PI_LIST === 'fail') process.exit(1);
  const models = Object.keys(FAKE_MODES).map((k) => ({ provider: 'fake', id: k }));
  console.log(JSON.stringify({ id: '1', type: 'response', command: 'get_available_models', success: true, data: { models } }));
  process.exit(0);
}
log('pi ' + (fakeMode || model));
let stdin = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (d) => { stdin += d; });
process.stdin.on('end', () => {
  const fn = FAKE_MODES[fakeMode];
  if (!fn) process.exit(1);
  fn();
  process.exit(0);
});
`;
  const p = path.join(binDir, 'pi');
  fs.writeFileSync(p, body);
  fs.chmodSync(p, 0o755);
}

function writeFakeCursor(binDir) {
  const body = String.raw`#!/usr/bin/env node
import fs from 'node:fs';
let model = '';
for (let i = 0; i < process.argv.length; i++) if (process.argv[i] === '--model') model = process.argv[++i] || '';
const calls = process.env.FAKE_CALLS;
if (calls) fs.appendFileSync(calls, 'cursor-agent ' + model + '\n');
let s = '';
process.stdin.on('data', (d) => { s += d; }).on('end', () => {
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
let model = '';
for (let i = 0; i < process.argv.length; i++) if (process.argv[i] === '--model') model = process.argv[++i] || '';
const calls = process.env.FAKE_CALLS;
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
let model = '';
let outFile = '';
for (let i = 0; i < process.argv.length; i++) {
  if (process.argv[i] === '-m') model = process.argv[++i] || '';
  if (process.argv[i] === '-o') outFile = process.argv[++i] || '';
}
const calls = process.env.FAKE_CALLS;
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

function runSelfTestCase(tmp, spec) {
  const repo = path.join(tmp, `r-${spec.name}`);
  fs.mkdirSync(repo, { recursive: true });
  spawnSync('git', ['init', '-q'], { cwd: repo, env: hermeticEnv(tmp, { HOME: path.join(tmp, 'home-git') }) });
  fs.writeFileSync(path.join(repo, 'a.txt'), 'base\n');
  spawnSync('git', ['add', 'a.txt'], { cwd: repo, env: hermeticEnv(tmp, { HOME: path.join(tmp, 'home-git') }) });
  spawnSync('git', ['commit', '-q', '-m', 'init'], { cwd: repo, env: hermeticEnv(tmp, { HOME: path.join(tmp, 'home-git') }) });
  const home = path.join(tmp, `home-${spec.name}`);
  const calls = path.join(tmp, `calls-${spec.name}.log`);
  const copy = writeCopy(tmp, spec.name, spec.config || {});
  const env = hermeticEnv(tmp, { HOME: home, XDG_CONFIG_HOME: path.join(home, '.config'), FAKE_CALLS: calls, ...(spec.env || {}) });
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

function blackBoxSelfTest() {
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
    fs.symlinkSync(gitBin, path.join(binDir, 'git'));
    writeFakePi(binDir);
    writeFakeCursor(binDir);
    writeFakeOpencode(binDir);
    writeFakeCodex(binDir);

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
        check: (r) => (r.stdout === '## Summary\ndone\n' ? null : `stdout=${JSON.stringify(r.stdout)}`),
      },
      {
        name: 'parser-codex',
        args: ['--prefer', 'codex', '--model-codex', 'fake-ok-codex'],
        config: { prefer: ['codex'] },
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=dirty action=stop$/,
        check: (r) => (r.stdout === '## Summary\nok\n' ? null : `stdout=${JSON.stringify(r.stdout)}`),
      },
      {
        name: 'parser-pi-ansi',
        args: ['--prefer', 'pi', '--model-pi', 'fake/ansi'],
        exit: 0,
        status: /^AIKIT-XAI status=ok .* tree=dirty action=stop$/,
        check: (r) => (r.stdout === 'Done.\n\n## Summary\nC# is fine. Use ## inline\n' ? null : `stdout=${JSON.stringify(r.stdout)}`),
      },
    ];

    let failed = false;
    for (const c of cases) {
      const reason = runSelfTestCase(tmp, c);
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
  liveFields = { cli: '-', model: '-', cli_rc: '-', out: 0, tree: 'clean' };
  let o;
  try { o = parseArgs(argv); } catch (e) {
    process.stderr.write(`cross-ai: ${e.message}\n`);
    return finish('usage', { ...liveFields, tree: 'unknown', exit: 2 });
  }
  if (o.selfTest) return blackBoxSelfTest();
  const order = o.prefer || CONFIG.prefer;
  const models = { ...CONFIG.models, ...o.models };
  const cands = order.map((name) => ({
    name, rt: RUNTIMES[name], model: models[name],
    bin: RUNTIMES[name].bins.map((b) => which(b)).find(Boolean) || null,
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
    process.stderr.write('cross-ai: pipe the prompt on stdin\n');
    return finish('empty_stdin', { ...liveFields, tree: 'clean', exit: 2 });
  }
  const prompt = raw + (o.preamble ? (o.mode === 'exec' ? EXEC_PREAMBLE : REVIEW_PREAMBLE) : '');
  const innerS = o.timeout || innerTimeoutS(outerTimeoutS(process.cwd()));
  const deadline = Date.now() + innerS * 1000;

  let last = null;
  let sawModel = false;
  for (const c of cands) {
    if (!c.bin) { process.stderr.write(`cross-ai: ${c.name} not installed, skipping\n`); continue; }
    if (!c.model) {
      process.stderr.write(`cross-ai: no model configured for ${c.name} (--model-${c.name}), skipping\n`);
      last = last || { kind: 'no_model' };
      continue;
    }
    sawModel = true;
    liveFields.cli = c.name;
    liveFields.model = c.model;
    const before = gitState(process.cwd());
    const r = await runCli(c.name, c.rt, c.bin, c.model, o.mode, prompt, deadline);
    liveFields.out = r.outBytes || 0;
    liveFields.cli_rc = r.cli_rc ?? r.code ?? '-';
    const tree = treeAfter(before, process.cwd());
    liveFields.tree = tree;
    if (r.ok) {
      process.stdout.write(r.text);
      return finish('ok', { ...liveFields, tree, exit: 0, cli_rc: 0, out: r.outBytes || 0 });
    }
    if (r.timedOut || aborting) {
      return finish('timeout', { ...liveFields, tree, exit: r.code, cli_rc: r.cli_rc ?? r.code });
    }
    last = { ...r, tree, cli: c.name, model: c.model };
    if (tree !== 'clean') {
      return finish('crash', { ...liveFields, tree, exit: r.code || 1, cli_rc: r.cli_rc ?? r.code });
    }
    process.stderr.write(`cross-ai: ${c.name} failed without touching the repo, trying the next CLI\n`);
  }
  if (!sawModel && last && last.kind === 'no_model') {
    return finish('no_model', { ...liveFields, tree: 'clean', exit: 2 });
  }
  if (!last) {
    process.stderr.write(`cross-ai: none of [${order.join(', ')}] is installed\n`);
    return finish('not_installed', { ...liveFields, tree: 'clean', exit: 127 });
  }
  return finish('crash', { ...liveFields, cli: last.cli || '-', model: last.model || '-', tree: last.tree || 'unknown', exit: last.code || 1, cli_rc: last.cli_rc ?? last.code });
}

if (process.argv[1] && fs.realpathSync(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(process.argv.slice(2)).then(
    (code) => { process.exitCode = code; },
    (e) => {
      process.stderr.write(`cross-ai: internal error: ${e && e.stack || e}\n`);
      process.exitCode = finish('crash', { ...liveFields, tree: 'unknown', exit: 1, cli_rc: '-' });
    },
  );
}

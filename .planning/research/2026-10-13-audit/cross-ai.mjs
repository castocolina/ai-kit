#!/usr/bin/env node
// ai-kit-cross-ai generator=ai-kit-gsd-curated-config template=1 sha256=41d4a79c1fc423662c7ad9a07c68d92605472da20640e4d00c6f87b6ab3d24ec
/*
 * cross-ai.mjs: the GSD `workflow.cross_ai_command` dispatcher.
 *
 * GSD runs:  echo "$TASK_PROMPT" | gsd-tools run-with-timeout $T -- node .planning/cross-ai.mjs [flags]
 *   - The prompt arrives on stdin. stdout becomes the plan's SUMMARY candidate, and stderr is GSD's error log.
 *   - The cwd is the project root, and the command string is word-split with NO shell, so flags must not contain spaces.
 *
 * What it does: it picks the first installed CLI from --prefer and runs it with the
 * full-permission formula (no sandbox, no ask/plan mode, no permission waits).
 * It prints only the final answer and maps exit codes:
 *   0   success (the CLI exited 0 and a non-empty final answer was parsed)
 *   N   the CLI's own non-zero exit code (1 when the CLI said 0 but reported an error or gave no answer)
 *   124 this script's inner deadline was hit (GNU timeout / gsd run-with-timeout parity)
 *   127 none of the preferred CLIs is installed
 *   2   usage or configuration error (bad flag, no prompt on stdin, no model configured)
 *   128+n  this script was killed by signal n (the CLI's process group is killed first)
 *
 * Standard library only. Edit the CONFIG block and the RUNTIMES argv lines freely; the
 * generator will then refuse to overwrite this file silently (sha256 header above).
 *
 * Flags:
 *   --prefer pi,cursor,opencode,grok,codex   order to try (default CONFIG.prefer)
 *   --model-<cli> <id>                       model per CLI, e.g. --model-cursor auto
 *   --mode exec|review                       exec = full permissions (default); review = read-only
 *   --timeout <s>                            inner deadline (default: workflow.cross_ai_timeout - margin)
 *   --print-argv                             print the resolved command per CLI and exit (no model call)
 *   --no-preamble                            send the prompt unchanged
 *   --self-test                              offline checks (parsers, classifier, argv, spawn/timeout/retry)
 */
import { spawn, spawnSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// <config> (written by the generator; keep it valid JSON so regeneration can diff it)
const CONFIG = {
  "prefer": ["pi", "cursor", "opencode", "grok"],
  "models": {
    "cursor": "auto",
    "opencode": "router-env/my-coding",
    "grok": "grok-4.7",
    "pi": "openai-codex/gpt-5.6-terra:medium",
    "codex": "gpt-5.6-luna"
  },
  "timeoutMarginS": 30,
  "defaultOuterTimeoutS": 300,
  "retries": 2,
  "backoffS": [30, 60],
  "heartbeatS": 30
};
// </config>

// Appended to GSD's prompt in exec mode. GSD's prompt only carries <objective>/<tasks>/PROJECT.md,
// so without this the executor neither knows nobody will answer nor what shape stdout must have.
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

// Host signals that would make a child (or the ai-kit/gsd tools it runs) think it is still inside the parent agent.
const SCRUB_ENV = ['CLAUDECODE', 'CLAUDE_CODE_ENTRYPOINT', 'CLAUDE_CODE_SSE_PORT', 'OPENCODE', 'CURSOR_AGENT',
  'PI_CODING_AGENT', 'CODEX_THREAD_ID', 'CODEX_SANDBOX', 'GROK_AGENT'];

// Retry only on these (and never when FATAL also matches). Sources: Phase 16 16-HANDOFF router errors,
// pi's retry classifier, and the codex token_expired probe (xai-probe/codex.stderr.txt).
const TRANSIENT = /temporarily unavailable|cooling down|is locked|rate.?limit|overloaded|too many requests|\b429\b|\b50[234]\b|service unavailable|ECONNRESET|ETIMEDOUT|socket hang up|stream (?:closed|disconnected)/i;
const FATAL = /\b40[123]\b|spending limit|billing|quota exceeded|insufficient_quota|token_expired|invalid_refresh_token|could not be refreshed|not logged in|log ?in required|please (?:log|sign) ?in|unauthori[sz]ed|invalid api key|requires an opencode API key|pre-dispatch filters|credential gate|model not found|unknown model|invalid model/i;

/*
 * RUNTIMES: one block per CLI. Each block holds the verified formula; see
 * research/10-cross-ai-runtimes-reference.md for evidence. The fields are:
 *   bins:    executable names searched on PATH (shell functions/aliases are never seen here, by design)
 *   exec:    argv for full-permission execution;  review: argv for read-only review
 *   resume:  argv for a retry that continues the captured session (null = re-run with RESUME_MSG)
 *   parse:   stdout -> { text, sessionId, error }
 *   env:     extra env for the child
 * ctx = { cwd, sid (pre-assigned uuid), outFile (scratch file for CLIs that write the answer to a file) }
 */
const RUNTIMES = {
  // cursor-agent 2026.10.01. Live: xai-probe/cursor.result.txt (exec, 46 s, commit made) and cursor-ask.result.txt (ask, no writes).
  //   -p              headless; "Has access to all tools, including write and shell" (--help)
  //   --force         without it "changes are only proposed, not applied" (cursor.com/docs/cli/headless)
  //   --trust         without it a fresh dir stops at "Workspace Trust Required" (ai-kit commands.py live finding)
  //   --sandbox disabled  explicit, because ~/.cursor/cli-config.json differs per machine
  //   --approve-mcps  MCP servers would otherwise wait for approval
  //   --model         ALWAYS explicit: the interactive `cursor-agent` shell function that injects one is invisible here
  //   The prompt comes from stdin (verified). JSON gives a session_id for resume and an is_error flag.
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

  // opencode 1.18.35. Live: xai-probe/opencode.result.txt (exec, 27 s, commit) and opencode-plan.result.txt (plan agent, no writes, no stall).
  //   run --auto      "auto-approve permissions that are not explicitly denied" (opencode run --help); without it
  //                   external_directory/doom_loop stay "ask" (opencode.ai/docs/permissions)
  //   --format json   JSONL events carrying sessionID; the final answer is rebuilt from the last message's text parts
  //   --agent plan    the built-in read-only agent, used for review
  //   The prompt comes from stdin (verified). The cwd is the project root, so --dir is not needed.
  //   Skills: uncomment OPENCODE_DISABLE_CLAUDE_CODE_SKILLS to hide ~/.claude/skills (docs/cli env table).
  opencode: {
    bins: ['opencode'],
    exec: (m) => ['run', '--model', m, '--auto', '--format', 'json'],
    review: (m) => ['run', '--model', m, '--agent', 'plan', '--format', 'json'],
    resume: (m, c, sid, mode) => [...RUNTIMES.opencode[mode](m, c), '--session', sid],
    parse: parseOpencode,
    env: { OPENCODE_DISABLE_AUTOUPDATE: '1' /* , OPENCODE_DISABLE_CLAUDE_CODE_SKILLS: '1' */ },
  },

  // grok 1.0.52 (Grok Build). Live: xai-probe/grok.result.txt (plain, 25 s) and grok-json.result.txt (json, 13 s, commit).
  //   --prompt-file /dev/stdin   single-turn headless run with the prompt from stdin (verified). This avoids `-p "$(cat)"`,
  //                              which needs a shell that GSD's word-split never provides.
  //   --always-approve           "Auto-approve all tool executions" (--help)
  //   --permission-mode bypassPermissions  explicit, because ~/.grok/config.toml [ui] permission_mode differs per machine
  //   --sandbox                  is deliberately NOT passed (no sandbox); GROK_SANDBOX is scrubbed below
  //   --no-auto-update           hidden in --help but accepted (unknown flags are rejected); docs.x.ai headless-scripting
  //   --output-format json       one object {text, stopReason, sessionId, usage, total_cost_usd}
  //   Gotcha: `text` concatenates every assistant message ("...hash.## Summary"); normalize() re-breaks the heading.
  //   Gotcha: grok imports ~/.claude skills, plugins, hooks and MCP (`grok inspect`); no verified per-run off switch.
  grok: {
    bins: ['grok'],
    exec: (m, c) => ['--prompt-file', '/dev/stdin', '-m', m, '--always-approve', '--permission-mode', 'bypassPermissions',
      '--output-format', 'json', '--no-alt-screen', '--no-auto-update', '--cwd', c.cwd],
    // review: plan mode is the documented read-only mode; not live-tested in headless runs (reference doc marks it [U]).
    review: (m, c) => ['--prompt-file', '/dev/stdin', '-m', m, '--permission-mode', 'plan', '--output-format', 'json',
      '--no-alt-screen', '--no-auto-update', '--no-subagents', '--cwd', c.cwd],
    resume: (m, c, sid, mode) => [...RUNTIMES.grok[mode](m, c), '--resume', sid],
    parse: (out) => {
      const j = parseJson(out);
      if (!j) return { text: '', sessionId: null, error: 'grok output is not JSON' };
      const bad = j.error || /error|abort|refus/i.test(String(j.stopReason || ''));
      return { text: j.text || '', sessionId: j.sessionId || null, error: bad ? String(j.error || j.stopReason) : null };
    },
    env: { GROK_SANDBOX: '' },
  },

  // pi (@earendil-works/pi-coding-agent). NOT installed on this machine at test time; the formula comes from report 06
  // (live on 0.82.1) and the pi.dev/docs/latest/cli docs. pi has no permission prompts and no sandbox at all.
  //   -p              print mode: stdout = the last assistant message's text only; exit 1 on error/aborted
  //   --session-id    pre-assigned id ("creates it if absent"), reused verbatim for resume
  //   --no-approve    ignore trust-gated project-local .pi resources;  --offline: no catalog/update network calls
  //   Strip-down (optional): --no-skills --no-extensions (1.x: also MCP), --no-context-files drops AGENTS.md
  //   stdin: pi waits for EOF forever on an open stdin; this script always closes it.
  pi: {
    bins: ['pi'],
    exec: (m, c) => ['-p', '--model', m, '--session-id', c.sid, '--no-approve', '--offline'],
    review: (m, c) => ['-p', '--model', m, '--session-id', c.sid, '--no-approve', '--offline', '--tools', 'read,grep,find,ls'],
    resume: (m, c, sid, mode) => RUNTIMES.pi[mode](m, c), // same --session-id continues the session
    parse: (out) => ({ text: out, sessionId: null, error: null }),
    env: {},
  },

  // codex-cli 0.153.4 (not in the user's runtime list; kept because GSD hosts may be codex). Live probe hit an
  // expired login (xai-probe/codex.result.txt: 401 token_expired) so the success path is unverified here.
  //   exec --dangerously-bypass-approvals-and-sandbox   the only exec flag with no sandbox and no approvals
  //   (--full-auto and -a are rejected by exec in 0.153.4; workspace-write is a sandbox)
  //   -o <file> holds the last message; --json stdout gives thread.started.thread_id for `exec resume <id>`
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

// ---------- parsing helpers ----------
function parseJson(s) { try { return JSON.parse(s); } catch { return null; } }
function* jsonLines(s) { for (const l of s.split('\n')) { const j = l.trim().startsWith('{') ? parseJson(l) : null; if (j) yield j; } }
function lastJson(s, pred) { let hit = null; for (const j of jsonLines(s)) if (pred(j)) hit = j; return hit; }

function parseOpencode(out) {
  let sessionId = null, error = null;
  const msgs = new Map(); // messageID -> Map(partID -> text); insertion order = message order
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

// Strip ANSI; re-break a markdown heading glued to the previous sentence (grok's concatenated messages).
function normalize(text) {
  return text.replace(/\x1B\[[0-9;?]*[A-Za-z]/g, '').replace(/([.!?:])(#{1,6} \S)/g, '$1\n\n$2').trim() + '\n';
}

function classify(blob) {
  if (FATAL.test(blob)) return 'fatal';
  if (TRANSIENT.test(blob)) return 'transient';
  return 'other';
}

// ---------- environment ----------
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
  return Number.isFinite(t) && t > 0 ? t : CONFIG.defaultOuterTimeoutS;
}
// Always below GSD's outer timeout: the margin is capped at a fifth of it (20 s -> 16 s, 300 s -> 270 s).
function innerTimeoutS(outer) { return outer - Math.min(CONFIG.timeoutMarginS, Math.floor(outer / 5)); }
function readOr(p, dflt) { try { return fs.readFileSync(p, 'utf8'); } catch { return dflt; } }

function gitState(cwd) {
  const head = spawnSync('git', ['rev-parse', 'HEAD'], { cwd, encoding: 'utf8' });
  const st = spawnSync('git', ['status', '--porcelain'], { cwd, encoding: 'utf8' });
  return head.status === 0 && st.status === 0 ? head.stdout + st.stdout : null;
}

function childEnv(extra) {
  const env = { ...process.env, ...extra };
  for (const k of SCRUB_ENV) if (!(k in extra)) delete env[k];
  for (const [k, v] of Object.entries(extra)) if (v === '') delete env[k];
  return env;
}

// ---------- process control ----------
let current = null;   // live child, for signal forwarding
let aborting = 0;     // signal number once we were told to stop

function killGroup(child, sig) { try { process.kill(-child.pid, sig); } catch { try { child.kill(sig); } catch { /* gone */ } } }

for (const [sig, n] of [['SIGTERM', 15], ['SIGINT', 2], ['SIGHUP', 1]]) {
  process.on(sig, () => {
    aborting = n;
    if (!current) process.exit(128 + n);
    killGroup(current, 'SIGTERM');
    // gsd run-with-timeout SIGKILLs our group 3 s after SIGTERM, and the CLI is in its own group: kill it first.
    setTimeout(() => { if (current) killGroup(current, 'SIGKILL'); process.exit(128 + n); }, 2000).unref();
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
      resolve({ code, signal, timedOut, spawnErr, stdout: Buffer.concat(out).toString('utf8'), stderr: errTail });
    };
    child.on('error', (e) => done(null, null, e));
    child.on('close', (code, signal) => done(code, signal, null));
  });
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// One CLI, with transient-only retries inside the shared deadline. Returns { ok, text, code, timedOut }.
async function runCli(name, rt, binPath, model, mode, prompt, deadline, opts = {}) {
  const backoff = opts.backoffS || CONFIG.backoffS;
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'cross-ai-'));
  const ctx = { cwd: process.cwd(), sid: crypto.randomUUID(), outFile: path.join(tmp, 'last-message.md') };
  const env = childEnv(rt.env);
  let argv = rt[mode](model, ctx); let input = prompt;
  try {
    for (let attempt = 0; ; attempt++) {
      process.stderr.write(`cross-ai: cli=${name} bin=${binPath} mode=${mode} attempt=${attempt + 1} timeout=${Math.round((deadline - Date.now()) / 1000)}s\n`);
      process.stderr.write(`cross-ai: argv=${JSON.stringify(argv)}\n`);
      const r = await runOnce(binPath, argv, input, env, ctx.cwd, deadline, name);
      if (aborting) return { ok: false, code: 128 + aborting };
      if (r.timedOut) return { ok: false, code: 124, timedOut: true };
      if (r.spawnErr) return { ok: false, code: r.spawnErr.code === 'ENOENT' ? 127 : 126, error: String(r.spawnErr) };
      const p = rt.parse(r.stdout, ctx);
      if (r.code === 0 && !p.error && p.text.trim()) return { ok: true, text: normalize(p.text) };
      const blob = `${r.stderr}\n${p.error || ''}\n${r.stdout.slice(-4000)}`;
      const kind = classify(blob);
      const wait = (backoff[attempt] ?? backoff[backoff.length - 1]) * 1000;
      process.stderr.write(`cross-ai: ${name} failed (exit ${r.code}${r.signal ? ' ' + r.signal : ''}, ${kind}${p.error ? ': ' + p.error.slice(0, 200) : ''})\n`);
      if (kind !== 'transient' || attempt >= (opts.retries ?? CONFIG.retries) || deadline - Date.now() < wait + 60000) {
        return { ok: false, code: r.code || 1, kind };
      }
      await sleep(wait);
      const sid = p.sessionId || (name === 'pi' ? ctx.sid : null);
      if (sid && rt.resume) { argv = rt.resume(model, ctx, sid, mode); input = RESUME_MSG; } else { input = `${RESUME_MSG}\n\n${prompt}`; }
    }
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

// ---------- CLI ----------
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

async function main(argv) {
  let o;
  try { o = parseArgs(argv); } catch (e) { process.stderr.write(`cross-ai: ${e.message}\n`); return 2; }
  if (o.selfTest) return selfTest();
  const order = o.prefer || CONFIG.prefer;
  const models = { ...CONFIG.models, ...o.models };
  const cands = order.map((name) => ({ name, rt: RUNTIMES[name], model: models[name],
    bin: RUNTIMES[name].bins.map((b) => which(b)).find(Boolean) || null }));

  if (o.printArgv) {
    const ctx = { cwd: process.cwd(), sid: '<uuid>', outFile: '<tmp>/last-message.md' };
    for (const c of cands) process.stdout.write(`${c.name}\t${c.bin || 'MISSING'}\t${c.model ? JSON.stringify(c.rt[o.mode](c.model, ctx)) : 'NO MODEL'}\n`);
    return 0;
  }
  const raw = readStdin();
  if (!raw || !raw.trim()) { process.stderr.write('cross-ai: pipe the prompt on stdin\n'); return 2; }
  const prompt = raw + (o.preamble ? (o.mode === 'exec' ? EXEC_PREAMBLE : REVIEW_PREAMBLE) : '');
  const innerS = o.timeout || innerTimeoutS(outerTimeoutS(process.cwd()));
  const deadline = Date.now() + innerS * 1000;

  let last = null;
  for (const c of cands) {
    if (!c.bin) { process.stderr.write(`cross-ai: ${c.name} not installed, skipping\n`); continue; }
    if (!c.model) { process.stderr.write(`cross-ai: no model configured for ${c.name} (--model-${c.name}), skipping\n`); last = last || { code: 2 }; continue; }
    const before = gitState(process.cwd());
    const r = await runCli(c.name, c.rt, c.bin, c.model, o.mode, prompt, deadline);
    if (r.ok) { process.stdout.write(r.text); return 0; }
    if (r.timedOut || aborting) return r.code;
    last = r;
    // Fall through to the next CLI only when this one left the repo exactly as it found it.
    if (before === null || gitState(process.cwd()) !== before) return r.code;
    process.stderr.write(`cross-ai: ${c.name} failed without touching the repo, trying the next CLI\n`);
  }
  if (!last) { process.stderr.write(`cross-ai: none of [${order.join(', ')}] is installed\n`); return 127; }
  return last.code;
}

// ---------- self-test (no model calls) ----------
async function selfTest() {
  const assert = (await import('node:assert/strict')).default;
  const ctx = { cwd: '/p', sid: 'S', outFile: '/tmp/o' };
  // 1. every exec formula carries its permission flags and an explicit model; review carries none of them
  const must = { cursor: ['--trust', '--force', 'disabled'], opencode: ['--auto'], grok: ['--always-approve', 'bypassPermissions'],
    pi: ['-p'], codex: ['--dangerously-bypass-approvals-and-sandbox'] };
  const never = ['--force', '--auto', '--always-approve', 'bypassPermissions', '--dangerously-bypass-approvals-and-sandbox'];
  for (const [n, rt] of Object.entries(RUNTIMES)) {
    const ex = rt.exec('M', ctx); const rv = rt.review('M', ctx);
    for (const f of must[n]) assert.ok(ex.includes(f), `${n} exec lacks ${f}`);
    assert.ok(ex.includes('M') && rv.includes('M'), `${n} must pass the model`);
    for (const f of never) assert.ok(!rv.includes(f), `${n} review must not carry ${f}`);
    assert.ok(ex.every((t) => !/\s/.test(t) || t === ctx.cwd), `${n} argv token with whitespace`);
  }
  // 2. parsers on shapes captured in xai-probe/*.stdout.txt
  const cur = RUNTIMES.cursor.parse('{"type":"result","subtype":"success","is_error":false,"result":"## Summary\\nok","session_id":"c1"}\n');
  assert.deepEqual(cur, { text: '## Summary\nok', sessionId: 'c1', error: null });
  const oc = parseOpencode([
    '{"type":"text","sessionID":"ses_1","part":{"id":"p1","messageID":"m1","type":"text","text":"Plan first."}}',
    '{"type":"tool_use","sessionID":"ses_1","part":{"type":"tool","tool":"bash"}}',
    '{"type":"text","sessionID":"ses_1","part":{"id":"p2","messageID":"m2","type":"text","text":"## Summary\\ndone"}}'].join('\n'));
  assert.deepEqual(oc, { text: '## Summary\ndone', sessionId: 'ses_1', error: null });
  const gk = RUNTIMES.grok.parse('{"text":"I will commit.## Summary\\n\\nok","stopReason":"end_turn","sessionId":"g1"}');
  assert.equal(normalize(gk.text), 'I will commit.\n\n## Summary\n\nok\n');
  assert.equal(gk.sessionId, 'g1'); assert.equal(gk.error, null);
  assert.equal(normalize('\x1B[0mC# is fine. Use ## inline\n'), 'C# is fine. Use ## inline\n');
  // 3. classifier on real error strings
  assert.equal(classify('Chat admission capacity is temporarily unavailable'), 'transient');
  assert.equal(classify('429 Too Many Requests'), 'transient');
  assert.equal(classify('"code": "token_expired" ... could not be refreshed'), 'fatal');
  assert.equal(classify('403 spending limit reached'), 'fatal');
  assert.equal(classify('rate limit: 402 requires an opencode API key'), 'fatal');
  assert.equal(classify('SyntaxError in test'), 'other');
  assert.deepEqual([20, 300, 600].map(innerTimeoutS), [16, 270, 570]);
  // 4. spawn path with a fake CLI (node itself): pass-through, transient retry, deadline -> 124
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'cross-ai-test-'));
  const fake = { bins: [process.execPath], env: {}, parse: (out) => ({ text: out, sessionId: null, error: null }),
    exec: () => ['-e', `const fs=require('fs');const m=process.env.FAKE;let s='';process.stdin.on('data',d=>s+=d).on('end',()=>{
      if(m==='ok'){process.stdout.write('# T\\n'+s.length);}
      else if(m==='fail7'){process.exit(7);}
      else if(m==='flaky'){const f=${JSON.stringify(path.join(dir, 'n'))};if(!fs.existsSync(f)){fs.writeFileSync(f,'1');process.stderr.write('429 rate limit\\n');process.exit(1);}process.stdout.write('# T\\nretried');}
      else if(m==='hang'){setTimeout(()=>{},60000);}});`] };
  fake.review = fake.exec; fake.resume = null;
  const far = () => Date.now() + 120000;
  const run = (mode, dl = far()) => { process.env.FAKE = mode; return runCli('fake', fake, process.execPath, 'M', 'exec', 'hello', dl, { backoffS: [0], retries: 1 }); };
  let r = await run('ok'); assert.equal(r.ok, true); assert.equal(r.text, '# T\n5\n');
  r = await run('fail7'); assert.equal(r.ok, false); assert.equal(r.code, 7);
  // flaky needs deadline headroom > backoff + 60 s; far() gives 120 s
  r = await run('flaky'); assert.equal(r.ok, true); assert.equal(r.text, '# T\nretried\n');
  const t0 = Date.now(); r = await run('hang', Date.now() + 1500);
  assert.equal(r.code, 124); assert.ok(Date.now() - t0 < 10000, 'deadline kill too slow');
  delete process.env.FAKE; fs.rmSync(dir, { recursive: true, force: true });
  // 5. header hash state (informational)
  process.stdout.write(`self-test ok; header: ${headerState(fs.readFileSync(fileURLToPath(import.meta.url), 'utf8'))}\n`);
  return 0;
}

// sha256 over everything after line 2. The generator stamps it; a mismatch means a human edited the file.
export function headerState(text) {
  const lines = text.split('\n');
  const m = /sha256=([0-9a-f]{64}|UNSTAMPED)/.exec(lines[1] || '');
  if (!m || m[1] === 'UNSTAMPED') return 'unstamped';
  const h = crypto.createHash('sha256').update(lines.slice(2).join('\n')).digest('hex');
  return h === m[1] ? 'pristine' : 'edited';
}

if (process.argv[1] && fs.realpathSync(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(process.argv.slice(2)).then((code) => { process.exitCode = code; },
    (e) => { process.stderr.write(`cross-ai: internal error: ${e && e.stack || e}\n`); process.exitCode = 2; });
}

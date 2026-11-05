'use strict';
// GSD command module for the fold: node built-ins only, fixed argv, no shell (T-29-16).
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

// Mirrors jev_ladder.py SKILLS_ROOTS: [env variable or null, home fallback, suffix].
const SKILLS_ROOTS = [["CLAUDE_CONFIG_DIR", ".claude", "skills"], [null, ".agents", "skills"], ["XDG_CONFIG_HOME", ".config", "opencode/skills"], ["CURSOR_CONFIG_DIR", ".cursor", "skills"], ["PI_CODING_AGENT_DIR", ".pi/agent", "skills"]];

// Verb -> fold.py subcommand. `run` keeps its own fold.py form (see argvFor); `ship` is handled here.
const VERBS = { run: 'gsd', start: 'start', guard: 'guard', checkpoint: 'checkpoint', ready: 'ready' };
const PHASE = /^\d+(\.\d+)?$/;

// A capability copy has no skills root of its own, so the lookup starts at the host dirs.
function skillsRoots(env = process.env) {
  const home = env.HOME || os.homedir();
  return SKILLS_ROOTS.map(([variable, fallback, suffix]) => {
    const value = variable ? (env[variable] || '').trim() : '';
    return path.join(value || path.join(home, fallback), suffix);
  });
}

function findFold(env = process.env) {
  for (const root of skillsRoots(env)) {
    const script = path.join(root, 'ai-kit-commit-fold', 'scripts', 'fold.py');
    if (fs.existsSync(script)) return script;
  }
  return null;
}

// Accepts `<ai-kit-fold> <verb> --phase <N> [--raw]`; the trailing --raw comes from GSD's step dispatch.
function parse(args) {
  const [, verb, flag, phase, ...rest] = args;
  const extra = rest.length === 1 && rest[0] === '--raw' ? [] : rest;
  const known = verb === 'ship' || Object.prototype.hasOwnProperty.call(VERBS, verb);
  if (!known || flag !== '--phase' || !PHASE.test(phase || '') || extra.length) return null;
  return { verb, phase };
}

function argvFor(script, verb, phase, cwd) {
  if (verb === 'run') return [script, 'gsd', '--phase', phase, '--repo', cwd, '--mode', 'inline'];
  return [script, VERBS[verb], '--phase', phase, '--repo', cwd];
}

// The ship:pre gate: GSD's own ship is always blocked; it is pointed at the unit flow.
function ship(phase, cwd) {
  const script = findFold();
  const show = script ? spawnSync('python3', [script, 'show', '--phase', phase, '--repo', cwd], { cwd, encoding: 'utf8' }) : null;
  const match = show && show.status === 0 ? /^state:\s*(\S+)/m.exec(show.stdout || '') : null;
  const state = match ? match[1] : null;
  if (state === 'ready' || state === 'merged') {
    process.stdout.write('ai-kit-fold: refused ship_redirect: this project ships through the unit flow; the owner runs fold.py merge-chain\n');
  } else {
    process.stdout.write(`ai-kit-fold: refused not_ready: run gsd-tools ai-kit-fold ready --phase ${phase} after verification passes, then the owner runs fold.py merge-chain\n`);
  }
  process.exitCode = 1;
}

// With workflow.use_worktrees on, executor worktrees must fork from the live HEAD (D-03).
function setBaseRefForWorktrees(cwd, tools) {
  const config = spawnSync(process.execPath, [tools, 'config-get', 'workflow.use_worktrees', '--raw'], { cwd, encoding: 'utf8' });
  if (config.status === 0 && (config.stdout || '').trim() === 'true') {
    spawnSync(process.execPath, [tools, 'worktree', 'set-baseref'], { cwd, encoding: 'utf8' });
  }
}

function route({ args, cwd }) {
  const parsed = parse(args);
  if (!parsed) {
    process.stderr.write('usage: gsd-tools ai-kit-fold <run|start|guard|checkpoint|ready|ship> --phase <N>\n');
    process.exitCode = 2;
    return;
  }
  if (parsed.verb === 'ship') {
    ship(parsed.phase, cwd);
    return;
  }
  const script = findFold();
  if (!script) {
    process.stdout.write('ai-kit-fold: fold script not found in any skills dir\n');
    process.stdout.write(`outcome: phase-${parsed.phase} nothing folded (install ai-kit-commit-fold) (inline)\n`);
    process.exitCode = 1;
    return;
  }
  if (parsed.verb === 'start') setBaseRefForWorktrees(cwd, process.argv[1]);
  const run = spawnSync('python3', argvFor(script, parsed.verb, parsed.phase, cwd), { cwd, encoding: 'utf8' });
  if (run.error) process.stderr.write(`ai-kit-fold: ${run.error.message}\n`);
  process.stdout.write(run.stdout || '');
  process.stderr.write(run.stderr || '');
  process.exitCode = run.status === null ? 1 : run.status;
}

module.exports = { route, skillsRoots, findFold };

'use strict';
// GSD command module for the fold: node built-ins only, fixed argv, no shell (T-29-16).
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

// Mirrors jev_ladder.py SKILLS_ROOTS: [env variable or null, home fallback, suffix].
const SKILLS_ROOTS = [["CLAUDE_CONFIG_DIR", ".claude", "skills"], [null, ".agents", "skills"], ["XDG_CONFIG_HOME", ".config", "opencode/skills"], ["CURSOR_CONFIG_DIR", ".cursor", "skills"], ["PI_CODING_AGENT_DIR", ".pi/agent", "skills"]];

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

function route({ args, cwd }) {
  const [, verb, flag, phase] = args;
  if (verb !== 'run' || flag !== '--phase' || !/^\d+(\.\d+)*$/.test(phase || '')) {
    process.stderr.write('usage: gsd-tools ai-kit-fold run --phase <N>\n');
    process.exitCode = 2;
    return;
  }
  const script = findFold();
  if (!script) {
    process.stdout.write('ai-kit-fold: fold script not found in any skills dir\n');
    process.stdout.write(`outcome: phase-${phase} nothing folded (install ai-kit-commit-fold) (inline)\n`);
    process.exitCode = 1;
    return;
  }
  const run = spawnSync('python3', [script, 'gsd', '--phase', phase, '--repo', cwd, '--mode', 'inline'], { cwd, encoding: 'utf8' });
  if (run.error) process.stderr.write(`ai-kit-fold: ${run.error.message}\n`);
  process.stdout.write(run.stdout || '');
  process.stderr.write(run.stderr || '');
  process.exitCode = run.status === null ? 1 : run.status;
}

module.exports = { route, skillsRoots, findFold };

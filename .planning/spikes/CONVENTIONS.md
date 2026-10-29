# Spike Conventions

## Stack
Bash drivers plus small stdlib Python helpers; no dependencies.

## Structure
`.planning/spikes/NNN-name/` holds `run.sh` (takes a log dir outside the repo) and `README.md`;
logs and scratch sessions stay outside the tracked tree.

## Patterns
- Live CLI checks use throwaway sessions in a `mktemp -d` cwd, the cheapest model or the owner's
  router lane, `< /dev/null` stdin, and strip host markers (`CLAUDECODE`, ...) from the child env.
- Timers are transient `systemd-run --user --on-active=N` units: no unit file in the home.
- Evidence that cannot be induced safely (quota exhaustion) comes from existing transcripts and is
  labelled with its source; anything else stays `unverified`.

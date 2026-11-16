# Phase 34: jev backends by host and Laya calibration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-14
**Phase:** 34-jev-backends-by-host-and-laya-calibration
**Mode:** owner-led; order of authority: the owner's words of 2026-11-14, then the 2026-11-07 transcript, then jev
(advisory), then the owner on low confidence.

## The owner's input (2026-11-14, translated)

- Learn from the official `typesafe-ai` skill's remote usage and apply that kind of use to our skill; be aware of what
  can be done.
- For Laya, before jev itself is involved, look up Laya's information and capabilities on its page; one initial web
  fetch of the page where it publishes capabilities or a changelog is cheap.
- Nothing goes to tools-installer. The owner already upgraded Laya in `llm-env`; this phase does not upgrade it. The
  skill checks which version the Laya it talks to runs; the address may not be localhost. At this address there is
  this version; if what it can do is not known, consult its changelog and see how it helps from there.
- Remove the Zen fallback if the skill still mentions it.

## Decisions

| Question | Options considered | jev (advisory) | Decision |
|----------|--------------------|----------------|----------|
| Upgrade Laya before calibrating (2026-11-07 wording) | upgrade step vs calibrate the running version | none (owner's words) | Calibrate the running version; no upgrade (D-10) |
| Version source when the server exposes none | server field → config → "not exposed", fingerprint as key; ask the user each time; read the container | none; own reasoning | Server field, then `[jev] laya_version`, then "not exposed" with a fingerprint (D-04); the container is not reachable from a client at another address |
| When to fetch Laya's notes | fixed 24 h cache and 7-day check (2026-11-07) vs once per unknown version or fingerprint | none (owner's words) | Once per unknown key, plus on-demand refresh (D-06, D-08) |
| Who decides how a new feature is used | the script vs the agent | none; own reasoning | The script records, the agent decides; cells turn verified only through a live run (D-07) |
| TypeSafe awareness | none vs the same fetch-once step on new model ids | none (owner's words) | Fetch the official doc flow once per new model id (D-09) |
| First-run question | the script prompts vs the agent asks | none; own reasoning | The agent asks through its host's question tool; scripts stay non-interactive (D-03) |
| Zen and delegation | trust JEV-02 vs add a guard | none | Guard test (D-13) |

## Live facts behind the decisions (2026-11-14)

- The upgraded Laya at `127.0.0.1:8010` exposes `laya-serve` 0.1.0 (serve API) and four routes, checkpoint revisions in
  `/health`, and no package version; `/version`, `/v1/version`, `/v1/models` return 404.
- The skill has no Zen backend left (JEV-02 done in Phase 32.1).

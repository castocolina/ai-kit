---
phase: "17"
slug: "curated-config-inventory-recommendation-engine"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-15"
---

# Phase 17 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| `opencode serve` / `opencode models` -> ai-kit | A local opencode child reports models and capabilities | model list, server password (medium) |
| cwd and ancestors -> opencode config loader | opencode loads `opencode.json` and `.opencode/` from its cwd upward | config, MCP commands (high) |
| inventory.json -> `recommend` | A user-supplied file drives the whole plan | inventory (medium) |
| project-local gsd-core -> `node` | `inventory` runs the project's own `gsd-tools.cjs` and `lib/*.cjs` | code execution (medium, accepted) |
| ai-kit -> project `.planning/` and global gsd defaults | `inventory`/`recommend` never write there | config files (high) |

---

## Threat Register

Evidence comes from the gsd-security-auditor run at HEAD 6a75c3c (file:line in the run ledger), and then from fix pass 4 (`17-REVIEW-FIX.md`). Abbreviations: DET = `ai_kit_spec/detection.py`, INV/REC/ROLES/PRE/PIO/CA/GC/HOST/CLI = `ai_kit_gsd_curated_config/{inventory,recommend,roles,presets,plan_io,catalog_adapter,gsd_catalog,host,cli}.py`.

| Threat ID | Severity | Disposition | Mitigation | Status |
|-----------|----------|-------------|------------|--------|
| T-17-01 | medium | mitigate | probe binds 127.0.0.1, loopback URL only, token held in a local, stderr to DEVNULL, `ProxyHandler({})`; Authorization is unredirected (44d2ee6) | closed |
| T-17-02 | medium | mitigate | daemon timer, and `finally` SIGTERM -> SIGKILL on the probe's own process group | closed |
| T-17-03 | medium | mitigate | version `fullmatch`; Popen/urlopen seams threaded through snapshot and CLI | closed |
| T-17-04 | low | mitigate | strict shape checks; non-JSON gives `{}` | closed |
| T-17-05 | medium | mitigate | exact `schema_version`, key/type validation, exit 2 (PIO, CLI) | closed |
| T-17-06 | medium | mitigate | mkstemp + `os.replace`, temp removed on failure | closed |
| T-17-07 | medium | mitigate | `_drop_rejected` per layer; an unprobed key exits 2 | closed |
| T-17-08 | low | mitigate | AST import guard plus patched I/O; CLI-level I/O pin (cbb8036) | closed |
| T-17-09 | medium | mitigate | constant node script, argv list, keys as one JSON arg, no shell (GC) | closed |
| T-17-10 | medium | mitigate | shared resolver, project-local first; `.pi/gsd-core` first on pi (HOST); scope and path reported | closed |
| T-17-11 | medium | mitigate | full output shape required, else exit 2 | closed |
| T-17-12 | low | accept | see AR-01 | accepted |
| T-17-13 | medium | mitigate | eligibility needs a score for the purpose; otherwise `needs_choice` | closed |
| T-17-14 | medium | mitigate | `-fast` twins excluded; variants chosen by effort target | closed |
| T-17-15 | low | mitigate | cheapest eligible fallback with `why` | closed |
| T-17-16 | medium | mitigate | explicit `env=` on both subprocesses; tests use a scratch HOME/XDG | closed |
| T-17-17 | medium | mitigate | 120 s timeout, process-group SIGTERM then SIGKILL; grace raised to 15 s, above `_stop_server`'s worst case (1b19826) | closed |
| T-17-18 | low | mitigate | fixed field copy; the AA key is read only in the spec CLI | closed |
| T-17-19 | medium | mitigate | routers carry no vendor; `router_confirmed` needs a recorded confirmation | closed |
| T-17-20 | medium | mitigate | gsd-planner's resolved slot is the reference; unknown vendors are never eligible | closed |
| T-17-21 | low | mitigate | only confirmed execute routers win | closed |
| T-17-22 | low | mitigate | notes rather than `needs_choice` | closed |
| T-17-23 | high | mitigate | inventory has no write call; read-only chmod plus byte-identical tests (also against real gsd-core in e2e) | closed |
| T-17-24 | medium | mitigate | top-level allow-lists; planted-secret tests | closed |
| T-17-25 | low | mitigate | non-UTF-8 / too-deep JSON is treated as unreadable, and `gsd_core_version` tolerates a non-UTF-8 VERSION (79d1aea) | closed |
| T-17-26 | high | mitigate | leftover unsets gated by `is_managed`; families narrowed to writable keys (RUN-42 A-IN-09) | closed |
| T-17-27 | medium | mitigate | a latent global value becomes a conflict with `effect`; `--out` guard covers the nearest `.planning/` above the resolved config (08a235a) | closed |
| T-17-28 | low | mitigate | exit 2 on a malformed plan | closed |
| T-17-29 | medium | mitigate | absolute-path hygiene regex over the goldens | closed |
| T-17-30 | medium | mitigate | masked digest; `UPDATE_GOLDEN` rewrites and then skips | closed |
| T-17-31 | low | mitigate | skipped without node or gsd-core 1.16.0; scratch HOME/GSD_HOME | closed |
| T-17-32 | medium | mitigate | `real_gsd_run` allows only node and git | closed |
| T-17-33 | high (amended: local code execution, C-CR-01) | mitigate | register text was stale (it declared the `gettempdir()` cwd that was itself the bug). Now: a private 0700 dir under the user cache, removed afterwards; both project-config opt-outs set to 1; both password variables dropped (fd69fc1) | closed |
| T-17-SC | high | mitigate | stdlib-only runtime; `uv.lock` unchanged; the `pyproject.toml` diff is lint config only | closed |
| T-17-NF1 | medium | mitigate | `opencode models`, `--version` and `models --verbose` go through the same hardened env and private cwd (fd69fc1) | closed |
| T-17-NF2 | low | mitigate | `OPENCODE_CONFIG_PROJECT_DISABLE=1` is set alongside `OPENCODE_DISABLE_PROJECT_CONFIG=1`, overriding inherited values (fd69fc1) | closed |
| T-17-NF3 | low | mitigate | `OPENCODE_PASSWORD` is dropped too; covered by a test (fd69fc1) | closed |
| T-17-NF4 | medium | accept | see AR-02 | accepted |

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-01 | T-17-12 | Allow-listed config fields only; the rationale is in 17-03-PLAN. | plan 17-03 (planner) | 2026-10-15 |
| AR-02 | T-17-NF4 | `inventory` must run the project's own gsd-core to probe `isValidConfigKey` and its tables (17 D-11, D-31): there is no other source of truth for the project's key set. The same trust boundary was noted in 16.1 (D-18). The warning sits in the CLI help and the module docstring. The `SKILL.md` mention is owned by Phase 18 R15 (SKILL.md documents v2 as the primary flow). | orchestrator (autonomous run, RUN-44) | 2026-10-15 |
| AR-03 | probe_codegraph (16.1 code) | `opencode mcp list` still runs in the caller's cwd with project config on. That is deliberate: it reports project-level MCP registration, and it runs only in the user's own checkout. Unlike the `/tmp` case, the cwd is user-owned. | orchestrator (autonomous run, RUN-44) | 2026-10-15 |

*Accepted risks do not resurface in future audit runs.*

### Residual notes (not registered)

- Global opencode config (`~/.config/opencode`, `OPENCODE_CONFIG*`) still loads in every probe. It is user-owned and trusted, but each re-detect may start the user's global MCP servers and plugins.
- From the binary, `project === false` skips the whole parent walk (`opencode.json(c)`, `.opencode`, `.claude`, `.agents`). This comes from reading the bundled source and was not verified live (uz: no live opencode runs in this pass).

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-15 | 34 | 32 | 1 non-blocking (T-17-25), plus 1 accepted and 4 new findings | gsd-security-auditor (xhigh), HEAD 6a75c3c |
| 2026-10-15 | 38 | 36 | 0 (2 accepted) | orchestrator after fix pass 4 (79d1aea..34bb3d5) and test isolation d960fcb |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-15

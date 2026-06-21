# Status-line render pipeline

How `tools/status-line.py` turns one JSON blob on stdin into the multi-line
status bar — traced from `main()`, with the role of every piece and the exact
points you touch to add or change a segment.

> Runtime is **stdlib-only**: Claude Code pipes a status JSON to the script on
> stdin once per render; the script prints the rendered lines to stdout. There
> is no daemon and no shared state between renders.

---

## 1. Top-level pipeline

`main()` dispatches CLI subcommands first (`--check`, `--doctor`,
`--print-config`); the normal path resolves config, builds the theme, reads the
JSON, and renders.

```mermaid
flowchart TD
    start(["main() — stdin = status JSON"]) --> t0["t0 = perf_counter_ns()<br/>(start of the render-time measure)"]
    t0 --> args["parse_args(argv)"]
    args --> sub{"subcommand?"}
    sub -->|"--check / --doctor / --print-config"| cmd["run cmd_* and exit"]
    sub -->|"none (render)"| cfg["load_config(env)<br/>defaults &lt; TOML &lt; env"]
    cfg --> theme["build_theme(cfg)<br/>palette + ramps -> Theme"]
    theme --> readjson["raw = json.load(stdin)<br/>(on error: raw = {})"]
    readjson --> safe["safe_render(raw, env, cfg, theme, t0)"]
    safe --> bd["build_data(...) -> data, cols, lines"]
    bd --> render["render(data, cols, lines, cfg, theme)"]
    render --> out(["print lines to stdout"])

    safe -. "any exception" .-> backstop(["single ⚠ doctor line<br/>(never a blank bar)"])

    classDef io   fill:#e3f2fd,stroke:#1565c0,color:#0d2b4b
    classDef proc fill:#ede7f6,stroke:#4527a0,color:#1a0e3d
    classDef stop fill:#fdecea,stroke:#c62828,color:#3b0d0a
    class start,out io
    class t0,args,cmd,cfg,theme,readjson,safe,bd,render proc
    class backstop stop
```

**Key functions**

| Function | Responsibility |
|---|---|
| `load_config(env)` | Merge internal defaults `<` TOML file `<` env into a `Config` (segments, layout, palette, ramps, `[git]`, external providers). |
| `build_theme(cfg)` | Resolve palette + ramps into a `Theme` (the color lookups builders use). |
| `build_data(raw, env, t0, …)` | Gather everything builders read into one `_LazyData` map. **Segment-agnostic.** |
| `render(...)` | Walk the layout, pack each line, append a diagnostic line if any builder crashed. |
| `safe_render(...)` | Outermost backstop: any unexpected failure becomes a single diagnostic line, never a blank bar. |

---

## 2. One render, end to end

The interesting property: **expensive probes do not run in `build_data`.** They
are deferred and fire inside the *measured build* of the first segment that
reads them, so the `slowest` readout attributes the cost truthfully.

```mermaid
sequenceDiagram
    autonumber
    participant M as main
    participant SR as safe_render
    participant BD as build_data
    participant LD as _LazyData
    participant R as render
    participant PL as pack_line
    participant SB as safe_build
    participant SEG as seg_x builder
    participant P as probe (git/todo/rss/…)

    M->>SR: safe_render(raw, env, cfg, theme, t0)
    SR->>BD: build_data(raw, env, t0)
    BD->>LD: _LazyData(base, probes)
    Note over BD,LD: base = cheap fields (eager)<br/>probes = thunks (NOT run yet)
    BD-->>SR: data, cols, lines
    SR->>R: render(data, cols, lines, cfg, theme)
    loop each Line in layout (height-gated)
        R->>PL: pack_line(line.segments, data, cols, …)
        loop pass 1 — each non-meta segment
            PL->>SB: safe_build(key, data, avail, theme)
            SB->>SEG: seg_x(data, avail, theme)
            SEG->>LD: data.get("branch") — first read
            LD->>P: run thunk once, memoize result
            P-->>LD: value (also fills siblings)
            LD-->>SEG: value
            SEG-->>SB: rendered string
            SB-->>PL: string — time it, crown slowest
        end
        Note over PL: pass 2 — build meta segments<br/>render_time (reads t0), slowest
        PL-->>R: packed line
    end
    R-->>SR: list of lines
    SR-->>M: lines (or ⚠ backstop line)
```

---

## 3. Render core — layout and the two-pass packer

`render` is layout-driven: `cfg.layout` is a list of `Line(min_rows,
[segment keys])`. A line is skipped if the terminal is too short; otherwise
`pack_line` fits it to the width budget.

`pack_line` runs **two passes plus assembly** so the meta segments
(`render_time`, `slowest`) — which report the whole render rather than one
builder — can sit at their declared layout positions instead of being forced
last:

```mermaid
flowchart TD
    inp(["pack_line(keys, data, cols, …)"]) --> en["enabled = keys filtered by cfg.segments<br/>budget = cols - RIGHT_MARGIN"]
    en --> p1start["PASS 1 — non-meta segments, left to right"]

    subgraph P1["Pass 1: build + time + crown"]
        direction TB
        p1["for key not in SLOWEST_META:<br/>t0 = perf_counter_ns()<br/>s = safe_build(key, data, avail)<br/>ns = elapsed"]
        p1 --> fit1{"fits avail<br/>(or pinned)?"}
        fit1 -->|yes| keep1["built[key] = s<br/>used_est += width<br/>_crown_slowest(key, ns)"]
        fit1 -->|no| skip1["skip"]
    end

    p1start --> P1
    P1 --> p2["PASS 2 — meta segments<br/>render_time reads t0; slowest reads data['slowest']<br/>(now populated by pass 1)"]
    p2 --> asm["ASSEMBLY — walk enabled in layout order<br/>keep each if used + sep + width &lt;= budget<br/>(pinned always kept)"]
    asm --> join(["SEP.join(kept)"])

    classDef io   fill:#e3f2fd,stroke:#1565c0,color:#0d2b4b
    classDef proc fill:#ede7f6,stroke:#4527a0,color:#1a0e3d
    class inp,join io
    class en,p1start,p1,keep1,skip1,p2,asm proc
```

`safe_build` is the **single guarded entry point**: it calls
`builders[key](data, avail, theme)` and, on *any* exception, records the key in
the shared `failed` set and returns a width-bounded `⚠key` marker — so one bad
segment can never blank the bar. `_crown_slowest` tracks the running max into
`data["slowest"]`, skipping meta segments and crashed builders.

---

## 4. How a segment is "built"

Every segment — built-in or external — is reached through **one merged
registry** and **one gate**:

- **Gate:** `cfg.segments.get(key, False)` (the on/off flag).
- **Registry:** `_builders_for(cfg)` = the static `BUILDERS` map merged with one
  synthetic builder per external provider. Every builder has the same shape:
  `seg_x(data, avail, theme) -> str | None`.

```mermaid
flowchart TD
    pl["pack_line"] -->|"key, avail"| sb["safe_build(key, …)"]
    sb -->|"builders[key]"| reg
    subgraph reg["_builders_for(cfg)"]
        direction LR
        b1["BUILDERS<br/>(built-in seg_* funcs)"]
        b2["external providers<br/>(one wrapper each)"]
    end
    reg -->|"core: reads data fields"| core["seg_x(data, avail, theme)"]
    reg -->|"external: spawns provider"| ext["run_external(spec, data, avail)"]
    core --> data["_LazyData map<br/>(pre-gathered fields)"]
    ext --> rawjson["data['raw'] = original JSON<br/>+ AI_KIT_SEGMENT_* env"]

    classDef proc fill:#ede7f6,stroke:#4527a0,color:#1a0e3d
    classDef data fill:#e8f5e9,stroke:#2e7d32,color:#10300f
    class pl,sb,core,ext proc
    class b1,b2,data,rawjson data
```

This is the crux of the **core vs external** difference:

- A **core** builder reads *pre-gathered fields* from the `_LazyData` map
  (`data.get("branch")`, `data["model_name"]`, …). Those fields are produced
  centrally by `build_data`.
- An **external** provider receives the *original JSON* (`data["raw"]`) plus
  segment metadata on stdin and **gathers its own data** in its own subprocess.
  It never touches `build_data`.

---

## 5. The data layer — `_LazyData`

`build_data` returns a `_LazyData` (a `dict` subclass) with two kinds of entry:

```mermaid
flowchart TD
    bd["build_data(raw, env, t0)"] --> base["base — cheap, eager fields<br/>(stored directly)"]
    bd --> probes["probes — {key: thunk}<br/>(deferred; not yet run)"]
    base --> ld["_LazyData(base, probes)"]
    probes --> ld

    ld --> readcheap["data.get('model_name')<br/>-> direct hit"]
    ld --> readlazy["data.get('branch')<br/>-> _resolve: pop + run thunk once,<br/>memoize, fill siblings"]

    subgraph shared["one shared thunk, many keys"]
        git["_git() fills branch, dirty,<br/>is_worktree, wt_name, in_repo"]
    end
    readlazy -.-> shared

    classDef proc fill:#ede7f6,stroke:#4527a0,color:#1a0e3d
    classDef data fill:#e8f5e9,stroke:#2e7d32,color:#10300f
    class bd,readcheap,readlazy,git proc
    class base,probes,ld data
```

- **`base`** holds fields that are cheap to compute up front: `model_name`,
  `work_dir`, `clock`, the `cost`/`context` numbers, `cols`/`lines`, `t_start`,
  etc.
- **`probes`** holds thunks for the expensive work: git (`branch`/`dirty`/
  worktree fields), transcript `ago`, todo parse, process RSS, effort-auto. A
  thunk runs at most once (first read), memoizes into the dict, and may fill
  several sibling keys in one shot (the single `git_snapshot` feeds all five git
  fields). Builders read via `.get(...)`, so `_resolve` runs on both `.get()`
  and item access.
- **Laziness is the compute gate.** A disabled segment is never built, so its
  field is never read, so its probe never runs. `build_data` itself knows
  *nothing* about which segments are enabled.

---

## 6. Adding or changing a segment — the touch-points

To add a **core** segment, you edit up to four places (all near the top of the
file except the builder):

```mermaid
flowchart TD
    idea(["new core segment 'foo'"]) --> seg["1. SEGMENTS<br/>add 'foo': True/False (the flag)"]
    seg --> lay["2. LAYOUT<br/>place 'foo' in a Line"]
    lay --> bld["3. seg_foo(data, avail, theme)<br/>+ register in BUILDERS"]
    bld --> needs{"needs data not<br/>already in the map?"}
    needs -->|no| done(["done — reads existing fields"])
    needs -->|yes| data["4. build_data<br/>add an eager field to base,<br/>or a thunk to probes"]
    data --> done

    classDef io   fill:#e3f2fd,stroke:#1565c0,color:#0d2b4b
    classDef proc fill:#ede7f6,stroke:#4527a0,color:#1a0e3d
    class idea,done io
    class seg,lay,bld,data proc
```

Adding an **external** segment touches **none** of these: drop an executable
provider in the `[external]` segments dir; `load_config` discovers it, makes its
id a known segment key (enabled by default), and `_place_external` slots it into
the layout. It sources its own data from `data["raw"]`.

---

## 7. Design observation — is `build_data` redundant?

This is a known tension, recorded here rather than hidden.

`build_data`'s `base` dict enumerates every core field by hand. That gives the
render loop a flat, uniform map to read and lets the packer **time** the
gathering as part of each segment's build (truthful `slowest`). The cost is
**coupling**: a core segment that needs new data forces a `build_data` edit
(touch-point 4 above), so the data layer's field list implicitly tracks the core
segment set.

External segments show the alternative shape already in the codebase: a segment
that **owns its own data sourcing** (gets the raw JSON, fetches what it needs)
needs no central registry edit. Pushing core segments toward that model — each
builder declaring/fetching its own inputs through the same lazy, timed path —
would let `build_data` shrink to just the genuinely shared primitives (`raw`,
`work_dir`, `cols`/`lines`, `t_start`) and remove touch-point 4 for most new
segments.

That is a design direction, not a defect in the current behavior — captured so
the trade-off is explicit when the next core segment is added.

---

## Reference — pipeline at a glance

| Stage | Function | Input | Output |
|---|---|---|---|
| Entry | `main` | stdin JSON | printed lines |
| Config | `load_config` | env, TOML | `Config` |
| Theme | `build_theme` | `Config` | `Theme` |
| Data | `build_data` | raw, env, t0 | `_LazyData`, cols, lines |
| Render | `render` | data, cols, lines, cfg, theme | `list[str]` |
| Pack | `pack_line` | one line's keys | one packed string |
| Build | `safe_build` | one key | one segment string (guarded) |
| Backstop | `safe_render` | everything | lines, or one ⚠ line |

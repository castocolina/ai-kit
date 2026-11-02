# Phase 17 spike — opencode 2.x `image_input` source (D-24)

Run 2026-10-15 on opencode v2.0.29, under a scratch HOME/XDG (the real `~/.config/opencode` was
untouched), with every spawned server killed afterwards (confirmed with `pgrep`).

## Findings

- `opencode models --verbose` is gone. `opencode models [--standalone | --server <url>]` prints only
  bare `provider/model` ids (11 lines in the scratch HOME), with no capability data.
- `opencode serve --hostname 127.0.0.1 --port <p>` starts the v2 HTTP API. It prints
  `server password <token>` on stdout, and `/api/*` needs HTTP **basic** auth with user `opencode`
  and that token (Bearer gives 401). The OpenAPI document is at `GET /openapi.json` (same auth).
- **`GET /api/model`** returns `{"location": ..., "data": [Model.Info]}`. `Model.Info` has
  `capabilities: {tools: bool, input: [string], output: [string]}` (required fields), where
  `input` lists modalities such as `text`, `image`, `audio`, `video` and `pdf`. A model is
  vision-capable when `"image" in capabilities.input`. In the scratch HOME, 6 of 11 built-in
  `opencode/*` models had `image`.
- `GET /api/provider` and `GET /api/provider/{providerID}` exist as well. `/api/model` is the one
  that carries capabilities.

## Sample (first 4 entries, trimmed to the relevant fields)

```json
[
  {
    "id": "exo-free",
    "modelID": "exo-free",
    "providerID": "opencode",
    "capabilities": {
      "tools": true,
      "input": [
        "text",
        "image"
      ],
      "output": [
        "text"
      ]
    },
    "status": "active",
    "enabled": true
  },
  {
    "id": "ling-3.1-flash-free",
    "modelID": "ling-3.1-flash-free",
    "providerID": "opencode",
    "capabilities": {
      "tools": true,
      "input": [
        "text"
      ],
      "output": [
        "text"
      ]
    },
    "status": "active",
    "enabled": true
  },
  {
    "id": "longcat-2.5-preview-free",
    "modelID": "longcat-2.5-preview-free",
    "providerID": "opencode",
    "capabilities": {
      "tools": true,
      "input": [
        "text",
        "image"
      ],
      "output": [
        "text"
      ]
    },
    "status": "active",
    "enabled": true
  },
  {
    "id": "space-bunny-free",
    "modelID": "space-bunny-free",
    "providerID": "opencode",
    "capabilities": {
      "tools": true,
      "input": [
        "text",
        "image",
        "video"
      ],
      "output": [
        "text"
      ]
    },
    "status": "active",
    "enabled": true
  }
]
```

## Consequence for Phase 17

D-24's first branch applies: add a version-gated opencode-2.x source that reads
`capabilities.input` from `/api/model`, recording `image_input_source` provenance. It sits beside the
1.x `--verbose` parser, which stays for older installs. Starting a server needs a free localhost
port, the printed token, a probe timeout, and a guaranteed kill. The planner should weigh that cost
against `opencode models --server <url>` when a background service is already running. Neither path
may touch the user's real opencode config.

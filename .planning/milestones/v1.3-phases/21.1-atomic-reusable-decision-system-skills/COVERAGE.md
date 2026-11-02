# API Coverage — Jev System One (TypeSafe direct, OpenCode Zen, local Laya)

> Full coverage by default. Opt-outs are explicit, reasoned decisions.

| capability | decision | reason |
|---|---|---|
| typesafe-choice | INTEGRATE | |
| typesafe-noul | INTEGRATE | |
| typesafe-score | INTEGRATE | |
| typesafe-multi-question-batch | INTEGRATE | |
| typesafe-model-alias-and-versioned-pin | INTEGRATE | |
| typesafe-usage-report | INTEGRATE | |
| typesafe-jev-preview-alias | OPT-OUT | not needed yet: reachable through the `JEV_TYPESAFE_MODEL` pin; the default stays `jev-latest` (D-26) |
| typesafe-box | OPT-OUT | explicitly out of scope: request builder is backlog 999.8; gated by `unsupported_feature` (D-21) |
| typesafe-images-single-and-compared | OPT-OUT | explicitly out of scope: request builder is backlog 999.8; gated by `unsupported_feature` (D-21) |
| typesafe-long-context-header | OPT-OUT | not needed yet: no in-scope caller exceeds the 1,500-character item limit; the cell is recorded as documented (D-24) |
| zen-choice | INTEGRATE | |
| zen-noul | INTEGRATE | |
| zen-multi-question-batch | INTEGRATE | |
| zen-free-to-paid-model-ladder | INTEGRATE | |
| zen-score | OPT-OUT | not needed yet: unverified on Zen and the budget is exhausted, so its capability cell keeps it filtered (D-25) until a live check |
| zen-box-images-long-context | OPT-OUT | explicitly out of scope: unverified and no builder (D-21, backlog 999.8) |
| zen-models-listing | OPT-OUT | not needed: the row's model ids are fixed and documented (D-26) |
| laya-health | INTEGRATE | |
| laya-choice | INTEGRATE | |
| laya-noul | INTEGRATE | |
| laya-score | INTEGRATE | |
| laya-usage-truncated | INTEGRATE | |
| laya-systemone-batch | OPT-OUT | not needed: it answers one shared question set over many states, the wrong shape for items with their own questions (RESEARCH Answer 1) |
| laya-model-selector | OPT-OUT | not needed: Laya picks the checkpoint from the state language; the client sends `jev-1` (D-26) |

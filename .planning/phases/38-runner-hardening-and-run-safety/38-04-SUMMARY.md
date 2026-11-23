# 38-04 Summary: one confirmed-router rule

Status: complete. Commits e72b395 (`feat(38-04): one confirmed-router rule read by resolve_route`) and 951cc47 (`feat(38-04): curated-config router_confirmed reads the one rule; build_runner_argv returns its list`). Executed through two cross-AI lanes (pi router-env/my-coding): lane a for Task 1 (status=ok, 456 s), lane b for Tasks 2 and 3 together (status=ok, 285 s).

## What changed

- `model_heuristics.py`: `ROUTER_ALIAS_SOURCE`, `router_statement(entry) -> bool | None` (owner false wins; disagreeing or missing heuristic fields never confirm; owner word or `user-stated` class confirms; the router-env alias assumption with its exact source confirms; a judged hint stays advisory) and `is_confirmed_router(entry)`.
- `catalog_facts.py`: `ROUTER_SOURCE = ROUTER_ALIAS_SOURCE` (lane_pool keeps importing it).
- `runner_dispatch.py`: `_confirmed_quota` replaced by `_row_matches`; `resolve_route` walks `sorted(entries)` and the first matching row's `router_statement` decides; `build_runner_argv` returns its list directly.
- `catalog_adapter.py`: `_ROUTER_PURPOSES` deleted; `_JoinCtx.router_rule` loaded once per build by `_router_rule()` (fails closed when the sibling is missing or older); `router_confirmed` reads it.
- Tests: `TestResolveRoute.test_alias_assumed_entry_is_router`; `TestRouterRuleMatrix` (12-row matrix through `router_statement`, `resolve_route`, `build_candidates`, `plan_edit._confirmed_router` and the rendered `routerBacked`; missing entry; missing quota; first sorted key wins for a shared lane; older sibling fails closed); `test_router_confirmed_rules` deleted; router fixtures gain `fallback_quota` / `is_router`.

## Verification (run by the chunk agent)

- Acceptance greps all at their expected counts (12 matrix rows); no grok text; baseline, goldens and detection.py untouched.
- tests.test_ai_kit_spec_runner_dispatch (80), test_ai_kit_spec_runtimes_table (59), test_catalog_build_sources (19), test_curated_config_inventory (116), test_curated_config_plan_edit (90), test_curated_config_cross_ai (55), test_curated_config_recommend (139), test_curated_config_script (50): all pass. Lanes ran make ruff, pyright, vulture, pylint (exit 0); hooks passed 130/130 and 132/132 covering modules.

## Deviations

- `tests/test_cross_ai_runner_e2e.py` (`_route_catalog`, outside the plan's file list): its confirmed router entry gained `"is_router": True`. The old fixture confirmed `fallback_quota` alone, which the one rule no longer treats as a confirmed router (both heuristic fields must be true); the e2e route assertion is unchanged.
- Tasks 2 and 3 landed in one commit (the chunk's lane prompt); the wave fold makes one commit per plan anyway.
- Handoff (from the plan): whether curated-config SKILL.md (lines 108-115) should name the alias case is the orchestrator's call; no 38 plan owns that paragraph.

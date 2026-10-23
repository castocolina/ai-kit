in-session judge: pending (orchestrator)
format: replace this file with one block per run: DIGEST <python3 tests/gsd_curated_eval.py digest --skill-dir skills/jev-fast-decision>,
TREE <git rev-parse HEAD:skills/jev-fast-decision>, then the judge-prompt.md output (D1..D8 as D<k> <n>/<max>, CURRENT, CRITICAL,
IMPORTANT, FLOORS, ACTIVATION, CITE_PROBE and CITE_BACKEND for jev-fast-decision); append later runs;
21.1-07's check_verdict.py parses it

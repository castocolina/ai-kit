# E2E signals and evidence

The e2e facts detect reports, the zero-test markers, and the evidence a run must print.

Load when: before reporting any e2e fact (SKILL.md §3), or when detect's `e2e.none` is true.

## The four e2e signals

Detect lists them in `e2e.commands`, each with `source`, `kind` and `confidence`:

- `make` (kind `make`, `detected`): every Makefile target named `e2e`, `e2e-*`, `e2e_*` or `e2e.*`,
  in declaration order.
- `package` (kind `package`, `detected`): a package.json script with an e2e name.
- Browser config (kind `playwright` or `cypress`, `detected`): a browser config file, added only
  when no package script already runs that browser.
- PTY driver (kind `pty`, `inferred`): a test file that drives a terminal UI through a pseudo
  terminal (Python `pty` use, `node-pty`, or `textual.pilot`), found by its file. An inferred
  command is labelled inferred; never present it as a detected suite.

`e2e.gates` lists the commands the run checks first. `e2e.none` is true when `e2e.commands` is
empty.

## Zero-test markers

A runner can exit 0 or 5 while running no tests. The count line decides, not the exit code alone.
The table below is the data in `gp_e2e.ZERO_TEST_MARKERS`. A row marked `verified` was observed in
a scratch probe during research; a row marked `unverified` is an assumption about that runner.

| Runner | Exit code | Count marker | Label |
|---|---|---|---|
| `unittest` | 5 | `NO TESTS RAN` | verified |
| `node --test` | 0 | `tests 0` | verified |
| `go test` | 0 | `[no test files]` | verified |
| `shell harness` | — | `0 passed` | verified |
| `pytest` | 5 | `no tests ran` | unverified |
| `jest` | 1 | `No tests found` | unverified |
| `vitest` | 1 | `No test files found` | unverified |
| `playwright` | 1 | `No tests found` | unverified |
| `cypress` | — | — | unverified |
| `cargo` | 0 | `running 0 tests` | unverified |

The `shell harness` row is the ai-kit shell harness (`tests/test_install.sh`), whose final line is
`N passed, M failed`. A `—` means the data holds no value for that column.

## Evidence format

The generated prompt asks the run to print, for every command:

- its exact exit code;
- its count line;
- the last 20 lines of output, with ANSI codes stripped.

The run also prints the paths of any screenshots or TUI text snapshots its e2e run produced. A
mockup adds a human-review line: the captures are listed for review, and no automated judge
decides fidelity. Exit 0 with a zero count is not green.

## Process groups

Each long-lived e2e process starts in its own process group. The run records each group id in
`tmp/`, kills those groups after the run, and prints a `ps` listing showing none remain.

## Create-first rule

When `e2e.none` is true, the generated file's first task, before any feature plan, creates an e2e
suite. The suite launches the real app: a PTY drive for a terminal UI, a browser for a web UI. The
task then makes it pass. Whether that task succeeds in the target repository is unverified until a
run does it.

## Unit tests

The generated done rule says unit tests alone never count as done. The gates run first (`make
test-unit` in the golden example). The e2e command must exit 0 and print a count above zero.

## Unverified

- Zero-test markers for pytest, jest, vitest, Playwright, Cypress and cargo: assumptions, labelled
  `unverified` in the table above.
- Cypress: no count rule is known, so its marker is omitted.
- Whether an inferred PTY driver matches a real e2e suite in the target repository.
- Whether the create-first task succeeds in a repository with no e2e suite.

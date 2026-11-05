# CI failure summary (synthetic eval input)

- Job: unit tests, run 4417, branch feature/export-csv
- Failed test: tests.test_export.TestCsv.test_quotes_commas
- Error class: AssertionError (expected a quoted field, got the field with a trailing CR LF)
- Pass history: the same test passed on the previous three runs of this branch
- Other failures in this run: none
- Retries: 0
- Last change on the export path: the CSV writer's line-ending option (one commit, same branch)
- Runner: hosted Linux image, two vCPUs

### CRITICAL
None.
### HIGH
- **Slug keeps a trailing hyphen** — Location: text_utils.py:12. Required: strip trailing hyphens after replacing spaces. Why: slugs end in "-" and break the URL test.
### MEDIUM
- **Title-case test repeats a fixture** — Location: tests/test_text_utils.py:30. Required: reuse the shared fixture. Why: noise.
### LOW
None.
### Status: Issues Found — fix and re-invoke

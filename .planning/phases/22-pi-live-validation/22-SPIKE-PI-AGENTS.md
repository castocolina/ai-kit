# Pi GSD Agent Model Spike

Date: 2026-10-23

## Run conditions

- pi version: `1.3.0`; gsd-core installer package: `1.17.0`.
- Scratch HOME and PI_CODING_AGENT_DIR; models.json contains only the literal dummy key `dummy-not-a-key`.
- pi ran under `env -i`, with the scratch project extension trusted for this run using `--approve`.
- Requests went only to a localhost mock provider; no real credential or model call was used (ruling Q1).

## L2 (localhost mock)

| Arm | Project config | Trust path | pi exit | Selection | Wire model | Result |
|---|---|---|---:|---|---|---|
| A | `pi.sonnet=steered-id` | `--approve` | 0 | `selected` | `steered-id` | pass |

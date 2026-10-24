# Cursor fixtures

Dashboard responses are synthetic and inferred from the Cursor CLI bundle dated 2026.10.14,
its proto descriptors, and the `/usage` logic. Every value in `dashboard/` is synthetic;
`includedUsagePeriod`'s location under `planInfo` is inferred. No real response is committed.
Real redacted responses may be added only by `spike_check.py --promote` under `dashboard_real/`.

`payload_synthetic.json` is a synthetic bundle-shaped runner payload. The redacted POC fixture
comes from the single payload file when available; see the phase summary for provenance.

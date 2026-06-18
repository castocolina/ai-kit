# Fixture 03 — decision as rectangle (violates S1)

```mermaid
flowchart TD
    A[Validate input] -->|valid| B[Process]
    A -->|invalid| C[Reject]
```

# Unverified

Load this before claiming any of these works, or when asked what is not verified. Do NOT load it
for routine `arm`, `status`, `done` or `disarm`.

Nothing below is verified on this machine:

- That a wake survives a reboot.
- That the first timer fire resumes the session.
- That a running resume removes the wake after an in-wake `done`.
- That auth still works after a reboot.
- The claude transcript layout (reverse-engineered), the pi and codex session-store layouts
  (reverse-engineered or from help text), and the shape of opencode's JSON session listing.
- The StopFailure hook payload.
- The codex session-id source (`CODEX_THREAD_ID`) and the codex resume command.

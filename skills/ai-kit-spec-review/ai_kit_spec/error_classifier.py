"""One shared failure classifier for reviewer/dispatch subprocess failures (D-13,
HARD-04/R8). Inputs are the exit status and stderr ONLY — the model's answer (stdout) is
never classified, so an answer that happens to contain "quota exceeded" on a zero exit with
empty stderr is a success, never an unavailability. Callers store the returned reason as the
quota entry's own `reason` field (`quota.py:probe_reviewer_quota`) or map it into their own
vocabulary (`ai_kit_spec_superpowers.dispatch_injection.classify_dispatch_failure`).

The 18.1/25 runner adds `billing_or_access` and `capacity` by mapping its OWN status line
(Python maps the runner's `AIKIT-XAI` status marker); those reasons deliberately do NOT live
here — this module's vocabulary stays the six subprocess-shaped reasons below."""

# Closed reason vocabulary (D-13). Order here is documentation only; classify_error's
# check order is: timeout, exit 0, dispatch_unavailable, auth, quota, configuration.
REASONS = (
    "quota",               # time-bound rate/usage limit — worth an hourly retry
    "auth",                # authentication/entitlement/setup — never fixed by waiting
    "timeout",             # the invocation itself hung
    "configuration",       # malformed/missing command template or unknown model
    "dispatch_unavailable",  # the binary could not be invoked at all
    "real_error",          # anything else — a real, non-time-bound failure
)

# auth/entitlement/setup signals — checked BEFORE quota so "not logged in ... quota" reads
# auth, never the (retryable) quota. cursor-agent evidence, 16.1-RESEARCH.md: stderr
# "Warning: The provided API key is invalid" / "ActionRequiredError: Named models
# unavailable", exit 1 (the ActionRequiredError channel itself is marked [ASSUMED] stderr).
_AUTH_SIGNALS = (
    "actionrequirederror", "not authenticated", "not logged in", "unauthorized",
    "api key is invalid", "invalid api key",
)
_QUOTA_SIGNALS = ("usage limit", "quota", "rate limit", "rate_limit")
_CONFIGURATION_SIGNALS = ("cannot use this model", "unknown model", "model not found")
_DISPATCH_UNAVAILABLE_SIGNALS = ("command not found", "no such file or directory")


def _stderr_text(stderr: str | bytes) -> str:
    if isinstance(stderr, bytes):
        return stderr.decode("utf-8", errors="replace")
    return stderr


def _signal_reason(text: str, signal_groups: tuple[tuple[tuple[str, ...], str], ...]) -> str | None:
    for signals, reason in signal_groups:
        if any(s in text for s in signals):
            return reason
    return None


def classify_error(returncode: int | None, stderr: str | bytes, timed_out: bool = False
                   ) -> str | None:
    """Classify a subprocess failure from (exit status, stderr, timed_out) only.

    Returns None when the call succeeded (exit code 0 is never classified — and a zero
    exit never produces a reason even with hostile stderr text, R8). Never inspects the
    model's answer (stdout). Byte input is decoded with errors="replace", so non-UTF-8
    stderr cannot raise. A render ValueError from the command template maps to
    "configuration" at the call site (quota.py's probe_reviewer_quota), not here."""
    if timed_out:
        return "timeout"
    if returncode == 0:
        return None
    text = _stderr_text(stderr).lower()
    if returncode == 127 or any(s in text for s in _DISPATCH_UNAVAILABLE_SIGNALS):
        return "dispatch_unavailable"
    grouped = (
        (_AUTH_SIGNALS, "auth"),
        (_QUOTA_SIGNALS, "quota"),
        (_CONFIGURATION_SIGNALS, "configuration"),
    )
    return _signal_reason(text, grouped) or "real_error"

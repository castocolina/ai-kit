"""One shared failure classifier for reviewer/dispatch subprocess failures (D-13,
HARD-04/R8). Inputs are the exit status and stderr ONLY — the model's answer (stdout) is
never classified, so an answer that happens to contain "quota exceeded" on a zero exit with
empty stderr is a success, never an unavailability. Callers store the returned reason as the
quota entry's own `reason` field (`quota.py:probe_reviewer_quota`) or map it into their own
vocabulary (`ai_kit_spec_superpowers.dispatch_injection.classify_dispatch_failure`).

The 18.1/25 runner maps its OWN status line (`AIKIT-XAI status=...`) through
STATUS_TO_REASON / reason_for_status. `capacity` and `billing_or_access` come from that
map (Python never classifies those from stderr). `git_timeout` means the runner's git
work-tree check timed out before or after the CLI, not the CLI itself, and is not worth
waiting for."""

# Closed reason vocabulary (D-13). Order here is documentation only; classify_error's
# check order is: timeout, exit 0, auth, quota, dispatch_unavailable, configuration.
REASONS = (
    "quota",               # time-bound rate/usage limit — worth an hourly retry
    "auth",                # authentication/entitlement/setup — never fixed by waiting
    "timeout",             # the invocation itself hung
    "configuration",       # malformed/missing command template or unknown model
    "dispatch_unavailable",  # the binary could not be invoked at all
    "real_error",          # anything else — a real, non-time-bound failure
    "capacity",            # provider overloaded; mapped from the runner status line
    "billing_or_access",   # billing / entitlement; mapped from the runner status line
    "git_timeout",         # runner git work-tree check timed out, not the CLI
)

# Runner status -> reason (D-12 as amended by 25 D-21; D-34). Values are None (success)
# or a REASONS member. `unverified` is the D-31 route name only, never a status key.
STATUS_TO_REASON: dict[str, str | None] = {
    "ok": None,
    "quota": "quota",
    "quota_wait": "quota",
    "auth": "auth",
    "billing": "billing_or_access",
    "billing_or_access": "billing_or_access",
    "capacity": "capacity",
    "timeout": "timeout",
    "idle_stall": "timeout",
    "bad_model": "configuration",
    "bad_prompt": "configuration",
    "permission_blocked": "configuration",
    "usage": "configuration",
    "no_model": "configuration",
    "empty_stdin": "configuration",
    "not_installed": "dispatch_unavailable",
    "no_change": "real_error",
    "empty_answer": "real_error",
    "crash": "real_error",
    "contract_violation": "real_error",
    "signal": "real_error",
    "git_error": "real_error",
    "git_timeout": "git_timeout",
}
# Exit code -> reason when no status line counts (D-12: exit 2 is configuration, 124 the
# runner's timeout, 127 a missing binary).
_EXIT_FALLBACK: dict[int | None, str | None] = {
    0: None, 2: "configuration", 124: "timeout", 127: "dispatch_unavailable",
}

# auth/entitlement/setup signals — checked BEFORE quota so "not logged in ... quota" reads
# auth, never the (retryable) quota. cursor-agent evidence, 16.1-RESEARCH.md: stderr
# "Warning: The provided API key is invalid" / "ActionRequiredError: Named models
# unavailable", exit 1 (the ActionRequiredError channel itself is marked [ASSUMED] stderr).
_AUTH_SIGNALS = (
    "actionrequirederror", "not authenticated", "not logged in", "unauthorized",
    "api key is invalid", "invalid api key",
)
# Anchored phrases, never a bare "quota"/"rate limit": execute-dispatch stderr is a whole
# child transcript, so a task ABOUT rate limiting must not read as a quota event (A-WR-02).
_QUOTA_SIGNALS = (
    "usage limit", "quota exceeded", "exceeded your current quota", "rate limit exceeded",
    "rate limit reached", "rate_limit_error", "rate_limit_exceeded", "resource_exhausted",
)
_CONFIGURATION_SIGNALS = ("cannot use this model", "unknown model", "model not found")
# Only the tail is scanned: the failure that ended the run is printed last, while an earlier
# benign tool error in the transcript ("No such file or directory") must not outrank it.
_STDERR_TAIL_CHARS = 2048


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
    stderr cannot raise. Only the last _STDERR_TAIL_CHARS of stderr are scanned, and
    dispatch_unavailable comes from the exit status alone (126/127), never from transcript
    text. A spawn OSError never reaches here: runner_dispatch returns dispatch_unavailable
    (or configuration for E2BIG) itself, and quota.probe_reviewer_quota maps a template
    render ValueError to "configuration"."""
    if timed_out:
        return "timeout"
    if returncode == 0:
        return None
    text = _stderr_text(stderr)[-_STDERR_TAIL_CHARS:].lower()
    reason = _signal_reason(text, ((_AUTH_SIGNALS, "auth"), (_QUOTA_SIGNALS, "quota")))
    if reason:
        return reason
    if returncode in (126, 127):
        return "dispatch_unavailable"
    return _signal_reason(text, ((_CONFIGURATION_SIGNALS, "configuration"),)) or "real_error"


def reason_for_status(status: str | None, returncode: int | None) -> str | None:
    """Map a runner status (or a bare returncode) onto the closed reason vocabulary.

    A known STATUS_TABLE key uses STATUS_TO_REASON. Otherwise the exit code decides
    (`_EXIT_FALLBACK`, D-12), and every other code is real_error."""
    if status in STATUS_TO_REASON:
        return STATUS_TO_REASON[status]
    return _EXIT_FALLBACK.get(returncode, "real_error")

"""36 D-05 / SPEC R4: learn whether a lane's effort is accepted with one test call.

Stores nothing; the wizard writes effort and effort_source after an accepted call.
"""

import tempfile

from ai_kit_spec import lane_effort, secret_shapes
from ai_kit_spec.commands import ResolvedReviewer
from ai_kit_spec.lane_effort import effort_source_label
from ai_kit_spec.quota import ProbeSeams, probe_reviewer_quota
from ai_kit_spec.runner_dispatch import preview_setting, print_argv_lines, review_spec
from ai_kit_spec.usability import sanitize_error

REJECTING_REASONS = ("real_error", "configuration")
NO_ANSWER_REASON = "the call answered with no text, so acceptance is not shown"
NO_MODEL_REASON = "the lane has no model, so no call was made"
NO_PREVIEW_REASON = ("the runner preview did not run (node or the runner template is missing), "
                     "so the effort form is unknown")
NO_SETTING_REASON = "the runner preview printed no effort setting line"
CARRIED_REASON = ("the model id already carries an effort (runner: id_carries); "
                  "the call cannot show acceptance of the lane effort")
# The runner's own log and status lines and run_runner's lines, never the host's.
WRAPPER_LINE_PREFIXES = ("cross-ai:", "AIKIT-XAI ", "ai-kit-spec:")


def _outcome(state: str, effort: str, **fields) -> dict:
    result = {"state": state, "level": effort, "label": None, "error": None,
              "reason": None, "probe": None}
    result.update(fields)
    return result


def _host_error_line(result: dict) -> str | None:
    lines = [line for line in str(result.get("detail") or "").splitlines() if line.strip()]
    host = next((line for line in lines
                 if not line.lstrip().startswith(WRAPPER_LINE_PREFIXES)), None)
    return sanitize_error(secret_shapes.redact(host, "[redacted]")) if host is not None else None


def _classify(result: dict, effort: str, today: str) -> dict:
    if result.get("available") is True:
        if result.get("answered") is True:
            return _outcome("accepted", effort, label=effort_source_label(today), probe=result)
        return _outcome("inconclusive", effort, reason=NO_ANSWER_REASON, probe=result)
    reason = result.get("reason")
    if reason in REJECTING_REASONS:
        host = _host_error_line(result)
        if host:
            return _outcome("rejected", effort, reason=reason, error=host, probe=result)
        detail = str(result.get("detail") or "").splitlines()
        first = sanitize_error(secret_shapes.redact(detail[0], "[redacted]")) if detail else None
        return _outcome("inconclusive", effort, reason=f"runner: {first or reason}", probe=result)
    return _outcome("inconclusive", effort, probe=result, reason=(
        f"the call stopped on '{reason}', which does not show whether the effort is accepted"))


def _preview_outcome(resolved, effort, preview_fn) -> dict | None:
    with tempfile.TemporaryDirectory(prefix="aikit-probe-") as cwd:
        lines = preview_fn(review_spec(resolved.runtime, resolved.model,
                                       {**resolved.extra, "effort": effort}, 30, cwd=cwd))
    if lines is None:
        return _outcome("inconclusive", effort, reason=NO_PREVIEW_REASON)
    state = preview_setting(lines, "effort")
    if state is None or state[0] not in ("applied", "ignored"):
        return _outcome("inconclusive", effort, reason=NO_SETTING_REASON)
    if state == ("ignored", "id_carries"):
        return _outcome("inconclusive", effort, reason=CARRIED_REASON)
    if state[0] == "ignored":
        return _outcome("ignored", effort, reason=(
            f"ignored: the runner reports effort '{effort}' ignored (reason={state[1]})"))
    return None


def probe_effort(resolved: ResolvedReviewer, effort: str, today: str,
                 seams: ProbeSeams | None = None, preview_fn=None) -> dict:
    """One test call with the effort set; state accepted, rejected, inconclusive or ignored.
    `probe` holds the raw probe result (None when no call ran)."""
    if not isinstance(resolved.runtime, str) or not resolved.runtime:
        return _outcome("ignored", effort, reason=lane_effort.NO_RUNTIME_IGNORED)
    if not resolved.model:
        return _outcome("inconclusive", effort, reason=NO_MODEL_REASON)
    stop = _preview_outcome(resolved, effort, preview_fn or print_argv_lines)
    if stop is not None:
        return stop
    result = probe_reviewer_quota(resolved._replace(extra={**resolved.extra, "effort": effort}),
                                  seams=seams)
    return _classify(result, effort, today)

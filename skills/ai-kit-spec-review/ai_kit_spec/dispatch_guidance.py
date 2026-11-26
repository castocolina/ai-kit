"""Shared cross-AI/native-dispatch reinforcement prose -- ONE place, reused by every
ai-kit-spec-execute-* framework adapter, instead of each adapter re-inventing its own version of
the same ideas.

These functions NEVER edit the target framework's own workflow/skill prose -- those are
independent systems this repo does not own. They only ever
build supplementary prose a caller appends to a file IT controls (a phase prompt file, a command
string) -- reinforcing decisions this adapter has already made (which model/CLI was resolved,
what output shape the caller needs back) without re-implementing the target framework's own
execution logic. Framework-specific knowledge (e.g. a framework's own summary file shape) is never
hardcoded here -- callers supply it (see `build_output_format_guidance`'s own `format_block` arg)
so this module stays reusable across frameworks with genuinely different conventions.

Confirmed-only, mirroring tooling_guidance.py's own discipline: every sentence here is either a
structural instruction (ignore your own defaults, report failure honestly) that holds for ANY
dispatched CLI/subagent regardless of framework, or is left to the caller to supply when it is
framework-specific."""

import os

GATES_FRAME = (
    "Gates: before you report DONE, run each command below and judge it by its exit code "
    "alone; a version banner or any output after the summary line never fails a gate, and the "
    "tail of its output never decides it."
)
GUARD_FRAME = "Commit guard: apply these rules to every commit, on every dispatch path."


def build_model_selection_override_guidance(resolved_label: str) -> str:
    """Tells the dispatched CLI/subagent to skip its own default model/vendor-selection or
    cross-AI delegation logic -- this adapter already resolved the choice via ai-kit-spec's own
    live-quota-checked ladder, and re-deciding inside the dispatch would silently discard that
    resolution."""
    return (
        f"A model/CLI has already been resolved for this dispatch by ai-kit-spec-execute "
        f"({resolved_label}) -- do not re-select or second-guess it via your own default "
        f"model-routing or cross-AI delegation logic; use exactly what this dispatch was "
        f"configured with."
    )


def build_incremental_progress_guidance() -> str:
    """Reinforces committing/persisting real progress incrementally rather than all-or-nothing --
    so a timeout or crash mid-task leaves recoverable partial work instead of nothing."""
    return (
        "Make and persist real, verifiable progress incrementally as you work (e.g. commit or "
        "write intermediate artifacts as each sub-step completes) rather than holding everything "
        "until a single final step -- a timeout or interruption partway through should leave "
        "recoverable partial work, not nothing."
    )


def build_output_format_guidance(format_block: str) -> str:
    """Wraps a framework-specific output-format block (supplied by the caller -- e.g. a
    framework's own summary file shape) in a consistent instruction frame. This function holds no
    framework-specific knowledge itself, only the reusable "your final output must match this"
    framing shared across every ai-kit-spec-execute-* adapter."""
    return (
        "Your entire final response (the last thing you print to stdout) MUST match this exact "
        "structure -- nothing before it, nothing after it:\n\n" + format_block
    )


def build_failure_reporting_guidance() -> str:
    """Reinforces honest, diagnosable failure reporting -- so a caller reading the dispatch's own
    output can tell "genuinely done" from "silently gave up" and choose a safe fallback instead
    of trusting a false success."""
    return (
        "If you cannot complete the task as given, say so explicitly and describe exactly what "
        "you did and did not finish, and why -- never report success or produce output shaped "
        "like a completed summary for work that was not actually done. This dispatch's caller "
        "relies on your report to decide whether to retry, fall back to a different model/CLI, "
        "or escalate to a human -- a false success blocks all three."
    )


def build_gates_guidance(gates_text: str | None) -> str:
    """Frames the caller's gate commands once; nothing when there are none."""
    if gates_text is None or not gates_text.strip():
        return ""
    return GATES_FRAME + "\n\n" + gates_text.strip("\n")


def unsupported_owner_config(p: str) -> bool:
    """Only a non-empty, project-relative file path is supported: an empty value, `.` or a folder
    would exclude the whole tree or a folder from the clean-tree check, an absolute or `..` path
    leaves the project, a quote breaks the shell quoting of the pathspec sentence, a first
    character other than a letter, digit or `.` (or a backslash or glob character) turns the
    pathspec into magic or a pattern, and a non-printable character breaks the one-line command.
    """
    return (not p or p == "." or p.endswith("/") or os.path.isabs(p) or ".." in p or "'" in p
            or not (p[0].isalnum() or p[0] == ".") or any(c in p for c in "*?[\\")
            or not p.isprintable())


def checked_owner_config_paths(values) -> tuple:
    """The owner-config paths as a tuple; ValueError naming the first unsupported one."""
    for p in values or ():
        if unsupported_owner_config(p):
            raise ValueError(f"ai-kit-spec: --owner-config: unsupported path {p}")
    return tuple(values or ())


def build_commit_guard_guidance(guard_text: str | None, owner_config_paths: tuple = ()) -> str:
    """Frames the caller's commit-guard rules and keeps the owner's config files out of every
    commit and clean-tree check."""
    owner_config_paths = checked_owner_config_paths(owner_config_paths)
    has_text = guard_text is not None and bool(guard_text.strip())
    if not has_text and not owner_config_paths:
        return ""
    text = GUARD_FRAME
    if has_text:
        assert guard_text is not None
        text += "\n\n" + guard_text.strip("\n")
    if owner_config_paths:
        # top-anchored literal pathspecs: the check is the same from any folder of the checkout
        excludes = " ".join(f"':(top,exclude,literal){p}'" for p in owner_config_paths)
        text += (
            "\n\nThe owner's config files are never staged, committed or reverted, and a "
            "clean-tree check leaves them out: `git status --porcelain -- ':(top)' " + excludes
            + "`."
        )
    return text


def build_dispatch_reinforcement_guidance(
    resolved_label: str,
    format_block: str | None,
    gates_text: str | None = None,
    guard_text: str | None = None,
    owner_config_paths: tuple = (),
) -> str:
    """Composes the building blocks above into one prose section, in a fixed order (model
    override, incremental progress, failure reporting, caller gates, commit guard, then output
    format last so it is the
    freshest thing the dispatched CLI/subagent read before it starts). `format_block` is optional
    -- omit it (None) for a dispatch mode where the caller's own framework already knows its own
    output convention (e.g. a native in-framework subagent) and only the override/progress/
    failure-reporting guidance applies."""
    sections = [
        build_model_selection_override_guidance(resolved_label),
        build_incremental_progress_guidance(),
        build_failure_reporting_guidance(),
    ]
    gates = build_gates_guidance(gates_text)
    if gates:
        sections.append(gates)
    guard = build_commit_guard_guidance(guard_text, owner_config_paths)
    if guard:
        sections.append(guard)
    if format_block is not None:
        sections.append(build_output_format_guidance(format_block))
    return "\n\n".join(sections)

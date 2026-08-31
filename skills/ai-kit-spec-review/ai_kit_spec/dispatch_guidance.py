"""Shared cross-AI/native-dispatch reinforcement prose -- ONE place, reused by every
ai-kit-spec-execute-* framework adapter (ai-kit-spec-execute-gsd today, ai-kit-spec-execute-
superpowers later), instead of each adapter re-inventing its own version of the same ideas.

These functions NEVER edit the target framework's own workflow/skill prose (gsd-core,
superpowers-core, ...) -- those are independent systems this repo does not own. They only ever
build supplementary prose a caller appends to a file IT controls (a phase prompt file, a command
string) -- reinforcing decisions this adapter has already made (which model/CLI was resolved,
what output shape the caller needs back) without re-implementing the target framework's own
execution logic. Framework-specific knowledge (e.g. GSD's own real SUMMARY.md shape) is never
hardcoded here -- callers supply it (see `build_output_format_guidance`'s own `format_block` arg)
so this module stays reusable across frameworks with genuinely different conventions.

Confirmed-only, mirroring tooling_guidance.py's own discipline: every sentence here is either a
structural instruction (ignore your own defaults, report failure honestly) that holds for ANY
dispatched CLI/subagent regardless of framework, or is left to the caller to supply when it is
framework-specific."""


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
    """Wraps a framework-specific output-format block (supplied by the caller -- e.g. GSD's own
    real SUMMARY.md shape) in a consistent instruction frame. This function holds no
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


def build_dispatch_reinforcement_guidance(resolved_label: str, format_block: str | None) -> str:
    """Composes the four building blocks above into one prose section, in a fixed order (model
    override, incremental progress, failure reporting, then output format last so it is the
    freshest thing the dispatched CLI/subagent read before it starts). `format_block` is optional
    -- omit it (None) for a dispatch mode where the caller's own framework already knows its own
    output convention (e.g. a native in-framework subagent) and only the override/progress/
    failure-reporting guidance applies."""
    sections = [
        build_model_selection_override_guidance(resolved_label),
        build_incremental_progress_guidance(),
        build_failure_reporting_guidance(),
    ]
    if format_block is not None:
        sections.append(build_output_format_guidance(format_block))
    return "\n\n".join(sections)

"""Direct dispatch for ai-kit-spec-review's own external-CLI reviewer entries -- wraps
dispatch.dispatch_with_polling with the review-specific prompt composition (tooling guidance
only; no model-selection-override/incremental-progress/failure-reporting reinforcement, since
a reviewer's own checklist skill (ai-kit-spec-review-checklist) already owns that contract).
Read-only by construction: the command this module runs is always rendered from a review-mode
`command` template (built by commands.build_reviewer_command and stored on the reviewer entry),
never an execute-mode one -- this module itself has no read/write distinction to enforce, that
lives entirely in which builder produced the entry's `command` before it ever reaches here."""
from ai_kit_spec.commands import ResolvedReviewer, render_reviewer_command
from ai_kit_spec.detection import check_codegraph_mcp_healthy
from ai_kit_spec.dispatch import dispatch_with_polling
from ai_kit_spec.tooling_guidance import (
    build_tooling_guidance,
    resolve_shared_tooling_reference_path,
)


def dispatch_reviewer(reviewer_entry: dict, prompt: str, timeout_tiers: list[int],
                       tool_availability: dict, agents_tooling_path=None,
                       dispatch_fn=dispatch_with_polling,
                       build_tooling_guidance_fn=build_tooling_guidance,
                       resolve_shared_reference_fn=resolve_shared_tooling_reference_path,
                       render_command_fn=render_reviewer_command,
                       codegraph_health_fn=check_codegraph_mcp_healthy) -> dict:
    """Composes the reviewer's FULL prompt (tooling guidance + the caller's already-built
    reviewer prompt, see ai-kit-spec-review/SKILL.md's Step 1 template), renders the entry's
    own `command` template against that full prompt, and runs it via `dispatch_with_polling`.

    Rendering happens HERE, after composition, and deliberately not in a separate
    `render-command` step the orchestrator would pass back in as a string. Two reasons, both
    real defects found at whole-branch review:

    1. Not every CLI reads its prompt from stdin. grok's builder inlines the prompt into the
       command line via `{prompt}`, so a guidance prefix applied only to the stdin we feed the
       child is silently discarded for exactly the CLI this guidance exists for (grok has no
       AGENTS.md/GROK.md ingestion of its own). Rendering the command from the already-prefixed
       prompt means the guidance reaches stdin readers AND command-line readers alike.
    2. A pre-rendered command handed back through a `--command "<string>"` shell argument gets
       evaluated twice -- once by the orchestrator's own shell, once by `shell=True` here --
       which reintroduces the very `$`/backtick/backslash injection hazard
       `render_reviewer_command`'s shlex.quote exists to prevent. Rendering inside this process
       means the rendered string never round-trips through a second shell evaluation.

    `reviewer_entry` is one element of `resolve-reviewers`' saved JSON array (key/model/vendor/
    cli/command/extra). `cli` may be None for a hand-written/unknown-CLI reviewer entry
    (build_tooling_guidance's own `cli != "grok"` check only ever special-cases the literal
    string "grok", so None is safe to pass through unchanged).

    codegraph health is resolved HERE too, not asked of the caller: no subcommand ever exposed
    `check_codegraph_mcp_healthy`, so a prose-only orchestrator had no runnable way to compute
    the flag it was being told to pass. This matches the execute family's existing precedent
    (ai-kit-spec-execute-gsd's `prepare-tooling` resolves it internally as well). Skipped
    entirely when `cli` is None -- there is no MCP client to interrogate.

    Raises `ValueError` for a malformed entry (missing/bad `command` template) or an empty
    `timeout_tiers`, so the CLI layer can report a config error rather than crashing."""
    cli = reviewer_entry.get("cli")
    codegraph_registered = bool(cli) and codegraph_health_fn(cli)
    tooling_guidance = build_tooling_guidance_fn(
        cli, tool_availability or {}, agents_tooling_path, codegraph_registered,
        shared_reference_path=resolve_shared_reference_fn())
    full_prompt = (tooling_guidance + "\n\n" + prompt) if tooling_guidance else prompt
    resolved = ResolvedReviewer(
        key=reviewer_entry.get("key", ""), model=reviewer_entry.get("model", ""),
        vendor=reviewer_entry.get("vendor", ""), cli=cli,
        command=reviewer_entry.get("command"), extra=reviewer_entry.get("extra") or {})
    command = render_command_fn(resolved, full_prompt)
    return dispatch_fn(command, full_prompt, timeout_tiers)

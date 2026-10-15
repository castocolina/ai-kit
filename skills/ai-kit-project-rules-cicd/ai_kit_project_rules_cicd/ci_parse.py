"""GitLab CI and GitHub Actions readers (D-C1, D-C13, D-C14, D-C17, D-C28,
D-C29), built entirely on the shared `ai_kit_rules_common.yaml_text`
primitives -- reading nothing else.

This is a TEXT reader, not a YAML implementation, matching the sibling
docker skill's `compose_parse.py` approach and stating its limits in the
same voice: tab indentation may mis-attribute a block rather than raise
(YAML forbids tabs; this reader measures indentation as a raw
whitespace-character count); anchors, aliases, merge keys, and GitLab's
`!reference` are not resolved, and a site using them may be read
incompletely; a line containing a heredoc (`<<`) is skipped rather than
mis-parsed. And, D-C28: `include:` is a reserved non-job key, so it
contributes no command site, and NONE of its forms is ever resolved or
opened -- not `template:`, not `project:`, not `remote:`, not
`component:`, and not `local:` either -- so a pipeline composed from
included files can run a tool this reader never sees, meaning a
zero-finding result on such a repo is not evidence its CI is clean.

Plan 14-02 adds the GitHub Actions reader (`iter_workflow_command_sites`)
beside the GitLab one, sharing the same discovery function (extended,
D-C29), the same `read_ci_text`, and the same `(site_name,
[command_line, ...])` contract. Its own stated limits: a `uses:` step's
referenced action -- and a `jobs.<id>.uses` reusable workflow -- is never
fetched, downloaded, read or analyzed, so a tool invoked inside a
third-party or composite action is invisible to this reader; matrix
expansion, `if:` conditions and `working-directory:` are not evaluated,
so a command that would never actually run on this platform is still
read; `defaults.run` is not evaluated either, at workflow OR job level,
so a `shell:`/`working-directory:` default that changes how every
`run:` in the file actually executes contributes nothing to the command
text this reader sees; and `${{ }}` expressions are never resolved, so a
step whose command is entirely an expression has no classifiable tool
token.

Every public function degrades: no input raises, and an unreadable or
malformed file yields an empty/`None` result rather than a crash.
"""

from __future__ import annotations

import os
import re

from ai_kit_rules_common.yaml_text import (
    find_block_end,
    is_effective_structural,
    line_indent,
    match_key_header,
    own_level_lines,
    strip_inline_comment,
    strip_yaml_quotes,
)

# D-C1 -- the GitLab filename tuple and the workflows-directory relative
# path, declared here so the applicability gate and (from plan 14-02
# onward) CI-file discovery read ONE list -- the way
# `compose_parse.BASE_COMPOSE_FILENAMES` serves both the docker gate and
# its discovery.
GITLAB_CI_FILENAMES = (".gitlab-ci.yml", ".gitlab-ci.yaml")
WORKFLOWS_DIR_RELATIVE = os.path.join(".github", "workflows")

# Reserved top-level GitLab keys that are never job/command sites. Every
# entry is a PLAIN string literal, spelled normally -- GitLab's own real
# key names, never a computed or concatenated form.
_RESERVED_TOP_LEVEL_KEYS = (
    "stages",
    "variables",
    "include",
    "workflow",
    "image",
    "services",
    "cache",
)

_SCRIPT_KEYS = ("before_script", "script", "after_script")
_TOP_LEVEL_SCRIPT_PSEUDO_SITES = ("before_script", "after_script")

_BLOCK_SCALAR_RE = re.compile(r"^[|>][+-]?\d*$")


def repo_has_ci_config(repo_root: str) -> bool:
    """D-C1's applicability gate, evaluated FIRST and short-circuiting.

    This repo has CI config when EITHER holds at the repository ROOT: a
    root file named `.gitlab-ci.yml`/`.gitlab-ci.yaml`, or a root
    directory `.github/workflows/` containing at least one entry whose
    name ends in `.yml`/`.yaml`. Root-scoped: `os.path.isfile`/
    `os.path.isdir` against explicitly-joined paths plus ONE
    non-recursive `os.listdir` of the workflows directory. No walk, no
    descending glob. Clause (ii) is evaluated here even though this plan
    reads no workflow file, so the gate's answer does not change when
    plan 14-02 lands. Never raises.
    """
    for name in GITLAB_CI_FILENAMES:
        if os.path.isfile(os.path.join(repo_root, name)):
            return True

    workflows_dir = os.path.join(repo_root, WORKFLOWS_DIR_RELATIVE)
    if os.path.isdir(workflows_dir):
        try:
            entries = os.listdir(workflows_dir)
        except OSError:
            entries = []
        for entry in entries:
            if (entry.endswith(".yml") or entry.endswith(".yaml")) and os.path.isfile(
                os.path.join(workflows_dir, entry)
            ):
                return True

    return False


def discover_ci_files(repo_root: str) -> list[str]:
    """The SINGLE, complete list of CI files this repo has (D-C29): GitLab
    CI file(s) first (in `GITLAB_CI_FILENAMES` tuple order), then the root
    `.github/workflows/` directory's own entries whose names end in
    `.yml`/`.yaml`, sorted by filename -- ONE non-recursive `os.listdir`,
    matching `repo_has_ci_config`'s clause (ii) exactly so discovery and
    the applicability gate always agree on every extension and depth.
    Repo-relative paths, deduplicated by path before returning so a future
    third source cannot reintroduce a double-scan. This is the ONLY
    function that assembles the CI-file list; `cicd_checker` has exactly
    one loop over exactly what this returns and never calls it twice.
    Never raises."""
    found: list[str] = []
    for name in GITLAB_CI_FILENAMES:
        if os.path.isfile(os.path.join(repo_root, name)):
            found.append(name)

    workflows_dir = os.path.join(repo_root, WORKFLOWS_DIR_RELATIVE)
    if os.path.isdir(workflows_dir):
        try:
            entries = os.listdir(workflows_dir)
        except OSError:
            entries = []
        workflow_entries = sorted(
            entry
            for entry in entries
            if (entry.endswith(".yml") or entry.endswith(".yaml"))
            and os.path.isfile(os.path.join(workflows_dir, entry))
        )
        for entry in workflow_entries:
            found.append(os.path.join(WORKFLOWS_DIR_RELATIVE, entry))

    seen: set[str] = set()
    deduped: list[str] = []
    for path in found:
        if path in seen:
            continue
        seen.add(path)
        deduped.append(path)
    return deduped


def read_ci_text(path: str) -> str:
    """Read `path` as UTF-8 text; `""` on ANY read failure (missing file,
    permission error, invalid UTF-8) rather than raising."""
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError):
        return ""


def _lines(text: str) -> list[str]:
    return text.split("\n")


def _find_own_key(lines: list[str], start: int, end: int, key: str):
    """Search the own-level lines of `lines[start:end]` for a `key:`
    header matching `key` by exact (quote-stripped) name. Returns
    `(line_index, indent, rest)` or `None`."""
    for idx, content in own_level_lines(lines, start, end):
        parsed = match_key_header(content)
        if parsed is None:
            continue
        name, rest = parsed
        if strip_yaml_quotes(name.strip()) == key:
            return idx, line_indent(lines[idx]), rest
    return None


def _sequence_command_lines(lines: list[str], start: int, end: int) -> list[str]:
    """Command lines from a `- `-prefixed sequence. A block-scalar item
    (`- |`/`- >`, any chomping/indentation indicator) contributes each of
    its deeper-indented continuation lines as its own command line; an
    ordinary item contributes exactly one, quotes stripped.

    Stops at the first own-level line that is NOT `-`-prefixed, rather
    than skipping over it: GitLab CI commonly indents a job's
    `before_script`/`script`/`after_script` sibling keys at the SAME
    level as their own list items (ai-kit's own `.gitlab-ci.yml` uses
    this style for `stages:`), so a scan that merely skipped a
    non-`-`-prefixed line would bleed across the sibling-key boundary and
    absorb a LATER key's items as this sequence's own."""
    commands: list[str] = []
    for idx, content in own_level_lines(lines, start, end):
        if not content.startswith("-"):
            break
        item_text = content[1:].strip()
        if _BLOCK_SCALAR_RE.match(item_text):
            item_indent = line_indent(lines[idx])
            block_end = find_block_end(lines, idx + 1, item_indent)
            for j in range(idx + 1, block_end):
                if is_effective_structural(lines[j]):
                    commands.append(lines[j].strip())
            continue
        if not item_text:
            continue
        commands.append(strip_yaml_quotes(item_text))
    return commands


def _extract_script_command_lines(block_lines: list[str]) -> list[str]:
    """Command lines from a job-shaped block's `before_script`/`script`/
    `after_script` keys, emitted in that FIXED order regardless of their
    declaration order, preserving declaration order inside each.

    The sequence's own level is established from the FIRST line after
    the header (`_sequence_command_lines`'s `own_level_lines` call), not
    pre-derived from the header's own indent: GitLab CI commonly indents
    a `key:`'s list items at the SAME level as the key itself (ai-kit's
    own `.gitlab-ci.yml` does this for `stages:`), which a
    header-indent-relative block-end lookup would read as an EMPTY block
    -- the item line's indent already equals the would-be reference
    indent, so a `<=` block-end test stops before the first item. Scanning
    to the end of the enclosing job block and letting `own_level_lines`
    establish its own level handles both that shape and the
    deeper-indented one uniformly; a sibling key at the same level is
    silently skipped by `_sequence_command_lines`'s dash-prefix filter."""
    commands: list[str] = []
    for script_key in _SCRIPT_KEYS:
        found = _find_own_key(block_lines, 0, len(block_lines), script_key)
        if found is None:
            continue
        idx, _indent, rest = found
        if strip_inline_comment(rest).strip():
            # A same-line scalar/flow value -- not the block-sequence
            # form this reader supports; skip rather than mis-parse.
            continue
        commands.extend(_sequence_command_lines(block_lines, idx + 1, len(block_lines)))
    return commands


def _top_level_block_end(lines: list[str], header_idx: int) -> int:
    """The end index of a TOP-LEVEL key's value block (ref indent 0).

    Handles GitLab's same-indent-as-key sequence style (`key:\n- item\n-
    item\n`, the shape ai-kit's own `.gitlab-ci.yml` uses for `stages:`):
    a `-`-prefixed line at indent 0 is a sequence ITEM of this key, never
    the start of the next key, even though its indent equals the next
    top-level key's indent too. Falls back to the ordinary
    `find_block_end` boundary (the first line at indent <= 0) whenever
    the immediate next structural line is NOT itself a `-`-prefixed
    indent-0 line -- the common deeper-indented-children case."""
    n = len(lines)
    i = header_idx + 1
    while i < n and not is_effective_structural(lines[i]):
        i += 1
    if i >= n:
        return n
    if line_indent(lines[i]) == 0 and lines[i].strip().startswith("-"):
        j = i
        while j < n:
            line = lines[j]
            if not is_effective_structural(line):
                j += 1
                continue
            if line_indent(line) != 0:
                j += 1
                continue
            if not line.strip().startswith("-"):
                break
            j += 1
        return j
    return find_block_end(lines, header_idx + 1, 0)


def iter_command_sites(text: str):
    """Yield `(site_name, [command_line, ...])` for every top-level
    command site in one GitLab CI file's `text`, in file-declaration
    order.

    A command site is a top-level mapping key that is NOT one of the
    reserved non-job keys (`_RESERVED_TOP_LEVEL_KEYS`) and that declares
    at least one of `script:`/`before_script:`/`after_script:`. Reading
    it this way rather than from a hand-written job list means
    `default:` and `.`-prefixed job templates are both read -- both
    really do contribute commands that run -- without a second rule. A
    top-level `before_script:`/`after_script:` whose value is a sequence
    (not a job mapping) is its OWN command site under a fixed
    pseudo-name (its own key).

    `include:` is skipped as a reserved non-job key and NONE of its forms
    is ever resolved or opened (D-C28): a pipeline composed from included
    files can run a tool this reader never sees, so a zero-finding result
    on such a repo is not evidence its CI is clean. Never raises."""
    if not text:
        return
    lines = _lines(text)
    n = len(lines)
    i = 0
    while i < n:
        line = lines[i]
        if not is_effective_structural(line) or line_indent(line) != 0:
            i += 1
            continue
        parsed = match_key_header(line.strip())
        if parsed is None:
            i += 1
            continue
        key, rest = parsed
        key = strip_yaml_quotes(key.strip())
        block_end = _top_level_block_end(lines, i)

        if key in _RESERVED_TOP_LEVEL_KEYS:
            i = block_end
            continue
        if strip_inline_comment(rest).strip():
            # An inline scalar/flow value on this top-level key -- not a
            # job mapping or a script sequence this reader supports.
            i = block_end
            continue

        block_lines = lines[i + 1 : block_end]
        if key in _TOP_LEVEL_SCRIPT_PSEUDO_SITES:
            command_lines = _sequence_command_lines(block_lines, 0, len(block_lines))
        else:
            command_lines = _extract_script_command_lines(block_lines)
        if command_lines:
            yield key, command_lines
        i = block_end


def _iter_mapping_keys(lines: list[str], start: int, end: int):
    """Yield `(key, header_idx, rest, item_end)` for each own-level
    `key:` header in `lines[start:end]` -- a generic mapping-key
    iterator used here for `jobs:`'s own job-id keys, where each job
    is a normally-deeper-indented mapping value (no same-indent-as-key
    ambiguity, unlike a sequence). `item_end` is the next own-level
    entry's index, or `end` for the last one. Never raises."""
    entries = list(own_level_lines(lines, start, end))
    for i, (idx, content) in enumerate(entries):
        parsed = match_key_header(content)
        if parsed is None:
            continue
        key, rest = parsed
        item_end = entries[i + 1][0] if i + 1 < len(entries) else end
        yield strip_yaml_quotes(key.strip()), idx, rest, item_end


def _sequence_block_end(lines: list[str], header_idx: int, ref_indent: int) -> int:
    """The end index of a `key:`'s value block when that value may be a
    SEQUENCE whose items share the key's OWN indent rather than being
    nested deeper -- GitLab's convention for `stages:`
    (`_top_level_block_end`'s reason for existing), and -- verified live
    against this plan's own GitHub Actions fixtures -- also a real shape
    for `steps:`. A `-`-prefixed line at exactly `ref_indent` is treated
    as a sequence ITEM of this key, never the start of a sibling key,
    even though its indent equals a sibling key's indent too. Falls back
    to the ordinary `find_block_end` boundary (first line at indent <=
    `ref_indent`) whenever the immediate next structural line is not
    itself a `-`-prefixed line at `ref_indent` -- the more common
    deeper-indented-items case.

    A deliberate, GitHub-only duplicate of `_top_level_block_end`'s
    logic rather than a generalization of it: `_top_level_block_end` is
    plan 14-01's committed code, always called with `ref_indent=0` for
    the GitLab reader, and this function exists so the GitHub reader's
    own boundary computation cannot change that reader's behavior by
    being refactored underneath it. Never raises."""
    n = len(lines)
    i = header_idx + 1
    while i < n and not is_effective_structural(lines[i]):
        i += 1
    if i >= n:
        return n
    if line_indent(lines[i]) == ref_indent and lines[i].strip().startswith("-"):
        j = i
        while j < n:
            line = lines[j]
            if not is_effective_structural(line):
                j += 1
                continue
            if line_indent(line) != ref_indent:
                j += 1
                continue
            if not line.strip().startswith("-"):
                break
            j += 1
        return j
    return find_block_end(lines, header_idx + 1, ref_indent)


def _iter_step_items(lines: list[str], start: int, end: int):
    """D-C14: the sequence-of-mappings item iterator. Yields
    `(header_idx, item_text, item_end)` for each `-`-prefixed own-level
    entry in `lines[start:end]` -- `header_idx` is the item's own dash
    line, `item_text` is the text after `- ` on that line (its own first
    key, when the dash line itself declares one), and `item_end` is the
    index just past the item's LAST line: its own line PLUS every
    deeper-indented continuation line beneath it, stopping at the next
    own-level `-`-prefixed entry or at `end`.

    This is precisely the capability `compose_parse.block_sequence`
    states it does NOT have (SCALAR-ITEMS-ONLY): that reader returns
    only an item's leading `- ` fragment and drops every continuation
    line, so a mapping-shaped sequence item's `run:` key -- almost
    always on a continuation line beneath the dash -- is invisible to
    it. This reader exists here rather than in the shared package
    (D-C14) because it has exactly one consumer (this module) and no
    counterpart to converge with; promoting it to `skills/_shared/` is a
    clean additive follow-up whenever a second consumer appears. Stops
    at the first own-level line that is NOT `-`-prefixed rather than
    skipping over it, the same sibling-key-boundary discipline
    `_sequence_command_lines` uses. Calls `own_level_lines` only; never
    modifies it. Never raises."""
    entries = list(own_level_lines(lines, start, end))
    items: list[tuple[int, str, int]] = []
    for i, (idx, content) in enumerate(entries):
        if not content.startswith("-"):
            break
        item_text = content[1:].strip()
        item_end = entries[i + 1][0] if i + 1 < len(entries) else end
        items.append((idx, item_text, item_end))
    return items


def _iter_step_own_keys(lines: list[str], header_idx: int, item_text: str, item_end: int):
    """Yield `(key, rest, key_header_idx)` for one step item's own-level
    keys: `item_text`'s key first (when the dash line itself declares
    one, e.g. `- uses: actions/checkout@v4` or `- run: make lint`), then
    each own-level key among the item's continuation lines.
    `key_header_idx` is `header_idx` (the dash line) for the former case
    or the real continuation line's index for the latter -- the caller
    uses it as the block-scalar boundary reference. Never raises."""
    if item_text:
        parsed = match_key_header(item_text)
        if parsed is not None:
            yield parsed[0].strip(), parsed[1], header_idx
    for idx, content in own_level_lines(lines, header_idx + 1, item_end):
        parsed = match_key_header(content)
        if parsed is not None:
            yield parsed[0].strip(), parsed[1], idx


def _run_key_command_lines(lines: list[str], key_header_idx: int, rest: str) -> list[str]:
    """Command lines contributed by one step's `run:` key. `rest` is the
    text after `run:` on its own header line. A block-scalar value
    (`|`, `>`, any chomping/indentation indicator such as `|-`, `>+`,
    `|2`) contributes each of its deeper-indented body lines as its own
    command line, blank and comment lines excluded; an ordinary scalar
    value is one command line, quotes stripped. The block-scalar
    boundary reference is `key_header_idx`'s own indent -- correct
    whether `run:` is on a continuation line (its own real indent, with
    body lines nested deeper) or on the step's dash line itself (the
    dash's own indent, still strictly less than every real body line's
    indent and equal to the next sibling item's dash indent). Never
    raises."""
    value = strip_inline_comment(rest).strip()
    if _BLOCK_SCALAR_RE.match(value):
        ref_indent = line_indent(lines[key_header_idx])
        block_end = find_block_end(lines, key_header_idx + 1, ref_indent)
        return [
            lines[j].strip()
            for j in range(key_header_idx + 1, block_end)
            if is_effective_structural(lines[j])
        ]
    if not value:
        return []
    return [strip_yaml_quotes(value)]


def _workflow_step_commands(
    lines: list[str], header_idx: int, item_text: str, item_end: int
) -> tuple[list[str], str | None]:
    command_lines: list[str] = []
    found_run = False
    step_name: str | None = None
    for key, rest, key_header_idx in _iter_step_own_keys(
        lines, header_idx, item_text, item_end
    ):
        if key == "run" and not found_run:
            found_run = True
            command_lines = _run_key_command_lines(lines, key_header_idx, rest)
        elif key == "name" and step_name is None:
            value = strip_inline_comment(rest).strip()
            if value:
                step_name = strip_yaml_quotes(value)
    return command_lines, step_name


def _iter_job_run_steps(lines: list[str], job_header_idx: int, job_end: int, job_key: str):
    steps_found = _find_own_key(lines, job_header_idx + 1, job_end, "steps")
    if steps_found is None:
        return
    steps_idx, steps_indent, steps_rest = steps_found
    if strip_inline_comment(steps_rest).strip():
        return
    steps_end = _sequence_block_end(lines, steps_idx, steps_indent)
    for header_idx, item_text, item_end in _iter_step_items(
        lines, steps_idx + 1, steps_end
    ):
        command_lines, step_name = _workflow_step_commands(
            lines, header_idx, item_text, item_end
        )
        if command_lines:
            yield job_key, command_lines, step_name


def _iter_workflow_job_steps(lines: list[str], jobs_idx: int, jobs_end: int):
    """Yield `(job_key, step_command_lines, step_name)` for every `run:` step."""
    for job_key, job_header_idx, job_rest, job_end in _iter_mapping_keys(
        lines, jobs_idx + 1, jobs_end
    ):
        if strip_inline_comment(job_rest).strip():
            continue
        yield from _iter_job_run_steps(lines, job_header_idx, job_end, job_key)


def iter_workflow_command_sites(text: str):
    """Yield `(site_name, [command_line, ...])` for every step across
    every job in one GitHub Actions workflow `text`'s `steps:`
    sequences, in job-declaration order then step-declaration order.

    Only a step's `run:` key contributes command lines -- every other
    key (`uses`, `id`, `if`, `with`, `env`, `working-directory`,
    `shell`, `continue-on-error`, `timeout-minutes`, `name`) contributes
    none: a `uses:` step's action is never fetched or analyzed, and a
    `with:` block's values (however tool-looking) are never read as
    commands, because this reader never descends into any key but
    `run:`. `site_name` is the job key, or `"<job-key> / <step-name>"`
    when the step declares a `name:` (D-C17) -- the field SET stays
    exactly what plan 14-01 pinned.

    Uses `_sequence_block_end` for both `jobs:`'s block (a mapping, no
    same-indent ambiguity) and `steps:`'s block (a sequence, which this
    plan's own fixtures showed CAN share `steps:`'s own indent). Never
    raises."""
    if not text:
        return
    lines = _lines(text)
    jobs_found = _find_own_key(lines, 0, len(lines), "jobs")
    if jobs_found is None:
        return
    jobs_idx, jobs_indent, jobs_rest = jobs_found
    if strip_inline_comment(jobs_rest).strip():
        return
    jobs_end = find_block_end(lines, jobs_idx + 1, jobs_indent)
    for job_key, command_lines, step_name in _iter_workflow_job_steps(
        lines, jobs_idx, jobs_end
    ):
        site_name = job_key if step_name is None else f"{job_key} / {step_name}"
        yield site_name, command_lines


__all__ = [
    "GITLAB_CI_FILENAMES",
    "WORKFLOWS_DIR_RELATIVE",
    "discover_ci_files",
    "iter_command_sites",
    "iter_workflow_command_sites",
    "read_ci_text",
    "repo_has_ci_config",
]

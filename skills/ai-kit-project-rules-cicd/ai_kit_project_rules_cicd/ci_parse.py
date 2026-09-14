"""GitLab CI reader (D-C1, D-C13, D-C28), built entirely on the shared
`ai_kit_rules_common.yaml_text` primitives -- reading nothing else.

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
            if entry.endswith(".yml") or entry.endswith(".yaml"):
                if os.path.isfile(os.path.join(workflows_dir, entry)):
                    return True

    return False


def discover_ci_files(repo_root: str) -> list[str]:
    """Existing root-level GitLab CI files, repo-RELATIVE paths, in
    `GITLAB_CI_FILENAMES` tuple order (D-C13's discovery order). This
    plan reads GitLab files only; plan 14-02 appends
    `.github/workflows/` entries sorted by filename to this same list.
    Never raises."""
    found: list[str] = []
    for name in GITLAB_CI_FILENAMES:
        if os.path.isfile(os.path.join(repo_root, name)):
            found.append(name)
    return found


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
    ordinary item contributes exactly one, quotes stripped."""
    commands: list[str] = []
    for idx, content in own_level_lines(lines, start, end):
        if not content.startswith("-"):
            continue
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
        block_end = find_block_end(lines, i + 1, 0)

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


__all__ = [
    "GITLAB_CI_FILENAMES",
    "WORKFLOWS_DIR_RELATIVE",
    "discover_ci_files",
    "iter_command_sites",
    "read_ci_text",
    "repo_has_ci_config",
]

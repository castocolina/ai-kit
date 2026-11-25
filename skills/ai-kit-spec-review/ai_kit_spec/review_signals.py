"""Deterministic review signals and plan facts, computed from a plan's text and paths; no I/O."""

import re


def _words(alternatives: str) -> re.Pattern:
    return re.compile(rf"\b(?:{alternatives})\b", re.IGNORECASE)


SECURITY = _words(
    r"auth(?:n|z|entic\w*|ori[sz]\w*)?|oauth\d*|jwt|csrf|xss|crypto|cryptography|encrypt\w*"
    r"|decrypt\w*|secrets?|credential\w*|password\w*|permission\w*|sandbox\w*|vulnerab\w*"
    r"|injection|security"
)
DATA = _words(
    r"database|schema|migration\w*|sql|backfill|pii|gdpr|retention|datastore|data\s+loss"
)
IRREVERSIBLE = _words(
    r"drop\s+table|drop\s+database|truncate|rm\s+-rf|force\s+push|force-push|push\s+--force"
    r"|reset\s+--hard|purge|wipe|destroy|irreversibl\w*|rotate\s+key|delete\s+all"
)
SIGNAL_NAMES = ("security", "data", "irreversible")
_PATTERNS = {"security": SECURITY, "data": DATA, "irreversible": IRREVERSIBLE}
# A rule word that forbids the hit on its line; for irreversible, also a temp-dir cleanup.
_NEGATION_RE = re.compile(r"\b(?:never|do\s+not|don't|must\s+not)\b", re.IGNORECASE)
_NO_BEFORE_RE = re.compile(r"\bno\s+[`'\"]?$", re.IGNORECASE)
_TRAP_RE = re.compile(r"\btrap\b")
_TEMP_RM_RE = re.compile(
    r"""rm\s+-rf\s+["']?(?:\$\{?(?:TMPDIR|TMP|TEMP)\b|\$\(mktemp\b|(?:\.?/)?tmp/)""",
    re.IGNORECASE)

_PATH_LINE_RE = re.compile(r"^- (?:Create|Modify|Test|Delete): (.+)$", re.MULTILINE)
_BACKTICK_RE = re.compile(r"`([^`]+)`")
_LINE_SUFFIX_RE = re.compile(r":\d+(?:-\d+)?$")
_FILES_BLOCK_RE = re.compile(r"<files>(.*?)</files>", re.DOTALL)
_TASK_HEADING_RE = re.compile(r"^### Task \d+", re.MULTILINE)
_TASK_TAG_RE = re.compile(r"<task\b")
_MIGRATIONS_RE = re.compile(r"(^|/)migrations/")


def plan_paths(text: str) -> list:
    """Unique file paths in order of appearance."""
    found = []
    for match in _PATH_LINE_RE.finditer(text):
        value = match.group(1).strip()
        span = _BACKTICK_RE.search(value)
        found.append(_LINE_SUFFIX_RE.sub("", span.group(1).strip() if span else value))
    for block in _FILES_BLOCK_RE.finditer(text):
        found.extend(part.strip() for part in block.group(1).split(",") if part.strip())
    return list(dict.fromkeys(found))


def _data_path(path: str) -> bool:
    return bool(_MIGRATIONS_RE.search(path)) or path.lower().endswith(".sql")


def _text_hit(name: str, text: str) -> bool:
    """A match that no rule word before it on its line negates; an irreversible match must also
    be no temp-dir cleanup (a trap line, or an rm -rf of a temp path)."""
    for match in _PATTERNS[name].finditer(text):
        before = text[text.rfind("\n", 0, match.start()) + 1:match.start()]
        if _NEGATION_RE.search(before) or _NO_BEFORE_RE.search(before):
            continue
        if name == "irreversible" and (_TRAP_RE.search(before)
                                       or _TEMP_RM_RE.match(text, match.start())):
            continue
        return True
    return False


def plan_signals(text: str, paths: list) -> list:
    """The signal names, in SIGNAL_NAMES order, that the text or a path raises."""
    found = []
    for name in SIGNAL_NAMES:
        pattern = _PATTERNS[name]
        in_text = pattern.search(text) if name == "data" else _text_hit(name, text)
        hit = in_text or any(pattern.search(path) for path in paths)
        if name == "data" and not hit:
            hit = any(_data_path(path) for path in paths)
        if hit:
            found.append(name)
    return found


def plan_facts(text: str) -> dict:
    """Counts of tasks, files and steps, and a small, medium or large complexity."""
    tasks = len(_TASK_HEADING_RE.findall(text)) + len(_TASK_TAG_RE.findall(text))
    files = len(plan_paths(text))
    steps = text.count("- [ ]")
    if tasks <= 2 and files <= 3:
        complexity = "small"
    elif tasks >= 6 or files >= 10:
        complexity = "large"
    else:
        complexity = "medium"
    return {"tasks": tasks, "files": files, "steps": steps, "complexity": complexity}

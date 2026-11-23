"""35 D-04, D-06, D-20: jev seam for catalog name matching and class judgment and the
proposal's fit scores (36 D-07). A lookup copy of fold_group.py's jev client
(tests/test_arch.py LOOKUP_COPIES); one ladder call per batch;
advisory: no answer means unmatched or unknown."""

import json
import os
import subprocess
import sys

# The client's entry point, relative to a skills root: the lookup's last step, per root.
JEV_ENTRY_REL = os.path.join("jev-fast-decision", "scripts", "jev_review.py")
# A lookup copy of jev_ladder.py's SKILLS_ROOTS (same values; a test compares the parsed tuples).
SKILLS_ROOTS = (
    ("CLAUDE_CONFIG_DIR", ".claude", "skills"),
    (None, ".agents", "skills"),
    ("XDG_CONFIG_HOME", ".config", "opencode/skills"),
    ("CURSOR_CONFIG_DIR", ".cursor", "skills"),
    ("PI_CODING_AGENT_DIR", ".pi/agent", "skills"),
)

NAME_QUESTION = (
    "Which catalog entry is the same model as this host's model name? Pick the entry that "
    "names the same model; ignore effort words such as high or thinking."
)
CLASS_QUESTION = (
    "Which class fits this model best? flagship: top quality; coding: stronger at code than its "
    "overall level; general: balanced; fast: high output speed; small: light and cheap."
)
CLASSES = ("flagship", "coding", "general", "fast", "small")
CONTEXT_CHARS = 600
NAME_CHARS = 80
BATCH_CHARS = 7000
SCORE_LEVELS = ("very poor fit", "poor fit", "fair fit", "good fit", "excellent fit")
SCORE_CONTEXT_CHARS = 240
SCORE_QUESTIONS = {
    "review": (
        "Rate how well a model with these facts fits reviewing plans and code diffs for flaws: "
        "top quality and careful reasoning matter most; cost and speed barely matter."
    ),
    "execute": (
        "Rate how well a model with these facts fits writing code from a plan many times over: "
        "coding skill, speed and low cost matter most; top quality matters less."
    ),
}


def skills_roots(env, own_root):
    """The skills dirs to search, in lookup order: own_root first, then configured roots."""
    home = env.get("HOME", "~")
    roots = [own_root] if own_root else []
    for variable, fallback, suffix in SKILLS_ROOTS:
        base = (env.get(variable, "").strip() if variable else "") or os.path.join(home, fallback)
        roots.append(os.path.join(base, suffix))
    return [os.path.expanduser(root) for root in roots]


def _own_skills_root():
    """The skills dir that holds ai-kit-spec-review (three dirnames up from this file)."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def find_jev(env, own_root=None):
    """The first installed jev-fast-decision client in the lookup order, or None."""
    for root in skills_roots(env, own_root or _own_skills_root()):
        entry = os.path.join(root, JEV_ENTRY_REL)
        if os.path.isfile(entry):
            return entry
    return None


def _timeout(n_items: int) -> int:
    return 30 * (n_items + 3) + 10


def _clean(text) -> str:
    return "".join(ch for ch in str(text) if ch.isprintable())[:NAME_CHARS]


def name_item(index: int, host_name: str, names: list) -> dict:
    shown = [_clean(name) for name in names[:5]]
    context = f"Host model name: {_clean(host_name)}. Candidate entries: " + "; ".join(
        f"e{i} = {name}" for i, name in enumerate(shown)
    )
    criteria = {f"e{i}": name for i, name in enumerate(shown)}
    criteria["none"] = "none of these entries is the same model"
    return {
        "id": f"n{index}",
        "type": "choice",
        "instructions": NAME_QUESTION,
        "context": context[:CONTEXT_CHARS],
        "criteria": criteria,
    }


def class_item(index: int, model_name: str, summary: str) -> dict:
    return {
        "id": f"k{index}",
        "type": "choice",
        "instructions": CLASS_QUESTION,
        "context": f"Model: {_clean(model_name)}. Known facts: {summary}"[:CONTEXT_CHARS],
        "criteria": {name: name for name in CLASSES},
    }


def _batches(items: list) -> list:
    batches = []
    group = []
    for item in items:
        candidate = [*group, item]
        if group and len(json.dumps({"items": candidate})) > BATCH_CHARS:
            batches.append(group)
            group = [item]
        else:
            group = candidate
    if group:
        batches.append(group)
    return batches


def _column_answer(item, row) -> tuple:
    if not isinstance(row, dict) or not isinstance(row.get("decided_by"), str):
        return None, None, "no answer"
    column = row.get(row["decided_by"])
    if not isinstance(column, dict):
        return None, None, "no answer"
    top = column.get("top")
    if isinstance(top, bool) or not isinstance(top, (int, float)) or not 0 <= top <= 1:
        top = None
    if column.get("needs_fallback") or column.get("forced") or column.get("fallback"):
        return None, top, "low"
    if top is None:
        return None, None, "no answer"
    choice = column.get("choice")
    if isinstance(choice, str) and choice in item["criteria"]:
        return choice, top, ""
    return None, None, "no answer"


def ask_items(entry: str, items: list, env, run=subprocess.run, strict=False) -> dict:
    """Ask jev once per bounded batch; malformed, old and failed answers stay advisory."""
    answers = {}
    for group in _batches(items):
        try:
            proc = run(
                [sys.executable, entry, "ladder"],
                input=json.dumps({"items": group}),
                capture_output=True,
                text=True,
                env=env,
                timeout=_timeout(len(group)),
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as error:
            reason = "timeout" if isinstance(error, subprocess.TimeoutExpired) else "no answer"
            answers.update({item["id"]: (None, None, reason) for item in group})
            continue
        if proc.returncode == 2 and "invalid choice" in (proc.stderr or ""):
            answers.update({item["id"]: (None, None, "old") for item in group})
            continue
        if strict and proc.returncode != 0:
            answers.update({item["id"]: (None, None, "failed") for item in group})
            continue
        try:
            response = json.loads(proc.stdout)
        except (TypeError, ValueError):
            response = None
        rows = response.get("items") if isinstance(response, dict) else None
        for item in group:
            result = _column_answer(item, rows.get(item["id"])) if isinstance(rows, dict) else (
                None, None, "no answer"
            )
            answers[item["id"]] = result
    return answers


def name_judge(env, own_root=None, run=subprocess.run):
    """Return a batch name judge when jev is installed, otherwise None."""
    entry = find_jev(env, own_root)
    if entry is None:
        return None

    def judge(pairs):
        items = [name_item(index, name, names) for index, (name, names) in enumerate(pairs)]
        answers = ask_items(entry, items, env, run)
        result = []
        for item, (_host_name, names) in zip(items, pairs, strict=True):
            choice, confidence, reason = answers[item["id"]]
            if choice == "none":
                result.append((None, confidence, "none"))
            elif isinstance(choice, str) and choice.startswith("e") and choice[1:].isdigit():
                index = int(choice[1:])
                result.append((names[index], confidence, reason) if index < len(names)
                              else (None, confidence, "no answer"))
            else:
                result.append((None, confidence, reason))
        return result

    return judge


def class_judge(env, own_root=None, run=subprocess.run):
    """Return a batch class judge when jev is installed, otherwise None."""
    entry = find_jev(env, own_root)
    if entry is None:
        return None

    def judge(pairs):
        items = [class_item(index, model, summary)
                 for index, (model, summary) in enumerate(pairs)]
        answers = ask_items(entry, items, env, run)
        return [answers[item["id"]] for item in items]

    return judge


def score_item(index: int, purpose: str, summary: str) -> dict:
    """Build a score item containing only printable ASCII facts."""
    context = "".join(ch for ch in summary if ch.isascii() and ch.isprintable())
    return {"id": f"c{index}", "type": "score", "instructions": SCORE_QUESTIONS[purpose],
            "context": context[:SCORE_CONTEXT_CHARS], "criteria": list(SCORE_LEVELS)}


def score_judge(env, own_root=None, run=subprocess.run):
    """Return a batch score judge when jev is installed, otherwise None."""
    entry = find_jev(env, own_root)
    if entry is None:
        return None

    def judge(pairs):
        items = [score_item(index, purpose, summary)
                 for index, (purpose, summary) in enumerate(pairs)]
        answers = ask_items(entry, items, env, run)
        return [answers[item["id"]] for item in items]

    return judge

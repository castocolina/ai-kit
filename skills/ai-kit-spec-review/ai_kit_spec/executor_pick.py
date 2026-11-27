"""jev's advisory pick of the executor among the filtered roster candidates; labels only, never
names or config values."""

import subprocess
from typing import NamedTuple

from ai_kit_spec import catalog_bands, jev_names
from ai_kit_spec.jev_review import _confident, _label
from ai_kit_spec.lane_order import EFFORT_FACT_LEVELS
from ai_kit_spec.routing import strip_model_suffix
from ai_kit_spec.usability import find_runtime_key

PICK_QUESTION = "Which candidate should implement this task, judged only from these labels?"
TASK_LABELS = ("frontend", "backend", "mixed", "plan")
LITE_CLASSES = ("small", "fast")


class Pick(NamedTuple):
    key: str | None
    decided_by: str  # "jev" or "default"
    confidence: float | None
    note: str


def catalog_class(entries: dict, candidate: dict) -> str:
    """The catalog class value of the candidate's runtime and model, or unknown."""
    runtime = candidate.get("runtime")
    model = candidate.get("model") or ""
    if not runtime or not model:
        return "unknown"
    key = (find_runtime_key(entries, runtime, strip_model_suffix(runtime, model))
           or find_runtime_key(entries, runtime, model))
    if key is None:
        return "unknown"
    facts = entries[key].get("facts")
    klass = facts.get("class") if isinstance(facts, dict) else None
    value = klass.get("value") if isinstance(klass, dict) else None
    return value if value in catalog_bands.CLASSES else "unknown"


def candidate_labels(
    candidates: list, routes: dict, task_type: str | None, entries: dict,
) -> list:
    """Per-candidate labels: route kind, effort, catalog class, task affinity and the task type."""
    task = _label(task_type or "none", ("none", *TASK_LABELS))
    labels = []
    for c in candidates:
        if c.get("runtime") is None and not c.get("command"):
            route = "session"
        elif routes.get(c["key"]) == "native":
            route = "native"
        else:
            route = "external_cli"
        labels.append({"route": route,
                       "effort": _label(c.get("effort") or "none", EFFORT_FACT_LEVELS),
                       "class": catalog_class(entries, c),
                       "affinity": _label(c.get("task_affinity") or "none",
                                          ("none", *TASK_LABELS)),
                       "task": task})
    return labels


def is_lite(entries: dict, candidate: dict) -> bool:
    """True when the candidate's catalog class is a lite class."""
    return catalog_class(entries, candidate) in LITE_CLASSES


def candidate_items(candidates: list, labels: list) -> tuple[dict, dict]:
    """One jev choice item over opaque tokens, and the token -> key map."""
    tokens = {f"c{i + 1}": c["key"] for i, c in enumerate(candidates)}
    context = f"Task type: {labels[0]['task'] if labels else 'none'}." + "".join(
        f" {token}: route {lab['route']}, effort {lab['effort']}, class {lab['class']}, "
        f"affinity {lab['affinity']}." for token, lab in zip(tokens, labels, strict=True))
    item = {
        "id": "x0", "type": "choice", "instructions": PICK_QUESTION,
        # the context is never cut: pick_executor refuses an over-long one
        "context": context,
        "criteria": {token: f"candidate {token[1:]}" for token in tokens},
    }
    return item, tokens


def pick_executor(candidates: list, labels: list, env, run=subprocess.run, *,
                  own_root=None) -> Pick:
    """jev's pick among the candidates; Pick.key None keeps today's order."""
    if len(candidates) < 2:
        return Pick(None, "default", None, "one candidate")
    item, tokens = candidate_items(candidates, labels)
    if len(item["context"]) > jev_names.CONTEXT_CHARS:
        return Pick(None, "default", None, "too many candidates")
    entry = jev_names.find_jev(env, own_root)
    if entry is None:
        return Pick(None, "default", None, "jev absent")
    answer = jev_names.ask_items(entry, [item], env, run, strict=True).get(
        "x0", (None, None, "no answer"))
    choice, top, _reason = answer
    if not _confident(answer):
        return Pick(None, "default", top, "jev low")
    key = tokens.get(choice)
    return Pick(key, "jev", top, "") if key is not None else Pick(
        None, "default", top, "pick outside the roster discarded")


def dispatch_record(pick: Pick, dispatched_key: str) -> dict:
    """The injection's pick field: which side decided the lane actually dispatched."""
    if pick.key is not None and pick.key == dispatched_key:
        return {"decided_by": "jev", "confidence": pick.confidence, "note": ""}
    if pick.key is not None:
        # jev picked a key the walk could not use
        return {"decided_by": "default", "confidence": pick.confidence,
                "note": "jev pick unavailable"}
    return {"decided_by": "default", "confidence": pick.confidence, "note": pick.note}


def pick_line(dispatched_key: str, record: dict) -> str:
    """The one stderr line of the dispatch decision."""
    if record["decided_by"] == "jev":
        return f"ai-kit-spec: executor pick: {dispatched_key} (jev, {record['confidence']:.2f})"
    return f"ai-kit-spec: executor pick: {dispatched_key} (default: {record['note']})"

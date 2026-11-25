"""The review's append-only round log: one JSON object per line, one lane state per event."""

import json
import os
from typing import NamedTuple

from ai_kit_spec.error_classifier import NEVER_RESOLVED, REASONS

LANE_STATES = ("chosen", "judged", "failed", "replaced", "never_resolved")


def lane_event(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        round_no: int, key: str, state: str, at: float, reason=None, cause=None,
        by=None) -> dict:
    """One lane state of the round log."""
    return {"round": round_no, "key": key, "state": state, "reason": reason, "cause": cause,
            "by": by, "at": at}


def append_event(path: str, *events: dict) -> None:
    """Use one write for all lines because two dispatch processes may append at the same time."""
    data = "".join(json.dumps(event, sort_keys=True) + "\n" for event in events).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)


def read_events(path: str) -> list:
    try:
        with open(path, encoding="utf-8") as stream:
            lines = stream.readlines()
    except FileNotFoundError:
        return []
    events = []
    for line in lines:
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def round_states(events: list, round_no: int) -> dict:
    states = {}
    for event in events:
        key, state, rnd = event.get("key"), event.get("state"), event.get("round")
        if not isinstance(key, str) or not isinstance(state, str) or state not in LANE_STATES:
            continue
        if isinstance(rnd, int) and not isinstance(rnd, bool) and rnd >= 1 and rnd == round_no:
            states[key] = event
    return states


class Outcome(NamedTuple):
    judged: list
    others: list
    partial: bool
    none_judged: bool
    round_no: int


def _shown_reason(event: dict) -> str:
    reason = event.get("reason")
    if not reason:
        return NEVER_RESOLVED
    return reason if reason in REASONS else "real_error"


def review_outcome(events: list, upto_round: int, roster: list) -> Outcome:
    final = round_states(events, upto_round)
    found = [key for key, event in final.items() if event["state"] == "judged"]
    judged = [key for key in roster if key in found] + [key for key in found if key not in roster]
    others = []
    for rnd in range(1, upto_round + 1):
        for key, event in round_states(events, rnd).items():
            if event["state"] != "judged":
                others.append((key, _shown_reason(event), event.get("by"), rnd))
    others.sort(key=lambda item: (item[3],
                                  roster.index(item[0]) if item[0] in roster else len(roster)))
    return Outcome(judged, others, bool(others), not judged, upto_round)


def judged_line(outcome: Outcome) -> str:
    line = "Judged by: " + ", ".join(outcome.judged)
    if outcome.others:
        entries = []
        for key, reason, by, rnd in outcome.others:
            entry = f"{key} ({reason}"
            if by:
                entry += f", by {by}"
            if rnd != outcome.round_no:
                entry += f", round {rnd}"
            entries.append(entry + ")")
        line += "; not judged: " + ", ".join(entries)
    return line


def record_merge(path: str, round_no: int, readable: list, failed: list, at: float) -> list:
    states = round_states(read_events(path), round_no)
    for key, missing in failed:
        state = states.get(key, {}).get("state")
        if state in ("failed", "replaced", "never_resolved"):
            continue
        unresolved = missing and state == "chosen"
        append_event(path, lane_event(
            round_no, key, "never_resolved" if unresolved else "failed", at,
            NEVER_RESOLVED if unresolved else "real_error"))
    judged = []
    for key in readable:
        state = states.get(key, {}).get("state")
        if state not in (None, "chosen", "judged"):
            continue
        if state != "judged":
            append_event(path, lane_event(round_no, key, "judged", at))
        judged.append(key)
    return judged

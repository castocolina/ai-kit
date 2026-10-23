#!/usr/bin/env python3
"""Env-driven stub of the 21.1 decision client for precompact tests.

Selected through AI_KIT_PRECOMPACT_CLIENT so no test reaches the real client
or a real backend. With argv ["--probe"] it prints a probe report chosen by
STUB_PROBE ("up" default, "down", "remote_only"); otherwise it reads one JSON
request object on stdin and answers items[0] with a label chosen by
STUB_LABELS (JSON map by id), else STUB_LABEL_CYCLE (comma list, index = the
integer after the id's "c"), else "keep". Ids in STUB_ERROR_IDS get a
status "unavailable" reply; ids in STUB_FALLBACK_IDS get needs_fallback true.
STUB_SLEEP seconds (or 3600 with STUB_HANG=1) delay the answer, only for ids
in STUB_SLEEP_IDS when that list is set. With STUB_LOG set, every call first
appends one JSON line with argv, pid, the JEV_*/GSD_PATH_JEV*/XDG_CONFIG_HOME
env and the payload. Always exits 0.
"""

import json
import os
import sys
import time

_LABELS = ("keep", "summarize", "discard")


def _log_line(argv, payload):
    """One JSON line describing this call, appended to STUB_LOG when set."""
    path = os.environ.get("STUB_LOG")
    if not path:
        return
    env = {key: value for key, value in os.environ.items()
           if key.startswith("JEV_") or key.startswith("GSD_PATH_JEV")
           or key == "XDG_CONFIG_HOME"}
    line = {"argv": list(argv), "pid": os.getpid(), "env": env, "payload": payload}
    try:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(line, sort_keys=True) + "\n")
    except OSError:
        pass


def _id_list(name):
    raw = os.environ.get(name)
    return [item for item in raw.split(",") if item] if raw else []


def _probe():
    mode = os.environ.get("STUB_PROBE", "up")
    laya = {"name": "laya", "remote": False, "batch": False, "host": "127.0.0.1",
            "usable": True, "key_source": "stub"}
    typesafe = {"name": "typesafe", "remote": True, "batch": True, "host": "api.example",
                "usable": True, "key_source": "stub"}
    if mode == "down":
        laya = {"name": "laya", "remote": False, "batch": False, "host": "127.0.0.1",
                "usable": False, "reason": "unreachable", "key_source": "stub"}
        return {"status": "unavailable", "backends": [laya]}
    if mode == "remote_only":
        laya = {"name": "laya", "remote": False, "batch": False, "host": "127.0.0.1",
                "usable": False, "reason": "unreachable", "key_source": "stub"}
    return {"status": "ok", "backends": [laya, typesafe]}


def _label_for(item_id):
    labels = os.environ.get("STUB_LABELS")
    if labels:
        try:
            mapped = json.loads(labels)
        except ValueError:
            mapped = None
        if isinstance(mapped, dict) and item_id in mapped:
            return str(mapped[item_id])
    cycle = _id_list("STUB_LABEL_CYCLE")
    if cycle:
        try:
            index = int(item_id.split("c", 1)[1])
        except (IndexError, ValueError):
            index = 0
        return cycle[index % len(cycle)]
    return "keep"


def _sleep_for(item_id):
    wanted = _id_list("STUB_SLEEP_IDS")
    if wanted and item_id not in wanted:
        return
    if os.environ.get("STUB_HANG") == "1":
        seconds = 3600.0
    else:
        seconds = 0.0
        raw = os.environ.get("STUB_SLEEP")
        if raw:
            try:
                seconds = float(raw)
            except ValueError:
                seconds = 0.0
    if seconds > 0:
        time.sleep(seconds)


def _screen():
    try:
        payload = json.loads(sys.stdin.read())
    except ValueError:
        payload = None
    _log_line(["screen"], payload)
    if not isinstance(payload, dict):
        print(json.dumps({"advisory": True, "status": "invalid_input"}))
        return 0
    items = payload.get("items")
    if not isinstance(items, list) or not items or not isinstance(items[0], dict):
        print(json.dumps({"advisory": True, "status": "invalid_input"}))
        return 0
    item_id = str(items[0].get("id", ""))
    _sleep_for(item_id)
    if item_id in _id_list("STUB_ERROR_IDS"):
        print(json.dumps({"advisory": True, "status": "unavailable",
                          "reason": "invalid_response"}))
        return 0
    label = _label_for(item_id)
    probabilities = {name: 0.05 for name in _LABELS}
    probabilities[label] = 0.9
    answer = {"type": "choice", "choice": label, "confidence": 0.9,
              "probabilities": probabilities,
              "needs_fallback": item_id in _id_list("STUB_FALLBACK_IDS"),
              "backend": "laya", "model": "stub"}
    print(json.dumps({"advisory": True, "status": "ok", "answers": {item_id: answer}}))
    return 0


def main(argv):
    """--probe prints the table report, anything else screens stdin. Always exit 0."""
    if "--probe" in argv[1:]:
        _log_line(["--probe"], None)
        print(json.dumps(_probe(), sort_keys=True))
        return 0
    return _screen()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

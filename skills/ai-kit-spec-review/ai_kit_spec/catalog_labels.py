"""35 D-08: one label vocabulary for catalog facts.

Every fact is {value, label, source, fetched_at}; judged facts carry a confidence
('rule' or 0..1). Stdlib only.
"""

import time

LABELS = ("measured", "judged", "assumed", "user-stated")
UNKNOWN = "unknown"


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def fact(value, label: str, source: str, fetched_at: str, confidence=None) -> dict:
    if label not in LABELS:
        raise ValueError(f"unknown label: {label}")
    if label == "judged" and confidence is None:
        raise ValueError("judged needs a confidence")
    result = {"value": value, "label": label, "source": source, "fetched_at": fetched_at}
    if label == "judged":
        result["confidence"] = confidence
    return result


def fact_problem(value) -> str | None:
    if not isinstance(value, dict):
        return "bad fact: not an object"
    for key in ("value", "label", "source", "fetched_at"):
        if key not in value:
            return f"bad fact: missing {key}"
    if value["label"] not in LABELS:
        return f"bad fact: label {value['label']}"
    if not isinstance(value["source"], str) or not isinstance(value["fetched_at"], str):
        return "bad fact: source or fetched_at not text"
    if value["label"] == "judged":
        confidence = value.get("confidence")
        valid_rule = confidence == "rule" and isinstance(confidence, str)
        valid_score = isinstance(confidence, (int, float)) and not isinstance(confidence, bool) \
            and 0 <= confidence <= 1
        if not (valid_rule or valid_score):
            return f"bad fact: confidence {confidence}"
    return None


def show(value) -> str:
    if not isinstance(value, dict) or value.get("value") is None:
        return UNKNOWN
    problem = fact_problem(value)
    if problem:
        return UNKNOWN
    raw = value["value"]
    rendered = ", ".join(str(item) for item in raw) if isinstance(raw, list) else str(raw)
    details = [value["label"]]
    if value["label"] == "judged":
        details[0] += f" {value['confidence']}"
    details.extend((value["source"], value["fetched_at"]))
    return f"{rendered} ({', '.join(details)})"

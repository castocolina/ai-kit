"""36 HUB-10, SPEC R13, contract item 4: consistency of a free lane's data-use record.

The calling skill reads the vendor page and sets values; nothing here defaults a value.
"""

import datetime
import re

from ai_kit_spec import secret_shapes

DATA_USE_VALUES = ("zero_retention", "may_be_kept_or_trained", "unknown")
DATA_USE_LABELS = ("verified", "reported")
DATA_USE_KEYS = ("data_use", "data_use_line", "data_use_source", "data_use_read",
                 "data_use_label", "data_use_confirmed")
LINE_MAX = 200
SOURCE_MAX = 300
_CONTROL_RX = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_SOURCE_RX = re.compile(r"https://\S{1,292}")
_DATE_RX = re.compile(r"\d{4}-\d{2}-\d{2}")


def clean_line(text) -> str:
    line = " ".join(_CONTROL_RX.sub(" ", str(text)).split())
    line = secret_shapes.redact(line, "[redacted]")
    return line[:LINE_MAX].strip()


def _valid_source(value) -> bool:
    return value == "none" or (isinstance(value, str) and bool(_SOURCE_RX.fullmatch(value))
                               and not secret_shapes.detect(value))


def _valid_date(value) -> bool:
    if not isinstance(value, str) or not _DATE_RX.fullmatch(value):
        return False
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return True


_FIELD_CHECKS = (
    ("data_use", lambda v: v in DATA_USE_VALUES,
     "data_use must be one of: zero_retention, may_be_kept_or_trained, unknown"),
    ("data_use_line", lambda v: isinstance(v, str) and bool(v) and v == clean_line(v),
     "data_use_line must be one non-empty line of at most 200 characters, "
     "with no control characters and no key shapes"),
    ("data_use_source", _valid_source,
     "data_use_source must be an https:// address of at most 300 characters "
     "with no key shape, or none"),
    ("data_use_read", _valid_date, "data_use_read must be a date in the form YYYY-MM-DD"),
    ("data_use_confirmed", lambda v: v is True,
     "data_use_confirmed must be true (a lane the owner declined is not written)"),
)


def _cross_problem(entry: dict) -> str | None:
    if entry["data_use"] == "unknown":
        return ("data_use_label must be absent when data_use is unknown"
                if "data_use_label" in entry else None)
    if entry.get("data_use_label") not in DATA_USE_LABELS:
        return ("data_use_label must be one of: verified, reported "
                "(required when data_use is not unknown)")
    if entry["data_use_source"] == "none":
        return ("data_use zero_retention or may_be_kept_or_trained needs the https:// "
                "source it was read from")
    return None


def validate_note(entry: dict) -> str | None:
    if not any(key in entry for key in DATA_USE_KEYS):
        return None
    missing = [key for key in DATA_USE_KEYS if key != "data_use_label" and key not in entry]
    if missing:
        return "data-use record is incomplete: missing " + ", ".join(missing)
    for key, predicate, message in _FIELD_CHECKS:
        if not predicate(entry[key]):
            return message
    return _cross_problem(entry)

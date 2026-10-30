"""The host-reported reset parser (D-28, D-29, D-30, D-37; SPEC R4).

Claude Code's limit line (`You've hit your session limit · resets 1pm
(America/Santiago)`, spike 004) is parsed with the stdlib only — `re`,
`datetime` and `zoneinfo`; no `tzdata` package (T-26-SC). Everything derived
here (the +60 s margin, the year of a year-less date, the day rollover) is
inference and is labelled so by every caller; only the redacted evidence is
observed. The redaction policy is the runner's own (`cross-ai.mjs`
`redactSecrets`/`replaceCopies`) ported to Python — D-37 keeps this parser
separate from the runner.
"""

import re
from datetime import UTC, datetime, timedelta
from typing import NamedTuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

MAX_RESET_AHEAD_S = 604800  # 7 days, the recurring-job expiry (spike 004)
RESET_MARGIN_S = 60  # absorbs the timer's 1-minute AccuracySec (D-28)
EVIDENCE_MAX = 2000

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# The spike-004 grammar: anchored on the literal `resets`, an optional
# `<Mon> <D>,` (three-letter English month), `H` or `H:MM`, `am|pm`, and a
# parenthesised IANA name. The `·` separator and any surrounding prose are
# irrelevant.
RESET_RE = re.compile(
    r"\bresets\s+"
    r"(?:(?P<mon>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
    r"\s+(?P<day>[0-9]{1,2}),\s*)?"
    r"(?P<hour>[0-9]{1,2})(?::(?P<min>[0-9]{1,2}))?\s*(?P<ampm>am|pm)\s*"
    r"\((?P<zone>[A-Za-z0-9_./+-]+)\)",
    re.IGNORECASE,
)


class ResetResult(NamedTuple):
    """One parsed reset: the epoch instant, or the refusal reason.

    `evidence` always carries the input redacted and capped, so a refusal can
    still be logged without storing a secret."""

    at: float | None
    reason: str | None
    evidence: str


# ── evidence redaction (the runner's policy, ported) ────────────────────────

# Child text can echo credentials and identifiers. Key rules preserve the key
# and replace only its complete quoted or delimited value; shape rules replace
# the whole match. The alternatives are the runner's, kept exactly.
_SECRET_SHAPE_RES = [
    re.compile(r"(?:sk|rk)-[A-Za-z0-9_-]{8,}", re.IGNORECASE),
    re.compile(r"(?<=\bBearer )[A-Za-z0-9._~+/=-]{8,}", re.IGNORECASE),
    re.compile(r"(?<=\bBasic )[A-Za-z0-9+/=]{8,}", re.IGNORECASE),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"conn:[0-9a-f]{8,}", re.IGNORECASE),
    re.compile(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE
    ),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b", re.IGNORECASE),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b", re.IGNORECASE),
    # ai-kit addition (review round 1, T-26-20): any run of 32+ hex characters.
    re.compile(r"[0-9a-fA-F]{32,}"),
]

_VALUE = (
    r'(?:\\?"(?:\\.|[^"\\])*\\?"'  # "..." with \-escapes
    r"|\\?'(?:\\.|[^'\\])*\\?'"  # '...' with \-escapes
    r'|[^\s,"\'\]};&]+)'  # or one bare delimited word
)
KEY_VALUE_RE = re.compile(
    r'((?:\\?["\']?)(?:api[_-]?key|token|secret|password|passwd|(?<=[?&])key)'
    r'(?:\\?["\']?)\s*(?:=>|[:=])\s*)' + _VALUE,
    re.IGNORECASE,
)
ID_VALUE_RE = re.compile(
    r'((?:\\?["\']?)(?:account|connection|conn|org|organization|user|request|session|key)'
    r'[_-]?id(?:\\?["\']?)\s*(?:=>|[:=])\s*)' + _VALUE,
    re.IGNORECASE,
)

_QUOTE_PREFIX_RE = re.compile(r'^\\?["\']')


def _redacted_values(text: str) -> list[str]:
    """The values the key rules remove, deduplicated (the runner's
    `redactedValues`): each is replaced wherever else it appears."""
    values: list[str] = []
    for pattern in (KEY_VALUE_RE, ID_VALUE_RE):
        for match in pattern.finditer(text):
            removed = match.group(0)[len(match.group(1)) :]
            removed = re.sub(r'^\\?["\']', "", removed)
            removed = re.sub(r'\\?["\']$', "", removed)
            if removed:
                values.append(removed)
    return list(dict.fromkeys(values))


def _replace_copies(text: str, values: list[str]) -> str:
    """Replace every whole-word occurrence of each removed value (the runner's
    `replaceCopies`)."""
    out = text
    for value in values:
        if not value:
            continue
        pattern = f"(?<![A-Za-z0-9]){re.escape(value)}(?![A-Za-z0-9])"
        out = re.sub(pattern, "<redacted>", out)
    return out


def _keep_prefix(match: re.Match[str]) -> str:
    """The key rules' replacement: keep the key (and its quote), redact the
    value."""
    prefix = match.group(1)
    value = match.group(0)[len(prefix) :]
    quote_match = _QUOTE_PREFIX_RE.match(value)
    quote = quote_match.group(0) if quote_match else ""
    if quote:
        return f"{prefix}{quote}<redacted>{quote}"
    return f"{prefix}<redacted>"


def redact(text: str) -> str:
    """The runner's `redactSecrets`: key rules (plain, quoted and
    backslash-escaped-quote keys) keep their key and quote; shape rules
    replace the whole match; every value a key rule removed is also replaced
    wherever else it appears."""
    out = text
    copies = _redacted_values(out)
    for pattern in (KEY_VALUE_RE, ID_VALUE_RE):
        out = pattern.sub(_keep_prefix, out)
    for shape in _SECRET_SHAPE_RES:
        out = shape.sub("<redacted>", out)
    return _replace_copies(out, copies)


def cap_code_points(text: str, n: int) -> str:
    """Cap at `n` code points. A Python `str` slices by code point, so no
    character (or surrogate pair) is ever split (SPEC R4 encoding)."""
    return text[:n]


def iso_z(when: float) -> str:
    """`YYYY-MM-DDTHH:MM:SSZ`, the ISO UTC form the state and output use."""
    return datetime.fromtimestamp(when, tz=UTC).isoformat().replace("+00:00", "Z")


def calendar_line(when: float) -> str:
    """`OnCalendar=YYYY-MM-DD HH:MM:SS UTC` — the absolute second entry on the
    persistent timer (D-28); seconds are exact, the +60 s margin absorbs
    `AccuracySec` (SPEC R4 precision)."""
    moment = datetime.fromtimestamp(when, tz=UTC)
    return f"OnCalendar={moment.strftime('%Y-%m-%d %H:%M:%S')} UTC"


# ── parsing ─────────────────────────────────────────────────────────────────


def check_bounds(at: float, now: float) -> str | None:
    """SPEC R4 boundary: strictly future, at most 7 days ahead. Exactly 7 days
    is accepted, one second later is refused."""
    if at <= now:
        return "reset is not in the future"
    if at - now > MAX_RESET_AHEAD_S:
        return "reset is more than 7 days away"
    return None


def _result(at: float, now: float, evidence: str) -> ResetResult:
    reason = check_bounds(at, now)
    if reason is not None:
        return ResetResult(None, reason, evidence)
    return ResetResult(at, None, evidence)


def _clock_hour(hour: int, ampm: str) -> int:
    """12am -> 0, 12pm -> 12, else am unchanged, pm +12."""
    suffix = ampm.lower()
    if suffix == "am":
        return 0 if hour == 12 else hour
    return 12 if hour == 12 else hour + 12


def _minute(match: re.Match[str]) -> int:
    return int(match.group("min") or 0)


def _parse_dated(match: re.Match[str], zone: ZoneInfo, now: float, evidence: str) -> ResetResult:
    """A dated form (`resets Oct 22, 10pm`) carries no year: build the date in
    the zone's current year and in the next year, and take whichever lands in
    (now, now + 7 d]."""
    month = _MONTHS[match.group("mon").lower()]
    day = int(match.group("day"))
    hour = _clock_hour(int(match.group("hour")), match.group("ampm"))
    minute = _minute(match)
    year = datetime.fromtimestamp(now, tz=zone).year
    for candidate_year in (year, year + 1):
        try:
            local = datetime(candidate_year, month, day, hour, minute, tzinfo=zone)
        except ValueError:
            return ResetResult(
                None, f"reset date does not exist ({month:02d}-{day:02d})", evidence
            )
        result = _result(local.timestamp(), now, evidence)
        if result.reason is None:
            return result
    return ResetResult(None, "reset date is not within the next 7 days", evidence)


def _parse_time_only(
    match: re.Match[str], zone: ZoneInfo, now: float, evidence: str
) -> ResetResult:
    """A date-less form (`resets 1pm`) is the next such local time strictly
    after now."""
    local_now = datetime.fromtimestamp(now, tz=zone)
    candidate = local_now.replace(
        hour=_clock_hour(int(match.group("hour")), match.group("ampm")),
        minute=_minute(match),
        second=0,
        microsecond=0,
    )
    if candidate.timestamp() <= now:
        candidate += timedelta(days=1)
    return _result(candidate.timestamp(), now, evidence)


def parse_reset_text(text: str, now: float) -> ResetResult:
    """Parse the host's limit text in its own IANA zone (D-37, SPEC R4).

    # shortcut: local times are built with fold=0 and no DST gap or fold
    # special case; the host prints real instants, so a gap time has never
    # been observed (research Q4). Upgrade if one ever is.
    """
    evidence = cap_code_points(redact(text), EVIDENCE_MAX)
    match = RESET_RE.search(text)
    if match is None:
        return ResetResult(None, "reset text not recognized", evidence)
    hour = int(match.group("hour"))
    if not 1 <= hour <= 12 or _minute(match) > 59:
        return ResetResult(None, "reset time is malformed (hour 1..12, minute 0..59)", evidence)
    zone_name = match.group("zone")
    try:
        zone = ZoneInfo(zone_name)
    except (ZoneInfoNotFoundError, ValueError):
        return ResetResult(
            None,
            f"unknown time zone {zone_name!r}: not in the system zone database",
            evidence,
        )
    if match.group("mon") is not None:
        return _parse_dated(match, zone, now, evidence)
    return _parse_time_only(match, zone, now, evidence)


def parse_reset_at(value: str, now: float) -> ResetResult:
    """Parse `--reset-at`: epoch seconds, or ISO 8601 with `Z` or an explicit
    offset (D-30). A naive ISO time is refused."""
    evidence = cap_code_points(redact(value), EVIDENCE_MAX)
    if value.isdigit():
        return _result(float(value), now, evidence)
    text = value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return ResetResult(None, "reset time is not epoch seconds or ISO 8601", evidence)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return ResetResult(
            None, "no UTC offset: pass epoch seconds or ISO 8601 with Z or an offset", evidence
        )
    return _result(parsed.timestamp(), now, evidence)

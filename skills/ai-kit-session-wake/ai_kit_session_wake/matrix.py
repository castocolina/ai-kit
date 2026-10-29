"""Evidence-labelled wake primitives and the Phase 27 JSON contract."""

import json
from typing import Any

MATRIX_SCHEMA_VERSION = 1


# pylint: disable=too-many-arguments,too-many-positional-arguments


def _row(
    host: str,
    primitive: str,
    kind: str,
    surface: str,
    stall: bool,
    death: bool,
    reboot: bool,
    source: str,
    unverified: tuple[str, ...],
    evidence: str,
    version: str | None,
) -> dict[str, Any]:
    return {
        "host": host,
        "primitive": primitive,
        "kind": kind,
        "surface": surface,
        "survives_stall": stall,
        "survives_process_death": death,
        "survives_reboot": reboot,
        "source": source,
        "evidence": evidence,
        "unverified": unverified,
        "version_floor": version,
    }


MATRIX = (
    _row(
        "claude",
        "systemd user timer",
        "os-timer",
        "cli",
        True,
        True,
        True,
        "verified",
        ("reboot", "first fire after enable"),
        "spike 001: claude -p --resume <id> from a systemd user timer re-enters the session "
        "(claude 2.1.310); reboot survival of the enabled unit is unverified",
        "2.1.310",
    ),
    _row(
        "claude",
        "CronCreate one-shot",
        "schedule",
        "tool",
        True,
        False,
        False,
        "verified",
        (),
        "spike 004: a fire scheduled after the reset does work; a fire inside a limit is lost "
        "(claude 2.1.299)",
        "2.1.299",
    ),
    _row(
        "claude",
        "CronCreate recurring",
        "schedule",
        "tool",
        True,
        False,
        False,
        "verified",
        (),
        "spike 004: fires inside a limit are lost; recurring jobs expire after 7 days "
        "(claude 2.1.299)",
        "2.1.299",
    ),
    _row(
        "claude",
        "/goal",
        "goal",
        "slash-command",
        False,
        False,
        False,
        "verified",
        (),
        "spike 004: pauses at a usage limit and needs a message after the reset (claude 2.1.299)",
        "2.1.299",
    ),
    _row(
        "claude",
        "ScheduleWakeup",
        "wake",
        "tool",
        False,
        False,
        False,
        "unverified",
        ("stall",),
        "docs via the source todo: 1 min to 1 h, not restored on resume; never measured",
        None,
    ),
    _row(
        "claude",
        "/loop",
        "loop",
        "slash-command",
        False,
        False,
        False,
        "unverified",
        ("stall",),
        "docs via the source todo: session-scoped; never measured",
        None,
    ),
    _row(
        "claude",
        "cloud routine",
        "schedule",
        "slash-command",
        False,
        False,
        False,
        "unverified",
        (),
        "inference from the docs: runs in the cloud and cannot re-enter a local session",
        None,
    ),
    _row(
        "pi",
        "systemd user timer",
        "os-timer",
        "cli",
        True,
        True,
        True,
        "verified",
        ("reboot",),
        "spike 003: pi -p --session-id <id> from a systemd user timer re-enters the session "
        "(pi 1.3.0)",
        "1.3.0",
    ),
    _row(
        "opencode",
        "systemd user timer",
        "os-timer",
        "cli",
        True,
        True,
        True,
        "verified",
        ("reboot",),
        "spike 003: opencode run --session <id> from a systemd user timer re-enters the session "
        "(opencode 2.0.31)",
        "2.0.31",
    ),
    _row(
        "codex",
        "systemd user timer",
        "os-timer",
        "cli",
        True,
        True,
        True,
        "unverified",
        ("re-entry", "reboot"),
        "codex exec resume <id> seen in --help only (codex-cli 0.162.1); re-entry from a timer "
        "never measured",
        "0.162.1",
    ),
)


def rank(row: dict[str, Any]) -> int:
    if row["survives_reboot"]:
        return 3
    if row["survives_process_death"]:
        return 2
    if row["survives_stall"]:
        return 1
    return 0


def rows_for(host: str) -> list[dict[str, Any]]:
    return sorted((row for row in MATRIX if row["host"] == host), key=rank, reverse=True)


def best_primitive(host: str, systemd_ok: bool) -> dict[str, Any] | None:
    for row in rows_for(host):
        if rank(row) and (systemd_ok or row["kind"] != "os-timer"):
            return row
    return None


def _ranked(row: dict[str, Any]) -> dict[str, Any]:
    return {**row, "rank": rank(row)}


def matrix_json() -> str:
    hosts = ("claude", "codex", "pi", "opencode")
    rows = [_ranked(row) for host in hosts for row in rows_for(host)]
    return json.dumps(
        {"schema_version": MATRIX_SCHEMA_VERSION, "rows": rows}, separators=(",", ":")
    )


def render_matrix() -> str:
    lines = []
    for row in MATRIX:
        flags = "/".join(
            "yes" if row[key] else "no"
            for key in ("survives_stall", "survives_process_death", "survives_reboot")
        )
        extra = f"; unverified: {', '.join(row['unverified'])}" if row["unverified"] else ""
        lines.append(
            f"{row['host']}: {row['primitive']} [{flags}] {row['source']}{extra} — "
            f"{row['evidence']}"
        )
    return "\n".join(lines)

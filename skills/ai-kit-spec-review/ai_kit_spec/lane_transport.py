"""Per-lane transport choice: a fresh subprocess, a resumed session or a herdr pane, offered only
when its label reads verified for the installed host version; one record per plan. A round's
transport is chosen under the record's exclusive lock and counted back under the same lock.

Limits: the installed version comes from the runtimes snapshot (`clis.<id>.listed_from.version`),
which only some hosts carry (claude and copilot read unverified) and which can lag a binary
upgrade until the snapshot is refreshed; a recorded session is reused only by the same runtime,
model and mode."""
import contextlib
import fcntl
import json
import os
import re
import shutil
import sys
from typing import NamedTuple

from ai_kit_spec import herdr_pane, herdr_source, lane_settings, runner_dispatch, runner_facts
from ai_kit_spec.cache import cache_read_json, cache_write_json
from ai_kit_spec.detection import cache_runtimes_path
from ai_kit_spec.runner_dispatch import OS_SANDBOXED_EXEC

TRANSPORTS = ("subprocess", "resume", "pane")
TRANSPORT_RENEW_ROUNDS = 3
RECORD_VERSION = 1
# the caller closes the entry's pane and opens a new one before the round
PANE_RENEWED = "pane renewed"
# flipped only by a recorded live run; until then no pane is chosen
PANE_LABEL = {"state": "unverified", "source": "interactive pane: no live run recorded"}
_VERSION_RE = re.compile(r"\d+(?:\.\d+)+")


class TransportRequest(NamedTuple):
    lane_id: str
    runtime: str
    interactive: bool
    verified: frozenset
    herdr_ok: bool
    # "review" for a review lane, "sandbox" for a sandboxed execute call, else "execute";
    # the two fields come last with defaults so positional callers keep working.
    model: str = ""
    mode: str = "execute"


class TransportChoice(NamedTuple):
    transport: str
    session_id: str | None
    reason: str


def _dig(value, *keys):
    """Walk nested dicts, returning None as soon as a level is not a dict."""
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _version_token(text) -> str | None:
    """The first dotted version token of a string, else None."""
    if not isinstance(text, str):
        return None
    match = _VERSION_RE.search(text)
    return match.group(0) if match else None


def verified_transports(describe: dict | None, snapshot: dict | None,
                        runtime: str, mode: str = "execute") -> frozenset:
    """resume when the runner's session label is verified for the installed version and the
    call's mode allows it; pane when PANE_LABEL is verified."""
    label = _dig(describe, "runtimes", runtime, "session", "label")
    no_resume = _dig(describe, "runtimes", runtime, "session", "noResume")
    installed = _version_token(_dig(snapshot, "clis", runtime, "listed_from", "version"))
    transports = set()
    # Only the session label above counts; the runner's session.noResume lists the modes it
    # ignores a session id in (for codex ["review", "sandbox"]).
    if isinstance(label, dict) and label.get("state") == "verified" and installed is not None \
            and _version_token(label.get("source")) == installed \
            and not (isinstance(no_resume, list) and mode in no_resume):
        transports.add("resume")
    if PANE_LABEL.get("state") == "verified":
        transports.add("pane")
    return frozenset(transports)


def choose_transport(request: TransportRequest, entry: dict | None) -> TransportChoice:
    """Pane only for an interactive lane with a verified pane and herdr present; else a verified
    resume under the renewal count; else a fresh subprocess."""
    session = entry.get("session_id") if isinstance(entry, dict) else None
    rounds = entry.get("rounds") if isinstance(entry, dict) else 0
    if not isinstance(session, str) or not session:
        session = None
    if not isinstance(rounds, int) or isinstance(rounds, bool) or rounds < 0:
        # an invalid entry reads as no recorded session
        session = None
        rounds = 0
    # None never equals a bound field, so an unbound pair is rejected below
    bound = isinstance(entry, dict) and entry.get("runtime") == request.runtime \
        and entry.get("model") == request.model and entry.get("mode") == request.mode
    if request.interactive and "pane" in request.verified and request.herdr_ok:
        renewed = isinstance(entry, dict) and entry.get("transport") == "pane" \
            and (not bound or rounds >= TRANSPORT_RENEW_ROUNDS)
        return TransportChoice(
            "pane", None, PANE_RENEWED if renewed else "interactive lane with a verified pane")
    if "resume" not in request.verified:
        return TransportChoice("subprocess", None, "no verified resume")
    if entry is not None and not bound:
        return TransportChoice("subprocess", None, "lane pair or mode changed")
    if session is None:
        return TransportChoice("subprocess", None, "no recorded session")
    if rounds >= TRANSPORT_RENEW_ROUNDS:
        return TransportChoice("subprocess", None, f"renewed after {TRANSPORT_RENEW_ROUNDS} rounds")
    return TransportChoice(
        "resume", session, f"verified resume, round {rounds + 1} of {TRANSPORT_RENEW_ROUNDS}")


def record_round(record: dict, lane_id: str, choice: TransportChoice,
                session_id: str | None, request: TransportRequest) -> dict:
    """A new record with the round counted: a fresh subprocess round, a renewed pane or a first
    pane round starts the count at 1, a resume or reused pane round adds one; the pane field is
    kept; the entry stores the request's runtime, model and mode."""
    lanes_field = record.get("lanes") if isinstance(record, dict) else None
    lanes = dict(lanes_field) if isinstance(lanes_field, dict) else {}
    old = lanes.get(lane_id)
    if not isinstance(old, dict):
        old = {}
    old_rounds = old.get("rounds")
    if not isinstance(old_rounds, int) or isinstance(old_rounds, bool):
        old_rounds = 0
    if choice.transport == "subprocess" or choice.reason == PANE_RENEWED \
            or (choice.transport == "pane" and old.get("transport") != "pane"):
        rounds = 1
    else:
        rounds = old_rounds + 1
    session = session_id if session_id is not None else (
        choice.session_id if choice.transport == "resume" else None)
    lanes[lane_id] = {"transport": choice.transport, "session_id": session, "rounds": rounds,
                      "pane": old.get("pane"), "runtime": request.runtime,
                      "model": request.model, "mode": request.mode}
    return {"version": RECORD_VERSION, "lanes": lanes}


def read_record(path: str) -> dict:
    """The plan's record; a missing, unreadable or foreign file reads as an empty record."""
    data = cache_read_json(path)
    lanes = data.get("lanes") if isinstance(data, dict) else None
    if isinstance(data, dict) and data.get("version") == RECORD_VERSION \
            and isinstance(lanes, dict):
        return data
    return {"version": RECORD_VERSION, "lanes": {}}


def write_record(path: str, record: dict) -> None:
    """Persist the plan's record (the cache helpers write atomically and create the folder)."""
    cache_write_json(path, record)


def call_mode(role: str, runtime: str) -> str:
    """The call's mode: a review lane reviews, an OS-sandboxed exec runtime runs sandboxed,
    everything else executes."""
    if role == "review":
        return "review"
    if runtime in OS_SANDBOXED_EXEC:
        return "sandbox"
    return "execute"


def lane_request(role: str, index: int, entry: dict, env: dict,
                 which_fn=shutil.which) -> TransportRequest:
    """The lane's transport request: its id and pair, the transports verified for the installed
    host version, and herdr's presence. The owner's per-lane marker is read through
    lane_settings; a non-boolean one prints one note and reads as not interactive."""
    lane_id = f"{role}:{index}:{entry.get('key', '')}"
    runtime = entry.get("runtime") or ""
    mode = call_mode(role, runtime)
    fact = runner_facts.stored_fact(env)
    describe = fact.get("describe") if isinstance(fact, dict) else None
    snapshot = cache_read_json(cache_runtimes_path(env))
    verified = verified_transports(describe, snapshot if isinstance(snapshot, dict) else None,
                                   runtime, mode)
    herdr_ok = herdr_source.herdr_available(env, which_fn)[0] is not None
    try:
        interactive = lane_settings.lane_interactive(entry)
    except lane_settings.LaneSettingError as exc:
        # the marker only steers the transport, so a bad value runs the lane as not interactive
        print(f"ai-kit-spec: {exc}; read as not interactive", file=sys.stderr)
        interactive = False
    return TransportRequest(lane_id=lane_id, runtime=runtime, interactive=interactive,
                            verified=verified, herdr_ok=herdr_ok,
                            model=entry.get("model") or "", mode=mode)


def _foreign_record(value) -> bool:
    """True unless value is a version-1 record whose lanes field is a dict."""
    lanes = value.get("lanes") if isinstance(value, dict) else None
    return not isinstance(value, dict) or value.get("version") != RECORD_VERSION \
        or not isinstance(lanes, dict)


def _under_record_lock(record_path: str, body):
    """Run body on the lock file's handle (the catalog's lock shape). The lock file stays."""
    os.makedirs(os.path.dirname(os.path.abspath(record_path)), exist_ok=True)
    with open(record_path + ".lock", "a", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            return body()
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _load_raw_record(record_path: str) -> dict:
    """The raw record. OSError propagates; a foreign file raises ValueError and is not written."""
    with open(record_path, encoding="utf-8") as handle:
        try:
            loaded = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError(record_path) from exc
    if _foreign_record(loaded):
        raise ValueError(record_path)
    return loaded


def _read_locked_record(record_path: str) -> dict:
    """The record read under the lock: a missing file is an empty record; a file that is not a
    record raises ValueError and is never written."""
    if not os.path.lexists(record_path):
        return {"version": RECORD_VERSION, "lanes": {}}
    return _load_raw_record(record_path)


def _locked_update(record_path: str, update) -> dict | None:
    """Read-modify-write of the record under the record lock: the update returns the new record,
    the record it was given to leave the file as it is, or None to remove the file. A file that
    is not a record raises ValueError before any write."""
    def body() -> dict | None:
        current = _read_locked_record(record_path)
        new = update(current)
        if new is None:
            # a missing record file reads as empty, so removing an absent one is fine
            with contextlib.suppress(FileNotFoundError):
                os.remove(record_path)
        elif new is not current:
            write_record(record_path, new)
        return new

    return _under_record_lock(record_path, body)


class RoundStart(NamedTuple):
    record_path: str
    request: TransportRequest
    # the caller's pid; a busy mark another pid holds is never cleared
    pid: int = 0


def begin_round(start: RoundStart) -> TransportChoice:
    """The lane's transport for this round: chosen under the record's lock and printed to stderr
    as exactly one line; nothing is written."""
    picked: list[TransportChoice] = []

    def update(record: dict) -> dict:
        entry = record["lanes"].get(start.request.lane_id)
        choice = choose_transport(start.request, entry)
        print(f"ai-kit-spec: transport {start.request.lane_id}: {choice.transport} "
              f"({choice.reason})", file=sys.stderr)
        picked.append(choice)
        return record

    _locked_update(start.record_path, update)
    return picked[0]


# record paths already reported unusable in this process: a CLI call is one round, one line
_REPORTED_UNUSABLE: set[str] = set()


def _record_unusable(start: RoundStart, exc: Exception, outcome: str) -> None:
    """One stderr line for a record file that cannot be read or written as a record.

    Printed once per record path per process.
    """
    if start.record_path in _REPORTED_UNUSABLE:
        return
    _REPORTED_UNUSABLE.add(start.record_path)
    why = "not a transport record" if isinstance(exc, ValueError) else (
        getattr(exc, "strerror", None) or type(exc).__name__)
    print(f"ai-kit-spec: transport record {start.record_path} unusable: {why}; {outcome}",
          file=sys.stderr)


def try_begin_round(start: RoundStart) -> TransportChoice | None:
    """begin_round, or None after one stderr line when the record cannot be used; the caller
    then runs a plain subprocess round and writes no record."""
    try:
        return begin_round(start)
    except (ValueError, OSError) as exc:
        _record_unusable(start, exc, "the round runs as a fresh subprocess")
        return None


def end_round(start: RoundStart, choice: TransportChoice, status: dict | None) -> None:
    """Count the round into the record under the record's lock with the status session; a pane
    the caller does not hold is recorded as a subprocess round, the caller's own busy mark is
    cleared, an entry another live pid holds is left as it is, and a dead pid's mark is kept."""
    token = (status or {}).get("session")
    session = None if token in (None, "", "-") else token

    def update(record: dict) -> dict:
        old = record["lanes"].get(start.request.lane_id)
        if not isinstance(old, dict):
            old = {}
        busy = _positive_pid(old.get("busy_pid"))
        if busy is not None and busy != start.pid and herdr_pane.pid_alive(busy):
            # another live round holds the lane: its entry is left as it is
            return record
        held = old.get("busy_pid") == start.pid
        recorded = choice if choice.transport != "pane" or held \
            else choice._replace(transport="subprocess", session_id=None)
        new = record_round(record, start.request.lane_id, recorded, session, start.request)
        new["lanes"][start.request.lane_id]["busy_pid"] = (
            None if held else old.get("busy_pid"))
        return new

    _locked_update(start.record_path, update)


def try_end_round(start: RoundStart, choice: TransportChoice, status: dict | None) -> None:
    """end_round, or one stderr line when the record cannot be used: the round is not counted
    and the file is left as it is."""
    try:
        end_round(start, choice, status)
    except (ValueError, OSError) as exc:
        _record_unusable(start, exc, "the round is not counted")


def _lane_entry(record: dict, lane_id: str) -> dict | None:
    """The lane's entry when it is a dict, else None."""
    entry = record["lanes"].get(lane_id)
    return entry if isinstance(entry, dict) else None


def _positive_pid(value) -> int | None:
    """A positive int pid, or None for a bool, a non-int or a non-positive value."""
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return None


def _claim_pane(start: RoundStart) -> dict | None:
    """Mark the lane busy with this pid and return the entry as written under the lock. None
    when another live pid already holds it: the entry is left unchanged and this round falls
    back to a subprocess."""
    claimed: list[dict | None] = []

    def update(record: dict) -> dict:
        entry = _lane_entry(record, start.request.lane_id)
        busy = _positive_pid(entry.get("busy_pid") if entry else None)
        if busy is not None and busy != start.pid and herdr_pane.pid_alive(busy):
            claimed.append(None)
            return record
        lanes = dict(record["lanes"])
        lanes[start.request.lane_id] = {**(entry or {}), "busy_pid": start.pid}
        claimed.append(lanes[start.request.lane_id])
        return {**record, "lanes": lanes}

    _locked_update(start.record_path, update)
    return claimed[0]


def _pane_needs_renewal(start: RoundStart, entry: dict) -> bool:
    """True when the recorded pane must be closed before this round: it is marked closed, the
    chooser says the pane is renewed, or the entry is not a pane entry, or its launcher is no
    longer alive."""
    pane = entry.get("pane")
    if not isinstance(pane, dict):
        return False
    renewed = choose_transport(start.request, entry).reason == PANE_RENEWED
    return bool(pane.get("closed")) or renewed or entry.get("transport") != "pane" \
        or herdr_pane.live_launcher_pid(pane) is None


def _run_dir_gone(pane: dict) -> bool:
    """True when the pane names a run dir that no longer exists: nothing is left to close, the
    runner's sweep owns the tab."""
    run_dir = pane.get("run_dir")
    return isinstance(run_dir, str) and bool(run_dir) and not os.path.lexists(run_dir)


def _close_for_renewal(start: RoundStart, entry: dict | None) -> dict | None:
    """The entry's pane after a renewal close, or the pane as it stands. A failed close prints
    one stderr line and the pane is still treated as absent."""
    pane = entry.get("pane") if isinstance(entry, dict) else None
    if not isinstance(entry, dict) or not isinstance(pane, dict) \
            or not _pane_needs_renewal(start, entry):
        return pane if isinstance(pane, dict) else None
    if not herdr_pane.close_pane(pane) and not _run_dir_gone(pane):
        print(f"ai-kit-spec: pane: renewal close failed for {start.request.lane_id}",
              file=sys.stderr)
    return None


def _store_pane(start: RoundStart, pane: dict) -> None:
    """Record the freshly opened pane with its round count at 0, keeping the busy mark."""
    def update(record: dict) -> dict:
        entry = _lane_entry(record, start.request.lane_id) or {}
        lanes = dict(record["lanes"])
        lanes[start.request.lane_id] = {**entry, "pane": pane, "rounds": 0}
        return {**record, "lanes": lanes}

    _locked_update(start.record_path, update)


def _clear_busy(start: RoundStart) -> None:
    """Drop this round's busy mark and the entry's pane: no pane opened (an old one was closed
    for renewal), so the fallback runs the round."""
    def update(record: dict) -> dict:
        entry = _lane_entry(record, start.request.lane_id)
        if entry is None:
            return record
        lanes = dict(record["lanes"])
        lanes[start.request.lane_id] = {**entry, "busy_pid": None, "pane": None}
        return {**record, "lanes": lanes}

    _locked_update(start.record_path, update)


def _close_one_pane(lane_id: str, entry: dict, close_fn, outcome: dict) -> dict:
    """Close one lane's pane. A live busy pid is left alone; a pane whose run dir is gone counts
    as closed; a failed close keeps the entry."""
    pane = entry.get("pane")
    if not isinstance(pane, dict):
        return entry
    busy = _positive_pid(entry.get("busy_pid"))
    if busy is not None and herdr_pane.pid_alive(busy):
        outcome["busy"].append(lane_id)
        return entry
    try:
        closed = close_fn(pane) is True
    except OSError:
        closed = False
    if closed or _run_dir_gone(pane):
        outcome["closed"].append(lane_id)
        return {**entry, "pane": None}
    outcome["failed"].append(lane_id)
    return entry


def _close_panes(record: dict, close_fn) -> tuple[dict, dict]:
    """Close every recorded pane, returning the updated record and the three lists."""
    outcome = {"closed": [], "failed": [], "busy": []}
    lanes = {}
    for lane_id, entry in record["lanes"].items():
        lanes[lane_id] = _close_one_pane(lane_id, entry, close_fn, outcome) \
            if isinstance(entry, dict) else entry
    return {**record, "lanes": lanes}, outcome


def _sweep_text(sweep_fn) -> str:
    """One sweep, after the lock is released. A failure is text, never an exception."""
    try:
        result = sweep_fn()
    except OSError as exc:
        return f"unavailable: {exc}"
    if result.returncode != 0:
        return f"unavailable: {result.reason}"
    counts = [line for line in result.stderr_tail.splitlines()
              if line.startswith("cross-ai: sweep: closed")]
    return counts[-1] if counts else "ran"


def _close_under_lock(record_path: str, close_fn) -> dict:
    """Close the panes and persist the record. A clean close removes the file, not the lock."""
    def body() -> dict:
        updated, outcome = _close_panes(_load_raw_record(record_path), close_fn)
        if outcome["failed"] or outcome["busy"]:
            write_record(record_path, updated)
        else:
            os.remove(record_path)
        return outcome

    return _under_record_lock(record_path, body)


def close_record(record_path: str, close_fn, sweep_fn) -> dict:
    """Close the plan's recorded panes under the record lock, then sweep once outside it."""
    if not os.path.lexists(record_path):
        return {"closed": [], "failed": [], "busy": [],
                "sweep": "skipped: no transport record"}
    outcome = _close_under_lock(record_path, close_fn)
    outcome["sweep"] = _sweep_text(sweep_fn)
    return outcome


def _drop_closed_pane(start: RoundStart, pane: dict) -> None:
    """Forget a pane the round closed, so the next round opens a new one."""
    if not pane.get("closed"):
        return

    def update(record: dict) -> dict:
        entry = _lane_entry(record, start.request.lane_id)
        if entry is None:
            return record
        lanes = dict(record["lanes"])
        lanes[start.request.lane_id] = {**entry, "pane": None}
        return {**record, "lanes": lanes}

    _locked_update(start.record_path, update)


def _prepare_pane(start: RoundStart, entry: dict, spec, cwd: str, role: str):
    """The pane this round runs in, or None when the round falls back to a subprocess."""
    pane = _close_for_renewal(start, entry)
    if pane is not None:
        return pane
    opened = herdr_pane.open_pane(role, spec.runtime, cwd)
    if opened is None:
        _clear_busy(start)
        return None
    try:
        _store_pane(start, opened)
    except (ValueError, OSError):
        # an opened pane the record cannot hold is closed before the fallback runs
        herdr_pane.close_pane(opened)
        raise
    return opened


def pane_runner(start: RoundStart, cwd: str, role: str, fallback):
    """A runner-tiers callable that runs the round in the lane's reused pane. A busy pane, or a
    pane that will not open, runs through fallback instead; the runner builds the argv, the env
    and the result. A fallback prints one `transport <lane>: subprocess (pane fallback: <why>)`
    line."""
    def run(spec, tiers, prompt, seams=None):
        active = seams or runner_dispatch.RunnerSeams()
        try:
            entry = _claim_pane(start)
            pane = None if entry is None else _prepare_pane(start, entry, spec, cwd, role)
        except (ValueError, OSError) as exc:
            _record_unusable(start, exc, "the round runs as a fresh subprocess")
            return fallback(spec, tiers, prompt, seams)
        if pane is None:
            why = "pane busy" if entry is None else "pane did not open"
            print(f"ai-kit-spec: transport {start.request.lane_id}: subprocess "
                  f"(pane fallback: {why})", file=sys.stderr)
            return fallback(spec, tiers, prompt, seams)
        widest = spec._replace(host="none", timeout_s=max(tiers), cwd=cwd)
        result = runner_dispatch.run_runner(
            widest, prompt, active._replace(spawn_fn=herdr_pane.pane_spawn(pane)))
        try:
            _drop_closed_pane(start, pane)
        except (ValueError, OSError) as exc:
            _record_unusable(start, exc, "the record is left as it is")
        return result

    return run

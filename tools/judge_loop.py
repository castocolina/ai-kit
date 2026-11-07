#!/usr/bin/env python3
"""Skill-judge loop: build judge prompts, record lane verdicts, check the records.

Usage (from a git checkout, or pass --root):
  judge_loop.py prompt --loop L --round N --judge J --skill S [--skill S ...] --out DIR
                [--judge-package DIR]
  judge_loop.py ingest --lane-dir DIR --records DIR
  judge_loop.py check RECORDS [--skills S ...] [--judges J ...] [--gate] [--require-current]
  judge_loop.py pool --loop L --native ID --probe-dir DIR --records DIR [--judges J ...]
  judge_loop.py count --loop L --records DIR [--skill S ...] [--no-jev] [--client PATH]
Exit codes: 0 ok, 1 an invalid, missing or mis-pinned verdict or a refused ingest, 2 usage.
Stdlib only; the staged-test mapper is loaded beside this file by path.
"""

import argparse
import contextlib
import hashlib
import importlib.util
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, NamedTuple

PREFIX = "judge-loop:"
DIMS = tuple(f"D{i}" for i in range(1, 9))
VERDICT_KEYS = frozenset({"skill", "judge", "rubric_version", "spec_sha", "scores", "max",
                          "total", "max_total", "percent", "grade", "findings"})
FINDING_KEYS = frozenset({"id", "dimension", "severity", "file", "line", "evidence", "fix"})
SEVERITIES = frozenset({"critical", "high", "medium", "low"})
STATUS_PREFIX = "AIKIT-XAI "
CODE_SUFFIXES = (".py", ".mjs", ".cjs", ".js", ".sh")
NON_PACKAGE_DIRS = frozenset({"scripts", "references", "evals"})
NO_TEST_LINE = "no script test found"
SAFE_SKILL = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
LOOP_RE = re.compile(r"\d+(?:\.\d+)*")
ROUND_DIR_RE = re.compile(r"r\d+")
SHA40 = re.compile(r"[0-9a-f]{40}")
JEV_ENTRY_REL = os.path.join("jev-fast-decision", "scripts", "jev_review.py")
JUDGE_SKILL = "skill-judge"
# Installed-skill lookup copy (29 D-13); tests/test_arch.py compares it with jev's reference.md.
SKILLS_ROOTS = (
    ("CLAUDE_CONFIG_DIR", ".claude", "skills"),
    (None, ".agents", "skills"),
    ("XDG_CONFIG_HOME", ".config", "opencode/skills"),
    ("CURSOR_CONFIG_DIR", ".cursor", "skills"),
    ("PI_CODING_AGENT_DIR", ".pi/agent", "skills"),
)


class JudgeLoopError(Exception):
    """A refusal or a bad input; main prints it and returns 1."""


class PromptRequest(NamedTuple):
    loop: str
    number: int
    judge: str
    skill: str
    out: Path


class CheckOptions(NamedTuple):
    skills: tuple[str, ...] = ()
    judges: tuple[str, ...] = ()
    gate: bool = False
    require_current: bool = False


# ─── roots and the installed skill-judge ──────────────────────────────────────

def find_root(override, cwd=None):
    """The repository root: `override` when given, else git's toplevel of `cwd`."""
    if override is not None:
        return Path(override).resolve()
    try:
        proc = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd,
                              capture_output=True, text=True, check=False)
    except OSError as exc:
        raise JudgeLoopError(f"cannot run git: {exc}") from exc
    if proc.returncode != 0:
        raise JudgeLoopError("not inside a git repository; pass --root")
    return Path(proc.stdout.strip()).resolve()


def skills_roots(env, own_root):
    """Skills dirs to search, in lookup order: `own_root` first, then the SKILLS_ROOTS rows."""
    home = env.get("HOME", "~")
    roots = [own_root] if own_root else []
    for variable, fallback, suffix in SKILLS_ROOTS:
        base = (env.get(variable, "").strip() if variable else "") or os.path.join(home, fallback)
        roots.append(os.path.join(base, suffix))
    return [os.path.expanduser(root) for root in roots]


def find_judge_package(root, env, override):
    """The skill-judge package: `override` when given, else the first installed copy found."""
    if override is not None:
        return Path(override).resolve()
    for base in skills_roots(env, str(root / "skills")):
        candidate = Path(base) / JUDGE_SKILL
        if (candidate / "references" / "rubric.md").is_file():
            return candidate
    raise JudgeLoopError("no installed skill-judge found; pass --judge-package")


def read_pin(package):
    """(rubric_version, spec_sha) from the first two lines of references/rubric.md."""
    lines = (Path(package) / "references" / "rubric.md").read_text(encoding="utf-8").splitlines()
    version = re.fullmatch(r"rubric_version: (\d+)", lines[0]) if lines else None
    sha = re.fullmatch(r"spec_sha: ([0-9a-f]{40})", lines[1]) if len(lines) > 1 else None
    if version is None or sha is None:
        raise JudgeLoopError("rubric has no rubric_version/spec_sha pin lines")
    return int(version.group(1)), sha.group(1)


def embedded_files(package):
    """SKILL.md, the rubric, the spec files its source column cites, then the verdict schema."""
    package = Path(package)
    rubric = (package / "references" / "rubric.md").read_text(encoding="utf-8")
    sources = []
    for line in rubric.splitlines():
        if re.match(r"\| D\d+ \|", line):
            for part in line.split("|")[4].split(";"):
                rel = part.strip().split("#", 1)[0]
                if rel and rel not in sources:
                    sources.append(rel)
    files = ["SKILL.md", "references/rubric.md", *sources, "references/verdict.schema.json"]
    for rel in files:
        if not (package / rel).is_file():
            raise JudgeLoopError(f"embedded file missing from the skill-judge package: {rel}")
    return files


# ─── the skill under judgment ─────────────────────────────────────────────────

def skill_files(root, name):
    """The git-tracked files under skills/<name>/, sorted, as root-relative POSIX paths."""
    if not SAFE_SKILL.fullmatch(name):
        raise JudgeLoopError(f"bad skill name {name!r}")
    proc = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--", f"skills/{name}/"],
                          capture_output=True, check=False)
    files = sorted(os.fsdecode(raw) for raw in proc.stdout.split(b"\0") if raw)
    if not files:
        raise JudgeLoopError(f"no tracked files for skill {name}")
    return files


def skill_digest(root, name):
    """sha256 over `<sha256 of file bytes>  <path>\\n` of each tracked file of the skill."""
    lines = "".join(hashlib.sha256((Path(root) / rel).read_bytes()).hexdigest() + "  " + rel + "\n"
                    for rel in skill_files(root, name))
    return hashlib.sha256(lines.encode("utf-8")).hexdigest()


def ships_code(root, name):
    """True when the skill has runnable code at its root or under scripts/, or a package folder."""
    prefix = f"skills/{name}/"
    for part in (rel[len(prefix):] for rel in skill_files(root, name)):
        pieces = part.split("/")
        if part.endswith(CODE_SUFFIXES) and (len(pieces) == 1 or pieces[0] == "scripts"):
            return True
        if len(pieces) == 2 and pieces[1] == "__init__.py" and pieces[0] not in NON_PACKAGE_DIRS:
            return True
    return False


def _load_mapper():
    """tools/staged_mapper.py, loaded beside this file by path (never from the repo root)."""
    path = Path(__file__).resolve().with_name("staged_mapper.py")
    spec = importlib.util.spec_from_file_location("staged_mapper", path)
    if spec is None or spec.loader is None:
        raise JudgeLoopError(f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def module_list(root, name):
    """The test modules the commit hook runs when the skill changes, as sorted tests/<stem>.py."""
    mapper = _load_mapper()
    try:
        found = mapper.covering_modules(mapper.build_index(Path(root)),
                                        f"skills/{name}/SKILL.md")
    except mapper.MapperError as exc:
        raise JudgeLoopError(str(exc)) from exc
    return sorted("tests/" + module.removeprefix("tests.") + ".py" for module in found)


# ─── the prompt ───────────────────────────────────────────────────────────────

def judge_slug(judge):
    """A file-name-safe form of a judge id (`cli-a:model-a` becomes `cli-a_model-a`)."""
    slug = re.sub(r"[^A-Za-z0-9._-]", "_", judge or "")
    if not re.search(r"[A-Za-z0-9]", slug):
        raise JudgeLoopError(f"bad judge id {judge!r}")
    return slug


def text_sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _rule_1():
    return ("1. The skill-judge package is embedded below, byte for byte: its SKILL.md, "
            "references/rubric.md, every spec file the rubric's source column cites, and "
            "references/verdict.schema.json. These copies replace every step that says to read "
            "a file under references/; do not open those files.")


def _rule_2(skill):
    return (f"2. The skill to judge is the directory skills/{skill}/ under the repository root. "
            "Read its SKILL.md and any other file in that directory the rubric needs, with "
            "read-only tools only; never modify a file.")


def _rule_3():
    return ("3. Script tests live flat in tests/test_*.py, not in tests/skills/<name>/. This "
            "reading replaces every mention of tests/skills/<name>/ in the embedded files.")


def _rule_5():
    return ("5. A skill ships runnable code when it has a tracked .py, .mjs, .cjs, .js or .sh "
            "file at its root or under scripts/, or a top-level folder holding __init__.py; .txt "
            "templates and references/ do not count. Score D7 of a skill that ships runnable code "
            "with the 5/5/5 split (output evals, trigger queries, a script test), the script-test "
            "part on the modules in rule 4. Score D7 of a skill with no runnable code with the "
            "8/7 split; the modules in rule 4 are then context only and not scored.")


def _rule_6():
    return ("6. Attribution is required content: lines that credit an original author, an "
            "upstream source, an inspiration or a license never count against any dimension, "
            "and no finding may propose removing or shortening them.")


def _rule_7(judge, skill):
    return ("7. Output: print exactly one verdict JSON object on one line and nothing else (no "
            "Markdown, no code fence, no commentary). Set \"judge\" to "
            f"\"{judge}\" and \"skill\" to \"{skill}\". Set \"file\" in each finding to a path "
            "relative to the repository root.")


def _embed(rel, text, after_end=""):
    """One embedded block: the file text between its markers, then `after_end` and a blank line."""
    body = text if text.endswith("\n") else text + "\n"
    return (f"===== BEGIN EMBEDDED FILE skill-judge/{rel} sha256={text_sha(text)} =====\n"
            f"{body}===== END EMBEDDED FILE skill-judge/{rel} =====\n{after_end}\n")


def _read_blocks(package):
    """(rel, text) for every embedded file, each decoded from its exact bytes."""
    return [(rel, (Path(package) / rel).read_bytes().decode("utf-8"))
            for rel in embedded_files(package)]


def build_probe(judge, codes, blocks):
    """The probe prompt: one `PROBE PART <n>: <code>` line after each embedded file. Pure."""
    head = (
        f"You are judge `{judge}`. This is a probe, not a judging run.\n"
        "The skill-judge package is embedded below. Do not judge anything and do not open any "
        "file.\n"
        "Right after each END EMBEDDED FILE marker there is one line PROBE PART <n>: <code>. "
        "Reply with exactly one word: AIKIT-SENTINEL, then a hyphen and each code in order "
        "(AIKIT-SENTINEL-<code 1>-<code 2>-...). Print nothing else.\n\n"
    )
    parts = [head]
    for number, ((rel, text), code) in enumerate(zip(blocks, codes, strict=True), start=1):
        parts.append(_embed(rel, text, f"PROBE PART {number}: {code}\n"))
    parts.append("Reply now with only that word.\n")
    return "".join(parts)


def write_probe(package, judge, out):
    """Write the probe prompt and its one-word expected answer; returns the lane folder."""
    blocks = _read_blocks(package)
    codes = [secrets.token_hex(4) for _ in blocks]
    lane = Path(out) / judge_slug(judge)
    lane.mkdir(parents=True, exist_ok=True)
    (lane / "prompt.md").write_bytes(build_probe(judge, codes, blocks).encode("utf-8"))
    (lane / "token").write_text("AIKIT-SENTINEL-" + "-".join(codes) + "\n", encoding="utf-8")
    return lane


def build_prompt(judge, skill, modules, blocks):
    """The judge prompt: the rules, then each (rel, text) block byte for byte. Pure."""
    head = [
        f"You are judge `{judge}`. Judge this skill: {skill}",
        "",
        "Rules for this run. They replace the matching steps of the embedded skill-judge files:",
        _rule_1(),
        _rule_2(skill),
        _rule_3(),
        f"4. Script test modules for this skill: {', '.join(modules) or NO_TEST_LINE}",
        _rule_5(),
        _rule_6(),
        _rule_7(judge, skill),
        "",
    ]
    return "\n".join(head) + "\n" + "".join(_embed(rel, text) for rel, text in blocks)


def write_lane_prompt(root, package, request):
    """Write prompt.md and manifest.json for one judge and one skill; returns the lane folder."""
    skill_files(root, request.skill)  # validates the skill name before any path is built
    if not LOOP_RE.fullmatch(request.loop):
        raise JudgeLoopError(f"bad loop id {request.loop!r}")
    if request.number < 1:
        raise JudgeLoopError("round must be 1 or more")
    blocks = _read_blocks(package)
    modules = module_list(root, request.skill)
    prompt = build_prompt(request.judge, request.skill, modules, blocks)
    rubric_version, spec_sha = read_pin(package)
    manifest = {
        "schema": 1,
        "loop": request.loop,
        "skill": request.skill,
        "round": request.number,
        "judge": request.judge,
        "digest": skill_digest(root, request.skill),
        "rubric_version": rubric_version,
        "spec_sha": spec_sha,
        "embedded": [{"path": rel, "sha256": text_sha(text)} for rel, text in blocks],
        "modules": modules,
        "ships_code": ships_code(root, request.skill),
        "prompt_sha256": text_sha(prompt),
    }
    lane = (Path(request.out) / request.loop / request.skill / f"r{request.number}"
            / judge_slug(request.judge))
    lane.mkdir(parents=True, exist_ok=True)
    (lane / "prompt.md").write_bytes(prompt.encode("utf-8"))
    atomic_write_json(lane / "manifest.json", manifest)
    return lane


# ─── lane output and verdicts ─────────────────────────────────────────────────

def parse_status_line(line):
    """The `key=value` tokens of an `AIKIT-XAI ` line, or None for anything else."""
    if not line.startswith(STATUS_PREFIX):
        return None
    return dict(token.split("=", 1) for token in line.split() if "=" in token)


def last_status_line(text):
    """The last `AIKIT-XAI ` line of a lane's stderr, or None."""
    found = [line.rstrip() for line in text.splitlines() if line.startswith(STATUS_PREFIX)]
    return found[-1] if found else None


def lane_ok(fields):
    """True for a status line that reports a finished, clean review lane."""
    return bool(fields) and (fields.get("status") == "ok" and fields.get("exit") == "0"
                             and fields.get("tree") == "clean")


def verdict_lines(text):
    """The stripped lines of a lane's stdout that start a verdict object."""
    return [line.strip() for line in text.splitlines() if line.strip().startswith('{"skill"')]


def grade_of(pct):
    for floor, grade in ((90, "A"), (80, "B"), (70, "C"), (60, "D")):
        if pct >= floor:
            return grade
    return "F"


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _shape_error(v):
    for name in ("scores", "max"):
        d = v[name]
        if not isinstance(d, dict) or set(d) != set(DIMS) or not all(
                _is_int(x) and x >= 0 for x in d.values()):
            return name + " is not exactly D1..D8 integers"
    if not all(_is_int(v[key]) for key in ("total", "max_total", "rubric_version")):
        return "total, max_total and rubric_version must be integers"
    return None


def _arith_errors(v):
    errs = []
    scored, maxed = sum(v["scores"].values()), sum(v["max"].values())
    if scored != v["total"]:
        errs.append(f"sum(scores) {scored} != total {v['total']}")
    if maxed != v["max_total"]:
        errs.append(f"sum(max) {maxed} != max_total {v['max_total']}")
    if any(v["scores"][d] > v["max"][d] for d in DIMS):
        errs.append("a score exceeds its max")
    return errs


def _grade_errors(v):
    if not isinstance(v["percent"], (int, float)) or v["max_total"] <= 0:
        return ["percent or max_total unusable"]
    pct = round(v["total"] / v["max_total"] * 100, 1)
    errs = []
    if v["percent"] != pct:
        errs.append(f"percent {v['percent']} != {pct}")
    if v["grade"] != grade_of(pct):
        errs.append(f"grade {v['grade']} != {grade_of(pct)}")
    return errs


def _finding_ok(f):
    return (isinstance(f, dict) and set(f) == FINDING_KEYS
            and f["severity"] in SEVERITIES and f["dimension"] in DIMS
            and (f["line"] is None or (_is_int(f["line"]) and f["line"] >= 1))
            and all(isinstance(f[key], str) and f[key]
                    for key in ("id", "file", "evidence", "fix")))


def _finding_errors(v):
    findings = v["findings"]
    if not isinstance(findings, list):
        return ["findings is not a list"]
    if not all(_finding_ok(f) for f in findings):
        return ["a finding is malformed"]
    ids = [f["id"] for f in findings]
    errs = [f"duplicate finding id {i}" for i in sorted({i for i in ids if ids.count(i) > 1})]
    covered = {f["dimension"] for f in findings}
    errs += [f"{d} is below its max but has no finding" for d in DIMS
             if v["scores"][d] < v["max"][d] and d not in covered]
    return errs


def validate_verdict(v, pin):
    """Errors of one verdict object: its exact keys, arithmetic, grade, pin and findings."""
    if not isinstance(v, dict) or set(v) != VERDICT_KEYS:
        return ["keys are not exactly the schema's"]
    shape = _shape_error(v)
    if shape:
        return [shape]
    errs = []
    if not isinstance(v["spec_sha"], str) or not SHA40.fullmatch(v["spec_sha"]):
        errs.append("spec_sha is not 40 hex")
    if (v["rubric_version"], v["spec_sha"]) != tuple(pin):
        errs.append("rubric_version/spec_sha differ from the manifest")
    return errs + _arith_errors(v) + _grade_errors(v) + _finding_errors(v)


def atomic_write_json(path, data):
    """Write `data` as JSON through a temp file and os.replace; the temp file goes on failure."""
    path = Path(path)
    text = json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except OSError:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def record_path(records, loop, skill, number, judge):
    return Path(records) / "verdicts" / loop / skill / f"r{number}" / f"{judge_slug(judge)}.json"


def _text_or_empty(path):
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def finding_path_errors(verdict, root):
    """Each finding's file must sit under the root and exist; each line must be inside the file."""
    base = Path(root).resolve()
    errs = []
    for finding in verdict["findings"]:
        target = (base / finding["file"]).resolve()
        if not target.is_relative_to(base):
            errs.append(f"finding {finding['id']} file escapes the repository: {finding['file']}")
        elif not target.is_file():
            errs.append(f"finding {finding['id']} file does not exist: {finding['file']}")
        elif finding["line"] is not None:
            count = len(target.read_text(encoding="utf-8", errors="replace").splitlines())
            if finding["line"] > count:
                errs.append(f"finding {finding['id']} line {finding['line']} is beyond the "
                            f"file's {count} lines")
    return errs


def _refuse_mismatch(verdict, manifest):
    """Refusals that stop an ingest before anything is written: another judge, skill or pin."""
    if verdict.get("judge") != manifest["judge"]:
        raise JudgeLoopError(f"verdict judge {verdict.get('judge')!r} is not the lane's judge "
                             f"{manifest['judge']!r}")
    if verdict.get("skill") != manifest["skill"]:
        raise JudgeLoopError(f"verdict skill {verdict.get('skill')!r} is not the lane's skill "
                             f"{manifest['skill']!r}")
    pin = (verdict.get("rubric_version"), verdict.get("spec_sha"))
    if pin != (manifest["rubric_version"], manifest["spec_sha"]):
        raise JudgeLoopError("verdict rubric_version/spec_sha differ from the manifest pin")


def _read_verdict(lane, manifest, root):
    """(verdict line, verdict, error) of a usable lane; refusals raise before any write."""
    verdicts = verdict_lines(_text_or_empty(lane / "lane.out"))
    if len(verdicts) != 1:
        return None, None, ("no verdict line" if not verdicts else "more than one verdict line")
    try:
        verdict = json.loads(verdicts[0])
    except json.JSONDecodeError:
        return verdicts[0], None, "verdict line is not JSON"
    _refuse_mismatch(verdict, manifest)
    errors = validate_verdict(verdict, (manifest["rubric_version"], manifest["spec_sha"]))
    errors = errors or finding_path_errors(verdict, root)
    return verdicts[0], verdict, (errors[0] if errors else None)


def _lane_usable(lane, status, native_note):
    """(usable, error): a native lane needs its lane.out; any other lane needs a clean status."""
    if native_note is not None:
        if (lane / "lane.out").is_file():
            return True, None
        return False, "native lane has no lane.out"
    if lane_ok(parse_status_line(status) if status else None):
        return True, None
    return False, f"lane is not usable: {status or 'no AIKIT-XAI line'}"


def _new_record(manifest):
    record: dict[str, Any] = dict(manifest)
    record.update(substitute=None, attempts=[], verdict=None)
    return record


def _load_record(path, manifest):
    """The record to extend, or a new one; a record with a verdict or another judge is refused."""
    if not path.is_file():
        return _new_record(manifest)
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("verdict") is not None:
        raise JudgeLoopError("a verdict is already recorded for this round; "
                             "a re-judge adds a round")
    if record.get("judge") != manifest["judge"]:
        raise JudgeLoopError(f"record {path.name} belongs to judge {record.get('judge')!r}, "
                             f"not {manifest['judge']!r}")
    return record


def ingest(lane_dir, records, root, native_note=None, substitute=None):
    """Record one lane's outcome with its manifest, status line and verdict; returns the message.

    A usable lane whose verdict passes is recorded with the verdict. Any other lane is recorded
    as an attempt with its error and no verdict. The refusals raise before anything is written.
    """
    lane = Path(lane_dir)
    manifest = json.loads((lane / "manifest.json").read_text(encoding="utf-8"))
    status = None if native_note is not None else last_status_line(
        _text_or_empty(lane / "lane.err"))
    usable, error = _lane_usable(lane, status, native_note)
    verdict_line, verdict = None, None
    if usable:
        verdict_line, verdict, error = _read_verdict(lane, manifest, root)
    path = record_path(records, manifest["loop"], manifest["skill"], manifest["round"],
                       manifest["judge"])
    record = _load_record(path, manifest)
    record["attempts"].append({"status_line": status, "note": native_note, "lane_ok": usable,
                               "verdict_line": verdict_line, "error": error})
    if error is None:
        record["verdict"] = verdict
    if substitute is not None:
        record["substitute"] = substitute
    atomic_write_json(path, record)
    if error is None:
        return f"verdict recorded: {path}"
    return f"attempt recorded without a verdict ({error}): {path}"


# ─── the checker ──────────────────────────────────────────────────────────────

def _loop_key(name):
    return tuple(int(part) for part in name.split("."))


def _latest_loop(verdict_root, skill):
    if not verdict_root.is_dir():
        return None
    loops = [p for p in verdict_root.iterdir()
             if LOOP_RE.fullmatch(p.name) and (p / skill).is_dir()]
    return max(loops, key=lambda p: _loop_key(p.name)) if loops else None


def _round_dirs(skill_dir):
    return sorted((p for p in skill_dir.iterdir() if ROUND_DIR_RE.fullmatch(p.name)),
                  key=lambda p: int(p.name[1:]))


def _count(verdict, severity):
    return sum(f["severity"] == severity for f in verdict["findings"])


def _summary(root, skill, loop, number, valid):
    """The one summary line of a skill, plus its stale-digest note when the digest moved."""
    worst = min(valid, key=lambda r: r["verdict"]["percent"])
    current = worst["digest"] == skill_digest(root, skill)
    rounds = len(_round_dirs(loop / skill))
    line = (f"{skill}: loop {loop.name} round {number} (rounds {rounds}); "
            f"judges {', '.join(r['judge'] for r in valid)}; "
            f"worst {worst['verdict']['percent']:.1f} {worst['verdict']['grade']}; "
            f"critical {max(_count(r['verdict'], 'critical') for r in valid)}; "
            f"high {max(_count(r['verdict'], 'high') for r in valid)}; "
            f"digest {'current' if current else 'stale'}")
    note = None if current else (f"{skill}: stale digest (the skill changed after loop "
                                 f"{loop.name} round {number})")
    return line, note


def _round_verdicts(top, skill, number, judges):
    """(problems, scored, valid) of one round: scored holds the verdict-bearing records."""
    problems, scored, valid = [], [], []
    for path in sorted(top.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        judge = record["judge"]
        if judge not in judges:
            problems.append(f"{skill} r{number} {judge}: judge {judge} is not in the judge list")
        if record.get("verdict") is None:
            continue
        scored.append(record)
        errors = validate_verdict(record["verdict"], (record["rubric_version"], record["spec_sha"]))
        problems.extend(f"{skill} r{number} {judge}: {error}" for error in errors)
        if not errors:
            valid.append(record)
    return problems, scored, valid


def _check_skill(root, records, opts, skill):
    """(lines, problems, notes) for one skill: its latest loop's highest round."""
    loop = _latest_loop(records / "verdicts", skill)
    rounds = _round_dirs(loop / skill) if loop is not None else []
    if loop is None or not rounds:
        return [], [f"{skill}: no verdict records"], []
    top = rounds[-1]
    number = int(top.name[1:])
    problems, scored, valid = _round_verdicts(top, skill, number, opts.judges)
    if not scored:
        problems.append(f"{skill}: not judged (no verdict in loop {loop.name} round {number})")
    if not valid:
        return [], problems, []
    line, note = _summary(root, skill, loop, number, valid)
    return [line], problems, [note] if note else []


def check(root, records, opts):
    """Check the records of the given skills; returns (lines, problems, notes)."""
    lines, problems, notes = [], [], []
    for skill in opts.skills:
        found_lines, found_problems, found_notes = _check_skill(root, Path(records), opts, skill)
        lines += found_lines
        problems += found_problems
        notes += found_notes
    return lines, problems, notes


# ─── the judge pool ───────────────────────────────────────────────────────────

POOL_SIZE = 2
SUBSTITUTE_ONE = "only one configured judge passed its probe"
SUBSTITUTE_NONE = "no configured judge passed its probe"
SUBSTITUTE_EMPTY = "judge list empty"


def _probe_files(lane):
    """(token, lane.out, lane.err) texts of a probe lane, or None when one of them is missing."""
    names = ("token", "lane.out", "lane.err")
    if not all((lane / name).is_file() for name in names):
        return None
    return tuple((lane / name).read_text(encoding="utf-8", errors="replace") for name in names)


def _probe_verdict(judge, usable, status, reason):
    return {"judge": judge, "usable": usable, "status_line": status, "reason": reason}


def probe_result(probe_dir, judge):
    """One judge's probe: usable only on a clean exit with the exact expected answer."""
    files = _probe_files(Path(probe_dir) / judge_slug(judge))
    if files is None:
        return _probe_verdict(judge, False, None, "no probe output")
    token, out, err = files
    status = last_status_line(err)
    fields = parse_status_line(status) if status else None
    if not fields:
        return _probe_verdict(judge, False, None, "no AIKIT-XAI line")
    if not lane_ok(fields):
        reason = (f"status {fields.get('status')} exit {fields.get('exit')} "
                  f"tree {fields.get('tree')}")
        return _probe_verdict(judge, False, status, reason)
    if out.strip() != token.strip():
        return _probe_verdict(judge, False, status, "answer is not the sentinel")
    return _probe_verdict(judge, True, status, "")


def choose_pool(judges, native, results):
    """The pool: the first two usable judges; else one usable judge plus native; else native."""
    if native in judges:
        raise JudgeLoopError("the native id must not be in the judge list")
    usable = [result["judge"] for result in results if result["usable"]]
    pool = {"judges": list(judges), "native": native, "probes": list(results),
            "members": [], "substitutes": []}
    if len(usable) >= POOL_SIZE:
        pool["members"] = usable[:POOL_SIZE]
        return pool
    if usable:
        reason = SUBSTITUTE_ONE
        pool["members"] = [usable[0], native]
    else:
        reason = SUBSTITUTE_EMPTY if not judges else SUBSTITUTE_NONE
        pool["members"] = [native]
    pool["substitutes"] = [{"judge": native, "reason": reason}]
    return pool


def read_loop_file(records, loop):
    """The loop record <records>/loops/<loop>.json as a dict ({"loop": loop} when absent)."""
    if not LOOP_RE.fullmatch(loop):
        raise JudgeLoopError(f"bad loop id {loop!r}")
    path = Path(records) / "loops" / f"{loop}.json"
    if not path.is_file():
        return {"loop": loop}
    return json.loads(path.read_text(encoding="utf-8"))


def update_loop_file(records, loop, key, value):
    """Set `key` in the loop record, keeping its other keys; returns the record's path."""
    data = read_loop_file(records, loop)
    data[key] = value
    path = Path(records) / "loops" / f"{loop}.json"
    atomic_write_json(path, data)
    return path


def _cmd_pool(args, root):
    probe_dir = _abs(root, args.probe_dir)
    results = [probe_result(probe_dir, judge) for judge in args.judges]
    pool = choose_pool(args.judges, args.native, results)
    update_loop_file(_abs(root, args.records), args.loop, "pool", pool)
    for result in results:
        state = "usable" if result["usable"] else f"unusable ({result['reason']})"
        print(f"{PREFIX} probe {result['judge']}: {state}")
    for substitute in pool["substitutes"]:
        print(f"{PREFIX} substitute {substitute['judge']}: {substitute['reason']}")
    print(f"{PREFIX} pool {args.loop}: {', '.join(pool['members'])}")
    return 0


# ─── the judge count ──────────────────────────────────────────────────────────

JEV_INSTRUCTIONS = ("How likely is it that the change since the last judged version moves a "
                    "skill-judge score past normal run-to-run variation?")
JEV_LEVELS = ("no change likely to move the score",
              "a small move within run-to-run variation is possible",
              "a move past run-to-run variation is likely",
              "a move past run-to-run variation is near certain")
BAR_TENTHS = 800
BAND_TENTHS = 70


class JevUnavailable(Exception):
    """The jev client could not answer; the count keeps one judge and records why."""


JEV_ITEM_ID = "judge-count"
JEV_CALL_TIMEOUT = 120
BASE_RE = re.compile(r"[0-9a-f]{7,40}")


def deterministic_count(last_v4):
    """(count, reasons) from the deterministic triggers alone: two when one applies, else one."""
    if last_v4 is None:
        return 2, ["no rubric-v4 verdict"]
    reasons = []
    if last_v4["critical"] or last_v4["high"]:
        reasons.append("last verdict had a critical or high finding")
    if abs(round(last_v4["percent"] * 10) - BAR_TENTHS) <= BAND_TENTHS:
        reasons.append(f"last percent {last_v4['percent']:.1f} is within "
                       f"{BAND_TENTHS / 10:.1f} points of {BAR_TENTHS / 10:.0f}")
    if reasons:
        return 2, reasons
    return 1, ["no deterministic trigger"]


def percent_words(percent):
    """A fixed phrase for how far the last percent sat from the pass mark, never the number."""
    distance = abs(round(percent * 10) - BAR_TENTHS)
    side = "above" if percent >= BAR_TENTHS / 10 else "below"
    if distance <= 100:
        return f"the last score sat just outside judge variation, {side} the pass mark"
    if distance <= 150:
        return f"the last score sat moderately far {side} the pass mark"
    return f"the last score sat far {side} the pass mark"


def _lines_word(count):
    if count == 0:
        return "SKILL.md unchanged"
    if count <= 10:
        return "a few SKILL.md lines changed"
    if count <= 50:
        return "a moderate SKILL.md change"
    return "a large SKILL.md change"


def _files_word(count):
    if count == 0:
        return "none"
    return "one or two files" if count <= 2 else "several files"


def change_words(rows):
    """Fixed words for the change since the judged commit; rows are (added, deleted, path)."""
    paths = [path for _added, _deleted, path in rows]
    lines = sum((added or 0) + (deleted or 0) for added, deleted, path in rows
                if path.endswith("/SKILL.md"))
    references = [p for p in paths if "/references/" in p]
    evals = [p for p in paths if "/evals/" in p and p not in references]
    scripts = [p for p in paths if p.endswith(CODE_SUFFIXES)
               and p not in references and p not in evals]
    return {"skill_md": _lines_word(lines), "references": _files_word(len(references)),
            "scripts": _files_word(len(scripts)), "evals": _files_word(len(evals))}


def jev_item(pct_word, words):
    """The one score item sent to jev: fixed instructions, levels and words; no path or name."""
    context = (f"{pct_word}; no critical or high findings; {words['skill_md']}; "
               f"reference files: {words['references']}; script files: {words['scripts']}; "
               f"eval files: {words['evals']}.")
    return {"id": JEV_ITEM_ID, "type": "score", "instructions": JEV_INSTRUCTIONS,
            "context": context, "criteria": list(JEV_LEVELS)}


def jev_level(result, item):
    """(level index, note) from a ladder document; the index is None without a usable answer."""
    items = result.get("items") if isinstance(result, dict) else None
    entry = items.get(item["id"]) if isinstance(items, dict) else None
    if not isinstance(entry, dict):
        return None, "jev gave no answer"
    decided_by = entry.get("decided_by")
    if not isinstance(decided_by, str) or decided_by == "own_reasoning":
        return None, "jev needs_fallback (own reasoning)"
    column = entry.get(decided_by)
    choice = column.get("choice") if isinstance(column, dict) else None
    if choice not in item["criteria"]:
        return None, "jev answer is not one of the levels"
    index = item["criteria"].index(choice)
    return index, f"jev level {index} ({choice}) from {decided_by}"


def final_count(det, level, note):
    """The count after jev: a deterministic two stays; level 2 or more raises one to two."""
    count, reasons = det
    if count == 2:
        return 2, list(reasons)
    if level is None:
        return 1, [*reasons, note]
    if level >= 2:
        return 2, [*reasons, f"{note}: asks for two"]
    return 1, [*reasons, f"{note}: keeps one"]


def ask_jev(item, client, run=subprocess.run):
    """Send one score item to the jev client's ladder; JevUnavailable when it cannot answer."""
    env = {**os.environ, "GSD_PATH_JEV": "1", "GSD_PATH_JEV_TIMEOUT_SECONDS": "30",
           "JEV_CALLER": "judge_loop"}
    try:
        proc = run([sys.executable, "-B", str(client), "ladder"],
                   input=json.dumps({"items": [item]}), capture_output=True, text=True,
                   timeout=JEV_CALL_TIMEOUT, check=False, env=env)
    except (OSError, subprocess.SubprocessError) as exc:
        raise JevUnavailable(f"cannot run the jev client: {exc}") from exc
    if proc.returncode != 0:
        raise JevUnavailable(f"jev client exited {proc.returncode}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise JevUnavailable("jev client output is not JSON") from exc


def find_jev_client(root, env, override):
    """The jev client: `override` when it is a file, else the first installed copy found."""
    if override is not None:
        return str(override) if Path(override).is_file() else None
    for base in skills_roots(env, str(root / "skills")):
        candidate = os.path.join(base, JEV_ENTRY_REL)
        if os.path.isfile(candidate):
            return candidate
    return None


def numstat(root, base, skill):
    """(added, deleted, path) rows of the skill since `base`; None when `base` is no commit."""
    if not SAFE_SKILL.fullmatch(skill):
        raise JudgeLoopError(f"bad skill name {skill!r}")
    if not BASE_RE.fullmatch(base):
        return None
    probe = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "--quiet",
                            f"{base}^{{commit}}"], capture_output=True, text=True, check=False)
    if probe.returncode != 0:
        return None
    diff = subprocess.run(["git", "-C", str(root), "diff", "--numstat", base, "HEAD", "--",
                           f"skills/{skill}/"], capture_output=True, text=True, check=False)
    rows = []
    for line in diff.stdout.splitlines():
        added, deleted, path = line.split("\t", 2)
        rows.append((None if added == "-" else int(added),
                     None if deleted == "-" else int(deleted), path))
    return rows


def _ask_jev_level(root, name, last, ask, jev):
    """Fill `jev` (item, asked, level, note) for a skill whose judged commit is known."""
    rows = numstat(root, last["judged_at"], name)
    if rows is None:
        jev["note"] = f"jev input absent: base commit {last['judged_at']} not found"
        return
    item = jev_item(percent_words(last["percent"]), change_words(rows))
    jev["item"] = item
    jev["asked"] = True
    try:
        answer = ask(item)
    except (JevUnavailable, OSError, subprocess.SubprocessError, ValueError) as exc:
        jev["note"] = f"jev unavailable: {exc}"
        return
    jev["level"], jev["note"] = jev_level(answer, item)


def count_skill(root, name, entry, ask):
    """One skill's count record: the deterministic triggers, then the jev item when it applies."""
    last = entry["last_v4"]
    det = deterministic_count(last)
    jev = {"asked": False, "item": None, "level": None, "note": ""}
    if det[0] == 2:
        jev["note"] = "not asked (deterministic two)"
    elif ask is None:
        jev["note"] = "jev not asked (--no-jev)"
    elif last["judged_at"] is None:
        jev["note"] = "jev input absent: no base commit recorded"
    else:
        _ask_jev_level(root, name, last, ask, jev)
    count, reasons = final_count(det, jev["level"], jev["note"])
    return {"count": count, "reasons": reasons, "last_v4": last, "jev": jev}


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _last_ok(last):
    return (isinstance(last, dict) and _is_number(last.get("percent"))
            and _is_int(last.get("critical")) and _is_int(last.get("high"))
            and (last.get("judged_at") is None or isinstance(last.get("judged_at"), str))
            and isinstance(last.get("source"), str))


def _old_ok(old):
    return (isinstance(old, dict) and isinstance(old.get("value"), str)
            and isinstance(old.get("source"), str))


def _entry_error(name, entry):
    """The shape problem of one skills entry, or None."""
    batch = entry.get("batch") if isinstance(entry, dict) else None
    if not isinstance(batch, str) or not LOOP_RE.fullmatch(batch):
        return f"skill {name} has no valid batch"
    if entry.get("last_v4") is not None and not _last_ok(entry["last_v4"]):
        return f"skill {name} has a malformed last_v4"
    if entry.get("old_score") is not None and not _old_ok(entry["old_score"]):
        return f"skill {name} has a malformed old_score"
    return None


def load_inputs(records):
    """inputs.json: the skills to count and the excluded names, shape-checked; raises otherwise."""
    path = Path(records) / "inputs.json"
    if not path.is_file():
        raise JudgeLoopError(f"inputs.json is missing in {records}")
    data = json.loads(path.read_text(encoding="utf-8"))
    skills = data.get("skills") if isinstance(data, dict) else None
    excluded = data.get("excluded", {}) if isinstance(data, dict) else None
    if not isinstance(skills, dict) or not isinstance(excluded, dict):
        raise JudgeLoopError("inputs.json: skills and excluded must be objects")
    for name in sorted(skills):
        problem = _entry_error(name, skills[name])
        if problem:
            raise JudgeLoopError(f"inputs.json: {problem}")
    for name in sorted(excluded):
        if not isinstance(excluded[name], str) or not excluded[name]:
            raise JudgeLoopError(f"inputs.json: excluded {name} needs a reason")
    both = sorted(set(skills) & set(excluded))
    if both:
        raise JudgeLoopError(f"inputs.json: {both[0]} is in both skills and excluded")
    return {"skills": skills, "excluded": excluded}


def _chosen_skills(inputs, requested):
    """The skills to count: the requested ones (each must be a skill), else all, in batch order."""
    names = list(requested) or list(inputs["skills"])
    for name in names:
        if name not in inputs["skills"]:
            raise JudgeLoopError(f"inputs.json: no skill {name}")
    return sorted(set(names), key=lambda n: (_loop_key(inputs["skills"][n]["batch"]), n))


def _ask_for(client):
    """The ask callable for count_skill: the jev client, or a refusal when none was found."""
    if client is None:
        def unavailable(_item):
            raise JevUnavailable("no jev client found")
        return unavailable
    return lambda item: ask_jev(item, client)


def _cmd_count(args, root):
    records = _abs(root, args.records)
    inputs = load_inputs(records)
    names = _chosen_skills(inputs, args.skill)
    ask = None
    if not args.no_jev:
        override = _abs(root, args.client) if args.client else None
        ask = _ask_for(find_jev_client(root, os.environ, override))
    counts = dict(read_loop_file(records, args.loop).get("counts", {}))
    for name in names:
        counts[name] = count_skill(root, name, inputs["skills"][name], ask)
    update_loop_file(records, args.loop, "counts", counts)
    for name in names:
        reasons = "; ".join(counts[name]["reasons"])
        print(f"{PREFIX} count {name}: {counts[name]['count']} ({reasons})")
    return 0


# ─── command line ─────────────────────────────────────────────────────────────

def _abs(root, value):
    path = Path(value)
    return path if path.is_absolute() else root / path


def _cmd_prompt(args, root):
    override = _abs(root, args.judge_package) if args.judge_package else None
    package = find_judge_package(root, os.environ, override)
    out = _abs(root, args.out)
    if args.probe:
        print(f"{PREFIX} probe written: {write_probe(package, args.judge, out)}")
        return 0
    for skill in args.skill:
        request = PromptRequest(args.loop, args.round, args.judge, skill, out)
        print(f"{PREFIX} lane written: {write_lane_prompt(root, package, request)}")
    return 0


def _cmd_ingest(args, root):
    substitute = {"replaces": args.replaces, "reason": args.reason} if args.replaces else None
    message = ingest(_abs(root, args.lane_dir), _abs(root, args.records), root,
                     native_note=args.native_note, substitute=substitute)
    print(f"{PREFIX} {message}")
    return 0


def _cmd_check(args, root):
    opts = CheckOptions(tuple(args.skills), tuple(args.judges), args.gate, args.require_current)
    lines, problems, notes = check(root, _abs(root, args.records), opts)
    for text in lines + notes + problems:
        print(f"{PREFIX} {text}")
    return 1 if problems else 0


def build_parser():
    parser = argparse.ArgumentParser(prog="judge_loop.py",
                                     description="Build judge prompts, record verdicts, check.")
    parser.add_argument("--root", help="repository root (default: the checkout of the cwd)")
    sub = parser.add_subparsers(dest="command")
    prompt = sub.add_parser("prompt", help="write a judge prompt and its manifest, or a probe")
    prompt.add_argument("--probe", action="store_true", help="write the probe prompt instead")
    prompt.add_argument("--loop")
    prompt.add_argument("--round", type=int)
    prompt.add_argument("--judge", required=True)
    prompt.add_argument("--skill", action="append", default=[])
    prompt.add_argument("--out", required=True)
    prompt.add_argument("--judge-package")
    ingest_p = sub.add_parser("ingest", help="record one lane's outcome")
    ingest_p.add_argument("--lane-dir", required=True)
    ingest_p.add_argument("--records", required=True)
    ingest_p.add_argument("--native-note", help="the lane is native: its note, no status line")
    ingest_p.add_argument("--replaces", help="the judge this lane substitutes for")
    ingest_p.add_argument("--reason", help="why the substitute ran (with --replaces)")
    check_p = sub.add_parser("check", help="check the verdict records")
    check_p.add_argument("records")
    check_p.add_argument("--skills", nargs="*", default=[])
    check_p.add_argument("--judges", nargs="*", default=[])
    check_p.add_argument("--gate", action="store_true")
    check_p.add_argument("--require-current", action="store_true")
    pool_p = sub.add_parser("pool", help="choose the judge pool from the probe results")
    pool_p.add_argument("--loop", required=True)
    pool_p.add_argument("--judges", nargs="*", default=[])
    pool_p.add_argument("--native", required=True, help="the native judge id, the fallback")
    pool_p.add_argument("--probe-dir", required=True)
    pool_p.add_argument("--records", required=True)
    count_p = sub.add_parser("count", help="the judge count per skill: triggers, then jev")
    count_p.add_argument("--loop", required=True)
    count_p.add_argument("--records", required=True)
    count_p.add_argument("--skill", action="append", default=[])
    count_p.add_argument("--no-jev", action="store_true", help="keep the deterministic count")
    count_p.add_argument("--client", help="the jev client (default: the installed one)")
    return parser


COMMANDS = {"prompt": _cmd_prompt, "ingest": _cmd_ingest, "check": _cmd_check,
            "pool": _cmd_pool, "count": _cmd_count}


def _check_args(parser, args):
    """The usage rules argparse cannot state alone; a violation exits 2 through the parser."""
    if args.command == "prompt":
        if args.probe and (args.skill or args.loop or args.round is not None):
            parser.error("--probe takes no --skill, --loop or --round")
        if not args.probe and not (args.skill and args.loop and args.round is not None):
            parser.error("prompt needs --loop, --round and --skill (or --probe)")
    if args.command == "ingest" and bool(args.replaces) != bool(args.reason):
        parser.error("--replaces and --reason go together")


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.error("a subcommand is required: prompt, ingest, check, pool or count")
    _check_args(parser, args)
    try:
        root = find_root(Path(args.root) if args.root else None)
        return COMMANDS[args.command](args, root)
    except (JudgeLoopError, OSError, ValueError) as exc:
        print(f"{PREFIX} {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

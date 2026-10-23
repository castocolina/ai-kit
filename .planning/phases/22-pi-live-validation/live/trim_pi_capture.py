#!/usr/bin/env python3
"""Owner tool for 22-INTERACTIVE-PI.md C1, ruling Q2; raw capture never leaves tmp/."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

_ALLOWED_MODEL_FIELDS = (
    "id", "name", "provider", "api", "input", "contextWindow", "maxTokens",
    "reasoning", "thinkingLevelMap", "cost", "type",
)
_FORBIDDEN_MARKERS = ("baseurl", "apikey", "authorization", "bearer", '"headers"')


def _responses(raw: str) -> list[dict]:
    responses = []
    for line in raw.splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict) and item.get("command") == "get_available_models":
            responses.append(item)
    return responses


def _capture_block(models: list, version: str) -> dict:
    providers: dict[str, int] = {}
    for model in models:
        if isinstance(model, dict):
            provider = model.get("provider")
            if isinstance(provider, str) and provider:
                providers[provider] = providers.get(provider, 0) + 1
    return {"pi_version": version, "captured": datetime.now(UTC).date().isoformat(),
            "count": sum(isinstance(model, dict) for model in models),
            "providers": dict(sorted(providers.items()))}


def _trimmed_object(response: dict, version: str) -> dict | None:
    if response.get("success") is not True:
        return None
    data = response.get("data")
    models = data.get("models") if isinstance(data, dict) else None
    if not isinstance(models, list):
        return None
    safe_models = [{key: model[key] for key in _ALLOWED_MODEL_FIELDS if key in model}
                   for model in models if isinstance(model, dict)]
    result = {key: response[key] for key in ("id", "type", "command", "success")
              if key in response}
    result["data"] = {"models": safe_models}
    result["_capture"] = _capture_block(models, version)
    return result


def _secret_scan(root: Path, temporary_dir: str) -> bool:
    root_string = str(root)
    if root_string not in sys.path:
        sys.path.insert(0, root_string)
    from tests.gsd_curated_eval import secret_scan

    return bool(secret_scan(temporary_dir))


def trim_capture(raw_path: Path, output_path: Path, version: str) -> int:
    try:
        raw = raw_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        print(f"unable to read raw capture: {exc}", file=sys.stderr)
        return 1
    responses = _responses(raw)
    if len(responses) != 1:
        print("expected exactly one get_available_models response", file=sys.stderr)
        return 1
    result = _trimmed_object(responses[0], version)
    if result is None:
        print("get_available_models response must succeed with a models list", file=sys.stderr)
        return 1
    serialized = json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n"
    if any(marker in serialized.lower() for marker in _FORBIDDEN_MARKERS):
        print("forbidden transport or credential marker in trimmed output", file=sys.stderr)
        return 1
    root = Path(__file__).resolve().parents[4]
    temporary_dir = tempfile.mkdtemp(prefix="pi-capture-trim-", dir=output_path.parent)
    staged = Path(temporary_dir) / "capture.json"
    try:
        staged.write_text(serialized, encoding="utf-8")
        if _secret_scan(root, temporary_dir):
            print("secret scan rejected trimmed output", file=sys.stderr)
            return 1
        os.replace(staged, output_path)
    except OSError as exc:
        print(f"unable to write trimmed capture: {exc}", file=sys.stderr)
        return 1
    finally:
        shutil.rmtree(temporary_dir, ignore_errors=True)
    capture = result["_capture"]
    counts = ", ".join(f"{provider}={count}"
                        for provider, count in capture["providers"].items())
    print(f"trimmed {capture['count']} models ({counts})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--pi-version", required=True)
    args = parser.parse_args()
    return trim_capture(args.raw, args.out, args.pi_version)


if __name__ == "__main__":
    raise SystemExit(main())

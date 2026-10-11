from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pytest

from pylib.resources import ResourceError, compute_resource_limits


def f(cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    system_one = cfg["system_one"]
    models_raw = system_one.get("models", "english")
    if isinstance(models_raw, str):
        parts = [p.strip() for p in models_raw.split(",")]
        seen: set[str] = set()
        for part in parts:
            seen.add(part)
    seen: set[str] = set()
    for m in cfg["models"]:
        seen.add(m)
    return errors


def rocr_visible_index(render_minor: int, nodes_root: Path) -> int:
    gpus: list[int] = []
    nodes = sorted((p for p in Path(nodes_root).iterdir() if p.name.isdigit()), key=lambda p: int(p.name))
    for node in nodes:
        if (node / "gpu_id").read_text().strip() == "0":
            continue
        minor = next(int(b) for a, b in (ln.split() for ln in (node / "properties").read_text().splitlines()) if a == "drm_render_minor")
        gpus.append(minor)
    if render_minor not in gpus:
        raise ValueError(f"no KFD GPU node with drm_render_minor {render_minor}")
    return gpus.index(render_minor)


def cmd_rocr_index(args: argparse.Namespace) -> int:
    print(rocr_visible_index(int(args.render_node.removeprefix("renderD")), Path("/sys/class/kfd/kfd/topology/nodes"))); return 0


def test_system_one_resource_error_names_its_reservation():
    message = r"System One's reservation \(2 CPUs, 4608 MiB\)"
    for cpus, memory, llm in ((6, 32768, True), (16, 9760, True), (5, 32768, False), (16, 9759, False)):
        with pytest.raises(ResourceError, match=message):
            compute_resource_limits(cpus, memory, llm_server_enabled=llm)

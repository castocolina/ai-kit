from __future__ import annotations

import os
import pathlib
import shutil
import subprocess

import yaml

from pylib.compose import render_compose

ROOT = pathlib.Path(__file__).resolve().parents[1]
CFG: dict = {}
SYSTEM_ONE = {"enabled": True, "port": 8010, "image": "localhost/llm-env-system-one:rocm",
              "models": "english", "vram_reserve_mib": 4096}


def system_one_document(cfg):
    text = render_compose(
        cfg,
        models_dir="/m", presets_path="/p", repo_root="/r",
    )
    return yaml.safe_load(text)


def test_system_one_requires_a_rocr_index():
    import pytest
    with pytest.raises(ValueError, match="ROCR_VISIBLE_DEVICES"):
        render_compose({**CFG, "system_one": SYSTEM_ONE}, models_dir="/m",
                       presets_path="/p", repo_root="/r")


def run_setup_no_gpu(tmp_path, **kw) -> tuple[subprocess.CompletedProcess[str], pathlib.Path, pathlib.Path]:
    raise NotImplementedError


def yq_value(config: pathlib.Path, expression: str) -> str:
    return ""


def test_setup_prefetches_system_one_weights_when_enabled(tmp_path: pathlib.Path) -> None:
    kfd = tmp_path / "kfd"
    kfd.touch()
    result, calls, _config = run_setup_no_gpu(tmp_path, system_one_env="1", kfd_path=str(kfd))
    recorded = calls.read_text()
    assert "llm-env-system-one-cache:/home/laya/.cache/huggingface" in recorded
    assert yq_value(_config, ".system_one.enabled") == "true"


def test_setup_skips_system_one_build_and_prefetch_when_disabled(tmp_path: pathlib.Path) -> None:
    result, calls, _config = run_setup_no_gpu(tmp_path)
    recorded = calls.read_text()
    assert "scripts/system-one-build.sh" not in recorded


def _print_endpoints(tmp_path: pathlib.Path, system_one_yaml: str):
    real = {name: shutil.which(name) for name in ("yq", "jq", "ip")}
    assert all(real.values())
    commands = tmp_path / "bin"
    home = tmp_path / "home"
    config = home / ".config/llm-env/models.yml"
    return subprocess.run(["/usr/bin/bash", "scripts/print-endpoints.sh"], cwd=ROOT, env=os.environ | {"HOME": str(home), "LLM_ENV_CONFIG": str(config), "PATH": f"{commands}:/usr/bin:/bin"}, stdin=subprocess.DEVNULL, text=True, capture_output=True, check=False)

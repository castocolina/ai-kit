import json
from argparse import Namespace
from types import SimpleNamespace
from typing import cast

import pytest
import yaml

from pylib.budget import compute_budget


def make_cfg(**overrides):
    return overrides


def write_test_config(tmp_path):
    return tmp_path


@pytest.fixture
def valid_cfg(): return make_cfg(system_one={"enabled": False})


def test_extra_reserved_mib_reduces_available():
    kwargs = dict(vram_total_mib=16384, compositor_used_mib=0, reserve_floor_mib=1024,
                  model_costs=[{"alias": "m", "weights_mib": 1000, "kv_mib": 100}], models_max=1)
    base = compute_budget(**kwargs)
    reserved = compute_budget(**kwargs, extra_reserved_mib=4096)
    assert reserved["available_mib"] == base["available_mib"] - 4096


def test_cmd_budget_system_one_lowers_ram_available_mib(tmp_path, monkeypatch, capsys):
    import llmenv; cfg = yaml.safe_load(write_test_config(tmp_path).read_text())
    monkeypatch.setattr(llmenv, "load_config", lambda path: cfg)
    ns = cast(Namespace, SimpleNamespace(config="cfg", models_dir="m")); llmenv.cmd_budget(ns); off = json.loads(capsys.readouterr().out)["ram_available_mib"]
    assert off

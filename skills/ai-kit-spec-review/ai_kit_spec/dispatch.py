"""What the one supervision core does not own: the child environment and resumable state.

`runner_dispatch` is the one supervision core (D-11). It spawns every cross-AI child,
table runtime and custom entry alike, and scrubs that child's environment through
`child_env` below. This module keeps that scrub and the resumable-state writer; it
runs no process of its own."""
import os

from ai_kit_spec.cache import cache_write_json
from ai_kit_spec.detection import HOST_SIGNAL_ENV_VARS


def child_env(extra: dict | None = None, env: dict | None = None) -> dict:
    """Builds the environment for a cross-AI child (D-14): copies `env` (or os.environ),
    removes every HOST_SIGNAL_ENV_VARS entry so the child never mistakes itself for the host,
    then applies `extra` -- an explicit per-runtime `env` addition survives the scrub because
    it is applied last."""
    base = dict(os.environ if env is None else env)
    for name in HOST_SIGNAL_ENV_VARS:
        base.pop(name, None)
    if extra:
        base.update(extra)
    return base


def write_resumable_state(path: str, state: dict, write_fn=cache_write_json) -> None:
    """Persists the minimal state needed to resume after a quota-exhaustion auto-wake."""
    write_fn(path, state)

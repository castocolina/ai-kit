"""Reads local, never-committed secrets (design spec 2026-09-02, Section 3/8) -- currently
just the Artificial Analysis API key. Not a general dotenv parser: flat KEY=VALUE lines only,
no quoting/escaping, matching the one real use case (an opaque API key string). Presence-only
reads for detection that must never hold a key value live here too (18 D-36). The secrets
folder follows ai-kit's one user-dir rule: a copy of config_io.cfg_config_base, pinned by
tests/test_config_dir_parity.py."""
import os


def _config_base(env: dict) -> str | None:
    xdg = env.get("XDG_CONFIG_HOME", "").strip()
    if os.path.isabs(xdg):
        return os.path.join(xdg, "ai-kit")
    home = env.get("HOME", "")
    return os.path.join(home, ".config", "ai-kit") if os.path.isabs(home) else None


def secrets_env_path(env: dict) -> str | None:
    base = _config_base(env)
    return os.path.join(base, "secrets.env") if base is not None else None


def load_secret(env: dict, key: str) -> str | None:
    """Env var takes precedence over the file. Missing file, missing key, no absolute home, or
    any read error -> None, never raises -- callers (model_sources.fetch_artificial_analysis)
    already treat a missing key as "skip this source", not a fatal error."""
    if env.get(key):
        return env[key]
    path = secrets_env_path(env)
    if path is None:
        return None
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                if k.strip() == key:
                    return v.strip()
    except OSError:
        return None
    return None


def secret_is_set(env: dict, key: str) -> bool:
    """True when `load_secret` would return a non-empty value; never returns the value."""
    return bool(load_secret(env, key))

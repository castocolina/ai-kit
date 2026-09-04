"""Reads local, never-committed secrets (design spec 2026-09-02, Section 3/8) -- currently
just the Artificial Analysis API key. Not a general dotenv parser: flat KEY=VALUE lines only,
no quoting/escaping, matching the one real use case (an opaque API key string)."""
import os


def secrets_env_path(env: dict) -> str:
    return os.path.join(env.get("HOME", ""), ".config", "ai-kit", "secrets.env")


def load_secret(env: dict, key: str) -> str | None:
    """Env var takes precedence over the file. Missing file, missing key, or any read error
    -> None, never raises -- callers (model_sources.fetch_artificial_analysis) already treat
    a missing key as "skip this source", not a fatal error."""
    if env.get(key):
        return env[key]
    try:
        with open(secrets_env_path(env), encoding="utf-8") as f:
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

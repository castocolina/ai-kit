"""35 D-02, D-09, D-13: the [models] table of config.toml: sources, per-source cache_days and
[[models.context]] overrides. Read through config_io's layered reader (project over user, per key),
written through toml_splice (byte-preserving, atomic). The Artificial Analysis key never lives here
(secrets.env)."""

import os
from typing import NamedTuple

from ai_kit_spec import config_io, toml_splice

KNOWN_SOURCES = ("models.dev", "artificial-analysis", "arena")
SOURCE_KEYS = {
    "models.dev": "models_dev",
    "artificial-analysis": "artificial_analysis",
    "arena": "arena",
}
DEFAULT_CACHE_DAYS = {"models_dev": 7, "artificial_analysis": 7, "arena": 7}
MAX_CACHE_DAYS = 365


class ContextOverride(NamedTuple):
    runtime: str
    model: str
    tokens: int


class ModelsSettings(NamedTuple):
    sources: tuple
    cache_days: dict
    context: tuple


def _sources(raw) -> tuple:
    if raw is None:
        return KNOWN_SOURCES
    if not isinstance(raw, list) or any(not isinstance(name, str) for name in raw):
        raise config_io.ConfigError("[models] sources", "must be a list of source names")
    result = []
    for name in raw:
        if name not in KNOWN_SOURCES:
            raise config_io.ConfigError(
                "[models] sources",
                f"unknown source '{name}'; known: models.dev, artificial-analysis, arena",
            )
        if name not in result:
            result.append(name)
    return tuple(result)


def _cache_days(raw) -> dict:
    if raw is None:
        return dict(DEFAULT_CACHE_DAYS)
    if not isinstance(raw, dict):
        raise config_io.ConfigError("[models.cache_days]", "must be a table")
    result = dict(DEFAULT_CACHE_DAYS)
    for key, value in raw.items():
        if key not in DEFAULT_CACHE_DAYS:
            raise config_io.ConfigError(
                "[models.cache_days]",
                f"unknown key '{key}'; known: models_dev, artificial_analysis, arena",
            )
        invalid = isinstance(value, bool) or not isinstance(value, int)
        if invalid or not 1 <= value <= MAX_CACHE_DAYS:
            raise config_io.ConfigError(
                "[models.cache_days]", f"{key} must be a whole number of days from 1 to 365"
            )
        result[key] = value
    return result


def _context(raw) -> tuple:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise config_io.ConfigError("[[models.context]]", "must be an array of tables")
    result = []
    for index, entry in enumerate(raw):
        if isinstance(entry, ContextOverride):
            entry = entry._asdict()
        if not isinstance(entry, dict):
            raise config_io.ConfigError(
                f"[[models.context]] entry {index}",
                "needs runtime, model and a positive whole tokens value",
            )
        runtime, model, tokens = entry.get("runtime"), entry.get("model"), entry.get("tokens")
        invalid_text = (
            not isinstance(runtime, str)
            or not runtime.strip()
            or not isinstance(model, str)
            or not model.strip()
        )
        invalid_tokens = (
            isinstance(tokens, bool) or not isinstance(tokens, int) or tokens <= 0
        )
        if invalid_text or invalid_tokens:
            raise config_io.ConfigError(
                f"[[models.context]] entry {index}",
                "needs runtime, model and a positive whole tokens value",
            )
        assert isinstance(runtime, str) and isinstance(model, str)
        assert isinstance(tokens, int) and not isinstance(tokens, bool)
        result.append(ContextOverride(runtime, model, tokens))
    return tuple(result)


def _unknown_keys(table: dict) -> None:
    for key in table:
        if key not in ("sources", "cache_days", "context"):
            raise config_io.ConfigError("[models]", f"unknown key '{key}'")


def read_models_settings(cwd: str, env) -> ModelsSettings:
    """Read project-over-user model settings, merged per [models] key."""
    table = config_io.cfg_layered_table(cwd, env, "models")
    _unknown_keys(table)
    return ModelsSettings(
        _sources(table.get("sources")),
        _cache_days(table.get("cache_days")),
        _context(table.get("context")),
    )


def _context_dicts(context: tuple) -> list:
    return [
        {"runtime": item.runtime, "model": item.model, "tokens": item.tokens}
        for item in context
    ]


def write_models_settings(path: str, sources=None, cache_days=None, context=None) -> None:
    """Validate and atomically splice provided model settings into a config file."""
    validated_sources = _sources(sources) if sources is not None else None
    validated_days = _cache_days(cache_days) if cache_days is not None else None
    validated_context = _context(context) if context is not None else None
    try:
        if os.path.exists(path):
            raw = config_io.cfg_read_bytes(path)
            parsed = config_io.cfg_parse_toml_bytes(raw, path)
            text = raw.decode("utf-8")
        else:
            parsed = {}
            text = ""
        if validated_sources is not None:
            text = toml_splice.set_table(text, ("models",), {"sources": list(validated_sources)})
        if validated_days is not None:
            assert cache_days is not None
            days_to_write = {key: cache_days[key] for key in cache_days}
            text = toml_splice.set_table(text, ("models", "cache_days"), days_to_write)
        if validated_context is not None:
            models_table = parsed.get("models", {})
            assert isinstance(models_table, dict)
            existing_context = models_table.get("context", [])
            if validated_context:
                if existing_context == []:
                    text = toml_splice.set_table(text, ("models",), {}, remove=("context",))
                text = toml_splice.set_array(
                    text, ("models", "context"), _context_dicts(validated_context)
                )
            else:
                text = toml_splice.set_array(text, ("models", "context"), [])
                text = toml_splice.set_table(text, ("models",), {"context": []})
        toml_splice.publish(path, text)
    except toml_splice.SpliceError as error:
        raise config_io.ConfigError(path, str(error)) from error

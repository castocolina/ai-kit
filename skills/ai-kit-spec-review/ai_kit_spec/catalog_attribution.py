"""35 R7 / Amend-5: credit lines for every catalog source used, in one fixed order,
and the Artificial Analysis terms line. Static text, ASCII."""

SOURCE_ORDER = ("models.dev", "artificial-analysis", "arena")
ATTRIBUTION = {
    "models.dev": (
        "models.dev (https://models.dev): repository license MIT; no attribution request found."
    ),
    "artificial-analysis": "Source: Artificial Analysis (artificialanalysis.ai)",
    "arena": (
        "Arena leaderboard dataset lmarena-ai/leaderboard-dataset (Hugging Face), CC BY 4.0; "
        "tiers and strengths are values derived from it."
    ),
}
AA_DERIVED_LINE = (
    "Tiers and classes based on data from Artificial Analysis. "
    "Not endorsed by Artificial Analysis."
)
AA_TERMS_LINE = (
    "Artificial Analysis redistribution terms: not granted for raw data or externally distributed "
    "derived data (free tier); caching rule not stated."
)


def attribution_lines(used_sources) -> list[str]:
    """Return credits for the named sources in their fixed presentation order."""
    sources = set(used_sources)
    unknown = sources.difference(SOURCE_ORDER)
    if unknown:
        name = sorted(unknown)[0]
        raise ValueError(f"unknown source: {name}")
    lines = []
    for source in SOURCE_ORDER:
        if source not in sources:
            continue
        lines.append(ATTRIBUTION[source])
        if source == "artificial-analysis":
            lines.extend((AA_DERIVED_LINE, AA_TERMS_LINE))
    return lines


def _sources_in_value(value: dict, used: set[str]) -> None:
    source = value.get("source")
    if source in SOURCE_ORDER:
        used.add(source)
    inputs = value.get("inputs", [])
    if isinstance(inputs, list):
        used.update(name for name in inputs if name in SOURCE_ORDER)


def _fact_sources(facts, used: set[str]) -> None:
    if not isinstance(facts, dict):
        return
    for fact in facts.values():
        if isinstance(fact, dict):
            _sources_in_value(fact, used)


def catalog_sources(catalog: dict) -> list[str]:
    """Find source provenance in catalog facts, including retained cached runtime facts."""
    used = set()
    for key, entry in catalog.items():
        if key == "_meta" or not isinstance(entry, dict):
            continue
        _fact_sources(entry.get("facts"), used)
        runtimes = entry.get("runtimes", {})
        if not isinstance(runtimes, dict):
            continue
        for runtime in runtimes.values():
            if not isinstance(runtime, dict):
                continue
            for field in ("context", "match"):
                _fact_sources(runtime.get(field), used)
    return [source for source in SOURCE_ORDER if source in used]

# Tier/quality/mode tokens known to appear as trailing, hyphen-joined
# suffixes on a model id across the CLIs this design has seen so far
# (confirmed live, cursor-agent's ~204-id catalog: e.g.
# "claude-opus-5-thinking-high-fast" is the "claude-opus-5" family with
# thinking+high+fast suffixes). This list is a snapshot, not a closed
# set — new CLIs/providers will invent new tier vocabulary this can't
# recognize, so group_models_by_family degrades gracefully (an
# unrecognized-suffix id just becomes its own single-member "family")
# rather than raising. It is a grouping AID for a human/wizard to skim a
# long catalog faster, never a substitute for actually reading the ids.
_MODEL_TIER_SUFFIXES = (
    "thinking", "low", "medium", "high", "xhigh", "max", "none", "fast",
)

# Longest/most-specific prefix first within each group — "cursor-grok-"
# must be checked before any bare "grok-" entry would be (there isn't one
# here: the standalone `grok` CLI is single-vendor by construction, so it
# never needs this table). opencode's ids are namespaced "<provider>/...";
# cursor-agent's are bare, vendor-prefixed strings with no separator.
_MODEL_VENDOR_PREFIXES = (
    ("opencode-go/kimi", "moonshot"),
    ("opencode-go/qwen", "alibaba"),
    ("opencode-go/grok", "xai"),
    ("opencode-go/gpt", "openai"),
    ("cursor-grok-", "xai"),
    ("claude-", "anthropic"),
    ("gpt-", "openai"),
    ("glm-", "zhipu"),
    ("kimi-", "moonshot"),
    ("gemini-", "google"),
    ("composer-", "cursor"),
)


def infer_vendor_from_model(model: str) -> str | None:
    """Deterministic best-effort vendor lookup from a model id's known
    prefix. Returns None when no prefix matches (e.g. `ollama-cloud/*`,
    `auto`, or an id this table hasn't seen yet) — the caller
    (review-spec-config) must ask the user to confirm/supply the vendor
    explicitly in that case, never guess further or fall back to a
    default vendor."""
    for prefix, vendor in _MODEL_VENDOR_PREFIXES:
        if model.startswith(prefix):
            return vendor
    return None

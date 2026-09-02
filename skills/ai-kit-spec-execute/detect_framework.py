"""Framework detection for ai-kit-spec-execute's router. Precedence (design spec S3, "same
signal-matching approach as ai-kit-spec-review Step 0.5" -- CRITICAL finding fix, repository
markers are supporting evidence only, never the primary signal):
  1. conversation_signal ("gsd"/"superpowers") -- the caller's own SKILL.md passes this when the
     user just invoked that framework's own planning skill in this conversation. Wins outright.
  2. document_path -- checked against each framework's own documented path convention: GSD phase/
     plan docs live under .planning/ (skills/ai-kit-spec-review-checklist/references/frameworks/
     gsd.md's own doc_types globs); superpowers plans live under docs/superpowers/plans/
     (writing-plans' own "Save plans to" line).
  3. Repository markers (isfile_fn/isdir_fn) -- confirmed signals: .planning/PROJECT.md (GSD, per
     skills/ai-kit-spec-review-checklist/references/frameworks/gsd.md) vs. docs/superpowers/plans/
     existing (superpowers, per writing-plans' own SKILL.md). GSD's marker is checked first when
     both are present -- the more specific, harder-to-fake signal, so it wins ties AT THIS
     FALLBACK TIER ONLY; it never overrides an explicit document_path/conversation_signal above.

Also runnable directly: `python3 detect_framework.py <cwd> [document_path]` prints the result on
stdout."""
import os
import sys


def _framework_from_document_path(document_path: str) -> str | None:
    normalized = document_path.replace(os.sep, "/")
    if "/.planning/" in normalized or normalized.startswith(".planning/"):
        return "gsd"
    if "docs/superpowers/plans/" in normalized:
        return "superpowers"
    return None


def detect_framework(cwd: str, document_path: str | None = None,
                      conversation_signal: str | None = None,
                      isfile_fn=os.path.isfile, isdir_fn=os.path.isdir) -> str:
    if conversation_signal in ("gsd", "superpowers"):
        return conversation_signal
    if document_path:
        from_path = _framework_from_document_path(document_path)
        if from_path is not None:
            return from_path
    if isfile_fn(os.path.join(cwd, ".planning", "PROJECT.md")):
        return "gsd"
    if isdir_fn(os.path.join(cwd, "docs", "superpowers", "plans")):
        return "superpowers"
    return "unknown"


if __name__ == "__main__":
    doc_path = sys.argv[2] if len(sys.argv) > 2 else None
    print(detect_framework(sys.argv[1], document_path=doc_path))

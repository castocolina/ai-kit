"""Classifies a writing-plans-style Task block by file-type/path signal, and estimates the
context a resolved executor will need. Both are pure functions over caller-supplied text/data
-- neither touches the filesystem, keeping this module trivially unit-testable.

classify_task's return type is deliberately the SAME frontend/backend/mixed/None axis
ai_kit_spec.execute_selection.filter_by_affinity already compares a candidate's own
task_affinity against (design spec Section 5) -- there is no separate infra/general category
here; execute_selection.py was never built to understand one, and inventing one here would
silently make every infra-flavored task behave as an untagged (None) one anyway, just with an
extra, unused label."""
import re


OVERHEAD_TOKENS = 2000  # fixed prompt/scaffolding overhead, on top of the touched files' content

_FRONTEND_EXTENSIONS = (".tsx", ".jsx", ".css", ".vue", ".scss")
_BACKEND_SIGNALS = (".py", ".go", ".rs", ".sql", "server/", "api/", "/api")


def _files_block(task_markdown: str) -> str:
    match = re.search(r"\*\*Files:\*\*(.*?)(?:\n\*\*|\Z)", task_markdown, re.DOTALL)
    return match.group(1) if match else ""


def classify_task(task_markdown: str) -> str | None:
    block = _files_block(task_markdown).lower()
    is_frontend = any(ext in block for ext in _FRONTEND_EXTENSIONS)
    is_backend = any(sig in block for sig in _BACKEND_SIGNALS)
    if is_frontend and is_backend:
        return "mixed"
    if is_frontend:
        return "frontend"
    if is_backend:
        return "backend"
    return None


def extract_touched_paths(task_markdown: str) -> list:
    """Every backtick-quoted path under the task's **Files:** block, in document order. Public
    (not the module-private _files_block regex directly) so Task 2's dispatch_injection.
    derive_files_touched_sizes can stat the SAME paths this module classifies/estimates over --
    one extraction, two consumers, never a second hand-rolled regex drifting from this one.

    Returned VERBATIM, including a writing-plans-style line-range qualifier
    (`existing.py:123-145`, the framework's own real `Modify:` convention) when the source text
    has one -- this function never normalizes a path to a filesystem-resolvable form. That
    normalization is deliberately Task 2's own job (derive_files_touched_sizes, CRITICAL
    finding), applied ONLY at the point a path is actually joined against cwd and stat'd; keeping
    the raw string here means estimate_required_context's files_touched_sizes dict lookups (keyed
    by this exact function's output) and derive_files_touched_sizes' dict keys always agree."""
    return re.findall(r"`([^`]+)`", _files_block(task_markdown))


def estimate_required_context(task_markdown: str, files_touched_sizes: dict) -> int:
    total_bytes = sum(files_touched_sizes.get(p, 0) for p in extract_touched_paths(task_markdown))
    return total_bytes // 4 + OVERHEAD_TOKENS

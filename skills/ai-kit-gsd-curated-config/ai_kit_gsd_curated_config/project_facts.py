"""Read-only project fact detection for inventory (R6). Inferred fields are listed in
`heuristic_fields`; nothing here writes to the project tree."""
from __future__ import annotations

import os

from . import claude_md_detect, frontend_detect

INSTRUCTION_FILES = ("AGENTS.md", "CLAUDE.md")
SKILL_ROOTS = (".claude/skills", ".agents/skills")

_DB_PACKAGE_KEYS = frozenset(
    {
        "pg",
        "mysql2",
        "prisma",
        "@prisma/client",
        "mongoose",
        "sqlite3",
        "better-sqlite3",
        "typeorm",
        "sequelize",
        "drizzle-orm",
        "knex",
    }
)


def detect_db_present(project_dir: str) -> bool:
    """True when common DB markers or package.json deps signal a database."""
    markers = (
        os.path.join(project_dir, "prisma", "schema.prisma"),
        os.path.join(project_dir, "alembic.ini"),
        os.path.join(project_dir, "schema.sql"),
    )
    if any(os.path.isfile(p) for p in markers):
        return True
    for rel in ("migrations", "db/migrate"):
        if os.path.isdir(os.path.join(project_dir, rel)):
            return True
    deps = frontend_detect.package_json_deps(project_dir)
    return bool(_DB_PACKAGE_KEYS & set(deps))


def detect_intel_index(project_dir: str) -> bool:
    intel_dir = os.path.join(project_dir, ".planning", "intel")
    if not os.path.isdir(intel_dir):
        return False
    for name in os.listdir(intel_dir):
        if name.endswith(".json") and os.path.isfile(os.path.join(intel_dir, name)):
            return True
    return False


def list_skills(project_dir: str) -> list[dict]:
    out: list[dict] = []
    for root in SKILL_ROOTS:
        root_path = os.path.join(project_dir, root)
        if not os.path.isdir(root_path):
            continue
        for name in sorted(os.listdir(root_path)):
            skill_md = os.path.join(root_path, name, "SKILL.md")
            if os.path.isfile(skill_md):
                out.append({"name": name, "root": root})
    return out


def _instruction_files(project_dir: str) -> dict[str, bool]:
    return {name: os.path.isfile(os.path.join(project_dir, name)) for name in INSTRUCTION_FILES}


def project_facts(project_dir: str, configured_claude_md_path: str | None) -> dict:
    """Returns the inventory `project` object."""
    planning_dir = os.path.join(project_dir, ".planning")
    return {
        "frontend": frontend_detect.detect_frontend_present(project_dir),
        "db": detect_db_present(project_dir),
        "instruction_files": _instruction_files(project_dir),
        "instruction_file": claude_md_detect.detect_claude_md_path(project_dir),
        "intel_index_present": detect_intel_index(project_dir),
        "planning_dir_present": os.path.isdir(planning_dir),
        "claude_md_path_configured": isinstance(configured_claude_md_path, str),
        "heuristic_fields": ["db", "frontend"],
    }

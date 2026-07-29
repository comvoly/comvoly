"""Render the additive v2 migrations as PostgreSQL SQL for review/rehearsal."""

from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from migrations import MIGRATIONS  # noqa: E402


def render() -> str:
    statements = [
        "BEGIN",
        """CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE,
            applied_at TEXT NOT NULL)""",
    ]
    for migration in MIGRATIONS:
        statements.extend(migration.statements)
        statements.append(
            "INSERT INTO schema_migrations (version, name, applied_at) "
            f"VALUES ({migration.version}, '{migration.name}', CURRENT_TIMESTAMP) "
            "ON CONFLICT (version) DO NOTHING"
        )
    statements.extend(
        [
            "COMMIT",
            "SELECT version, name FROM schema_migrations ORDER BY version",
            """SELECT count(*) AS v2_core_tables
               FROM information_schema.tables
               WHERE table_schema = 'public'
                 AND table_name IN ('accounts', 'workspaces', 'memberships',
                                    'content_items', 'import_jobs',
                                    'workspace_invitations')""",
        ]
    )
    return ";\n".join(statements) + ";\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base64", action="store_true")
    args = parser.parse_args()
    output = render().encode()
    print(base64.b64encode(output).decode() if args.base64 else output.decode(), end="")

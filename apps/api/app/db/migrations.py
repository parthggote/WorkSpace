from __future__ import annotations

import asyncio
import argparse
import hashlib
import os
from pathlib import Path

import asyncpg


REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_ENV_FILE = REPO_ROOT / ".env"
DEFAULT_MIGRATIONS_DIR = REPO_ROOT / "supabase" / "migrations"


def read_env_value(env_file: Path, key: str) -> str | None:
    if not env_file.exists():
        return None

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() != key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        return value
    return None


def get_database_url(env_file: Path = DEFAULT_ENV_FILE) -> str:
    database_url = os.environ.get("DATABASE_URL") or read_env_value(env_file, "DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured in the environment or repo .env file")
    return database_url


def discover_migration_files(migrations_dir: Path = DEFAULT_MIGRATIONS_DIR) -> list[Path]:
    if not migrations_dir.exists():
        raise RuntimeError(f"Migration directory does not exist: {migrations_dir}")
    return sorted(path for path in migrations_dir.iterdir() if path.suffix == ".sql" and path.is_file())


def filter_migration_files(
    migration_files: list[Path],
    *,
    from_version: str | None = None,
    only_version: str | None = None,
) -> list[Path]:
    if from_version and only_version:
        raise RuntimeError("Use either --from or --only, not both")

    if only_version:
        selected = [path for path in migration_files if path.name == only_version]
        if not selected:
            raise RuntimeError(f"Migration not found: {only_version}")
        return selected

    if from_version:
        selected = [path for path in migration_files if path.name >= from_version]
        if not selected:
            raise RuntimeError(f"No migrations found from: {from_version}")
        return selected

    return migration_files


def checksum_sql(sql: str) -> str:
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()


async def ensure_migration_table(conn: asyncpg.Connection) -> None:
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            checksum TEXT NOT NULL,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )


async def apply_migrations(
    database_url: str,
    migrations_dir: Path = DEFAULT_MIGRATIONS_DIR,
    *,
    from_version: str | None = None,
    only_version: str | None = None,
) -> list[str]:
    migration_files = filter_migration_files(
        discover_migration_files(migrations_dir),
        from_version=from_version,
        only_version=only_version,
    )
    applied_versions: list[str] = []
    conn = await asyncpg.connect(database_url)
    try:
        await ensure_migration_table(conn)
        existing_rows = await conn.fetch("SELECT version FROM schema_migrations")
        existing_versions = {row["version"] for row in existing_rows}

        for migration_file in migration_files:
            version = migration_file.name
            if version in existing_versions:
                continue

            sql = migration_file.read_text(encoding="utf-8")
            try:
                async with conn.transaction():
                    await conn.execute(sql)
                    await conn.execute(
                        "INSERT INTO schema_migrations (version, checksum) VALUES ($1, $2)",
                        version,
                        checksum_sql(sql),
                    )
            except Exception as exc:
                raise RuntimeError(f"Failed to apply migration {version}: {exc}") from exc
            applied_versions.append(version)
    finally:
        await conn.close()
    return applied_versions


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply SQL migrations from supabase/migrations.")
    parser.add_argument("--from", dest="from_version", help="Apply migrations starting from this filename.")
    parser.add_argument("--only", dest="only_version", help="Apply only this migration filename.")
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    applied_versions = await apply_migrations(
        get_database_url(),
        from_version=args.from_version,
        only_version=args.only_version,
    )
    if not applied_versions:
        print("No pending migrations.")
        return
    print("Applied migrations:")
    for version in applied_versions:
        print(f"- {version}")


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()

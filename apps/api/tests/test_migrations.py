from pathlib import Path

from app.db.migrations import discover_migration_files, filter_migration_files, read_env_value


def test_read_env_value_supports_unquoted_and_quoted_values(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        """
        TAVILY_API_KEY=
        DATABASE_URL="postgresql://user:pass@localhost:5432/app"
        OTHER=value
        """,
        encoding="utf-8",
    )

    assert read_env_value(env_file, "DATABASE_URL") == "postgresql://user:pass@localhost:5432/app"
    assert read_env_value(env_file, "TAVILY_API_KEY") == ""


def test_discover_migration_files_returns_sql_files_in_order(tmp_path):
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "202606180002_second.sql").write_text("SELECT 2;", encoding="utf-8")
    (migrations_dir / "README.md").write_text("ignore", encoding="utf-8")
    (migrations_dir / "202606180001_first.sql").write_text("SELECT 1;", encoding="utf-8")

    assert [path.name for path in discover_migration_files(migrations_dir)] == [
        "202606180001_first.sql",
        "202606180002_second.sql",
    ]


def test_filter_migration_files_can_start_from_named_file(tmp_path):
    files = [
        tmp_path / "202606170001_initial.sql",
        tmp_path / "202606180001_auth.sql",
        tmp_path / "202606180002_backend.sql",
    ]

    assert [path.name for path in filter_migration_files(files, from_version="202606180001_auth.sql")] == [
        "202606180001_auth.sql",
        "202606180002_backend.sql",
    ]


def test_filter_migration_files_can_apply_only_named_file(tmp_path):
    files = [
        tmp_path / "202606170001_initial.sql",
        tmp_path / "202606180001_auth.sql",
        tmp_path / "202606180002_backend.sql",
    ]

    assert [path.name for path in filter_migration_files(files, only_version="202606180002_backend.sql")] == [
        "202606180002_backend.sql",
    ]

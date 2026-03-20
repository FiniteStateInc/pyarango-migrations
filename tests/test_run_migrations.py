import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pyarango_migrations import migrations


class DummyMigration:
    key = "0001"


class RunMigrationsTests(unittest.TestCase):
    def test_run_migrations_reraises_unexpected_errors(self):
        failing_db = unittest.mock.Mock()
        failing_db.migrate.side_effect = RuntimeError("boom")

        with patch.object(migrations, "_load_migrations_from_dir", return_value=[DummyMigration()]):
            with patch.object(migrations, "Database", return_value=failing_db):
                with self.assertRaises(RuntimeError):
                    migrations.run_migrations(
                        dbname="example",
                        host="http://localhost:8529",
                        username="root",
                        password="password",
                    )

    def test_run_migrations_raises_value_error_when_credentials_are_missing_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            credentials_path = Path(tmpdir) / "creds.json"
            credentials_path.write_text(json.dumps({"username": "root"}), encoding="utf-8")

            with self.assertRaises(ValueError):
                migrations._read_credentials_from_file(str(credentials_path))

    def test_create_migration_script_creates_first_migration_in_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            migrations.create_migration_script("initial_setup", directory=tmpdir)

            self.assertTrue((Path(tmpdir) / "0001_initial_setup.py").exists())

    def test_database_migrate_handles_empty_history(self):
        migration = unittest.mock.Mock()
        migration.key = "0001"

        history = unittest.mock.Mock()
        history.all.return_value = []

        connection = unittest.mock.Mock()
        connection.name = "example"
        connection.aql.execute.return_value = iter(())

        db = object.__new__(migrations.Database)
        db.conn = connection
        db.history = history
        db.collection_name = "migrations"

        db.migrate([migration], None)

        migration.upgrade.assert_called_once_with(connection)
        history.insert.assert_called_once()

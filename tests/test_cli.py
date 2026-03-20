import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from pyarango_migrations import cli, migrations


class DummyMigration:
    key = "0001"


class CliTests(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_run_command_exits_non_zero_when_migration_fails(self):
        failing_db = unittest.mock.Mock()
        failing_db.migrate.side_effect = RuntimeError("boom")

        with patch.object(migrations, "_load_migrations_from_dir", return_value=[DummyMigration()]):
            with patch.object(migrations, "Database", return_value=failing_db):
                result = self.runner.invoke(
                    cli.cli,
                    [
                        "run",
                        "--host",
                        "http://localhost:8529",
                        "--dbname",
                        "example",
                        "--username",
                        "root",
                        "--password",
                        "password",
                        "--script-directory",
                        ".",
                    ],
                )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("boom", result.output)

    def test_run_multi_tenant_exits_non_zero_when_migration_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tenants_path = Path(tmpdir) / "tenants.json"
            tenants_path.write_text(json.dumps([{"databaseName": "tenant-a"}]), encoding="utf-8")

            with patch.object(cli, "run_migrations", side_effect=RuntimeError("boom")):
                result = self.runner.invoke(
                    cli.cli,
                    [
                        "run-multi-tenant",
                        "--host",
                        "http://localhost:8529",
                        "--username",
                        "root",
                        "--password",
                        "password",
                        "--script-directory",
                        ".",
                        "--tenants-file",
                        str(tenants_path),
                    ],
                )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("boom", result.output)

    def test_run_multi_tenant_exits_non_zero_for_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tenants_path = Path(tmpdir) / "tenants.json"
            tenants_path.write_text("{not json", encoding="utf-8")

            result = self.runner.invoke(
                cli.cli,
                [
                    "run-multi-tenant",
                    "--host",
                    "http://localhost:8529",
                    "--username",
                    "root",
                    "--password",
                    "password",
                    "--script-directory",
                    ".",
                    "--tenants-file",
                    str(tenants_path),
                ],
            )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Invalid tenants file", result.output)

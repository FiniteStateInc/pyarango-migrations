__all__ = ("cli_migration", "create_migration_script", "run_migrations", "run_multi_tenant_migrations")
import json
import logging
import os
import re
import sys
from collections import deque
from datetime import datetime
from functools import cache
from types import ModuleType
from typing import Iterator

import arango.exceptions
import click
from arango import ArangoClient, database

from toolbox.settings import MIGRATION_COLLECTION, MIGRATION_DIR, MIGRATION_TEMPLATE
from toolbox.utils import generate_timestamp, has_method, import_module

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@click.group(name="migration")
def cli_migration() -> None:
    pass


def _get_migration_filenames_in_path(directory: str) -> Iterator[str]:
    """
    Get the filenames of all migration scripts in a directory.

    A migration script is identified by its filename format which is a 4-digit number followed by an underscore and
    a descriptive name, concluding with the .py extension.

    :param directory: Path to directory containing backfill scripts.
    :return: Sorted list of filenames in the directory.
    """
    if not os.path.isdir(directory):
        raise NotADirectoryError(f"Directory not found: {directory}")

    regex = re.compile(r"^\d{4}_\w+\.py$")

    for file in filter(regex.match, sorted(os.listdir(directory))):
        yield file


def _get_next_migration_filename_prefix(directory: str) -> str:
    """
    Get the zero-padded prefix for the next migration script filename in a sequence.

    :param directory: Path to directory containing migration scripts.
    :return: Zero-padded string representing the next migration script filename prefix.
    """
    try:
        prefix = str(int(deque(_get_migration_filenames_in_path(directory), maxlen=1)[0].split("_")[0]) + 1)
    except IndexError:
        prefix = "1"
    return prefix.zfill(4)


@cli_migration.command(name="create")
@click.argument("name", required=True, type=str)
def create_migration_script(name: str) -> None:
    """
    Create a new migration script. The name will be prefixed with a 4-digit number and appended with the .py extension.

    :param name: Name of the migration script.
    :return: None
    """
    filename = f"{_get_next_migration_filename_prefix(MIGRATION_DIR)}_{name}.py"

    with open(os.path.join(MIGRATION_TEMPLATE), "r") as f:
        template = f.read().format_map({"date": datetime.now().strftime("%Y-%m-%d"), "filename": filename})

    with open(os.path.join(MIGRATION_DIR, filename), "w") as f:
        f.write(template)

    logger.info(f"Created migration script: {filename}")


class InvalidMigrationError(Exception):
    """
    Thrown when a client migration contains an error.
    """

    pass


class Migration:
    """
    A migration object represents a migration script.
    """

    def __init__(self, filepath: str) -> None:
        """
        Initialize a migration object.

        :param filepath: Path to migration script.
        """
        location, filename = os.path.split(filepath)

        # load the migration module and validate it has the required methods
        module_name = re.sub(r"[^\w]+", "_", os.path.splitext(filename)[0]).lower()
        self.module = import_module(module_name, os.path.join(location, filename))
        self.validate_import(self.module)

        # save reference to filename prefix (e.g. 0001) as the migration key
        self.key = filename.split("_")[0]

    @staticmethod
    def validate_import(module: ModuleType) -> None:
        """
        Validate the imported migration module has the required methods.
        """
        if missing := [method for method in ("upgrade", "downgrade") if not has_method(module, method)]:
            raise InvalidMigrationError(f"Invalid migration script. Missing methods: {missing}")

    def upgrade(self, db: database.Database) -> None:
        """
        Run the upgrade function of the migration script.

        :param db: Database object.
        """
        self.module.upgrade(db)

    def downgrade(self, db: database.Database) -> None:
        """
        Run the downgrade function of the migration script.

        :param db: Database object.
        """
        self.module.downgrade(db)

    def __repr__(self):
        return f"<Migration: {self.module.__name__}>"


class Database:
    """
    A database object represents a connection to an ArangoDB database. It is used to run migrations.
    """

    def __init__(self, host: str, name: str, username: str, password: str):
        """
        Initialize a database object.

        :param host: ArangoDB host address.
        :param name: ArangoDB database name.
        :param username: ArangoDB username.
        :param password: ArangoDB password.
        """
        if invalid_args := [arg for arg in (host, name, username, password) if not isinstance(arg, str)]:
            raise TypeError(f"Invalid argument types: {invalid_args}")

        client = ArangoClient(hosts=host, request_timeout=900)

        # save reference to database connection
        self.conn = client.db(name, username=username, password=password)

        # save reference to migration history collection, create it if it does not exist.
        c_name = MIGRATION_COLLECTION
        self.history = self.conn.collection(c_name) if self.conn.has_collection(c_name) else self.conn.create_collection(c_name)

    def __migrate_up(self, migrations: list[Migration]) -> None:
        logger.info("db.upgrade: running upgrade migrations")
        if migrations:
            applied_migrations = {entity["_key"] for entity in self.history.all()}

            for m in migrations:
                if m.key not in applied_migrations:
                    logger.info(f"db.upgrade: running migration {m.key}")
                    m.upgrade(self.conn)
                    self.history.insert({"_key": m.key, "ts": generate_timestamp()})
                else:
                    logger.info(f"db.upgrade: migration {m.key} has already been applied, skipping.")
        else:
            logger.warning("db.upgrade: no migrations to run")

        logger.info("db.upgrade: complete")

    def __migrate_down(self, migrations: list[Migration]) -> None:
        logger.info("db.upgrade: running downgrade migrations")

        if migrations:
            for m in migrations:
                logger.info(f"db.downgrade: running migration {m.key}")
                m.downgrade(self.conn)
                self.history.delete(m.key)
        else:
            logger.warning("db.downgrade: no migrations to run")

        logger.info("db.downgrade: complete")

    def migrate(self, migrations: list[Migration], target: str | None) -> None:
        logger.info(f"db.migrate: starting {self.conn.name}")

        target = target or migrations[-1].key

        try:
            # get the latest migration key from the history collection
            latest = self.conn.aql.execute(
                "FOR m IN @@collection SORT m._key DESC LIMIT 1 RETURN m", bind_vars={"@collection": MIGRATION_COLLECTION}
            ).next()["_key"]
        except StopIteration:
            # if no migrations have been applied, set latest to 0000
            latest = "0000"

        if target == latest:
            logger.info(f"db.migrate: target migration {target} is the latest migration, skipping {self.conn.name}")
            return

        is_target_less_than_latest = target < latest

        # filter migrations to only those between the latest and target
        migrations = sorted(
            [m for m in migrations if (latest < m.key <= target) or (target < m.key <= latest)],
            key=lambda m: m.key,
            reverse=is_target_less_than_latest,
        )

        if is_target_less_than_latest:
            self.__migrate_down(migrations)
        else:
            self.__migrate_up(migrations)

        logger.info(f"db.migrate: complete {self.conn.name}")

    def __repr__(self):
        return f"<Database: {self.conn.name}>"


@cache
def load_migrations_from_dir(path: str) -> list[Migration]:
    """
    Load migrations from a directory.

    :param path: Path to directory containing migration scripts.
    :return: List of migrations.
    """
    return [Migration(os.path.join(path, filename)) for filename in _get_migration_filenames_in_path(path)]


@cache
def read_credentials_from_file(path: str) -> tuple[str, str]:
    """
    Read database credentials from a JSON file.

    :param path: Path to JSON file containing database credentials.
    :return: Tuple containing database username and password.
    """
    try:
        with open(path, "r") as f:
            creds = json.load(f)
            return creds["username"], creds["password"]
    except KeyError as e:
        raise Exception(f"Invalid credentials file: {path}. Missing key: {e}")


@cli_migration.command(name="run")
@click.option("--db-creds-path", type=click.Path(exists=True), help="Path to JSON file containing database credentials.")
@click.option("--db-host", type=str, help="ArangoDB host address.", default="http://localhost:8529")
@click.option("--db-name", type=str, required=True, help="ArangoDB database name.")
@click.option("--db-username", type=str, help="ArangoDB username.", default="root")
@click.option("--db-password", type=str, help="ArangoDB password.", default="")
@click.argument("target", type=str, required=False)
def run_migrations(target: str | None, **kwargs) -> None:
    """
    Run database migrations for single-tenant database.`

    If the target migration is prior to the latest migration, the `downgrade` method will be invoked for each migration
    from the latest down to the target.

    If the target migration is after the latest migration, the `upgrade` method will be invoked for each migration from
    the latest up to and including the target.

    If the target migration is the latest migration, no migrations will be run.

    :param target: Target migration.
    :param kwargs: Additional command options. For more information, please refer to the `--help` command.
    :return: None
    """
    if target and not re.match(r"^\d{4}$", target):
        raise click.BadArgumentUsage("Invalid target migration. Must be a 4-digit number. e.g. 0001")
    try:
        # attempt to load migration scripts from local filesystem
        migrations = load_migrations_from_dir(MIGRATION_DIR)

        if len(migrations) == 0:
            raise Exception("No migrations found.")

        # attempt to establish a connection to the database.
        db = Database(
            kwargs["db_host"],
            kwargs["db_name"],
            *(
                read_credentials_from_file(db_cred_path)
                if (db_cred_path := kwargs.get("db_creds_path"))
                else (kwargs["db_username"], kwargs["db_password"])
            ),
        )

        # run database migrations
        db.migrate(migrations, target)
    except arango.exceptions.ArangoServerError as e:
        logger.error(f"db.migrate: failed to connect to {kwargs['db_name']} database. Error code: {e.http_code}")
    except Exception as e:
        logger.error(e)


@cli_migration.command(name="run-multi")
@click.option(
    "--db-creds-path", type=click.Path(exists=True), help="Path to JSON file containing database credentials.", required=True
)
@click.option(
    "--db-tenants-path", type=click.Path(exists=True), help="Path to JSON file containing database tenants.", required=True
)
@click.option("--db-host", type=str, help="ArangoDB host address.", default="http://localhost:8529")
@click.argument("target", type=str, required=False)
def run_multi_tenant_migrations(target: str | None, db_creds_path, db_tenants_path, db_host) -> None:
    """
    Run database migrations for all tenants specified in tenants JSON file.

    :param target: Target migration.
    :param db_creds_path: Path to JSON file containing database credentials.
    :param db_tenants_path: Path to JSON file containing database tenant information.
    :return: None
    """
    try:
        db_username, db_password = read_credentials_from_file(db_creds_path)
        tenants = json.load(open(db_tenants_path, "r"))
    except Exception as e:
        logger.error(e)
        sys.exit(1)

    ctx = click.get_current_context()

    for tenant in tenants:
        db_name = tenant["databaseName"]
        # fmt: off
        run_migrations.main(
            args=[
                "--db-host", db_host,
                "--db-username", db_username,
                "--db-password", db_password,
                "--db-name", db_name,
                target or "",
            ],
            prog_name=ctx.find_root().info_name,
            standalone_mode=False,
        )
        # fmt: on

    logger.info("run_multi_tenant_migrations: complete")
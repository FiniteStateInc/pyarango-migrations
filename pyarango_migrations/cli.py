#!/usr/bin/env poetry run python
# -*- coding: utf-8 -*-
import json
import logging
import sys

import click

from pyarango_migrations.constants import DEFAULTS
from pyarango_migrations.migrations import create_migration_script, run_migrations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.group()
def cli() -> None:
    pass


@cli.command(name="create")
@click.option(
    "--directory",
    "-d",
    type=click.Path(exists=False, file_okay=False, dir_okay=True),
    required=False,
    default=DEFAULTS.script_directory,
    show_default=True,
    help="Directory where the migration script will be created.",
)
@click.argument("name", required=True, type=str)
def create_cmd(name: str, **kwargs) -> None:
    """
    Create a new migration script in the specified directory. If no directory is specified, the script will be created
    in the current working directory.
    """
    create_migration_script(name, kwargs["directory"])


class StdRunCommand(click.Command):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.params += [
            click.Option(("--host", "-h"), type=str, help="Host address.", default=DEFAULTS.host, show_default=True),
            click.Option(("--dbname", "-d"), type=str, required=True, help="Database name."),
            click.Option(
                ("--collection", "-c"),
                type=str,
                default=DEFAULTS.collection,
                show_default=True,
                help="Name of collection to store migration history.",
            ),
            click.Option(("--username", "-u"), type=str, default=DEFAULTS.user, show_default=True, help="Username."),
            click.Option(("--password", "-p"), type=str, default=DEFAULTS.password, show_default=True, help="Password."),
            click.Option(
                ("--credentials-file", "-P"),
                type=click.Path(exists=True, file_okay=True, dir_okay=False),
                help="Path to JSON file containing database credentials.",
            ),
            click.Option(
                ("--script-directory", "-s"),
                type=click.Path(exists=True, file_okay=False, dir_okay=True),
                default=DEFAULTS.script_directory,
                show_default=True,
                help="Path to directory containing migration scripts.",
            ),
            click.Option(
                ("--target", "-t"), type=str, required=False, default=None, help="Target migration version. e.g. 0001"
            ),
        ]


@cli.command(name="run", cls=StdRunCommand)
def run_cmd(**kwargs) -> None:
    """
    Run database migrations for single-tenant database. If a target is specified, only migrations up to and including
    the target will be run. If no target is specified, all migrations will be run.

    If target is less than the current migration version, migrations will be rolled back. This is a non-inclusive
    operation, so if the current migration is 0003 and the target is 0001, migrations 0002 and 0003 will be rolled back.
    To roll back 0001 you must specify 0000 as the target.

    If target is same as the current migration version, no migrations will be run.
    """
    dbname = kwargs.pop("dbname")
    target = kwargs.pop("target")
    run_migrations(dbname=dbname, target=target, **kwargs)


@cli.command(name="run-multi-tenant", cls=StdRunCommand)
@click.option(
    "--tenants-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Path to JSON file containing database tenants.",
    required=True,
)
def run_multi_tenant_cmd(**kwargs) -> None:
    """
    Run database migrations for all tenants specified in tenants JSON file.
    """
    try:
        tenants = json.load(open(kwargs["tenants_file"], "r"))
    except json.JSONDecodeError as e:
        logger.error(f"Invalid tenants file. {e}")
        sys.exit(1)

    target = kwargs.pop("target")

    for tenant in tenants:
        dbname = tenant["databaseName"]
        run_migrations(dbname=dbname, target=target, **kwargs)


def main():
    cli()


if __name__ == "__main__":
    main()

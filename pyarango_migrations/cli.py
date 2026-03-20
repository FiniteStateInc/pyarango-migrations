#!/usr/bin/env poetry run python
# -*- coding: utf-8 -*-
import json
import logging

import click

from pyarango_migrations.constants import DEFAULTS
from pyarango_migrations.migrations import create_migration_script, run_migrations

logging.basicConfig(level=logging.INFO)


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


class MultiTenantRunCommand(click.Command):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.params += [
            click.Option(("--host", "-h"), type=str, help="Host address.", default=DEFAULTS.host, show_default=True),
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


def _raise_cli_error(exc: Exception) -> None:
    raise click.ClickException(str(exc)) from exc


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
    try:
        run_migrations(dbname=dbname, target=target, **kwargs)
    except click.ClickException:
        raise
    except Exception as exc:
        _raise_cli_error(exc)


@cli.command(name="run-multi-tenant", cls=MultiTenantRunCommand)
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
        with open(kwargs["tenants_file"], "r") as f:
            tenants = json.load(f)
    except json.JSONDecodeError as exc:
        _raise_cli_error(ValueError(f"Invalid tenants file. {exc}"))

    target = kwargs.pop("target")
    kwargs.pop("tenants_file")

    try:
        for tenant in tenants:
            dbname = tenant["databaseName"]
            run_migrations(dbname=dbname, target=target, **kwargs)
    except click.ClickException:
        raise
    except Exception as exc:
        _raise_cli_error(exc)


def main():
    cli()


if __name__ == "__main__":
    main()

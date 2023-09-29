#!/usr/bin/env poetry run python
# -*- coding: utf-8 -*-
import logging

import click

from toolbox.migrations import cli_migration

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.group()
def pyarango_migrations():
    pass


def main():
    pyarango_migrations.add_command(cli_migration)
    pyarango_migrations()


if __name__ == "__main__":
    main()

import os
from collections import namedtuple
from typing import Final

BASE_DIR: Final = os.path.dirname(os.path.realpath(__file__))

# static files directory (for templates)
TEMPLATES_DIR: Final = os.path.join(BASE_DIR, "templates")
MIGRATION_TEMPLATE_PATH: Final = os.path.join(TEMPLATES_DIR, "migration.txt")

# database collection to store migration run information
MIGRATION_COLLECTION: Final = "pyarango_migration_history"

# directory to store migration files if not specified
DEFAULT_MIGRATION_DIR: Final = f"{os.getcwd()}/avocado_migrations"

TIMESTAMP_FORMAT: Final = "%Y-%m-%dT%H:%M:%S.%fZ"

Defaults = namedtuple(
    "Defaults",
    [
        "host",
        "collection",
        "user",
        "password",
        "script_directory",
    ],
)
DEFAULTS = Defaults(
    host="http://localhost:8529",
    collection=MIGRATION_COLLECTION,
    user="root",
    password="",
    script_directory=DEFAULT_MIGRATION_DIR,
)

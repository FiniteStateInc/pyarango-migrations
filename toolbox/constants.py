import os
from typing import Final

BASE_DIR: Final = os.path.dirname(os.path.realpath(__file__))

# static files directory (for templates)
TEMPLATES_DIR: Final = os.path.join(BASE_DIR, "templates")
MIGRATION_TEMPLATE: Final = os.path.join(TEMPLATES_DIR, "migration.txt")

# database collection to store migration run information
MIGRATION_COLLECTION: Final = "pyarango_migration_history"

TIMESTAMP_FORMAT: Final = "%Y-%m-%dT%H:%M:%S.%fZ"

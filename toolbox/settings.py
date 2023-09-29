import os

TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

BASE_DIR = os.path.dirname(os.path.realpath(__file__))

# static files directory (for templates)
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
MIGRATION_TEMPLATE = os.path.join(TEMPLATES_DIR, "migration.txt")

# directory where migration scripts are stored
MIGRATION_DIR = os.path.join(BASE_DIR, "..", "migrations")

# database collection to store migration run information
MIGRATION_COLLECTION = "migration_history"

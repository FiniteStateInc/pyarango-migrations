"""
0001_inital.py Example migration.
"""
__date__ = "2023-09-05"

import logging

from arango import database

logger = logging.getLogger("0001_inital.py")
logger.setLevel(logging.INFO)


def upgrade(db: database.StandardDatabase):
    print("Hello world! 1")


def downgrade(db: database.StandardDatabase):
    print("Goodbye world! 1")

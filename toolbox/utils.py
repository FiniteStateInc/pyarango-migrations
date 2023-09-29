import importlib.util
from datetime import datetime
from types import ModuleType

from toolbox.settings import TIMESTAMP_FORMAT


def import_module(module_name: str, location: str) -> ModuleType:
    """
    Import module from a file location.
    https://docs.python.org/3.11/library/importlib.html#importing-a-source-file-directly
    """
    module_spec = importlib.util.spec_from_file_location(module_name, location)
    loader = importlib.util.LazyLoader(module_spec.loader)
    module_spec.loader = loader
    module = importlib.util.module_from_spec(module_spec)
    loader.exec_module(module)
    return module


def has_method(an_object: object, method_name: str) -> bool:
    return hasattr(an_object, method_name) and callable(getattr(an_object, method_name))


def generate_timestamp() -> str:
    """
    Generate a timestamp string in the format specified in toolbox/settings.py.

    :return: Timestamp string.
    """
    return datetime.now().strftime(TIMESTAMP_FORMAT)

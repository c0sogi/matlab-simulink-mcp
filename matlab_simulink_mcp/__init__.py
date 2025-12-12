from importlib import resources


def package_files():
    return resources.files(__package__)


def get_package_name() -> str:
    return __package__ or "app"

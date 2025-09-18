"""File-related utilities for project-level paths."""

import os


def get_config_path() -> str:
    """Return the absolute path to the project's config.yaml file."""
    this_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(this_dir, os.pardir, os.pardir))
    return os.path.join(project_root, "config.yaml")

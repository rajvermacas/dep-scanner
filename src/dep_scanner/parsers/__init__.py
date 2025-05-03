"""Dependency file parsers for the dependency scanner."""

# Import all parsers to register them
# These imports are needed for registration even though they appear unused
# ruff: noqa: F401
from dep_scanner.parsers.requirements_txt import RequirementsTxtParser
from dep_scanner.parsers.pyproject_toml import PyprojectTomlParser
from dep_scanner.parsers.build_sbt import BuildSbtParser

__all__ = []

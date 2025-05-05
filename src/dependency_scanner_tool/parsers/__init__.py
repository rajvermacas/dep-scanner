"""Dependency file parsers for the dependency scanner."""

# Import all parsers to register them
# These imports are needed for registration even though they appear unused
# ruff: noqa: F401
from dependency_scanner_tool.parsers.requirements_txt import RequirementsTxtParser
from dependency_scanner_tool.parsers.pyproject_toml import PyprojectTomlParser
from dependency_scanner_tool.parsers.build_sbt import BuildSbtParser

__all__ = []

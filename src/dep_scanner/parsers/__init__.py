"""Dependency file parsers for the dependency scanner."""

# Import all parsers to register them
from dep_scanner.parsers.requirements_txt import RequirementsTxtParser
from dep_scanner.parsers.pyproject_toml import PyprojectTomlParser
from dep_scanner.parsers.build_sbt import BuildSbtParser

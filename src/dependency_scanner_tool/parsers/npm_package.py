"""Parser for npm package.json and package-lock.json files."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Any

from dependency_scanner_tool.parsers.base import DependencyParser, ParserRegistry
from dependency_scanner_tool.scanner import Dependency, DependencyType

logger = logging.getLogger(__name__)


class NpmPackageParser(DependencyParser):
    """Parser for npm package.json and package-lock.json files."""

    supported_filenames: Set[str] = {"package.json", "package-lock.json"}

    def parse(self, file_path: Path) -> List[Dependency]:
        """Parse npm package files.

        Args:
            file_path: Path to package.json or package-lock.json

        Returns:
            List of dependencies found in the file
        """
        logger.debug(f"Parsing npm package file: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return []

        dependencies = []

        if file_path.name.endswith("package.json") and not file_path.name.endswith("package-lock.json"):
            dependencies = self._parse_package_json(data, file_path)
        elif file_path.name.endswith("package-lock.json"):
            dependencies = self._parse_package_lock_json(data, file_path)

        logger.info(f"Found {len(dependencies)} dependencies in {file_path}")
        return dependencies

    def _parse_package_json(self, data: Dict[str, Any], file_path: Path) -> List[Dependency]:
        """Parse dependencies from package.json.

        Args:
            data: Parsed JSON data
            file_path: Path to the package.json file

        Returns:
            List of dependencies
        """
        dependencies = []
        bundled_deps = set(data.get("bundledDependencies", []))
        bundled_deps.update(data.get("bundleDependencies", []))  # Both spellings are valid

        # Parse regular dependencies
        if "dependencies" in data and isinstance(data["dependencies"], dict):
            for name, version in data["dependencies"].items():
                dep = Dependency(
                    name=name,
                    version=version,
                    source_file=str(file_path),
                    dependency_type=DependencyType.UNKNOWN
                )
                # Store additional metadata in name suffix for now
                if name in bundled_deps:
                    dep.name = f"{name} [bundled]"
                dependencies.append(dep)
                logger.debug(f"Found dependency: {name} @ {version}")

        # Parse dev dependencies
        if "devDependencies" in data and isinstance(data["devDependencies"], dict):
            for name, version in data["devDependencies"].items():
                dep = Dependency(
                    name=f"{name} [dev]",  # Mark as dev dependency in name
                    version=version,
                    source_file=str(file_path),
                    dependency_type=DependencyType.UNKNOWN
                )
                dependencies.append(dep)
                logger.debug(f"Found dev dependency: {name} @ {version}")

        # Parse peer dependencies
        if "peerDependencies" in data and isinstance(data["peerDependencies"], dict):
            peer_meta = data.get("peerDependenciesMeta", {})
            for name, version in data["peerDependencies"].items():
                is_optional = peer_meta.get(name, {}).get("optional", False)
                suffix = " [peer-optional]" if is_optional else " [peer]"
                dep = Dependency(
                    name=f"{name}{suffix}",
                    version=version,
                    source_file=str(file_path),
                    dependency_type=DependencyType.UNKNOWN
                )
                dependencies.append(dep)
                logger.debug(f"Found peer dependency: {name} @ {version} (optional: {is_optional})")

        # Parse optional dependencies
        if "optionalDependencies" in data and isinstance(data["optionalDependencies"], dict):
            for name, version in data["optionalDependencies"].items():
                dep = Dependency(
                    name=f"{name} [optional]",
                    version=version,
                    source_file=str(file_path),
                    dependency_type=DependencyType.UNKNOWN
                )
                dependencies.append(dep)
                logger.debug(f"Found optional dependency: {name} @ {version}")

        return dependencies

    def _parse_package_lock_json(self, data: Dict[str, Any], _file_path: Path) -> List[Dependency]:
        """Parse dependencies from package-lock.json.

        Args:
            data: Parsed JSON data
            _file_path: Path to the package-lock.json file (unused but kept for interface consistency)

        Returns:
            List of dependencies
        """
        dependencies = []
        lockfile_version = data.get("lockfileVersion", 1)

        logger.debug(f"Parsing package-lock.json with lockfileVersion: {lockfile_version}")

        # For lockfileVersion 2 and 3, use the packages field
        if lockfile_version >= 2 and "packages" in data:
            dependencies = self._parse_packages_field(data["packages"])
        # For lockfileVersion 1 or as fallback, use dependencies field
        elif "dependencies" in data:
            dependencies = self._parse_dependencies_field(data["dependencies"])

        return dependencies

    def _parse_packages_field(self, packages: Dict[str, Any]) -> List[Dependency]:
        """Parse the packages field from lockfileVersion 2+ format.

        Args:
            packages: The packages field from package-lock.json

        Returns:
            List of dependencies
        """
        dependencies = []

        # Get root package info to determine dev dependencies
        root_package = packages.get("", {})
        dev_deps = set(root_package.get("devDependencies", {}).keys())
        optional_deps = set(root_package.get("optionalDependencies", {}).keys())
        peer_deps = set(root_package.get("peerDependencies", {}).keys())

        for path, info in packages.items():
            # Skip the root package entry
            if path == "":
                continue

            # Extract package name from path
            # Format: node_modules/package-name or node_modules/@scope/package-name
            if path.startswith("node_modules/"):
                name = path[len("node_modules/"):]
                # Remove any nested node_modules paths
                if "/node_modules/" in name:
                    name = name.split("/node_modules/")[0]

                version = info.get("version", "unknown")

                # Determine dependency type and add suffix
                is_dev = name in dev_deps or info.get("dev", False)
                is_optional = name in optional_deps or info.get("optional", False)
                is_peer = name in peer_deps or info.get("peer", False)

                display_name = name
                if is_dev:
                    display_name = f"{name} [dev]"
                elif is_optional:
                    display_name = f"{name} [optional]"
                elif is_peer:
                    display_name = f"{name} [peer]"

                dep = Dependency(
                    name=display_name,
                    version=version,
                    source_file="package-lock.json",
                    dependency_type=DependencyType.UNKNOWN
                )
                dependencies.append(dep)
                logger.debug(f"Found locked dependency: {name} @ {version}")

        return dependencies

    def _parse_dependencies_field(self, deps_data: Dict[str, Any]) -> List[Dependency]:
        """Parse the dependencies field from lockfileVersion 1 format.

        Args:
            deps_data: The dependencies field from package-lock.json

        Returns:
            List of dependencies
        """
        dependencies = []

        for name, info in deps_data.items():
            version = info.get("version", "unknown")
            is_dev = info.get("dev", False)
            is_optional = info.get("optional", False)

            display_name = name
            if is_dev:
                display_name = f"{name} [dev]"
            elif is_optional:
                display_name = f"{name} [optional]"

            dep = Dependency(
                name=display_name,
                version=version,
                source_file="package-lock.json",
                dependency_type=DependencyType.UNKNOWN
            )
            dependencies.append(dep)
            logger.debug(f"Found locked dependency: {name} @ {version}")

        return dependencies


# Register the parser with the ParserRegistry
ParserRegistry.register("npm_package", NpmPackageParser)
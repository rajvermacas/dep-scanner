"""Tests for npm package.json and package-lock.json parser."""

import json
import logging
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from dependency_scanner_tool.parsers.npm_package import NpmPackageParser
from dependency_scanner_tool.scanner import Dependency


class TestNpmPackageParser:
    """Test suite for NpmPackageParser."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        return NpmPackageParser()

    @pytest.fixture
    def test_data_dir(self):
        """Get the test data directory."""
        return Path(__file__).parent.parent / "test_data" / "npm_samples"

    def test_can_parse_package_json(self, parser):
        """Test that parser recognizes package.json files."""
        assert parser.can_parse(Path("package.json"))
        assert parser.can_parse(Path("/some/path/package.json"))
        assert not parser.can_parse(Path("requirements.txt"))
        assert not parser.can_parse(Path("package.json.bak"))

    def test_can_parse_package_lock_json(self, parser):
        """Test that parser recognizes package-lock.json files."""
        assert parser.can_parse(Path("package-lock.json"))
        assert parser.can_parse(Path("/some/path/package-lock.json"))
        assert not parser.can_parse(Path("yarn.lock"))

    def test_parse_basic_package_json(self, parser, test_data_dir):
        """Test parsing a basic package.json with dependencies and devDependencies."""
        file_path = test_data_dir / "basic_package.json"
        dependencies = parser.parse(file_path)

        # Check we got all dependencies
        dep_names = {dep.name for dep in dependencies}
        assert "express" in dep_names
        assert "lodash" in dep_names
        assert "axios" in dep_names
        assert "jest [dev]" in dep_names
        assert "eslint [dev]" in dep_names
        assert "prettier [dev]" in dep_names

        # Check versions
        express_dep = next(d for d in dependencies if d.name == "express")
        assert express_dep.version == "^4.18.2"
        assert express_dep.source_file == str(file_path)

        jest_dep = next(d for d in dependencies if d.name == "jest [dev]")
        assert jest_dep.version == "^29.5.0"

        # Check exact version
        axios_dep = next(d for d in dependencies if d.name == "axios")
        assert axios_dep.version == "1.4.0"

    def test_parse_complex_package_json(self, parser, test_data_dir):
        """Test parsing complex package.json with all dependency types."""
        file_path = test_data_dir / "complex_package.json"
        dependencies = parser.parse(file_path)

        dep_names = {dep.name for dep in dependencies}

        # Check regular dependencies
        assert "react" in dep_names
        assert "react-dom" in dep_names
        assert "@mui/material" in dep_names
        assert "uuid [bundled]" in dep_names  # uuid is bundled
        assert "semver" in dep_names

        # Check dev dependencies
        assert "@types/node [dev]" in dep_names
        assert "@types/react [dev]" in dep_names
        assert "typescript [dev]" in dep_names
        assert "webpack [dev]" in dep_names
        assert "babel-loader [dev]" in dep_names

        # Check optional dependencies
        assert "fsevents [optional]" in dep_names
        assert "chokidar [optional]" in dep_names

        # Check peer dependencies are included
        react_deps = [d for d in dependencies if "react" in d.name]
        assert len(react_deps) > 0  # Should have react from both dependencies and peerDependencies

    def test_parse_special_versions(self, parser, test_data_dir):
        """Test parsing special version formats."""
        file_path = test_data_dir / "special_versions_package.json"
        dependencies = parser.parse(file_path)

        dep_dict = {dep.name: dep for dep in dependencies}

        # Check special versions
        assert dep_dict["latest-package"].version == "latest"
        assert dep_dict["next-package"].version == "next"
        assert dep_dict["git-dependency"].version == "git+https://github.com/user/repo.git#v1.2.3"
        assert dep_dict["github-dependency"].version == "user/repo#feature-branch"
        assert dep_dict["local-package"].version == "file:../local-package"
        assert dep_dict["url-package"].version == "https://example.com/package.tar.gz"
        assert dep_dict["range-package"].version == ">=1.2.3 <2.0.0"
        assert dep_dict["prerelease-package"].version == "1.0.0-beta.1"
        assert dep_dict["workspace-tool [dev]"].version == "workspace:*"
        assert dep_dict["alias-package [dev]"].version == "npm:actual-package@^2.0.0"

    def test_parse_empty_package_json(self, parser, test_data_dir):
        """Test parsing package.json with no dependencies."""
        file_path = test_data_dir / "empty_package.json"
        dependencies = parser.parse(file_path)
        assert dependencies == []

    def test_parse_minimal_package_json(self, parser, test_data_dir):
        """Test parsing minimal package.json with only dependencies field."""
        file_path = test_data_dir / "minimal_package.json"
        dependencies = parser.parse(file_path)

        assert len(dependencies) == 1
        assert dependencies[0].name == "minimal-dep"
        assert dependencies[0].version == "1.0.0"

    def test_parse_basic_package_lock_json(self, parser, test_data_dir):
        """Test parsing basic package-lock.json."""
        file_path = test_data_dir / "basic_package-lock.json"
        dependencies = parser.parse(file_path)

        dep_names = {dep.name for dep in dependencies}
        assert "express" in dep_names
        assert "lodash" in dep_names
        assert "axios" in dep_names
        assert "jest [dev]" in dep_names

        # Check exact versions from lockfile
        express_dep = next(d for d in dependencies if d.name == "express")
        assert express_dep.version == "4.18.2"
        assert express_dep.source_file == "package-lock.json"

        lodash_dep = next(d for d in dependencies if d.name == "lodash")
        assert lodash_dep.version == "4.17.21"

        # Check dev dependency flag is reflected in name
        jest_dep = next(d for d in dependencies if d.name == "jest [dev]")
        assert jest_dep.version == "29.5.0"

    def test_parse_scoped_package_lock_json(self, parser, test_data_dir):
        """Test parsing package-lock.json with scoped packages."""
        file_path = test_data_dir / "scoped_package-lock.json"
        dependencies = parser.parse(file_path)

        dep_names = {dep.name for dep in dependencies}
        assert "@babel/core" in dep_names
        assert "@mui/material" in dep_names
        assert "@types/node" in dep_names

        babel_dep = next(d for d in dependencies if d.name == "@babel/core")
        assert babel_dep.version == "7.22.5"

    def test_parse_invalid_json(self, parser, tmp_path):
        """Test handling of invalid JSON."""
        invalid_json = tmp_path / "package.json"
        invalid_json.write_text("{ invalid json }")

        with patch("dependency_scanner_tool.parsers.npm_package.logger") as mock_logger:
            dependencies = parser.parse(invalid_json)
            assert dependencies == []
            mock_logger.error.assert_called()

    def test_parse_non_existent_file(self, parser):
        """Test handling of non-existent file."""
        with patch("dependency_scanner_tool.parsers.npm_package.logger") as mock_logger:
            dependencies = parser.parse(Path("/non/existent/package.json"))
            assert dependencies == []
            mock_logger.error.assert_called()

    def test_dependency_deduplication(self, parser, tmp_path):
        """Test that duplicate dependencies are handled correctly."""
        package_json = tmp_path / "package.json"
        package_json.write_text(json.dumps({
            "dependencies": {
                "react": "^18.0.0"
            },
            "devDependencies": {
                "react": "^18.0.0"
            },
            "peerDependencies": {
                "react": ">=16.0.0"
            }
        }))

        dependencies = parser.parse(package_json)
        react_deps = [d for d in dependencies if "react" in d.name]

        # Should have unique dependencies for each type
        assert len(react_deps) == 3

        # Check that they have different metadata reflected in names
        regular_react = next(d for d in react_deps if d.name == "react")
        dev_react = next(d for d in react_deps if d.name == "react [dev]")
        peer_react = next(d for d in react_deps if d.name == "react [peer]")

        assert regular_react.version == "^18.0.0"
        assert dev_react.version == "^18.0.0"
        assert peer_react.version == ">=16.0.0"

    def test_package_lock_json_lockfile_versions(self, parser, tmp_path):
        """Test handling different lockfileVersion formats."""
        # Test lockfileVersion 1 (legacy)
        lockfile_v1 = tmp_path / "package-lock.json"
        lockfile_v1.write_text(json.dumps({
            "lockfileVersion": 1,
            "dependencies": {
                "lodash": {
                    "version": "4.17.21",
                    "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz",
                    "integrity": "sha512-..."
                }
            }
        }))

        dependencies = parser.parse(lockfile_v1)
        assert len(dependencies) == 1
        assert dependencies[0].name == "lodash"
        assert dependencies[0].version == "4.17.21"

    def test_bundled_dependencies_flag(self, parser, tmp_path):
        """Test that bundledDependencies are marked correctly."""
        package_json = tmp_path / "package.json"
        package_json.write_text(json.dumps({
            "dependencies": {
                "express": "^4.0.0",
                "lodash": "^4.0.0"
            },
            "bundledDependencies": ["lodash"]
        }))

        dependencies = parser.parse(package_json)

        express_dep = next(d for d in dependencies if d.name == "express")
        lodash_dep = next(d for d in dependencies if d.name == "lodash [bundled]")

        assert "bundled" not in express_dep.name
        assert "bundled" in lodash_dep.name

    def test_logging_on_successful_parse(self, parser, test_data_dir, caplog):
        """Test that successful parsing logs appropriate messages."""
        with caplog.at_level(logging.DEBUG):
            file_path = test_data_dir / "basic_package.json"
            dependencies = parser.parse(file_path)

            assert len(dependencies) > 0
            assert "Parsing npm package file" in caplog.text
            assert "Found" in caplog.text
            assert "dependencies" in caplog.text.lower()
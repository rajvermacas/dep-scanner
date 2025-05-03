"""Tests for the build.sbt parser."""

import tempfile
from pathlib import Path
from unittest import TestCase

from dep_scanner.parsers.build_sbt import BuildSbtParser
from dep_scanner.scanner import DependencyType


class TestBuildSbtParser(TestCase):
    """Test cases for the build.sbt parser."""

    def setUp(self):
        """Set up the test environment."""
        self.parser = BuildSbtParser()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        """Clean up the test environment."""
        self.temp_dir.cleanup()

    def test_can_parse(self):
        """Test that the parser can identify build.sbt files."""
        # Test with a build.sbt file
        build_file = self.temp_path / "build.sbt"
        build_file.touch()
        self.assertTrue(self.parser.can_parse(build_file))

        # Test with a non-build.sbt file
        other_file = self.temp_path / "other.txt"
        other_file.touch()
        self.assertFalse(self.parser.can_parse(other_file))

        # Test with a .sbt file that's not named build.sbt
        other_sbt = self.temp_path / "other.sbt"
        other_sbt.touch()
        self.assertTrue(self.parser.can_parse(other_sbt))

    def test_parse_simple_dependencies(self):
        """Test parsing simple dependencies from build.sbt."""
        content = '''
        name := "example"
        scalaVersion := "2.13.8"
        
        libraryDependencies += "org.typelevel" %% "cats-core" % "2.7.0"
        libraryDependencies += "com.example" % "library" % "1.0.0"
        '''

        build_file = self.temp_path / "build.sbt"
        with open(build_file, "w") as f:
            f.write(content)

        dependencies = self.parser.parse(build_file)
        
        self.assertEqual(len(dependencies), 2)
        
        # Check first dependency
        self.assertEqual(dependencies[0].name, "org.typelevel:cats-core")
        self.assertEqual(dependencies[0].version, "2.7.0")
        self.assertEqual(dependencies[0].dependency_type, DependencyType.UNKNOWN)
        
        # Check second dependency
        self.assertEqual(dependencies[1].name, "com.example:library")
        self.assertEqual(dependencies[1].version, "1.0.0")

    def test_parse_complex_dependencies(self):
        """Test parsing dependencies with different formats and spacing."""
        content = '''
        name := "complex-example"
        
        libraryDependencies ++= Seq(
          "org.scala-lang" % "scala-library" % "2.13.8",
          "org.scalactic" %% 
            "scalactic" % "3.2.10",
          "org.scalatest" %% "scalatest" % "3.2.10" % Test
        )
        
        libraryDependencies += "com.typesafe.akka" %% 
          "akka-actor" % 
            "2.6.18"
        '''

        build_file = self.temp_path / "build.sbt"
        with open(build_file, "w") as f:
            f.write(content)

        dependencies = self.parser.parse(build_file)
        
        self.assertEqual(len(dependencies), 4)
        
        # Verify all dependency names and versions are correctly extracted
        dep_info = [(dep.name, dep.version) for dep in dependencies]
        expected = [
            ("org.scala-lang:scala-library", "2.13.8"),
            ("org.scalactic:scalactic", "3.2.10"),
            ("org.scalatest:scalatest", "3.2.10"),
            ("com.typesafe.akka:akka-actor", "2.6.18")
        ]
        
        for expected_dep in expected:
            self.assertIn(expected_dep, dep_info)

    def test_empty_file(self):
        """Test parsing an empty file."""
        build_file = self.temp_path / "build.sbt"
        build_file.touch()

        dependencies = self.parser.parse(build_file)
        self.assertEqual(len(dependencies), 0)

    def test_invalid_file(self):
        """Test parsing a file with invalid content."""
        content = '''
        This is not a valid build.sbt file.
        It doesn't contain any Scala build definitions.
        '''

        build_file = self.temp_path / "build.sbt"
        with open(build_file, "w") as f:
            f.write(content)

        dependencies = self.parser.parse(build_file)
        self.assertEqual(len(dependencies), 0)

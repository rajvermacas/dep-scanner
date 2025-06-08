"""Tests for the Scala import analyzer."""

import tempfile
from pathlib import Path
from unittest import TestCase

from dependency_scanner_tool.analyzers.scala_analyzer import ScalaImportAnalyzer


class TestScalaImportAnalyzer(TestCase):
    """Test cases for the Scala import analyzer."""

    def setUp(self):
        """Set up the test environment."""
        self.analyzer = ScalaImportAnalyzer()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        """Clean up the test environment."""
        self.temp_dir.cleanup()

    def test_can_analyze(self):
        """Test that the analyzer can identify Scala files."""
        # Test with a Scala file
        scala_file = self.temp_path / "test.scala"
        scala_file.touch()
        self.assertTrue(self.analyzer.can_analyze(scala_file))

        # Test with a Scala script file
        sc_file = self.temp_path / "test.sc"
        sc_file.touch()
        self.assertTrue(self.analyzer.can_analyze(sc_file))

        # Test with a non-Scala file
        other_file = self.temp_path / "test.java"
        other_file.touch()
        self.assertFalse(self.analyzer.can_analyze(other_file))

    def test_analyze_simple_imports(self):
        """Test analyzing simple import statements."""
        content = '''
        import scala.collection.mutable.Map
        import java.util.List
        import org.apache.spark.SparkContext
        import cats.effect.IO
        '''

        scala_file = self.temp_path / "simple_imports.scala"
        with open(scala_file, "w") as f:
            f.write(content)

        dependencies = self.analyzer.analyze(scala_file)
        
        # Should only include non-standard library imports
        self.assertEqual(len(dependencies), 2)
        
        # Check dependency names
        dep_names = {dep.name for dep in dependencies}
        self.assertIn("org.apache.spark:spark-core", dep_names)
        self.assertIn("org.typelevel:cats-effect", dep_names)
        
        # Standard library modules should be excluded
        self.assertNotIn("scala.collection.mutable", dep_names)
        self.assertNotIn("java.util", dep_names)

    def test_analyze_selective_imports(self):
        """Test analyzing selective import statements."""
        content = '''
        import java.util.{List, ArrayList, Map}
        import org.apache.spark.{SparkContext, SparkConf}
        import cats.{Effect, IO}
        import akka.actor.{Actor, ActorSystem => System}
        '''

        scala_file = self.temp_path / "selective_imports.scala"
        with open(scala_file, "w") as f:
            f.write(content)

        dependencies = self.analyzer.analyze(scala_file)
        
        # Check dependency names
        dep_names = {dep.name for dep in dependencies}
        self.assertIn("org.apache.spark:spark-core", dep_names)
        self.assertIn("org.typelevel:cats-core", dep_names)
        self.assertIn("com.typesafe.akka:akka-actor", dep_names)
        
        # Java standard library should be excluded
        self.assertNotIn("java.util", dep_names)

    def test_analyze_wildcard_imports(self):
        """Test analyzing wildcard import statements."""
        content = '''
        import scala.collection._
        import java.util._
        import org.apache.spark._
        import akka.http._
        import zio._
        '''

        scala_file = self.temp_path / "wildcard_imports.scala"
        with open(scala_file, "w") as f:
            f.write(content)

        dependencies = self.analyzer.analyze(scala_file)
        
        # Check dependency names
        dep_names = {dep.name for dep in dependencies}
        self.assertIn("org.apache.spark:spark-core", dep_names)
        self.assertIn("com.typesafe.akka:akka-http", dep_names)
        self.assertIn("dev.zio:zio", dep_names)
        
        # Standard library modules should be excluded
        self.assertNotIn("scala.collection", dep_names)
        self.assertNotIn("java.util", dep_names)

    def test_analyze_mixed_imports(self):
        """Test analyzing mixed import patterns."""
        content = '''
        import scala.util.Try
        import java.time.LocalDateTime
        import org.scalatest.FlatSpec
        import cats.effect.{IO, Resource}
        import akka.actor._
        import play.api.mvc.Controller
        import slick.driver.MySQLDriver.api._
        '''

        scala_file = self.temp_path / "mixed_imports.scala"
        with open(scala_file, "w") as f:
            f.write(content)

        dependencies = self.analyzer.analyze(scala_file)
        
        # Check dependency names
        dep_names = {dep.name for dep in dependencies}
        self.assertIn("org.scalatest:scalatest", dep_names)
        self.assertIn("org.typelevel:cats-effect", dep_names)
        self.assertIn("com.typesafe.akka:akka-actor", dep_names)
        self.assertIn("com.typesafe.play:play", dep_names)
        self.assertIn("com.typesafe.slick:slick", dep_names)
        
        # Standard library modules should be excluded
        self.assertNotIn("scala.util", dep_names)
        self.assertNotIn("java.time", dep_names)

    def test_analyze_with_comments(self):
        """Test analyzing imports with comments."""
        content = '''
        // Single line comment
        import org.scalatest.FlatSpec  // End of line comment
        
        /*
         * Multi-line comment
         * import scala.collection.mutable.Buffer  // This should be ignored
         */
        import cats.effect.IO
        
        /* Another comment import akka.actor.Actor */
        import play.api.mvc.Controller
        '''

        scala_file = self.temp_path / "with_comments.scala"
        with open(scala_file, "w") as f:
            f.write(content)

        dependencies = self.analyzer.analyze(scala_file)
        
        # Check dependency names
        dep_names = {dep.name for dep in dependencies}
        self.assertIn("org.scalatest:scalatest", dep_names)
        self.assertIn("org.typelevel:cats-effect", dep_names)
        self.assertIn("com.typesafe.play:play", dep_names)
        
        # Commented imports should not be included
        self.assertNotIn("scala.collection.mutable", dep_names)
        self.assertNotIn("com.typesafe.akka:akka-actor", dep_names)

    def test_analyze_unknown_packages(self):
        """Test analyzing imports with unknown package mappings."""
        content = '''
        import com.mycompany.mypackage.MyClass
        import org.unknown.library.SomeClass
        import single.package.Class
        '''

        scala_file = self.temp_path / "unknown_packages.scala"
        with open(scala_file, "w") as f:
            f.write(content)

        dependencies = self.analyzer.analyze(scala_file)
        
        # Should generate best-guess artifact names
        self.assertEqual(len(dependencies), 3)
        
        # Check dependency names
        dep_names = {dep.name for dep in dependencies}
        self.assertIn("com.mycompany:mypackage", dep_names)
        self.assertIn("org.unknown:library", dep_names)
        self.assertIn("single.package", dep_names)

    def test_analyze_empty_file(self):
        """Test analyzing an empty file."""
        scala_file = self.temp_path / "empty.scala"
        scala_file.touch()

        dependencies = self.analyzer.analyze(scala_file)
        self.assertEqual(len(dependencies), 0)

    def test_analyze_no_imports(self):
        """Test analyzing a file with no imports."""
        content = '''
        // This file has no imports
        object HelloWorld {
          def main(args: Array[String]): Unit = {
            println("Hello, world!")
          }
        }
        '''

        scala_file = self.temp_path / "no_imports.scala"
        with open(scala_file, "w") as f:
            f.write(content)

        dependencies = self.analyzer.analyze(scala_file)
        self.assertEqual(len(dependencies), 0)

    def test_parse_import_statement(self):
        """Test the _parse_import_statement method directly."""
        # Test standard import
        packages = self.analyzer._parse_import_statement("org.apache.spark.SparkContext")
        self.assertEqual(packages, ["org.apache.spark"])
        
        # Test selective import
        packages = self.analyzer._parse_import_statement("cats.effect.{IO, Resource}")
        self.assertEqual(packages, ["cats.effect"])
        
        # Test wildcard import
        packages = self.analyzer._parse_import_statement("akka.actor._")
        self.assertEqual(packages, ["akka.actor"])
        
        # Test aliased import
        packages = self.analyzer._parse_import_statement("play.api.{Application, Controller => BaseController}")
        self.assertEqual(packages, ["play.api"])

    def test_should_process_import(self):
        """Test the _should_process_import method directly."""
        # Should process third-party packages
        self.assertTrue(self.analyzer._should_process_import("org.apache.spark"))
        self.assertTrue(self.analyzer._should_process_import("cats.effect"))
        self.assertTrue(self.analyzer._should_process_import("akka.actor"))
        
        # Should not process standard library packages
        self.assertFalse(self.analyzer._should_process_import("scala.collection"))
        self.assertFalse(self.analyzer._should_process_import("java.util"))
        self.assertFalse(self.analyzer._should_process_import("javax.servlet"))
        
        # Should not process empty imports
        self.assertFalse(self.analyzer._should_process_import(""))
        self.assertFalse(self.analyzer._should_process_import("   "))
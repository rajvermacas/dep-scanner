# Documentation Requirements

For all new features or workflows implemented in this project:

1. **Always update README.md**
   - Document any new features, options, or workflows
   - Include clear examples of how to use new functionality
   - Explain configuration options and their effects
   - Update any relevant sections of existing documentation

2. **Documentation Structure**
   - Maintain a consistent style with the existing documentation
   - Use clear, concise language
   - Include code examples where appropriate
   - Organize information logically (e.g., group related options)

3. **Documentation Best Practices**
   - Keep examples simple but illustrative
   - Document both basic and advanced usage patterns
   - Include information about default values and behavior
   - Explain any limitations or edge cases
   - Update version information if applicable

4. **Documentation Review Process**
   - Review documentation changes for accuracy
   - Ensure documentation is updated in the same PR as code changes
   - Check for typos and grammatical errors
   - Verify that examples work as described

----------------

# Test-Driven Development Requirements

For all new code development in this project:

1. **Always write test cases for any new developed code**
   - Write tests before marking any feature as complete
   - Ensure tests cover both normal operation and error cases
   - Use mocking where appropriate to isolate components
   - Aim for high test coverage

2. **Test Case Structure**
   - Unit tests should be placed in the appropriate test directory
   - Follow the existing naming conventions (test_*.py)
   - Group related tests in test classes when appropriate
   - Include docstrings explaining what each test is verifying

3. **Test Execution Process**
   - Run tests using pytest
   - Fix any failing tests before committing code
   - Run ALL tests, not just tests for the new feature, to ensure no regressions
   - Run linting (ruff) after tests pass
   - Only commit code when both tests and linting pass

4. **Testing Best Practices**
   - Use fixtures to set up test environments
   - Keep tests independent from each other
   - Mock external dependencies and services
   - Test both success and failure paths
   - Include edge cases in test coverage

------------

# Dependency Scanner Tool PyPI Package

The dependency-scanner-tool package has been published to PyPI with version 0.1.2.

## Package Configuration
- Project name: dependency-scanner-tool
- Current version: 0.1.2
- Package description and README included
- GitHub repository link: https://github.com/rajvermacas/dep-scanner.git

## Version Update Process
Future version updates will require:
1. Incrementing the version number in pyproject.toml
2. Rebuilding the package with `python -m build`
3. Uploading to PyPI with `python -m twine upload dist/*`

------------
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

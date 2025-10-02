
import json
import csv
from unittest.mock import patch, MagicMock
import pytest
from click.testing import CliRunner

from dependency_scanner_tool.client_cli import cli

@pytest.fixture
def runner():
    return CliRunner()

@patch('dependency_scanner_tool.client_cli.DependencyScannerClient')
def test_group_scan_success(mock_client, runner):
    # Note: The CLI doesn't use gitlab_service directly - it makes HTTP calls to the server
    # The server internally uses gitlab_service

    # Mock client
    mock_client_instance = mock_client.return_value
    mock_scan_result = MagicMock()
    mock_scan_result.dependencies = {'DEPS': True, 'NO_DEPS': False}
    mock_client_instance.scan_repository_and_wait.return_value = ('job-123', mock_scan_result)

    with runner.isolated_filesystem():
        # Run the command
        result = runner.invoke(
            cli,
            [
                '--server', 'http://test.com',
                '--username', 'user',
                '--password', 'pass',
                'group-scan',
                'http://gitlab.com/group',
                '--json-output', 'results.json',
                '--csv-output', 'results.csv'
            ],
            catch_exceptions=False
        )

        # Verify exit code and output
        assert result.exit_code == 0
        assert "Group scan completed!" in result.output
        assert "Detailed results saved to: results.json" in result.output
        assert "Detailed results saved to: results.csv" in result.output

        # Verify JSON output
        with open('results.json', 'r') as f:
            data = json.load(f)
            assert data['group_url'] == 'http://gitlab.com/group'
            assert data['scan_summary']['total_projects'] == 2
            assert data['group_dependencies'] == {'DEPS': True, 'NO_DEPS': False}

        # Verify CSV output
        with open('results.csv', 'r') as f:
            reader = csv.reader(f)
            header = next(reader)
            assert header == ['group_url', 'dependency_category', 'dependency_status']
            rows = list(reader)
            assert len(rows) == 2
            assert rows[0] == ['http://gitlab.com/group', 'DEPS', 'True']
            assert rows[1] == ['http://gitlab.com/group', 'NO_DEPS', 'False']


@patch('dependency_scanner_tool.client_cli.DependencyScannerClient')
@patch('builtins.open')
def test_group_scan_io_error(mock_open, mock_client, runner):
    # Note: The CLI doesn't use gitlab_service directly - it makes HTTP calls to the server

    # Mock client
    mock_client_instance = mock_client.return_value
    mock_scan_result = MagicMock()
    mock_scan_result.dependencies = {'DEPS': True}
    mock_client_instance.scan_repository_and_wait.return_value = ('job-123', mock_scan_result)

    # Mock open to raise IOError
    mock_open.side_effect = IOError("Permission denied")

    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            [
                '--server', 'http://test.com',
                '--username', 'user',
                '--password', 'pass',
                'group-scan',
                'http://gitlab.com/group',
                '--json-output', 'results.json',
                '--csv-output', 'results.csv'
            ],
            catch_exceptions=False
        )

        # Verify exit code and error message
        assert result.exit_code == 0
        assert "Error saving JSON file: Permission denied" in result.output
        assert "Error saving CSV file: Permission denied" in result.output

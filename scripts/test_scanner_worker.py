#!/usr/bin/env python3
"""Test script for scanner_worker.py standalone execution."""

import sys
import json
import time
import shutil
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime

# Test with this repository itself since we know it exists and works
TEST_REPO = "https://github.com/anthropics/claude-code.git"
TEST_JOB_ID = "test-job-001"
TEST_REPO_INDEX = 0
TEST_REPO_NAME = "claude-code"


def cleanup_test_dir():
    """Clean up test job directory."""
    test_dir = Path("tmp/scan_jobs") / TEST_JOB_ID
    if test_dir.exists():
        shutil.rmtree(test_dir)
        print(f"Cleaned up test directory: {test_dir}")


def check_status_file():
    """Check if status file was created and read it."""
    status_file = Path("tmp/scan_jobs") / TEST_JOB_ID / f"repo_{TEST_REPO_INDEX}.json"

    if not status_file.exists():
        print(f"❌ Status file not found: {status_file}")
        return None

    with open(status_file, 'r') as f:
        status = json.load(f)

    print(f"✅ Status file found: {status_file}")
    print(f"   Status: {status.get('status')}")
    print(f"   Repo: {status.get('repo_name')}")
    print(f"   Started: {status.get('started_at')}")
    print(f"   Last update: {status.get('last_update')}")

    if status.get('errors'):
        print(f"   Errors: {status.get('errors')}")

    if status.get('dependencies_found') is not None:
        print(f"   Dependencies: {status.get('dependencies_found')}")

    return status


def test_scanner_worker():
    """Test the scanner worker subprocess."""
    print("\n" + "="*60)
    print("Testing Scanner Worker Subprocess")
    print("="*60)

    # Clean up any previous test
    cleanup_test_dir()

    # Build command to run scanner worker
    cmd = [
        sys.executable,
        "-m", "dependency_scanner_tool.api.scanner_worker",
        TEST_JOB_ID,
        str(TEST_REPO_INDEX),
        TEST_REPO_NAME,
        TEST_REPO
    ]

    print(f"\nRunning command: {' '.join(cmd)}")
    print(f"Test repository: {TEST_REPO}")
    print("-"*60)

    # Run the subprocess
    try:
        # Start the process
        start_time = time.time()
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        print("Process started, monitoring status file...")

        # Monitor status file while process runs
        last_status = None
        while process.poll() is None:
            time.sleep(2)  # Check every 2 seconds
            status = check_status_file()
            if status and status != last_status:
                print(f"\n[{time.time() - start_time:.1f}s] Status update detected")
                last_status = status

        # Get final output
        stdout, stderr = process.communicate()
        elapsed = time.time() - start_time

        print(f"\n" + "-"*60)
        print(f"Process completed in {elapsed:.1f} seconds")
        print(f"Exit code: {process.returncode}")

        if stdout:
            print(f"\nStdout:\n{stdout}")

        if stderr:
            print(f"\nStderr:\n{stderr}")

        # Check final status
        print("\n" + "-"*60)
        print("Final status check:")
        final_status = check_status_file()

        if final_status:
            if final_status.get('status') == 'completed':
                print("\n✅ SUCCESS: Scanner worker completed successfully")
                return True
            elif final_status.get('status') == 'failed':
                print(f"\n❌ FAILED: Scanner worker failed with error")
                return False
            else:
                print(f"\n⚠️ WARNING: Unexpected final status: {final_status.get('status')}")
                return False
        else:
            print("\n❌ FAILED: No status file found")
            return False

    except Exception as e:
        print(f"\n❌ ERROR running subprocess: {e}")
        return False

    finally:
        # Clean up
        cleanup_test_dir()


def test_error_handling():
    """Test scanner worker error handling with invalid URL."""
    print("\n" + "="*60)
    print("Testing Scanner Worker Error Handling")
    print("="*60)

    # Clean up any previous test
    cleanup_test_dir()

    # Test with invalid URL
    INVALID_URL = "not-a-valid-git-url"

    cmd = [
        sys.executable,
        "-m", "dependency_scanner_tool.api.scanner_worker",
        TEST_JOB_ID,
        str(TEST_REPO_INDEX),
        "invalid-repo",
        INVALID_URL
    ]

    print(f"\nTesting with invalid URL: {INVALID_URL}")
    print("-"*60)

    try:
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )

        print(f"Exit code: {process.returncode}")

        # Should exit with error
        if process.returncode != 0:
            print("✅ Correctly failed with non-zero exit code")

            # Check status file
            status = check_status_file()
            if status and status.get('status') == 'failed':
                print("✅ Status file correctly shows 'failed' status")
                if status.get('errors'):
                    print(f"   Error recorded: {status['errors'][0].get('message')}")
                return True
            else:
                print("❌ Status file doesn't show failed status")
                return False
        else:
            print("❌ Should have failed but exited with 0")
            return False

    except subprocess.TimeoutExpired:
        print("❌ Process timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        cleanup_test_dir()


if __name__ == "__main__":
    print("Scanner Worker Test Suite")
    print("="*60)

    # Test 1: Normal operation
    test1_result = test_scanner_worker()

    # Test 2: Error handling
    test2_result = test_error_handling()

    # Summary
    print("\n" + "="*60)
    print("Test Summary:")
    print(f"  Normal operation: {'✅ PASSED' if test1_result else '❌ FAILED'}")
    print(f"  Error handling: {'✅ PASSED' if test2_result else '❌ FAILED'}")
    print("="*60)

    sys.exit(0 if (test1_result and test2_result) else 1)
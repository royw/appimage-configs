#!/bin/bash
# Run tests for appimage-configs scripts using pytest
#
# Usage:
#   ./tests/run_tests.sh           # Run all tests
#   ./tests/run_tests.sh -v        # Verbose output
#   ./tests/run_tests.sh -k test_name  # Run specific test
#   ./tests/run_tests.sh --cov     # Run with coverage

set -e

# Change to repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

echo "Running tests from: $REPO_ROOT"
echo ""

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo "Error: pytest is not installed"
    echo "Install with: pip install pytest pytest-cov"
    exit 1
fi

# Add scripts and tests to PYTHONPATH for imports
export PYTHONPATH="$REPO_ROOT/scripts:$REPO_ROOT/tests:$PYTHONPATH"

# Run pytest with provided arguments
# Default: run with reasonable verbosity
if [ $# -eq 0 ]; then
    pytest tests/ -v --tb=short
else
    pytest tests/ "$@"
fi

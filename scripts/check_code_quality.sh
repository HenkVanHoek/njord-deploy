#!/bin/bash
# scripts/check_code_quality.sh
# Local code quality runner for NjordDeploy (Python & JavaScript)

# Exit on error
set -e

# Project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "Starting NjordDeploy Code Quality Checks"
echo "=========================================="

PYTHON_FAILED=0

# --- 1. Python Quality Checks ---
echo ""
echo "[1/3] Running Python static analysis and linters..."

if [ -f ".venv/bin/activate" ]; then
    PYTHON_BIN=".venv/bin"
else
    PYTHON_BIN=""
fi

# Run pre-commit checks on all files (this covers black, isort, flake8, mypy, bandit, json, yaml)
if [ -x "${PYTHON_BIN}/pre-commit" ]; then
    echo "Running pre-commit pipeline..."
    # Run pre-commit, allow it to fail so we can still run JS checks and output a final report
    "${PYTHON_BIN}/pre-commit" run --all-files || PYTHON_FAILED=1
else
    echo "pre-commit not found. Running fallback checks..."

    if [ -x "${PYTHON_BIN}/black" ]; then
        echo "Checking black..."
        "${PYTHON_BIN}/black" --check src tests || PYTHON_FAILED=1
    fi

    if [ -x "${PYTHON_BIN}/flake8" ]; then
        echo "Checking flake8..."
        "${PYTHON_BIN}/flake8" src tests || PYTHON_FAILED=1
    fi

    if [ -x "${PYTHON_BIN}/mypy" ]; then
        echo "Checking mypy..."
        "${PYTHON_BIN}/mypy" src tests || PYTHON_FAILED=1
    fi
fi

# --- 2. JavaScript Quality Checks ---
echo ""
echo "[2/3] Running JavaScript linter (ESLint)..."

JS_FAILED=0
TEMP_CONFIG_CREATED=0

# Check if eslint is available
if ! command -v eslint &> /dev/null; then
    echo "WARNING: eslint is not installed globally. Skipping JS checks."
    echo "To install: npm install -g eslint"
else
    # Check if config exists
    if [ ! -f ".eslintrc" ] && [ ! -f ".eslintrc.json" ] && [ ! -f ".eslintrc.js" ]; then
        echo "Creating temporary .eslintrc.json for inspection..."
        TEMP_CONFIG_CREATED=1
        cat <<EOF > .eslintrc.json
{
  "env": {
    "browser": true,
    "es6": true,
    "jquery": true
  },
  "extends": "eslint:recommended",
  "globals": {
    "bootstrap": "readonly",
    "CodeMirror": "readonly",
    "Sortable": "readonly",
    "deletePackage": "writable",
    "updatePackage": "writable"
  },
  "parserOptions": {
    "ecmaVersion": 2020,
    "sourceType": "module"
  },
  "rules": {
    "no-unused-vars": "warn",
    "no-undef": "warn",
    "no-console": "off",
    "require-atomic-updates": "off",
    "no-redeclare": "off"
  }
}
EOF
    fi

    # Find and lint JS files in src
    JS_FILES=$(find src -name "*.js" -not -path "*/node_modules/*" -not -path "*/.venv/*")
    if [ -n "$JS_FILES" ]; then
        echo "Linting JavaScript files..."
        eslint $JS_FILES || JS_FAILED=1
    else
        echo "No JavaScript files found to lint."
    fi

    # Clean up temp config if created
    if [ "$TEMP_CONFIG_CREATED" -eq 1 ]; then
        echo "Cleaning up temporary .eslintrc.json..."
        rm -f .eslintrc.json
    fi
fi

# --- 3. Final Report ---
echo ""
echo "=========================================="
echo "Quality Check Summary"
echo "=========================================="

if [ "$PYTHON_FAILED" = "1" ] || [ "$JS_FAILED" = "1" ]; then
    echo "❌ CODE QUALITY CHECKS FAILED!"
    [ "$PYTHON_FAILED" = "1" ] && echo "  - Python check failures detected."
    [ "$JS_FAILED" = "1" ] && echo "  - JavaScript lint failures detected."
    exit 1
else
    echo "✨ ALL CHECKS PASSED SUCCESSFULLY!"
    exit 0
fi

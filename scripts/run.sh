#!/bin/bash
# Wrapper script to run CLI with the bundled venv Python
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPT_DIR/../.venv/bin/python" "$SCRIPT_DIR/cli.py" "$@"

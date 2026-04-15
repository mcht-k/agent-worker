#!/bin/bash
# Agent Runner — installation script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Agent Runner Setup ==="

# Check Python 3.8+
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 is required but not found"
    exit 1
fi

PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 8 ]; }; then
    echo "ERROR: Python 3.8+ required, found $PY_VERSION"
    exit 1
fi
echo "Python $PY_VERSION OK"

# Install PyYAML
echo "Installing PyYAML..."
pip3 install --quiet pyyaml 2>/dev/null || pip install --quiet pyyaml

# Make entry point executable
chmod +x "$SCRIPT_DIR/agent-runner"

# Symlink to PATH (optional)
if [ "$1" = "--link" ]; then
    LINK_DIR="${2:-$HOME/.local/bin}"
    mkdir -p "$LINK_DIR"
    ln -sf "$SCRIPT_DIR/agent-runner" "$LINK_DIR/agent-runner"
    echo "Linked: $LINK_DIR/agent-runner"
    echo "Make sure $LINK_DIR is in your PATH"
fi

echo ""
echo "Setup complete!"
echo ""
echo "Usage:"
echo "  $SCRIPT_DIR/agent-runner init /path/to/repo   # initialize a repo"
echo "  $SCRIPT_DIR/agent-runner status                # show queue"
echo "  $SCRIPT_DIR/agent-runner run                   # run one cycle"
echo "  $SCRIPT_DIR/agent-runner daemon                # run continuous loop"
echo ""
echo "Or link to PATH:"
echo "  bash $SCRIPT_DIR/setup.sh --link ~/.local/bin"

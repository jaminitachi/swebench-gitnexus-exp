#!/bin/bash
# Setup: Index Django repo with GitNexus for the experiment
# Run this once before the experiment

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DJANGO_DIR="$ROOT_DIR/django_repo"

echo "=== GitNexus Django Index Setup ==="

# Check gitnexus is installed
if ! command -v gitnexus &> /dev/null; then
    echo "ERROR: gitnexus not found. Install with: npm install -g gitnexus"
    exit 1
fi

echo "GitNexus version: $(gitnexus --version 2>/dev/null || echo 'unknown')"

# Clone Django if not exists
if [ ! -d "$DJANGO_DIR" ]; then
    echo "Cloning Django repository..."
    git clone --depth 1 https://github.com/django/django.git "$DJANGO_DIR"
else
    echo "Django repo already exists at $DJANGO_DIR"
fi

# Index with GitNexus
echo "Indexing Django with GitNexus (this may take a few minutes)..."
cd "$DJANGO_DIR"
gitnexus analyze . --force --verbose

echo ""
echo "=== Index Status ==="
gitnexus status

echo ""
echo "Done! GitNexus context files will be generated from this index."
echo "You can now run: python scripts/prepare_dataset.py"

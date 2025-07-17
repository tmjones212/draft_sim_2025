#!/bin/bash

# Sync from WSL to Windows
# Windows path: C:\Users\alaba\source\repos\Python\draft_sim_2025
# WSL path: /mnt/c/Users/alaba/source/repos/Python/draft_sim_2025

SOURCE_DIR="/home/alaba/mock_sim_2025/"
DEST_DIR="/mnt/c/Users/alaba/source/repos/Python/draft_sim_2025/"

echo "Syncing Mock Draft Simulator to Windows..."
echo "From: $SOURCE_DIR"
echo "To: $DEST_DIR"

# Create destination directory if it doesn't exist
mkdir -p "$DEST_DIR"

# Rsync with options:
# -av: archive mode (preserves permissions, timestamps) and verbose
# --delete: delete files in dest that don't exist in source
# --exclude: exclude certain directories/files
rsync -av --delete \
    --exclude='venv/' \
    --exclude='venv_windows/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.git/' \
    --exclude='.idea/' \
    --exclude='.vscode/' \
    --exclude='data/custom_adp.json' \
    --exclude='data/cheat_sheet_tiers.json' \
    --exclude='templates/' \
    "$SOURCE_DIR" "$DEST_DIR"

echo "Sync complete!"
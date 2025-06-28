#!/bin/bash

# Sync from Windows to WSL
# Windows path: C:\Users\alaba\source\repos\Python\draft_sim_2025
# WSL path: /mnt/c/Users/alaba/source/repos/Python/draft_sim_2025

SOURCE_DIR="/mnt/c/Users/alaba/source/repos/Python/draft_sim_2025/"
DEST_DIR="/home/alaba/mock_sim_2025/"

echo "Syncing Mock Draft Simulator from Windows..."
echo "From: $SOURCE_DIR"
echo "To: $DEST_DIR"

# Rsync with options:
# -av: archive mode (preserves permissions, timestamps) and verbose
# --exclude: exclude certain directories/files
rsync -av \
    --exclude='venv/' \
    --exclude='venv_windows/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.git/' \
    --exclude='.idea/' \
    --exclude='.vscode/' \
    "$SOURCE_DIR" "$DEST_DIR"

echo "Sync complete!"
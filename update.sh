#!/usr/bin/env bash

set -euo pipefail
shopt -s nocasematch


REPO_DIR="$(pwd)"
VENV_DIR=".venv"
REQUIREMENTS="requirements.txt"
SERVER_SCRIPT="server"
SLEEP_INTERVAL=30
COMMIT_FILE=".last_commit"
BRANCH="main"
LOG() { echo "$(date '+%Y-%m-%d %H:%M:%S')  $*"; }


get_remote_commit() {
    git -C "$REPO_DIR" fetch --quiet "$BRANCH" >/dev/null 2>&1
    git -C "$REPO_DIR" rev-parse "origin/$BRANCH"
}

SERVER_PID=""
while true; do
    LOG "Checking for updates on https://github.com/06Days/158335---Assignment-1---Pi-Sensor-System"


    git -C "$REPO_DIR" pull --quiet >/dev/null 2>&1 || LOG "Git pull failed"


    NEW_COMMIT=$(get_remote_commit)
    OLD_COMMIT=$(<"$COMMIT_FILE" 2>/dev/null || echo "")

    if [[ "$NEW_COMMIT" == "$OLD_COMMIT" ]]; then
        LOG "No changes – keeping current VENV and server running"
        sleep "$SLEEP_INTERVAL"
        continue
    fi

    LOG "Repository updated – rebuilding environment"
    echo "$NEW_COMMIT" >"$COMMIT_FILE"


    if [[ -d "$VENV_DIR" ]]; then
        LOG "Removing old VENV"
        rm -rf "$VENV_DIR"
    fi
    LOG "Creating new VENV"
    python3 -m venv "$VENV_DIR"

    LOG "Installing dependencies from $REQUIREMENTS"
    "$VENV_DIR/bin/pip" install -r "$REQUIREMENTS"


    if [[ -n "$SERVER_PID" && -e "/proc/$SERVER_PID" ]]; then
        LOG "Stopping existing server (PID $SERVER_PID)…"
        kill "$SERVER_PID"
        wait "$SERVER_PID" 2>/dev/null || true
    fi


    LOG "Launching $SERVER_SCRIPT via uvicorn"

    "$VENV_DIR/bin/uvicorn" "$SERVER_SCRIPT:app" \
        --host 0.0.0.0 --port 8000 &
    SERVER_PID=$!
    LOG "Server started with PID $SERVER_PID"

    sleep "$SLEEP_INTERVAL"
done

#!/usr/bin/env bash

set -euo pipefail
shopt -s nocasematch


REPO_DIR="$(pwd)"
VENV_DIR=".venv"
REQUIREMENTS="requirements.txt"

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
    LOG "Fetching updates..."
    git -C "$REPO_DIR" fetch --quiet origin "$BRANCH"

    NEW_COMMIT=$(git -C "$REPO_DIR" rev-parse "origin/$BRANCH")
    OLD_COMMIT=$(cat "$COMMIT_FILE" 2>/dev/null || echo "")

    if [[ "$NEW_COMMIT" == "$OLD_COMMIT" ]]; then
        # Check if the server is actually still alive
        if [[ -n "$SERVER_PID" ]] && ! kill -0 "$SERVER_PID" 2>/dev/null; then
            LOG "Server died unexpectedly! Restarting..."
        else
            LOG "No changes – keeping current VENV and server running"
            sleep "$SLEEP_INTERVAL"
            continue
        fi
    fi

    LOG "Changes detected ($OLD_COMMIT -> $NEW_COMMIT). Updating..."
    git -C "$REPO_DIR" pull --quiet origin "$BRANCH"
    echo "$NEW_COMMIT" > "$COMMIT_FILE"


    if [[ -n "$SERVER_PID" ]]; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi


    "$VENV_DIR/bin/uvicorn" server:app \
        --host 0.0.0.0 --port 8000 \
        --app-dir "$REPO_DIR" &
    SERVER_PID=$!

    sleep "$SLEEP_INTERVAL"
done

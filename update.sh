REPO_DIR=$(pwd)
VENV_DIR=".venv"
REQUIREMENTS="requirements.txt"
SERVER_SCRIPT="server.py"
SLEEP_INTERVAL=30
# for debug
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S')  $*"
}

SERVER_PID=""
while true; do
    log "https://github.com/06Days/158335---Assignment-1---Pi-Sensor-System"
    git -C "$REPO_DIR" pull --quiet
    if [ $? -ne 0 ]; then
        log "Failed"
    else
        log "Repository updated."
    fi

    if [ -d "$VENV_DIR" ]; then
        log "Rebuilding VENV"
        rm -rf "$VENV_DIR"
    fi
    log "Setting up VENV for the first time"
    python3 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        log "Failed to make virtual environment"
        sleep "$SLEEP_INTERVAL"
        continue
    fi
    log "Installing dependencies from $REQUIREMENTS ..."
    "$VENV_DIR/bin/pip" install -r "$REQUIREMENTS"
    if [ $? -ne 0 ]; then
        log "Could not install dependencies"
        sleep "$SLEEP_INTERVAL"
        continue
    fi

    if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
        log "Stopping existing server (PID $SERVER_PID)..."
        kill "$SERVER_PID"
        wait "$SERVER_PID" 2>/dev/null
    fi

    log "Starting $SERVER_SCRIPT ..."
    "uvicorn server:app --host 0.0.0.0 --port 8000" &
    SERVER_PID=$!
    log "Server started with PID $SERVER_PID."

    sleep "$SLEEP_INTERVAL"
done

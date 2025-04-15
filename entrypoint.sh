#!/bin/env bash

echo "Initializing Globus Container..."

# Set up directories and permissions
mkdir -p /home/gridftp/globus_config /home/gridftp/data
chmod -R 777 /home/gridftp/globus_config /home/gridftp/data

# Check if optional mode is enabled
if [ "$GLOBUS_OPTIONAL_MODE" = "true" ]; then
    echo "Globus is running in optional mode. External connections can be configured later."
else
    echo "Globus is starting normally..."
    if [ "$START_GLOBUS" = "true" ]; then
        su gridftp -c "cd /home/gridftp && source ./globus-connect-personal.sh"
    else
        WATCHED_FILE="/home/gridftp/setup_key.txt"
        HANDLE_SCRIPT="initialization.sh"
        last_modified=""

        watch_file_stat() {
        echo "Watching $WATCHED_FILE using stat polling..."
        while true; do
            if [[ -f "$WATCHED_FILE" ]]; then
            current_modified=$(stat -c %Y "$WATCHED_FILE")
            if [[ "$current_modified" != "$last_modified" ]]; then
                echo "[$(date)] Detected change in $WATCHED_FILE"
                last_modified=$current_modified     

                # Read key values
                KEY1=$(grep "^KEY1=" "$WATCHED_FILE" | cut -d '=' -f2)
                KEY2=$(grep "^KEY2=" "$WATCHED_FILE" | cut -d '=' -f2)

                echo "Extracted KEY1=$KEY1"
                echo "Extracted KEY2=$KEY2"
                # Run your script with these keys as env vars
                sleep 10
                echo "Running initialization.sh"
                su gridftp -c "cd /home/gridftp &&  KEY1=$KEY1 KEY2=$KEY2 source ./$HANDLE_SCRIPT"
            fi
            fi
            sleep 2  # polling interval (adjust if needed)
        done
        }

        # Start watcher in the background
        watch_file_stat &

        # Start the FastAPI app (main app)
        echo "Starting FastAPI app..."

        su gridftp -c "cd /home/gridftp && ls &&  python3 run_with_ngrok.py"
    fi
fi

echo "Globus setup complete."

# Keep container running
tail -f /dev/null

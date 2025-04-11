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
                su gridftp -c "cd /home/gridftp && ls &&  KEY1=$KEY1 KEY2=$KEY2 source ./$HANDLE_SCRIPT"
            fi
        fi
        sleep 2 # polling interval (adjust if needed)
    done
}

# Start watcher in the background
watch_file_stat &

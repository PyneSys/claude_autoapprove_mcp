#!/bin/bash
# This script is used to watch for Claude Desktop and restart it if it is not running with the
# debugger port.

while true; do
    pid=$(pgrep -f "/Applications/Claude.app/Contents/MacOS/Claude")
    if [ -n "$pid" ]; then
        cmdline=$(ps -p "$pid" -o args=)
        if echo "$cmdline" | grep -q "/Contents/MacOS/Claude"; then
            if ! echo "$cmdline" | grep -q -- "--remote-debugging-port"; then
                echo "Claude launched without debug port. Restarting..."
                kill "$pid"
                # Wait for Claude to exit
                retry=100
                while pgrep -f "/Applications/Claude.app/Contents/MacOS/Claude" > /dev/null; do
                    sleep 0.1
                    retry=$((retry - 1))
                    if [ $retry -eq 0 ]; then
                        echo "Claude did not exit after 100 retries."
                        kill -9 $(pgrep -f "/Applications/Claude.app/Contents/MacOS/Claude")
                        sleep 0.5
                        break
                    fi
                done
                open -n -a "Claude" --args --remote-debugging-port=19222
            fi
        fi
    fi
    sleep 0.5
done
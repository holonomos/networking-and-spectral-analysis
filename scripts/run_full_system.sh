#!/bin/bash
# Run the full NetWatch system: 4 racks × 8 servers = 32 agents

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

export PYTHONPATH="$PROJECT_ROOT/src"

echo "=== Starting NetWatch Full System Test ==="
echo "4 Rack Controllers + 32 Server Agents"
echo ""

PIDS=()

cleanup() {
    echo ""
    echo "=== Shutting down all processes ==="
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    wait
    echo "All processes stopped."
}
trap cleanup EXIT INT TERM

# Start 4 Rack Controllers (each on different ports)
for rack_id in 0 1 2 3; do
    port=$((9999 + rack_id))
    echo "Starting Rack Controller $rack_id on port $port..."
    RACK_ID=$rack_id UDP_LISTEN_PORT=$port \
        python3 -m netwatch.rack_controller &
    PIDS+=($!)
    sleep 0.2
done

echo ""
sleep 1

# Start 8 servers per rack (32 total)
for rack_id in 0 1 2 3; do
    port=$((9999 + rack_id))
    for server_id in 0 1 2 3 4 5 6 7; do
        echo "Starting Server Agent rack=$rack_id server=$server_id -> port $port"
        RACK_ID=$rack_id SERVER_ID=$server_id \
            RACK_CONTROLLER_PORT=$port \
            python3 -m netwatch.server_agent &
        PIDS+=($!)
        sleep 0.05
    done
done

echo ""
echo "=== All 36 processes started ==="
echo "Press Ctrl+C to stop all processes"
echo ""

# Wait for all background jobs
wait

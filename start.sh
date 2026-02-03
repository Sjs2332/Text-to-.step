#!/bin/bash
# Start Docker Desktop (macOS/Linux) and launch the application

# Start Docker if not running
if ! docker ps > /dev/null 2>&1; then
    echo "Starting Docker Desktop..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open -a Docker
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo systemctl start docker 2>/dev/null || service docker start 2>/dev/null || echo "Please start Docker Desktop manually"
    fi
    
    # Wait for Docker to be ready
    echo "Waiting for Docker to start..."
    for i in {1..30}; do
        if docker ps > /dev/null 2>&1; then
            echo "Docker is ready!"
            break
        fi
        sleep 1
    done
fi

# Run setup and start
npm run setup && npm run dev:all

#!/bin/bash

# Ensure the script exits on any error
set -e

# Navigate to the project root directory on the Pi.
# This ensures that relative paths for config, etc., work correctly.
cd "$(dirname "$0")/.."

# --- Configuration ---
IMAGE_NAME="piselfhosting-utils"
# This is the crucial change: We now use the absolute, correct path for the live data
DASHY_LIVE_DATA_PATH="/opt/piselfhosting/data/dashy"
HOST_IP=$(hostname -I | awk '{print $1}')

if [ -z "$HOST_IP" ]; then
    echo "Error: Could not automatically determine the host IP address."
    exit 1
fi

echo "Using host IP address: $HOST_IP"
echo "Targeting LIVE config directory: ${DASHY_LIVE_DATA_PATH}"

# --- Script Logic ---
# Check if the utility image exists. If not, build it.
if [[ "$(docker images -q ${IMAGE_NAME}:latest 2> /dev/null)" == "" ]]; then
  echo "Utility image '${IMAGE_NAME}' not found. Building now..."
  docker build -t ${IMAGE_NAME} .
fi

# Check which utility script to run
if [ -z "$1" ]; then
    echo "Usage: $0 <utility_name> [args...]"
    exit 1
fi

UTILITY_NAME=$1
shift

echo "Running utility: ${UTILITY_NAME}"

# Run the container, mounting the LIVE config directory from /opt/
docker run --rm \
  -v "$(pwd)/config:/app/config:ro" \
  -v "${DASHY_LIVE_DATA_PATH}:/app/data/dashy:rw" \
  -v "$(pwd)/selected_components.txt:/app/selected_components.txt:ro" \
  ${IMAGE_NAME} \
  python "src/utils/${UTILITY_NAME}.py" "$HOST_IP" "$@"

echo "Utility '${UTILITY_NAME}' executed successfully."

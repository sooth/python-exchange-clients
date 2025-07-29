#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start the backend
echo "Starting backend with environment variables..."
echo "BITUNIX_API_KEY: ${BITUNIX_API_KEY:0:10}..."

cd /Users/dmalson/python-exchange-clients/backend
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
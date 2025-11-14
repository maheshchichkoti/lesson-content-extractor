#!/bin/bash
# Production startup script for Linux/Mac

echo "========================================"
echo "Starting Lesson Content Extractor"
echo "========================================"

# Activate virtual environment
source .venv/bin/activate

# Start API server in background
echo "Starting API server on port 8000..."
python -m uvicorn api:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# Wait for API to start
sleep 3

# Start Zoom fetcher worker
echo "Starting Zoom fetcher worker..."
python fetcher.py &
FETCHER_PID=$!

# Wait
sleep 2

# Start Zoom processor worker
echo "Starting Zoom processor worker..."
python worker.py &
WORKER_PID=$!

echo ""
echo "========================================"
echo "All services started!"
echo "========================================"
echo "API Server: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo "API PID: $API_PID"
echo "Fetcher PID: $FETCHER_PID"
echo "Worker PID: $WORKER_PID"
echo ""
echo "Press Ctrl+C to stop all services..."

# Trap Ctrl+C and kill all processes
trap "echo 'Stopping all services...'; kill $API_PID $FETCHER_PID $WORKER_PID; exit" INT

# Wait for all background processes
wait

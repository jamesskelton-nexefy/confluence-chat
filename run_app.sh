#!/bin/bash

# Start the FastAPI backend
echo "Starting FastAPI backend..."
uvicorn api:app --reload &

# Wait a bit for the backend to start
sleep 2

# Start the React frontend
echo "Starting React frontend..."
cd frontend && npm start 
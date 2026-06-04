#!/bin/bash

# Start the FastAPI backend in the background
echo "Starting FastAPI backend on port 8000..."
uvicorn app.api:app --host 127.0.0.1 --port 8000 &

# Wait briefly for backend startup
sleep 3

# Start the Streamlit dashboard in the foreground on port 7860
echo "Starting Streamlit dashboard on port 7860..."
streamlit run dashboard/app.py --server.port 7860 --server.address 0.0.0.0

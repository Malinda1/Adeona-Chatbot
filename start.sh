#!/usr/bin/env bash
set -e


# Install dependencies (optional if already installed)
pip install -r /Users/pasindumalinda/AI_projects/Agent_02/adeona-chatbot/backend/requirements.txt

# Set the port
export PORT=8000

# Start FastAPI with uvicorn
uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT --reload

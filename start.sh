
#!/usr/bin/env bash
set -e
# Install dependencies

pip install -r /Users/pasindumalinda/AI_projects/Agent_02/adeona-chatbot/backend/requirements.txt

# Start FastAPI with uvicorn
exec export PORT=8000
exec uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT

cat << 'EOF' > start.sh

#!/usr/bin/env bash
set -e
# Install dependencies

pip install -r requirements.txt

# Start FastAPI with uvicorn
export PORT=8000
exec uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT

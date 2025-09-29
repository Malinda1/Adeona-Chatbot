cat << 'EOF' > start.sh

#!/usr/bin/env bash
set -e
# Install dependencies

pip install -r requirements.txt

# Start FastAPI with uvicorn
exec uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1
EOF

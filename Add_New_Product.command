#!/bin/zsh
cd "$(dirname "$0")"

git pull

source venv/bin/activate

# Load local secrets/config without committing them.
# Prefer .env.local; fall back to .env.
if [ -f ".env.local" ]; then
  set -a
  source .env.local
  set +a
elif [ -f ".env" ]; then
  set -a
  source .env
  set +a
fi

# Run without debug/reloader so the script continues cleanly
export FLASK_ENV=production
export FLASK_DEBUG=0

# Stop any stale process already serving on port 5000.
existing_pids=("${(@f)$(lsof -t -nP -iTCP:5000 -sTCP:LISTEN 2>/dev/null)}")
if [ ${#existing_pids[@]} -gt 0 ]; then
  kill "${existing_pids[@]}" 2>/dev/null
  sleep 1
fi

python3 admin_app.py > admin.log 2>&1 &

sleep 1
open "http://127.0.0.1:5000"

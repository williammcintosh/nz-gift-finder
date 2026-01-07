#!/bin/zsh
cd "$(dirname "$0")"

git pull

source venv/bin/activate

# Run without debug/reloader so the script continues cleanly
export FLASK_ENV=production
export FLASK_DEBUG=0

python3 admin_app.py > admin.log 2>&1 &

sleep 1
open "http://127.0.0.1:5000"

#!/bin/bash
set -e

mkdir -p "${STORAGE_DIR:-/app/storage}"

# Start small web service for Render port binding / uptime pings
# (You can use a cron/uptime service to hit /ping periodically.)
exec_env_port="${PORT:-10000}"

gunicorn -w 1 -k gthread -t 120 -b 0.0.0.0:"$exec_env_port" app.web:app &

# Start the Telegram bot
python -m app.bot

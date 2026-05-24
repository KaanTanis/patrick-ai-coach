#!/usr/bin/env bash
set -euo pipefail

if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
  echo "Set TELEGRAM_BOT_TOKEN in .env"
  exit 1
fi

WEBHOOK_URL="${WEBHOOK_BASE_URL:-http://localhost:8000}/webhook/telegram"
SECRET="${TELEGRAM_WEBHOOK_SECRET:-}"

echo "Starting ngrok tunnel..."
ngrok http 8000 &
NGROK_PID=$!
sleep 2

PUBLIC_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data['tunnels'][0]['public_url'])
")

echo "Public URL: $PUBLIC_URL"
export WEBHOOK_BASE_URL="$PUBLIC_URL"

curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -d "url=${PUBLIC_URL}/webhook/telegram" \
  ${SECRET:+-d "secret_token=${SECRET}"}

echo ""
echo "Webhook set. Press Ctrl+C to stop ngrok."
wait $NGROK_PID

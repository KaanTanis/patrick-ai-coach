# Personal AI Self-Improvement Assistant (tbot)

A private Telegram-based AI coach for motivation, discipline, diet tracking, smoking cessation, workout consistency, and behavioral pattern analysis.

## Stack

- **Python 3.12** + FastAPI + aiogram 3
- **PostgreSQL 16** + pgvector
- **Redis** + ARQ (background jobs)
- **OpenAI** (gpt-4o, gpt-4o-mini, embeddings, vision)
- **Vite + React** dashboard (optional)

## Quick Start

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env with your TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, ALLOWED_TELEGRAM_IDS
```

### 2. Start services

```bash
docker compose up -d postgres redis
pip install -e ".[dev]"
alembic upgrade head
python scripts/seed_personalities.py
```

### 3. Run the app

```bash
uvicorn app.main:app --reload
arq app.jobs.worker.WorkerSettings  # separate terminal
```

### 4. Set Telegram webhook

```bash
# Production
curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://your-domain.com/webhook/telegram&secret_token=<SECRET>"

# Local dev with ngrok
chmod +x scripts/dev_webhook.sh
./scripts/dev_webhook.sh
```

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome and setup |
| `/checkin` | Daily 8-metric check-in |
| `/insights` | Behavioral pattern insights |
| `/personality <key>` | Switch coach style (stoic, therapist, coach, jungian, companion) |
| `/relapse` | Report setback (shame-free recovery) |
| `/food` | Log meal via photo |
| `/export` | Download all data as JSON |
| `/forget [type]` | Clear AI memories |

Free-form chat uses the full AI orchestrator with memory retrieval.

## Dashboard

```bash
cd dashboard && npm install && npm run dev
# API proxied to localhost:8000 — enter API_KEY from .env
```

Build for production:

```bash
cd dashboard && npm run build
# FastAPI serves dashboard/dist when present
```

## Architecture

```
Telegram → FastAPI webhook → aiogram handlers → AI Orchestrator
                                                      ↓
                              Memory Retriever ← PostgreSQL + pgvector
                                                      ↓
                              Prompt Composer → OpenAI → Response
                                                      ↓
                              ARQ jobs (extraction, insights, summaries)
```

## Background Jobs

| Job | Schedule |
|-----|----------|
| Session summarization | Every 6h |
| Behavioral analysis | Daily 06:00 |
| Check-in nudge | Daily (configurable hour) |
| Memory importance decay | Weekly |
| Weekly reflection | Sunday 18:00 |
| Conversation cleanup | Daily 04:00 |

## Security

- Single-user allowlist via `ALLOWED_TELEGRAM_IDS`
- Webhook secret token validation
- Dashboard protected by `API_KEY` header
- Self-hosted — your data stays on your infrastructure

## License

Private personal use.

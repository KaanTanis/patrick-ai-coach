# Personal AI Self-Improvement Assistant (tbot)

A private Telegram-based AI coach for motivation, discipline, diet tracking, workout consistency, Jung/Stoic/CBT reflection, and behavioral pattern analysis. Goals and reminders come from what you tell the bot — not from built-in habit trackers.

## Stack

- **Python 3.12** + FastAPI + aiogram 3
- **PostgreSQL 16** + pgvector
- **Redis** + ARQ (background jobs)
- **OpenAI** (gpt-4o, gpt-4o-mini, embeddings, vision)
- **Vite + React** dashboard (optional)

## Quick Start

```bash
cp .env.example .env
docker compose up -d postgres redis
pip install -e ".[dev]"
alembic upgrade head
python scripts/seed_personalities.py
```

```bash
uvicorn app.main:app --reload
arq app.jobs.worker.WorkerSettings  # separate terminal
```

See [LOCAL_START.md](LOCAL_START.md) for ngrok workflow.

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/basla` | Welcome and setup |
| `/rapor` | Adaptive daily check-in (questions vary by context) |
| `/durum` | Behavioral insights |
| `/mod <key>` | Personality mode (8 options) |
| `/lens jung\|stoic\|psych` | One-shot lens for next message |
| `/ruya`, `/golge`, `/sabah`, `/aksam`, `/dusunce`, `/duygu` | Philosophy / CBT flows |
| `/analiz` | Deep multi-lens analysis |
| `/serbest ac\|kapa` | Free mode (longer replies, no nudges) |
| `/zor` | Report a hard moment or setback |
| `/hatirla` | What the bot remembers (goals and reminders included) |
| `/veriler`, `/unut`, `/sil` | Export, forget, erase |
| `/iptal` | Cancel active flow |

During `/rapor` or chat, say **"bu kadar soru yeter"** to save partial answers and stop.

Free-form chat uses memory retrieval. Tell the bot your goals and reminders — it remembers and may nudge you later.

## Personality Modes (8)

| Key | Focus |
|-----|-------|
| `companion` | Warm daily companion |
| `coach` | Action-oriented coaching |
| `stoic` / `stoic_praxis` | Stoic philosophy and practice |
| `jungian` / `jung_shadow` | Jungian symbolic exploration |
| `therapist` / `psych_cbt` | CBT-informed support (not clinical therapy) |

## Architecture

```
Telegram → FastAPI → aiogram → AI Orchestrator → OpenAI
                    ↓
              PostgreSQL + pgvector (memories, check-ins)
                    ↓
              ARQ jobs (insights, reminders, summaries)
```

## License

Private personal use.

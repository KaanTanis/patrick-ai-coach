# tbot — İlk Kurulum

Bu rehber projeyi sıfırdan localhost + ngrok ortamına kurmak içindir.

## Gereksinimler

| Araç | Sürüm | Kontrol |
|------|-------|---------|
| Python | 3.12+ | `python3 --version` |
| Docker | güncel | `docker compose version` |
| ngrok | hesap + auth | `ngrok version` |
| Git | — | `git --version` |

Opsiyonel: dashboard için Node.js 20+

---

## 1. Repoyu al

```bash
git clone <repo-url> tbot
cd tbot
```

---

## 2. Python ortamı

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

---

## 3. Ortam değişkenleri

```bash
cp .env.example .env
```

`.env` dosyasını düzenle. **Localhost için kritik alanlar:**

```env
ENV=development

TELEGRAM_BOT_TOKEN=          # @BotFather
TELEGRAM_WEBHOOK_SECRET=       # rastgele uzun string (örn. openssl rand -hex 32)
ALLOWED_TELEGRAM_IDS=123456789 # kendi Telegram user ID'n
OPENAI_API_KEY=sk-...

# Host'tan çalıştırırken localhost kullan (postgres değil!)
DATABASE_URL=postgresql+asyncpg://tbot:tbot@localhost:5432/tbot
REDIS_URL=redis://localhost:6379/0

API_KEY=guclu-bir-anahtar
WEBHOOK_BASE_URL=http://localhost:8000
USER_TIMEZONE=Europe/Istanbul

# Async webhook açık — worker şart
ASYNC_WEBHOOK=true
```

Telegram user ID öğrenmek için: [@userinfobot](https://t.me/userinfobot)

---

## 4. Veritabanı ve Redis (Docker)

```bash
docker compose up -d postgres redis
```

Kontrol:

```bash
docker compose ps
# postgres ve redis "healthy" olmalı
```

---

## 5. Veritabanı migration ve seed

```bash
source .venv/bin/activate
alembic upgrade head
python scripts/seed_personalities.py
```

---

## 6. ngrok kurulumu (bir kez)

1. [ngrok.com](https://ngrok.com) hesabı aç
2. Auth token ekle:

```bash
ngrok config add-authtoken <TOKEN>
```

---

## 7. İlk çalıştırma doğrulaması

3 ayrı terminal aç (detay: [LOCAL_START.md](LOCAL_START.md)):

**Terminal 1 — API**
```bash
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — Worker** (async webhook + arka plan işleri)
```bash
source .venv/bin/activate
arq app.jobs.worker.WorkerSettings
```

**Terminal 3 — ngrok + webhook**
```bash
source .venv/bin/activate
set -a && source .env && set +a
chmod +x scripts/dev_webhook.sh
./scripts/dev_webhook.sh
```

Telegram'da bota `/basla` yaz. Yanıt geliyorsa kurulum tamam.

---

## 8. Dashboard (opsiyonel)

```bash
cd dashboard
npm install
npm run dev
```

Tarayıcı: `http://localhost:5173` — API key olarak `.env` içindeki `API_KEY` değerini gir.

---

## Sık karşılaşılan sorunlar

### Bot yanıt vermiyor
- 3 süreç çalışıyor mu? (uvicorn, worker, ngrok)
- ngrok URL değiştiyse webhook'u yeniden kur (`dev_webhook.sh`)
- `ALLOWED_TELEGRAM_IDS` doğru mu?

### `relation does not exist` / tablo yok
```bash
alembic upgrade head
```

### DB bağlantı hatası
`.env` içinde `DATABASE_URL` host'u `localhost` olmalı (Docker dışında çalışırken).

### Worker heartbeat uyarısı
Worker çalışmıyorsa `/health/ready` worker'ı "stale" gösterir. Terminal 2'yi başlat.

---

## Production (docker-compose.prod.yml)

1. `.env` içinde `ENV=production`, güçlü `API_KEY`, `TELEGRAM_WEBHOOK_SECRET` ayarla.
2. Sunucuda TLS için reverse proxy (Caddy/nginx) kullan; webhook URL `https://domain/webhook/telegram`.
3. İlk deploy sonrası:
   ```bash
   docker compose -f docker-compose.prod.yml exec app alembic upgrade head
   docker compose -f docker-compose.prod.yml exec app python scripts/seed_personalities.py
   ```
4. Yedekleme: `scripts/backup.sh` cron ile günlük çalıştır (pg_dump + photos).
5. Dashboard: image build aşamasında derlenir; `/` üzerinden API key ile erişilir.
6. API rate limit: `/api/*` için dakikada 120 istek (Redis tabanlı).

---

## Sonraki adımlar

Günlük kullanım için: **[LOCAL_START.md](LOCAL_START.md)**

Production sunucu için: README içindeki `docker-compose.prod.yml` bölümü.

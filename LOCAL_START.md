# tbot — Hızlı Başlat (Local + ngrok)

Kurulum tamamlandıysa her oturumda yapılacaklar. 3 terminal yeterli.

---

## Ön kontrol (30 saniye)

```bash
cd /path/to/tbot
docker compose ps          # postgres + redis "Up" / healthy
source .venv/bin/activate
```

Redis/Postgres kapalıysa:

```bash
docker compose up -d postgres redis
```

---

## Terminal 1 — API

```bash
cd /path/to/tbot
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Beklenen: `Application startup complete`

---

## Terminal 2 — Worker

```bash
cd /path/to/tbot
source .venv/bin/activate
arq app.jobs.worker.WorkerSettings
```

Beklenen: worker logları, `worker.started`

> `ASYNC_WEBHOOK=true` iken worker olmadan bot mesajları işlemez.

---

## Terminal 3 — ngrok + Telegram webhook

```bash
cd /path/to/tbot
source .venv/bin/activate
set -a && source .env && set +a
./scripts/dev_webhook.sh
```

Script ngrok tünelini açar ve Telegram webhook'unu otomatik ayarlar.

**ngrok her yeniden başladığında URL değişir** — bu scripti tekrar çalıştır.

Alternatif (manuel):

```bash
ngrok http 8000
# ngrok URL'ini kopyala, örn. https://abc123.ngrok-free.app

curl "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=https://abc123.ngrok-free.app/webhook/telegram" \
  -d "secret_token=<TELEGRAM_WEBHOOK_SECRET>"
```

---

## Sağlık kontrolü

```bash
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

Telegram'da: `/basla` veya kısa bir mesaj gönder.

---

## Dashboard (istersen)

Ayrı terminal:

```bash
cd dashboard && npm run dev
```

---

## Durdurma

| Terminal | Nasıl |
|----------|-------|
| uvicorn | `Ctrl+C` |
| worker | `Ctrl+C` |
| ngrok | `Ctrl+C` |
| Docker | `docker compose stop postgres redis` |

Verileri silmeden durdurmak için `stop` yeterli. Bir sonraki açılışta `docker compose up -d postgres redis`.

---

## Hızlı sorun giderme

| Belirti | Çözüm |
|---------|-------|
| Bot sessiz | Worker çalışıyor mu? ngrok webhook güncel mi? |
| 403 webhook | `.env` içindeki `TELEGRAM_WEBHOOK_SECRET` ile setWebhook aynı mı? |
| Erişim reddedildi | `ALLOWED_TELEGRAM_IDS` senin ID'n mi? |
| DB hatası | `docker compose up -d postgres redis` |
| Kod değişti, garip davranış | uvicorn `--reload` otomatik yeniler; worker'ı da restart et |

---

## İlk kurulum yapılmadıysa

→ [INSTALL.md](INSTALL.md)

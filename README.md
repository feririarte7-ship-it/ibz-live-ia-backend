# Backend (FastAPI)

Minimal backend API mounted on top of your existing Supabase-based frontend.

## 1) Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 2) Run in development (Uvicorn)

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 3) Run in production-like mode (Gunicorn + Uvicorn workers)

```bash
cd backend
source .venv/bin/activate
gunicorn app.main:app -c gunicorn_conf.py
```

## 4) Validate endpoints

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/ping
```

Expected responses:

- `{"status":"ok"}`
- `{"message":"pong"}`

# Seed workflow

This folder contains a safe, repeatable seed flow for the Supabase catalog tables.

## Files

- `input/*.csv`: source templates to fill with real data.
- `seed.py`: upsert loader with FK mapping.
- `validate_seed.py`: post-load checks.

## 1) Prepare environment

From `backend/.env`, ensure:

- `SUPABASE_URL` (or `VITE_SUPABASE_URL`)
- `SUPABASE_SERVICE_ROLE_KEY`

## 2) Fill CSV files

Complete these templates:

- `input/discotecas.csv`
- `input/eventos.csv`
- `input/evento_djs.csv`
- `input/playas.csv`
- `input/restaurantes.csv`
- `input/transportes_vip.csv`

Notes:

- Use stable, unique slugs.
- `eventos.csv` uses `discoteca_slug`.
- `evento_djs.csv` uses `evento_slug`.
- `metadata` accepts JSON (for example: `{"source":"manual"}`), or leave empty.

## 3) Run seed

```bash
cd backend
source .venv/bin/activate
python seed/seed.py
```

The script is idempotent:

- Upsert by `slug` for catalog tables
- Upsert by `(evento_id, set_order)` for `evento_djs`

## 4) Validate

```bash
cd backend
source .venv/bin/activate
python seed/validate_seed.py
```

Optional minimums can be overridden with environment variables:

- `SEED_MIN_DISCOTECAS` (default `5`)
- `SEED_MIN_PLAYAS` (default `15`)
- `SEED_MIN_EVENTOS` (default `1`)
- `SEED_MIN_EVENTO_DJS` (default `1`)
- `SEED_MIN_RESTAURANTES` (default `1`)
- `SEED_MIN_TRANSPORTES_VIP` (default `1`)

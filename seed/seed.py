import csv
import json
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
BATCH_SIZE = 500


def _load_env() -> tuple[str, str]:
    env_path = BASE_DIR.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()

    supabase_url = os.getenv("SUPABASE_URL") or os.getenv("VITE_SUPABASE_URL")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not service_role_key:
        raise RuntimeError(
            "Missing SUPABASE_URL (or VITE_SUPABASE_URL) and/or SUPABASE_SERVICE_ROLE_KEY."
        )
    return supabase_url.rstrip("/"), service_role_key


def _headers(service_role_key: str, count: bool = False) -> dict[str, str]:
    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Content-Type": "application/json",
    }
    if count:
        headers["Prefer"] = "count=exact"
    return headers


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def _as_bool(value: Any) -> Any:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text == "":
        return None
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return value


def _as_float(value: Any) -> Any:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    return float(text)


def _as_int(value: Any) -> Any:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    return int(text)


def _as_json(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    text = str(value).strip()
    if text == "":
        return {}
    return json.loads(text)


def _clean_common(row: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in row.items():
        if value is None:
            cleaned[key] = None
            continue
        text = str(value).strip()
        cleaned[key] = None if text == "" else text

    if "active" in cleaned:
        cleaned["active"] = _as_bool(cleaned.get("active"))
        if cleaned["active"] is None:
            cleaned["active"] = True

    if "covers_island" in cleaned:
        cleaned["covers_island"] = _as_bool(cleaned.get("covers_island"))
        if cleaned["covers_island"] is None:
            cleaned["covers_island"] = True

    if "has_parking" in cleaned:
        cleaned["has_parking"] = _as_bool(cleaned.get("has_parking"))
    if "has_beach_clubs" in cleaned:
        cleaned["has_beach_clubs"] = _as_bool(cleaned.get("has_beach_clubs"))
    if "family_friendly" in cleaned:
        cleaned["family_friendly"] = _as_bool(cleaned.get("family_friendly"))
    if "is_headliner" in cleaned:
        cleaned["is_headliner"] = _as_bool(cleaned.get("is_headliner"))
        if cleaned["is_headliner"] is None:
            cleaned["is_headliner"] = False

    for numeric_key in ("latitude", "longitude", "price_from", "price_to"):
        if numeric_key in cleaned:
            cleaned[numeric_key] = _as_float(cleaned.get(numeric_key))

    if "set_order" in cleaned:
        cleaned["set_order"] = _as_int(cleaned.get("set_order"))
        if cleaned["set_order"] is None:
            cleaned["set_order"] = 1

    if "metadata" in cleaned:
        cleaned["metadata"] = _as_json(cleaned.get("metadata"))

    return cleaned


def _request(
    session: requests.Session,
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    json_payload: Any = None,
) -> requests.Response:
    response = session.request(method, url, params=params, json=json_payload, timeout=60)
    if response.status_code >= 400:
        raise RuntimeError(f"HTTP {response.status_code} {url}: {response.text}")
    return response


def _upsert_rows(
    session: requests.Session,
    base_url: str,
    table: str,
    rows: list[dict[str, Any]],
    on_conflict: str,
) -> int:
    if not rows:
        return 0

    endpoint = f"{base_url}/rest/v1/{table}"
    total = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        params = {"on_conflict": on_conflict}
        session.headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
        _request(session, "POST", endpoint, params=params, json_payload=batch)
        total += len(batch)
    return total


def _slug_map(session: requests.Session, base_url: str, table: str) -> dict[str, str]:
    endpoint = f"{base_url}/rest/v1/{table}"
    response = _request(
        session,
        "GET",
        endpoint,
        params={"select": "id,slug", "limit": 10000},
    )
    rows = response.json()
    return {r["slug"]: r["id"] for r in rows if r.get("slug") and r.get("id")}


def _seed_simple_table(
    session: requests.Session,
    base_url: str,
    filename: str,
    table: str,
) -> int:
    path = INPUT_DIR / filename
    source_rows = _read_csv_rows(path)
    rows = [_clean_common(row) for row in source_rows]
    return _upsert_rows(session, base_url, table, rows, on_conflict="slug")


def _seed_eventos(session: requests.Session, base_url: str) -> int:
    path = INPUT_DIR / "eventos.csv"
    source_rows = _read_csv_rows(path)
    if not source_rows:
        return 0

    discotecas_by_slug = _slug_map(session, base_url, "discotecas")
    rows: list[dict[str, Any]] = []
    missing_discotecas: set[str] = set()

    for raw_row in source_rows:
        row = _clean_common(raw_row)
        discoteca_slug = row.pop("discoteca_slug", None)
        if not discoteca_slug:
            raise RuntimeError(f"eventos.csv row missing discoteca_slug: {raw_row}")
        discoteca_id = discotecas_by_slug.get(discoteca_slug)
        if not discoteca_id:
            missing_discotecas.add(discoteca_slug)
            continue
        row["discoteca_id"] = discoteca_id
        rows.append(row)

    if missing_discotecas:
        missing = ", ".join(sorted(missing_discotecas))
        raise RuntimeError(
            f"eventos.csv references unknown discoteca_slug values: {missing}"
        )

    return _upsert_rows(session, base_url, "eventos", rows, on_conflict="slug")


def _seed_evento_djs(session: requests.Session, base_url: str) -> int:
    path = INPUT_DIR / "evento_djs.csv"
    source_rows = _read_csv_rows(path)
    if not source_rows:
        return 0

    eventos_by_slug = _slug_map(session, base_url, "eventos")
    rows: list[dict[str, Any]] = []
    missing_eventos: set[str] = set()

    for raw_row in source_rows:
        row = _clean_common(raw_row)
        evento_slug = row.pop("evento_slug", None)
        if not evento_slug:
            raise RuntimeError(f"evento_djs.csv row missing evento_slug: {raw_row}")
        evento_id = eventos_by_slug.get(evento_slug)
        if not evento_id:
            missing_eventos.add(evento_slug)
            continue
        row["evento_id"] = evento_id
        rows.append(row)

    if missing_eventos:
        missing = ", ".join(sorted(missing_eventos))
        raise RuntimeError(
            f"evento_djs.csv references unknown evento_slug values: {missing}"
        )

    return _upsert_rows(session, base_url, "evento_djs", rows, on_conflict="evento_id,set_order")


def main() -> None:
    base_url, service_role_key = _load_env()

    session = requests.Session()
    session.headers.update(_headers(service_role_key))

    print("Starting seed...")
    summary: dict[str, int] = {}

    summary["discotecas"] = _seed_simple_table(
        session, base_url, "discotecas.csv", "discotecas"
    )
    summary["eventos"] = _seed_eventos(session, base_url)
    summary["evento_djs"] = _seed_evento_djs(session, base_url)
    summary["playas"] = _seed_simple_table(session, base_url, "playas.csv", "playas")
    summary["restaurantes"] = _seed_simple_table(
        session, base_url, "restaurantes.csv", "restaurantes"
    )
    summary["transportes_vip"] = _seed_simple_table(
        session, base_url, "transportes_vip.csv", "transportes_vip"
    )

    print("Seed completed.")
    for key, value in summary.items():
        print(f"- {key}: processed {value} rows")


if __name__ == "__main__":
    main()

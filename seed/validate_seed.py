import os
import sys
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent


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


def _request(
    session: requests.Session,
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
) -> requests.Response:
    response = session.request(method, url, params=params, timeout=60)
    if response.status_code >= 400:
        raise RuntimeError(f"HTTP {response.status_code} {url}: {response.text}")
    return response


def _count_table(session: requests.Session, base_url: str, table: str) -> int:
    endpoint = f"{base_url}/rest/v1/{table}"
    headers = {"Prefer": "count=exact"}
    response = session.get(
        endpoint, params={"select": "id", "limit": 1}, headers=headers, timeout=60
    )
    if response.status_code >= 400:
        raise RuntimeError(f"HTTP {response.status_code} {endpoint}: {response.text}")

    content_range = response.headers.get("Content-Range", "")
    if "/" not in content_range:
        return len(response.json())
    return int(content_range.split("/")[-1])


def _count_active_null(session: requests.Session, base_url: str, table: str) -> int:
    endpoint = f"{base_url}/rest/v1/{table}"
    response = _request(
        session,
        "GET",
        endpoint,
        params={"select": "id", "active": "is.null", "limit": 1000},
    )
    return len(response.json())


def _get_slugs(session: requests.Session, base_url: str, table: str) -> set[str]:
    endpoint = f"{base_url}/rest/v1/{table}"
    response = _request(
        session,
        "GET",
        endpoint,
        params={"select": "slug", "limit": 10000},
    )
    return {row["slug"] for row in response.json() if row.get("slug")}


def _get_active_event_ids(session: requests.Session, base_url: str) -> set[str]:
    endpoint = f"{base_url}/rest/v1/eventos"
    response = _request(
        session,
        "GET",
        endpoint,
        params={"select": "id", "active": "eq.true", "limit": 10000},
    )
    return {row["id"] for row in response.json() if row.get("id")}


def _get_evento_dj_event_ids(session: requests.Session, base_url: str) -> set[str]:
    endpoint = f"{base_url}/rest/v1/evento_djs"
    response = _request(
        session,
        "GET",
        endpoint,
        params={"select": "evento_id", "limit": 10000},
    )
    return {row["evento_id"] for row in response.json() if row.get("evento_id")}


def _min_count(name: str, default: int) -> int:
    return int(os.getenv(f"SEED_MIN_{name.upper()}", str(default)))


def main() -> None:
    base_url, service_role_key = _load_env()
    session = requests.Session()
    session.headers.update(
        {
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json",
        }
    )

    min_counts = {
        "discotecas": _min_count("discotecas", 5),
        "eventos": _min_count("eventos", 1),
        "evento_djs": _min_count("evento_djs", 1),
        "playas": _min_count("playas", 15),
        "restaurantes": _min_count("restaurantes", 1),
        "transportes_vip": _min_count("transportes_vip", 1),
    }

    counts = {table: _count_table(session, base_url, table) for table in min_counts}

    errors: list[str] = []
    warnings: list[str] = []

    for table, minimum in min_counts.items():
        if counts[table] < minimum:
            errors.append(
                f"{table}: expected at least {minimum}, found {counts[table]}"
            )

    for table in ("discotecas", "eventos", "playas", "restaurantes", "transportes_vip"):
        null_active = _count_active_null(session, base_url, table)
        if null_active > 0:
            errors.append(f"{table}: found {null_active} rows with active = null")

    expected_discotecas = {"pacha", "dc10", "ushuaia", "hi-ibiza", "unvrs"}
    found_discotecas = _get_slugs(session, base_url, "discotecas")
    missing_discotecas = expected_discotecas - found_discotecas
    if missing_discotecas:
        warnings.append(
            "Missing expected discoteca slugs: " + ", ".join(sorted(missing_discotecas))
        )

    active_event_ids = _get_active_event_ids(session, base_url)
    dj_event_ids = _get_evento_dj_event_ids(session, base_url)
    active_without_djs = sorted(active_event_ids - dj_event_ids)
    if active_without_djs:
        preview = ", ".join(active_without_djs[:10])
        errors.append(
            f"eventos: {len(active_without_djs)} active events without DJs in evento_djs. IDs: {preview}"
        )

    print("Seed validation report")
    print("----------------------")
    for table, count in counts.items():
        print(f"- {table}: {count}")

    if warnings:
        print("\nWarnings")
        print("--------")
        for msg in warnings:
            print(f"- {msg}")

    if errors:
        print("\nErrors")
        print("------")
        for msg in errors:
            print(f"- {msg}")
        sys.exit(1)

    print("\nValidation passed.")


if __name__ == "__main__":
    main()

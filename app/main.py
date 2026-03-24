import os
import re
import sqlite3
import time
from pathlib import Path
from typing import List, Optional

import requests
from dotenv import load_dotenv
from exa_py import Exa
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "IBIZA LIVE IA API")
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:5174")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
EXA_API_KEY = os.getenv("EXA_API_KEY")

exa_client = Exa(api_key=EXA_API_KEY) if EXA_API_KEY else None

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
DB_PATH = BASE_DIR / "sql" / "ibiza_local.db"
EVENTS_CACHE_TTL_SECONDS = 300  # 5 minutos

_events_cache: List[dict] = []
_events_cache_timestamp: float = 0.0

# Lugares conocidos: enlaces para Maps, teléfono e Instagram (solo incluir los que existan)
PLACES_LINKS = [
    {
        "name": "Ushuaïa",
        "aliases": ["ushuaia", "ushuaïa"],
        "maps_url": "https://www.google.com/maps/search/?api=1&query=Ushuaïa+Ibiza+Beach+Hotel+Playa+den+Bossa",
        "phone": "+34971300100",
        "instagram": "https://www.instagram.com/ushuaiaibiza/",
    },
    {
        "name": "Pacha",
        "aliases": ["pacha"],
        "maps_url": "https://www.google.com/maps/search/?api=1&query=Pacha+Ibiza",
        "phone": "+34971313612",
        "instagram": "https://www.instagram.com/pachaibiza/",
    },
    {
        "name": "Amnesia",
        "aliases": ["amnesia"],
        "maps_url": "https://www.google.com/maps/search/?api=1&query=Amnesia+Ibiza+San+Rafael",
        "phone": None,
        "instagram": "https://www.instagram.com/amnesiaibiza/",
    },
    {
        "name": "UNVRS",
        "aliases": ["unvrs"],
        "maps_url": "https://www.google.com/maps/search/?api=1&query=UNVRS+Ibiza+Playa+den+Bossa",
        "phone": None,
        "instagram": "https://www.instagram.com/unvrsibiza/",
    },
    {
        "name": "Santa Eulalia",
        "aliases": ["santa eulalia", "santa eulàlia"],
        "maps_url": "https://www.google.com/maps/search/?api=1&query=Santa+Eulalia+Ibiza",
        "phone": None,
        "instagram": None,
    },
]


def _build_places_links_block() -> str:
    """Construye el bloque de texto con enlaces por lugar para el system prompt."""
    lines = []
    for p in PLACES_LINKS:
        name = p["name"]
        maps_url = p.get("maps_url", "")
        phone = p.get("phone")
        instagram = p.get("instagram")
        place_lines = [f"- {name}:"]
        place_lines.append(f"  Maps: {maps_url}")
        if phone:
            place_lines.append(f"  Teléfono: {phone}")
        if instagram:
            place_lines.append(f"  Instagram: {instagram}")
        lines.append("\n".join(place_lines))
    return "\n\n".join(lines)


def _get_football_result_from_api(user_message: str) -> Optional[str]:
  """Intenta obtener un resultado de fútbol desde API-Sports a partir del mensaje del usuario.

  Devuelve una cadena legible con el marcador o None si no se encuentra nada útil.
  """
  try:
    if not FOOTBALL_API_KEY:
      return None

    # Heurística simple: buscar "Equipo1 vs Equipo2"
    lower = user_message.lower()
    if " vs " not in lower and "vs" not in lower:
      return None

    # Normalizar y extraer posibles nombres de equipos
    parts = re.split(r"\bvs\b", lower)
    if len(parts) < 2:
      return None

    def _clean_team(text: str) -> str:
      cleaned = re.sub(r"[^a-záéíóúüñ\s]", " ", text)
      return re.sub(r"\s+", " ", cleaned).strip()

    team_a = _clean_team(parts[0])
    team_b = _clean_team(parts[1])

    if len(team_a) < 3 or len(team_b) < 3:
      return None

    base_url = "https://v3.football.api-sports.io"
    headers = {"x-apisports-key": FOOTBALL_API_KEY}

    # 1) Intentar encontrarlo entre los partidos en vivo
    try:
      live_resp = requests.get(
        f"{base_url}/fixtures",
        params={"live": "all"},
        headers=headers,
        timeout=5,
      )
      if live_resp.ok:
        live_data = live_resp.json()
        for fixture in live_data.get("response", []):
          home_name = str(
            fixture.get("teams", {}).get("home", {}).get("name", "")
          ).lower()
          away_name = str(
            fixture.get("teams", {}).get("away", {}).get("name", "")
          ).lower()

          if (
            team_a in home_name or team_a in away_name
          ) and (team_b in home_name or team_b in away_name):
            goals = fixture.get("goals", {})
            gh = goals.get("home")
            ga = goals.get("away")
            status = fixture.get("fixture", {}).get("status", {})
            elapsed = status.get("elapsed")
            short_status = status.get("short")

            marcador = f"{gh}–{ga}" if gh is not None and ga is not None else "sin marcador disponible"
            estado = ""
            if short_status == "FT":
              estado = " (finalizado)"
            elif elapsed is not None:
              estado = f" (min {elapsed})"

            return f"{fixture['teams']['home']['name']} {marcador} {fixture['teams']['away']['name']}{estado}"
    except Exception:
      # Si falla la parte de live, seguimos con la búsqueda general
      pass

    # 2) Búsqueda general por uno de los equipos
    try:
      search_resp = requests.get(
        f"{base_url}/fixtures",
        params={"search": team_a},
        headers=headers,
        timeout=5,
      )
      if not search_resp.ok:
        return None

      search_data = search_resp.json()
      candidates = []
      for fixture in search_data.get("response", []):
        home_name = str(
          fixture.get("teams", {}).get("home", {}).get("name", "")
        ).lower()
        away_name = str(
          fixture.get("teams", {}).get("away", {}).get("name", "")
        ).lower()

        if (
          team_a in home_name or team_a in away_name
        ) and (team_b in home_name or team_b in away_name):
          candidates.append(fixture)

      if not candidates:
        return None

      # Elegimos el candidato más reciente por fecha
      def _fixture_date_key(fix: dict) -> str:
        return str(fix.get("fixture", {}).get("date", ""))

      fixture = sorted(candidates, key=_fixture_date_key)[-1]
      goals = fixture.get("goals", {})
      gh = goals.get("home")
      ga = goals.get("away")
      marcador = f"{gh}–{ga}" if gh is not None and ga is not None else "sin marcador disponible"

      status = fixture.get("fixture", {}).get("status", {})
      short_status = status.get("short")
      label_estado = {
        "FT": "finalizado",
        "NS": "no iniciado",
      }.get(short_status, short_status or "")

      extra = f" ({label_estado})" if label_estado else ""

      return f"{fixture['teams']['home']['name']} {marcador} {fixture['teams']['away']['name']}{extra}"
    except Exception:
      return None
  except Exception:
    return None


def _web_search(query: str) -> List[dict]:
  """Búsqueda web en tiempo real. Orden: Exa → Tavily → SerpAPI.

  Devuelve una lista normalizada: [{"title": str, "url": str, "content": str}]
  """
  results: List[dict] = []
  q = (query or "").strip()
  if not q:
    return results

  # Exa (preferido — búsqueda neural con contenido completo)
  if exa_client:
    try:
      exa_results = exa_client.search_and_contents(
        q,
        type="auto",
        num_results=5,
        text={"max_characters": 2000},
      )
      for r in exa_results.results:
        results.append({
          "title":   str(r.title or ""),
          "url":     str(r.url or ""),
          "content": str(r.text or "")[:2000],
        })
      if results:
        return results
    except Exception:
      pass

  # Tavily (fallback 1)
  if TAVILY_API_KEY:
    try:
      resp = requests.post(
        "https://api.tavily.com/search",
        json={
          "api_key": TAVILY_API_KEY,
          "query": q,
          "search_depth": "basic",
          "max_results": 5,
          "include_answer": False,
          "include_raw_content": False,
        },
        timeout=8,
      )
      if resp.ok:
        data = resp.json()
        for item in data.get("results", [])[:5]:
          results.append({
            "title":   str(item.get("title", "") or ""),
            "url":     str(item.get("url", "") or ""),
            "content": str(item.get("content", "") or ""),
          })
        return results
    except Exception:
      pass

  # SerpAPI (fallback 2)
  if SERPAPI_API_KEY:
    try:
      resp = requests.get(
        "https://serpapi.com/search.json",
        params={"engine": "google", "q": q, "api_key": SERPAPI_API_KEY, "num": 5},
        timeout=8,
      )
      if resp.ok:
        data = resp.json()
        for item in data.get("organic_results", [])[:5]:
          results.append({
            "title":   str(item.get("title", "") or ""),
            "url":     str(item.get("link", "") or ""),
            "content": str(item.get("snippet", "") or ""),
          })
    except Exception:
      pass

  return results


_SEARCH_KEYWORDS = [
  # Criptomonedas — tickers y nombres
  "bitcoin", "btc", "ethereum", "eth", "xrp", "ripple", "solana", "sol",
  "doge", "dogecoin", "bnb", "usdt", "ada", "cardano", "avax", "avalanche",
  "matic", "polygon", "dot", "polkadot", "link", "chainlink", "ltc", "litecoin",
  "shib", "shiba", "pepe", "crypto", "cripto", "criptomoneda", "token", "coin",
  # Precios / cotizaciones
  "precio", "price", "cotización", "cotizacion", "valor actual", "a cuánto",
  "a cuanto", "cuánto vale", "cuanto vale", "cuánto está", "cuanto esta",
  "dame el precio", "how much", "how much is", "what's the price",
  # Acciones / bolsa
  "acción", "accion", "acciones", "bolsa", "nasdaq", "s&p 500", "dow jones",
  "apple stock", "tesla stock", "nvidia", "índice bursátil",
  # Divisas
  "dólar", "dolar", "euro", "libra", "yen", "tipo de cambio", "cambio de moneda",
  # Tiempo / actualidad
  "clima", "temperatura", "tiempo hoy", "lluvia", "viento",
  "hoy", "ahora mismo", "en este momento", "actualmente", "último precio",
  # Deportes
  "resultado", "marcador", "vs", "partido de",
  # Noticias
  "noticias", "news", "última hora", "breaking",
]

def _should_web_search(message: str) -> bool:
  """Pre-check de keywords obvias; si no coincide, usa gpt-4o-mini para decidir."""
  if not message:
    return False

  text = message.lower()

  # 1. Pre-check rápido: si hay una keyword obvia, activar sin llamar al modelo
  if any(kw in text for kw in _SEARCH_KEYWORDS):
    return True

  # 2. Para queries ambiguas, usar el clasificador IA
  if not client:
    return False
  try:
    resp = client.chat.completions.create(
      model="gpt-4o-mini",
      messages=[
        {
          "role": "system",
          "content": (
            "Eres un clasificador binario. Decide si esta pregunta requiere "
            "información en tiempo real (precios, clima, noticias de hoy, "
            "resultados deportivos, cotizaciones, horarios actuales).\n"
            "Responde SOLO con 'SI' o 'NO'. Sin explicaciones."
          ),
        },
        {"role": "user", "content": message},
      ],
      max_tokens=3,
      temperature=0,
    )
    return resp.choices[0].message.content.strip().upper().startswith("S")
  except Exception:
    return True  # activar búsqueda por precaución si falla


def _load_events_from_db(limit: Optional[int] = 20) -> List[dict]:
  """Lee eventos desde SQLite, devolviendo una lista de dicts."""
  events: List[dict] = []
  try:
    if not DB_PATH.exists():
      print(f"ADVERTENCIA: Base de datos no encontrada en {DB_PATH}")
      return events

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
      base_query = """
        SELECT club, artista, nombre, precio_min, precio_max, dia_semana, fecha
        FROM eventos
        ORDER BY fecha
      """
      if limit is None:
        cursor = conn.execute(base_query)
      else:
        cursor = conn.execute(base_query + " LIMIT ?", (limit,))
      rows = cursor.fetchall()
      events = [dict(row) for row in rows]
    finally:
      conn.close()
  except Exception as e:  # pragma: no cover - solo logging defensivo
    print("ERROR al leer eventos desde SQLite:", e)
  return events


def _get_cached_events(limit: Optional[int] = None) -> List[dict]:
  """Devuelve eventos cacheados, recargando desde BD si el TTL expiró.

  Si limit es None, devuelve todos los eventos cacheados.
  Si limit es un entero, devuelve como máximo ese número de eventos.
  """
  global _events_cache, _events_cache_timestamp

  now = time.time()
  if _events_cache and (now - _events_cache_timestamp) < EVENTS_CACHE_TTL_SECONDS:
    return _events_cache if limit is None else _events_cache[:limit]

  events = _load_events_from_db(limit=None)
  if events:
    _events_cache = events
    _events_cache_timestamp = now

  return _events_cache if limit is None else _events_cache[:limit]


_MESES = (
  "enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


def _format_fecha_legible(fecha_raw: str) -> str:
  """Convierte una fecha ISO (YYYY-MM-DD) o similar en texto legible (ej. 12 de junio)."""
  if not fecha_raw or not isinstance(fecha_raw, str):
    return fecha_raw or ""
  s = fecha_raw.strip()
  # Intentar parsear YYYY-MM-DD
  m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
  if m:
    try:
      year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
      if 1 <= month <= 12 and 1 <= day <= 31:
        mes = _MESES[month - 1]
        return f"{day} de {mes}"
    except (ValueError, IndexError):
      pass
  return s


def _format_events_for_prompt(events: List[dict]) -> str:
  """Convierte la lista de eventos en texto legible para el system_prompt."""
  if not events:
    return ""

  lines: List[str] = []
  for ev in events:
    club = (ev.get("club") or "").strip() or "Club"
    artista = (ev.get("artista") or "").strip()
    nombre = (ev.get("nombre") or "").strip()
    precio_min = ev.get("precio_min")
    precio_max = ev.get("precio_max")
    fecha_raw = (ev.get("fecha") or "").strip()
    fecha = _format_fecha_legible(fecha_raw) if fecha_raw else ""
    dia_semana = ev.get("dia_semana")

    # Texto principal del evento
    main_label = nombre or artista or "Evento"
    artist_label = f" ({artista})" if artista and artista not in main_label else ""

    # Rango de precios
    price_str = ""
    if isinstance(precio_min, (int, float)) and isinstance(precio_max, (int, float)):
      price_str = f"desde {precio_min}–{precio_max}€"
    elif isinstance(precio_min, (int, float)):
      price_str = f"desde {precio_min}€"
    elif isinstance(precio_max, (int, float)):
      price_str = f"hasta {precio_max}€"

    # Día o fecha: si hay fecha exacta la mostramos legible; si no, día de la semana
    weekday_map = {
      0: "los lunes",
      1: "los martes",
      2: "los miércoles",
      3: "los jueves",
      4: "los viernes",
      5: "los sábados",
      6: "los domingos",
    }
    weekday_label = ""
    if not fecha and dia_semana is not None:
      try:
        weekday_label = weekday_map.get(int(dia_semana), "")
      except (TypeError, ValueError):
        weekday_label = ""

    if fecha:
      date_str = f" · {fecha}"
    elif weekday_label:
      date_str = f" · {weekday_label}"
    else:
      date_str = ""

    tail_parts = [part for part in [price_str, date_str] if part]
    tail = f" {' '.join(tail_parts)}" if tail_parts else ""

    lines.append(f"- {club}: {main_label}{artist_label}{tail}")

  return "\n".join(lines)


app = FastAPI(title=APP_NAME, version=APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in CORS_ORIGINS.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/v1/ping")
def ping():
    return {"message": "pong"}

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        if not client:
            return ChatResponse(response="⚠️ OpenAI no configurado")

        # Obtener eventos reales desde SQLite con cache simple (todos los eventos)
        eventos = _get_cached_events(limit=None)
        eventos_texto = _format_events_for_prompt(eventos)

        if not eventos_texto:
            eventos_bloque = (
                "No hay eventos cargados desde la base de datos en este momento. "
                "Si el usuario pregunta por eventos concretos, indica que ahora mismo no tienes datos."
            )
        else:
            eventos_bloque = (
                "Estos son los eventos REALES que tienes disponibles ahora mismo, "
                "basados en la base de datos SQLite (no inventes nada fuera de esta lista):\n\n"
                f"{eventos_texto}"
            )

        info_extra = """
Información adicional sobre ubicaciones y precios (aproximados):
- Ushuaïa: situado en Playa d'en Bossa, a unos 15 minutos en coche del centro de Ibiza. Precio medio de una copa: ~20€. Entrada típica: desde 60€.
- Pacha: en Ibiza ciudad, a unos 10 minutos andando del centro. Copa: ~18€. Entrada típica: 50–70€.
- Amnesia: en San Rafael, a unos 20 minutos en coche desde el centro. Copa: ~22€. Entrada típica: 55€.
- UNVRS: en Playa d'en Bossa, muy cerca de Ushuaïa. Copa: ~25€. Entrada típica: 70€.
- Distancias aproximadas entre clubs: Ushuaïa–UNVRS: ~2 minutos andando. Ushuaïa–Pacha: ~20 minutos en coche. Pacha–Amnesia: ~15 minutos en coche.

Si el usuario pregunta por distancias o tiempos de trayecto, usa estos datos como referencia aproximada y, si necesita más precisión, sugiere consultar Google Maps o una app de mapas.
"""

        places_links_block = _build_places_links_block()

        system_prompt = f"""Eres ibzAI, asistente local de Ibiza. Respondes de forma breve, directa y útil. Sin emojis de celebración, sin frases de relleno, sin entusiasmo exagerado. Cuando alguien pregunta por un evento o club: da la fecha exacta, el precio de entrada si lo tienes, el DJ o artista si está en los datos, y los enlaces útiles (Maps, Instagram, teléfono). Si no tienes un dato, dilo en una frase y sugiere dónde buscarlo. Máximo 3-4 líneas de texto antes de los enlaces.

{eventos_bloque}

{info_extra}

ENLACES TÁCTILES PARA LUGARES (usa estos datos cuando menciones un club, restaurante o lugar):
Lugares conocidos y sus enlaces oficiales (incluye en tu respuesta debajo del texto cuando hables de ese lugar):

{places_links_block}

Cuando en tu respuesta menciones alguno de estos lugares (Ushuaïa, Pacha, Amnesia, UNVRS, Santa Eulalia, etc.), añade DEBAJO del texto principal las líneas correspondientes con enlaces en este formato exacto (el usuario verá enlaces clicables):
- Siempre que hables de un lugar: una línea con 📍 [Ver en Google Maps](URL_MAPS) usando la URL de Maps del lugar.
- Si el lugar tiene teléfono en la lista: una línea 📞 [Llamar](tel:NUMERO) (sin espacios en el número).
- Si el lugar tiene Instagram en la lista: una línea 📸 [Instagram del club](URL_INSTAGRAM) o [Instagram](URL_INSTAGRAM).
Si no hay teléfono o Instagram para ese lugar, no incluyas esa línea. Usa solo las URLs y números de la lista de arriba. Un lugar por bloque de enlaces (Maps + opcional Llamar + opcional Instagram).

INSTRUCCIONES CRÍTICAS:
- Para información de eventos concretos de Ibiza (fechas, precios de entrada, etc.), usa los eventos listados arriba como referencia principal y evita contradecirlos.
- Fechas: si en la lista el evento tiene fecha exacta (ej. "12 de junio"), úsala en tu respuesta. Si solo tiene día de la semana (ej. "los lunes"), usa eso. Responde siempre con fechas o días tal como aparecen en los datos.
- Si el usuario pregunta por una fecha concreta o por cuándo abre/cierra un club y no tienes ese dato en la lista: dilo simple y ofrece una alternativa útil: "No lo tengo ahora, pero puedes consultar en la web o redes oficiales del club."
- Ejemplo cuando pregunten "cuándo abre UNVRS" y no haya fecha: "Aún no tengo la fecha exacta de apertura de UNVRS; puedes consultarlo en su web o redes oficiales."
- Para distancias, tiempos de trayecto y precios de consumiciones, puedes usar el bloque de información adicional como referencia aproximada.
- Puedes responder preguntas generales (fútbol, clima, etc.) con tu conocimiento. Si falta información muy reciente, dilo de forma natural y sugiere una fuente (ej. web oficial, app de resultados, Google Maps).
- No uses emojis a menos que el usuario los use primero.

REGLAS DE RESPUESTA:
- Máximo 3 líneas.
- Directo y natural, sin adornos tipo "increíble", "genial" o similares.
- Cuando hables de un sitio concreto de Ibiza, usa si puedes: Lugar + qué hay + precio (si se sabe) y, cuando aplique, cómo llegar o tiempo estimado."""

        # Búsqueda web (si la consulta requiere información actualizada)
        web_results = []
        if _should_web_search(request.message):
            query = request.message.strip()
            web_results = _web_search(query)

        # Intentar enriquecer el contexto con un posible resultado de fútbol
        football_result = _get_football_result_from_api(request.message)

        messages = [
            {"role": "system", "content": system_prompt},
        ]
        if web_results:
            sources_text = "\n".join(
                [
                    f"- {r.get('title','')}\n  {r.get('url','')}\n  {r.get('content','')}"
                    for r in web_results[:3]
                    if r.get("url")
                ]
            )
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "Resultados de búsqueda web en tiempo real. "
                        "Si contienen un precio, cotización o valor numérico concreto, cítalo directamente (ej: 'Bitcoin cotiza a $X según [fuente]'). "
                        "Si los datos son de hace más de 1 hora, acláralo. "
                        "Menciona siempre la fuente con el formato [Nombre](URL).\n\n"
                        f"{sources_text}"
                    ),
                }
            )
        if football_result:
            messages.append(
                {
                    "role": "system",
                    "content": f"Resultado de fútbol detectado para esta consulta: {football_result}. "
                               f"Si el usuario estaba preguntando por este partido, incluye este marcador de forma natural en tu respuesta.",
                }
            )
        messages.append({"role": "user", "content": request.message})

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=220,
        )
        return ChatResponse(response=response.choices[0].message.content)
    except Exception as e:
        print("ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))

from app.routes import eventos
app.include_router(eventos.router)

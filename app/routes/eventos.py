from fastapi import APIRouter
from app.models.evento import Evento, EventoResponse

router = APIRouter(prefix="/api/v1/eventos", tags=["eventos"])

# Datos de tus eventos de Ibiza
eventos_data = [
    Evento(club="ushuaia", artista="Dom Dolla", nombre="Dom Dolla & Friends", precio_min=60, precio_max=140, dia_semana=0),
    Evento(club="ushuaia", artista="Black Coffee", nombre="Black Coffee & Friends", precio_min=65, precio_max=150, dia_semana=5),
    Evento(club="pacha", artista="Sonny Fodera", nombre="Sonny Fodera & Friends", precio_min=45, precio_max=120, dia_semana=0),
    Evento(club="pacha", artista="Solomun", nombre="Solomun +1", precio_min=60, precio_max=140, dia_semana=6),
    Evento(club="unvrs", artista="John Summit", nombre="Experts Only", precio_min=70, precio_max=180, dia_semana=0),
    Evento(club="unvrs", artista="Anyma", nombre="ÆDEN", precio_min=80, precio_max=200, dia_semana=1),
    Evento(club="amnesia", artista="Sven Väth", nombre="Cocoon", precio_min=55, precio_max=130, dia_semana=1),
]

@router.get("/", response_model=EventoResponse)
async def get_eventos():
    return EventoResponse(eventos=eventos_data, total=len(eventos_data))

@router.get("/club/{club}", response_model=EventoResponse)
async def get_eventos_por_club(club: str):
    filtrados = [e for e in eventos_data if e.club.lower() == club.lower()]
    return EventoResponse(eventos=filtrados, total=len(filtrados))

@router.get("/dia/{dia}", response_model=EventoResponse)
async def get_eventos_por_dia(dia: int):
    filtrados = [e for e in eventos_data if e.dia_semana == dia]
    return EventoResponse(eventos=filtrados, total=len(filtrados))

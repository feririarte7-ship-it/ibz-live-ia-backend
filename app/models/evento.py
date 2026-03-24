from pydantic import BaseModel
from typing import Optional, List

class Evento(BaseModel):
    id: Optional[int] = None
    club: str
    artista: str
    nombre: str
    precio_min: int
    precio_max: int
    dia_semana: int
    
class EventoResponse(BaseModel):
    eventos: List[Evento]
    total: int

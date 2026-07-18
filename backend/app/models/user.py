"""
Modelos de dominio (no ORM — Supabase maneja la persistencia vía su cliente).
Se usan como estructuras internas tipadas dentro de los servicios.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

Role = Literal["admin", "client"]


@dataclass
class Profile:
    id: str
    email: str
    full_name: Optional[str]
    role: Role
    accepted_terms: bool
    trial_ends_at: Optional[datetime]
    created_at: datetime

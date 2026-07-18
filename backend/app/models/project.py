"""Modelo de dominio para proyectos/sesiones fotográficas."""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

ProjectStatus = Literal["processing", "review", "completed"]


@dataclass
class Project:
    id: str
    user_id: str
    name: str
    session_type: Optional[str]
    status: ProjectStatus
    created_at: datetime

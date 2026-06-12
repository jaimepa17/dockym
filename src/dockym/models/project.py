from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Service:
    name: str
    image: str
    status: str = "unknown"
    ports: str = ""
    container_name: str = ""
    project_path: str = ""

    @property
    def is_running(self) -> bool:
        return self.status == "running"

    @property
    def status_icon(self) -> str:
        return {
            "running": "●",
            "exited": "○",
            "paused": "◐",
            "created": "◌",
            "restarting": "↻",
            "removing": "×",
            "dead": "✕",
        }.get(self.status, "—")

    @property
    def status_label(self) -> str:
        labels = {
            "running": "En ejecución",
            "exited": "Detenido",
            "paused": "Pausado",
            "created": "Creado",
            "restarting": "Reiniciando",
            "removing": "Eliminando",
            "dead": "Muerto",
        }
        return labels.get(self.status, "Sin contenedor")


@dataclass
class Project:
    name: str
    path: str
    services: list[Service] = field(default_factory=list)

    @property
    def running_count(self) -> int:
        return sum(1 for s in self.services if s.is_running)

    @property
    def total_count(self) -> int:
        return len(self.services)

    @property
    def status_icon(self) -> str:
        if not self.services:
            return "▢"
        if all(s.is_running for s in self.services):
            return "▣"
        if any(s.is_running for s in self.services):
            return "▤"
        return "▢"

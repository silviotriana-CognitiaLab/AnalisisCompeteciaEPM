"""Carga de los archivos de configuración en scraper/config/."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


@dataclass
class Sector:
    id: str
    nombre: str
    descripcion: str
    tipos_dato: list[str] = field(default_factory=list)


@dataclass
class Competidor:
    id: str
    nombre: str
    confianza: str
    sitio: str = ""
    notas: str = ""
    fuentes_noticias: list[str] = field(default_factory=list)


@dataclass
class FuenteOficial:
    id: str
    nombre: str
    tipo_fuente: str
    url: str
    metodo: str
    notas: str = ""
    resource_id: str | None = None


def cargar_sectores() -> dict[str, Sector]:
    data = yaml.safe_load((CONFIG_DIR / "sectores.yaml").read_text())
    return {
        sid: Sector(id=sid, **{k: v for k, v in s.items()})
        for sid, s in data["sectores"].items()
    }


def cargar_competidores() -> dict[str, list[Competidor]]:
    data = yaml.safe_load((CONFIG_DIR / "competidores.yaml").read_text())
    resultado: dict[str, list[Competidor]] = {}
    for sector_id, entradas in data.items():
        resultado[sector_id] = [Competidor(**e) for e in entradas]
    return resultado


def cargar_fuentes_oficiales() -> dict[str, list[FuenteOficial]]:
    data = yaml.safe_load((CONFIG_DIR / "fuentes_oficiales.yaml").read_text())
    resultado: dict[str, list[FuenteOficial]] = {}
    for tipo_dato, entradas in data.items():
        resultado[tipo_dato] = [FuenteOficial(**e) for e in entradas]
    return resultado


def competidores_validos(sector_id: str) -> list[Competidor]:
    """Competidores de un sector que NO son placeholders 'completar'."""
    todos = cargar_competidores().get(sector_id, [])
    return [c for c in todos if c.confianza != "completar"]

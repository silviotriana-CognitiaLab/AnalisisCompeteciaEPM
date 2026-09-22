"""Manifest append-only (JSON Lines) de todo lo capturado, para trazabilidad.

Cada línea de ./fuentes/manifest.jsonl es una captura (exitosa, con
cambios, sin cambios, u omitida). Nunca se reescribe ni se borra una línea
existente: es el registro de auditoría exigido por el estándar de calidad
del proyecto (CLAUDE.md): "Toda cifra debe ser trazable a su fuente".
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

FUENTES_DIR = Path(__file__).resolve().parent.parent.parent / "fuentes"
MANIFEST_PATH = FUENTES_DIR / "manifest.jsonl"


@dataclass
class EntradaManifest:
    fecha_captura: str
    sector: str
    tipo_dato: str
    entidad: str
    tipo_fuente: str  # independiente | autorreportado | prensa
    url: str
    metodo: str  # http_api | http_simple | headless_browser
    estado_http: int | None
    archivo: str | None
    hash_contenido: str | None
    cambio_detectado: bool | None
    omitido_por_robots: bool = False
    notas: str = ""


def registrar(entrada: EntradaManifest) -> None:
    FUENTES_DIR.mkdir(parents=True, exist_ok=True)
    with MANIFEST_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(entrada), ensure_ascii=False) + "\n")


def ahora_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

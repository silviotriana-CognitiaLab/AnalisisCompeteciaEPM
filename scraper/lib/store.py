"""Persistencia de capturas crudas en ./fuentes/ + entrada de manifest.

Estructura de salida:
    fuentes/<sector>/<tipo_dato>/<entidad>/YYYY-MM-DD_<slug>.<ext>
    fuentes/manifest.jsonl
    fuentes/.state/hashes.json   (índice interno: última huella por URL)

Solo se reescribe el archivo del día si el contenido cambió respecto a la
última captura de esa URL (se compara por hash). Si no cambió, igual se
deja constancia en el manifest con cambio_detectado=false, sin duplicar el
archivo: así el manifest sigue siendo la fuente de verdad de "cuándo se
revisó" aunque no haya novedad.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .manifest import FUENTES_DIR, EntradaManifest, ahora_iso, registrar

ESTADO_PATH = FUENTES_DIR / ".state" / "hashes.json"


def _slug(texto: str, largo: int = 60) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", texto).strip("-").lower()
    return s[:largo] or "captura"


def _cargar_estado() -> dict[str, str]:
    if ESTADO_PATH.exists():
        return json.loads(ESTADO_PATH.read_text())
    return {}


def _guardar_estado(estado: dict[str, str]) -> None:
    ESTADO_PATH.parent.mkdir(parents=True, exist_ok=True)
    ESTADO_PATH.write_text(json.dumps(estado, ensure_ascii=False, indent=2))


def guardar_captura(
    *,
    sector: str,
    tipo_dato: str,
    entidad: str,
    url: str,
    contenido: str,
    tipo_fuente: str,
    metodo: str,
    estado_http: int | None,
    extension: str = "txt",
    omitido_por_robots: bool = False,
    notas: str = "",
) -> EntradaManifest:
    hash_contenido = hashlib.sha256(contenido.encode("utf-8")).hexdigest() if contenido else None

    estado = _cargar_estado()
    hash_previo = estado.get(url)
    cambio_detectado = None if omitido_por_robots else (hash_contenido != hash_previo)

    archivo_rel: str | None = None
    if not omitido_por_robots and contenido and cambio_detectado:
        carpeta = FUENTES_DIR / sector / tipo_dato / _slug(entidad)
        carpeta.mkdir(parents=True, exist_ok=True)
        fecha = ahora_iso()[:10]
        archivo = carpeta / f"{fecha}_{_slug(url)}.{extension}"
        archivo.write_text(contenido, encoding="utf-8")
        archivo_rel = str(archivo.relative_to(FUENTES_DIR.parent))
        estado[url] = hash_contenido
        _guardar_estado(estado)

    entrada = EntradaManifest(
        fecha_captura=ahora_iso(),
        sector=sector,
        tipo_dato=tipo_dato,
        entidad=entidad,
        tipo_fuente=tipo_fuente,
        url=url,
        metodo=metodo,
        estado_http=estado_http,
        archivo=archivo_rel,
        hash_contenido=hash_contenido,
        cambio_detectado=cambio_detectado,
        omitido_por_robots=omitido_por_robots,
        notas=notas,
    )
    registrar(entrada)
    return entrada

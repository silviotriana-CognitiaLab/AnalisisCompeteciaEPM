"""Collector de tipo 'noticias' vía navegador headless.

Recorre `fuentes_noticias` de cada competidor válido del sector (ver
scraper/config/competidores.yaml). Si un competidor no tiene URLs
concretas cargadas, se registra como pendiente en el manifest en vez de
adivinar una ruta de sala de prensa que podría no existir.

Requiere un entorno con salida real a internet hacia el dominio del
competidor (ver aviso en scraper/lib/browser.py y scraper/README.md).
"""

from __future__ import annotations

from ..lib import browser
from ..lib.config import competidores_validos
from ..lib.manifest import EntradaManifest
from ..lib.store import guardar_captura

nombre = "noticias_headless"
tipo_dato = "noticias"


def run(sector_id: str) -> list[EntradaManifest]:
    resultados: list[EntradaManifest] = []

    for competidor in competidores_validos(sector_id):
        if not competidor.fuentes_noticias:
            resultados.append(
                guardar_captura(
                    sector=sector_id,
                    tipo_dato=tipo_dato,
                    entidad=competidor.id,
                    url=competidor.sitio or "(sin url)",
                    contenido="",
                    tipo_fuente="autorreportado",
                    metodo="headless_browser",
                    estado_http=None,
                    notas="Sin fuentes_noticias configuradas para este competidor en competidores.yaml.",
                )
            )
            continue

        for url in competidor.fuentes_noticias:
            captura = browser.capturar(url)
            resultados.append(
                guardar_captura(
                    sector=sector_id,
                    tipo_dato=tipo_dato,
                    entidad=competidor.id,
                    url=url,
                    contenido=captura.texto,
                    tipo_fuente="autorreportado",
                    metodo="headless_browser",
                    estado_http=captura.estado_http,
                    omitido_por_robots=captura.omitido_por_robots,
                    extension="txt",
                )
            )
    return resultados

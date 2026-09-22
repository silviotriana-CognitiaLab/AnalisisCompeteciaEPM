"""Collector de tipo 'regulacion' para datasets de datos.gov.co (Socrata).

Usa el cliente HTTP simple (sin navegador): estos son endpoints JSON
públicos, no páginas anti-bot. No inventa resource_id: si
`fuentes_oficiales.yaml` trae un resource_id con el placeholder
'TODO-buscar-resource-id-exacto', el collector lo salta y lo deja
registrado como pendiente en el manifest en vez de adivinar una URL.
"""

from __future__ import annotations

from ..lib import http_client
from ..lib.config import cargar_fuentes_oficiales
from ..lib.manifest import EntradaManifest
from ..lib.store import guardar_captura

nombre = "regulacion_datos_abiertos"
tipo_dato = "regulacion"


def run(sector_id: str) -> list[EntradaManifest]:
    resultados: list[EntradaManifest] = []
    fuentes = cargar_fuentes_oficiales().get("regulacion", [])

    for fuente in fuentes:
        if fuente.metodo != "http_api" or not fuente.aplica_a(sector_id):
            continue

        resource_id = getattr(fuente, "resource_id", None)
        if not resource_id or resource_id.startswith("TODO"):
            resultados.append(
                guardar_captura(
                    sector=sector_id,
                    tipo_dato=tipo_dato,
                    entidad=fuente.id,
                    url=fuente.url,
                    contenido="",
                    tipo_fuente=fuente.tipo_fuente,
                    metodo=fuente.metodo,
                    estado_http=None,
                    omitido_por_robots=False,
                    notas=f"Pendiente de configurar resource_id real en config/fuentes_oficiales.yaml ({fuente.id}).",
                )
            )
            continue

        url = f"{fuente.url}/resource/{resource_id}.json"
        resp = http_client.get(url)
        resultados.append(
            guardar_captura(
                sector=sector_id,
                tipo_dato=tipo_dato,
                entidad=fuente.id,
                url=url,
                contenido=resp.contenido,
                tipo_fuente=fuente.tipo_fuente,
                metodo=fuente.metodo,
                estado_http=resp.estado_http,
                extension="json",
            )
        )
    return resultados

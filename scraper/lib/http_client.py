"""Cliente HTTP liviano para APIs/HTML sin bloqueo anti-bot conocido.

Úsalo para endpoints estructurados (Socrata/datos.gov.co, APIs de
reguladores) donde no hace falta un navegador. Para sitios que devuelven
403 a este cliente, usar lib/browser.py (headless) en su lugar.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

import httpx

CONTACTO = os.environ.get("SCRAPER_CONTACT", "contacto-no-configurado@ejemplo.com")
USER_AGENT = (
    f"AnalisisCompeteciaEPM-Monitor/0.1 (+{CONTACTO}; "
    "uso: inteligencia competitiva interna, respeta robots.txt)"
)

# Segundos mínimos entre solicitudes al mismo dominio.
INTERVALO_MIN_POR_DOMINIO = 3.0

_ultimo_acceso: dict[str, float] = {}


@dataclass
class RespuestaCaptura:
    url: str
    estado_http: int
    contenido: str
    content_type: str


def _rate_limit(dominio: str) -> None:
    ahora = time.monotonic()
    espera = INTERVALO_MIN_POR_DOMINIO - (ahora - _ultimo_acceso.get(dominio, 0.0))
    if espera > 0:
        time.sleep(espera)
    _ultimo_acceso[dominio] = time.monotonic()


def get(url: str, *, timeout: float = 20.0, reintentos: int = 2) -> RespuestaCaptura:
    from urllib.parse import urlparse

    dominio = urlparse(url).netloc
    _rate_limit(dominio)

    ultimo_error: Exception | None = None
    for intento in range(reintentos + 1):
        try:
            resp = httpx.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
            return RespuestaCaptura(
                url=url,
                estado_http=resp.status_code,
                contenido=resp.text,
                content_type=resp.headers.get("content-type", ""),
            )
        except httpx.HTTPError as exc:
            ultimo_error = exc
            time.sleep(2 ** intento)
    raise RuntimeError(f"Fallo al capturar {url} tras {reintentos + 1} intentos") from ultimo_error

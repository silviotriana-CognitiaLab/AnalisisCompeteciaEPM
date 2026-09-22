"""Navegador headless (Playwright/Chromium) para sitios que bloquean fetch simple.

Este es el mecanismo elegido para superar los 403 que sufrieron los
informes anteriores en portales de prensa y del regulador. Sigue
respetando robots.txt (ver lib/robots.py) y aplica rate limiting por
dominio: renderizar JS no es licencia para ignorar Disallow ni para
golpear un sitio sin pausas.

IMPORTANTE: este módulo solo funciona en un entorno con salida a
internet real hacia el sitio objetivo. En una sesión remota de Claude
Code en la nube, el sandbox de red normalmente solo permite un allowlist
de registros de paquetes/git, así que estas llamadas fallarán ahí. Ejecuta
este collector desde un entorno con internet abierto (tu máquina local,
un runner de GitHub Actions, un VPS). Ver scraper/README.md.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from urllib.parse import urlparse

from .http_client import USER_AGENT
from .robots import puede_capturar

CHROMIUM_PATH = os.environ.get(
    "PLAYWRIGHT_CHROMIUM_PATH", "/opt/pw-browsers/chromium/chrome-linux/chrome"
)
INTERVALO_MIN_POR_DOMINIO = 5.0

_ultimo_acceso: dict[str, float] = {}


@dataclass
class RespuestaCaptura:
    url: str
    estado_http: int | None
    html: str
    texto: str
    omitido_por_robots: bool = False


def _rate_limit(dominio: str) -> None:
    ahora = time.monotonic()
    espera = INTERVALO_MIN_POR_DOMINIO - (ahora - _ultimo_acceso.get(dominio, 0.0))
    if espera > 0:
        time.sleep(espera)
    _ultimo_acceso[dominio] = time.monotonic()


def _extraer_texto(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    return "\n".join(
        linea.strip() for linea in soup.get_text("\n").splitlines() if linea.strip()
    )


def capturar(url: str, *, espera_ms: int = 3000) -> RespuestaCaptura:
    """Renderiza `url` con Chromium headless y devuelve HTML + texto plano."""
    if not puede_capturar(url, USER_AGENT):
        return RespuestaCaptura(url=url, estado_http=None, html="", texto="", omitido_por_robots=True)

    dominio = urlparse(url).netloc
    _rate_limit(dominio)

    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROMIUM_PATH, headless=True)
        try:
            contexto = browser.new_context(user_agent=USER_AGENT)
            pagina = contexto.new_page()
            respuesta = pagina.goto(url, wait_until="networkidle", timeout=30000)
            pagina.wait_for_timeout(espera_ms)
            html = pagina.content()
            estado = respuesta.status if respuesta else None
        finally:
            browser.close()

    return RespuestaCaptura(
        url=url,
        estado_http=estado,
        html=html,
        texto=_extraer_texto(html),
    )

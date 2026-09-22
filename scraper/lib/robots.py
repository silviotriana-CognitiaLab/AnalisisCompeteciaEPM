"""Verificación de robots.txt con cache en memoria por dominio.

Regla del proyecto: si robots.txt prohíbe una ruta, el collector la salta y
lo registra en el manifest como 'omitido_por_robots'. No se ignora nunca
una regla Disallow, sin importar el método (http simple o navegador
headless) usado para el resto del sitio.
"""

from __future__ import annotations

import urllib.robotparser
from urllib.parse import urlparse

import httpx

_cache: dict[str, urllib.robotparser.RobotFileParser] = {}


def _robots_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}/robots.txt"

def puede_capturar(url: str, user_agent: str, timeout: float = 10.0) -> bool:
    robots_url = _robots_url(url)
    parser = _cache.get(robots_url)
    if parser is None:
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(robots_url)
        try:
            resp = httpx.get(robots_url, timeout=timeout, headers={"User-Agent": user_agent})
            if resp.status_code == 200:
                parser.parse(resp.text.splitlines())
            else:
                # Sin robots.txt accesible: se asume permitido, pero queda
                # registrado por el llamador vía estado_http de la captura real.
                parser.parse([])
        except httpx.HTTPError:
            parser.parse([])
        _cache[robots_url] = parser
    return parser.can_fetch(user_agent, url)

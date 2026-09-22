"""Interfaz común para todos los collectors.

Un collector es una función `run(sector_id: str) -> list[EntradaManifest]`
que sabe cómo recolectar UN tipo de dato (regulacion, noticias,
percepcion_cliente, expansion_negocio) para un sector dado, usando la
configuración en scraper/config/. El CLI (scraper/cli.py) los descubre por
nombre de módulo.
"""

from __future__ import annotations

from typing import Protocol

from ..lib.manifest import EntradaManifest


class Collector(Protocol):
    nombre: str
    tipo_dato: str

    def run(self, sector_id: str) -> list[EntradaManifest]: ...

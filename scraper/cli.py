"""CLI del monitor de competencia de EPM.

Uso:
    python -m scraper.cli run --sector energia_electrica
    python -m scraper.cli run --sector energia_electrica --tipo-dato noticias
    python -m scraper.cli run --todos
    python -m scraper.cli listar-sectores

Cada corrida escribe capturas crudas en ./fuentes/ y una línea por captura
en ./fuentes/manifest.jsonl. No genera el informe en Markdown: eso lo sigue
haciendo el subagente `inteligencia-estrategica` (o /mercado), leyendo
./fuentes/ como evidencia ya recolectada antes de salir a buscar en vivo.
"""

from __future__ import annotations

import argparse
import importlib
import sys

from .lib.config import cargar_sectores

COLLECTORS_POR_TIPO = {
    "regulacion": ["collectors.regulacion_datos_abiertos"],
    "noticias": ["collectors.noticias_headless"],
    # "percepcion_cliente" y "expansion_negocio": aún sin collector concreto,
    # ver scraper/README.md "Estado de implementación".
}


def _run_sector(sector_id: str, solo_tipo: str | None) -> None:
    sectores = cargar_sectores()
    sector = sectores.get(sector_id)
    if sector is None:
        print(f"Sector desconocido: {sector_id}. Usa 'listar-sectores'.", file=sys.stderr)
        sys.exit(1)

    tipos = [solo_tipo] if solo_tipo else sector.tipos_dato
    for tipo in tipos:
        modulos = COLLECTORS_POR_TIPO.get(tipo, [])
        if not modulos:
            print(f"[{sector_id}/{tipo}] sin collector implementado todavía, se omite.")
            continue
        for ruta_modulo in modulos:
            modulo = importlib.import_module(f"{__package__}.{ruta_modulo}" if __package__ else ruta_modulo)
            print(f"[{sector_id}/{tipo}] ejecutando {modulo.nombre}...")
            entradas = modulo.run(sector_id)
            capturados = sum(1 for e in entradas if e.cambio_detectado)
            print(f"[{sector_id}/{tipo}] {len(entradas)} fuentes revisadas, {capturados} con contenido nuevo/cambiado.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor de competencia EPM")
    sub = parser.add_subparsers(dest="comando", required=True)

    sub.add_parser("listar-sectores")

    p_run = sub.add_parser("run")
    p_run.add_argument("--sector", help="id del sector, ver 'listar-sectores'")
    p_run.add_argument("--tipo-dato", help="limitar a un tipo_dato (regulacion, noticias, ...)")
    p_run.add_argument("--todos", action="store_true", help="correr todos los sectores configurados")

    args = parser.parse_args()

    if args.comando == "listar-sectores":
        for sid, s in cargar_sectores().items():
            print(f"{sid}: {s.nombre} (tipos_dato: {', '.join(s.tipos_dato)})")
        return

    if args.comando == "run":
        if args.todos:
            for sid in cargar_sectores():
                _run_sector(sid, args.tipo_dato)
        elif args.sector:
            _run_sector(args.sector, args.tipo_dato)
        else:
            parser.error("especifica --sector <id> o --todos")


if __name__ == "__main__":
    main()

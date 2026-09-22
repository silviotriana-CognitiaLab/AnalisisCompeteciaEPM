# Monitor de competencia de EPM — diseño del proyecto de scraping

Herramienta de recolección automatizada de información pública sobre los
competidores de EPM en Colombia, pensada para alimentar con evidencia
trazable al subagente `inteligencia-estrategica` (ver `.claude/agents/`) y
sus informes en `./informes/`.

## 0. Aviso importante sobre dónde puede ejecutarse

**Este código NO puede correr dentro de una sesión remota de Claude Code en
la nube como la que lo generó.** Se comprobó en la construcción de este
proyecto: el sandbox de red de esas sesiones solo permite salida a un
allowlist de registros de paquetes/git (PyPI, npm, GitHub, APIs de
Anthropic); cualquier `curl`/`httpx`/Playwright hacia `xm.com.co`,
`datos.gov.co`, `epm.com.co`, etc. es rechazado por el proxy con 403 antes
de llegar a internet.

Esto significa que **el navegador headless y los collectors HTTP deben
ejecutarse en un entorno con salida a internet real**:

- Tu máquina local (terminal normal, o Claude Code CLI/desktop corriendo
  localmente — ahí Bash sí tiene tu internet real, no este sandbox).
- Un runner de GitHub Actions (salida a internet abierta por defecto).
- Un VPS o contenedor propio.

Dentro de una sesión remota de Claude Code en la nube, sí siguen
funcionando: leer/escribir archivos del repo, correr los collectors que
apuntan a datasets JSON *si* estuvieran en el allowlist (no es el caso
aquí), y todo lo que ya usa el subagente `inteligencia-estrategica`
(WebSearch/WebFetch tienen su propia salida a internet vía la
infraestructura de Anthropic, distinta del sandbox de Bash — por eso el
subagente sí puede buscar aunque este scraper de Bash no pueda).

## 1. Objetivo

Sistematizar la recolección de las 4 categorías de evidencia que ya usa
`inteligencia-estrategica` en sus informes, para dejar de depender
únicamente de búsquedas en vivo (que chocan con bloqueos 403 en portales
de prensa y del regulador, como quedó documentado en
`informes/2026-07-27_energia-electrica-colombia_inteligencia.md`, sección 0).

El scraper no reemplaza al subagente: le entrega materia prima ya
capturada y con procedencia marcada en `./fuentes/`, para que el análisis
(síntesis, segmentación, estimación de cuota) lo siga haciendo el
subagente con su metodología existente.

## 2. Alcance: líneas de negocio de EPM cubiertas

Definido en `config/sectores.yaml`:

1. **Energía eléctrica** (generación, distribución, comercialización) — ya
   tiene informe base.
2. **Gas natural** (distribución/comercialización).
3. **Agua, saneamiento y aseo** — ya tiene informe base.
4. **Generación solar distribuida (PPA / EPC)** — negocio no regulado,
   C&I, más fragmentado y sin reguladores publicando cuota de mercado.
5. **Alumbrado público** — contratación pública (SECOP) como fuente
   principal de señales de negocio.
6. **Alumbrado navideño** — muy estacional (jul-oct para licitaciones).
7. **Alumbrado arquitectónico** — nicho pequeño, poco documentado en
   prensa abierta.

Los competidores semilla de los sectores 4-7 están marcados como
`confianza: completar` en `config/competidores.yaml` en vez de que este
diseño invente nombres: son mercados más locales/nicho donde el
conocimiento de EPM sobre quién es el competidor real vale más que
cualquier búsqueda genérica.

## 3. Tipos de dato (collectors)

Definidos como categorías independientes del sector, en línea con lo que
pediste priorizar:

| tipo_dato            | Qué captura                                                | Método por defecto |
|-----------------------|-------------------------------------------------------------|---------------------|
| `regulacion`           | Tarifas y datos oficiales (CREG, SSPD/SUI, XM, UPME, datos abiertos) | `http_api` cuando existe endpoint estructurado; si no, `headless` |
| `noticias`             | Prensa económica y salas de prensa/IR de cada competidor    | `headless` (bypass de 403 por user-agent/JS) |
| `percepcion_cliente`   | Redes sociales, foros, reseñas, PQR                          | `headless` (aún sin collector concreto, ver §7) |
| `expansion_negocio`    | SECOP, vacantes, movimientos societarios                     | `http_api` para SECOP (Socrata), `headless` para lo demás |

## 4. Arquitectura

```
scraper/
├── config/
│   ├── sectores.yaml          # líneas de negocio EPM + qué tipos_dato aplican
│   ├── competidores.yaml      # jugadores por sector, con nivel de confianza
│   └── fuentes_oficiales.yaml # reguladores/datos abiertos por tipo_dato
├── lib/
│   ├── config.py              # carga de los YAML de arriba
│   ├── robots.py              # respeta robots.txt siempre, sin excepción
│   ├── http_client.py         # cliente simple con User-Agent propio + rate limit
│   ├── browser.py             # Playwright/Chromium headless (para sitios bloqueados)
│   ├── store.py                # guarda crudo en ../fuentes/ + dedup por hash
│   └── manifest.py             # esquema y escritura de fuentes/manifest.jsonl
├── collectors/
│   ├── base.py
│   ├── regulacion_datos_abiertos.py   # ejemplo funcional (APIs Socrata)
│   └── noticias_headless.py           # ejemplo funcional (headless browser)
└── cli.py                      # `python -m scraper.cli run --sector <id>`
```

Flujo de datos:

```
cli.py run --sector X
   └─> collectors/*.py (uno por tipo_dato)
         ├─> lib/http_client.py  (fuentes con API/HTML simple)
         │      └─> respeta lib/robots.py, User-Agent identificable, rate limit
         └─> lib/browser.py      (fuentes que bloquean fetch simple)
                └─> respeta lib/robots.py, User-Agent identificable, rate limit
   └─> lib/store.py
         ├─> ./fuentes/<sector>/<tipo_dato>/<entidad>/YYYY-MM-DD_<slug>.<ext>
         └─> ./fuentes/manifest.jsonl   (una línea por captura, con o sin cambio)

Luego, para el informe:
   /mercado <sector>  →  subagente inteligencia-estrategica
         lee ./fuentes/<sector>/... como evidencia ya recolectada
         + WebSearch/WebFetch en vivo para completar huecos
         → escribe ./informes/YYYY-MM-DD_<sector>_inteligencia.md
```

## 5. Esquema del manifest (`fuentes/manifest.jsonl`)

Una línea JSON por captura (éxito, sin cambios, u omitida), nunca se
reescribe una línea anterior — es el registro de auditoría:

```json
{
  "fecha_captura": "2026-09-22T18:42:57+00:00",
  "sector": "energia_electrica",
  "tipo_dato": "noticias",
  "entidad": "celsia",
  "tipo_fuente": "independiente | autorreportado | prensa",
  "url": "https://...",
  "metodo": "http_api | http_simple | headless_browser",
  "estado_http": 200,
  "archivo": "fuentes/energia_electrica/noticias/celsia/2026-09-22_....txt",
  "hash_contenido": "sha256...",
  "cambio_detectado": true,
  "omitido_por_robots": false,
  "notas": ""
}
```

`tipo_fuente` es el mismo concepto que ya usa `inteligencia-estrategica`
para distinguir dato independiente de autorreportado: el scraper lo
etiqueta en el momento de captura para que el subagente no tenga que
adivinarlo después.

## 6. Cumplimiento y buenas prácticas

- **robots.txt siempre se respeta** (`lib/robots.py`): si una ruta está en
  `Disallow`, se omite y queda registrada como `omitido_por_robots: true`.
  El navegador headless resuelve bloqueos por user-agent/JS, no permite
  saltarse reglas de robots.txt.
- **User-Agent identificable**: `lib/http_client.py` arma un User-Agent
  con un contacto configurable por variable de entorno
  (`SCRAPER_CONTACT`), nunca hardcodeado con datos personales. Configúralo
  antes de correr el scraper en serio.
- **Rate limiting por dominio**: mínimo 3s (HTTP simple) o 5s (headless)
  entre solicitudes al mismo dominio, con reintentos con backoff.
- **Nunca se elude un paywall o un login.**
- **Todo dato autorreportado se marca como tal** desde la captura (por
  ejemplo, el contenido del propio sitio de un competidor siempre se
  guarda con `tipo_fuente: autorreportado`), consistente con el principio
  de `inteligencia-estrategica` de nunca presentar eso como independiente.

## 7. Estado de implementación (qué es real y qué es esqueleto)

**Funcional y probado en este entorno (sin red externa, con datos de
prueba):**
- Carga de configuración YAML (`lib/config.py`).
- CLI (`listar-sectores`, `run --sector ... --tipo-dato ...`).
- `collectors/regulacion_datos_abiertos.py`: detecta correctamente que
  `resource_id` está pendiente de configurar y lo registra sin inventar
  una URL.
- `collectors/noticias_headless.py`: detecta correctamente qué
  competidores no tienen `fuentes_noticias` cargadas y lo registra como
  pendiente.
- `lib/store.py` + `lib/manifest.py`: dedup por hash y escritura de
  manifest, verificado con corridas de prueba.

**Diseñado pero pendiente de ejecutar contra internet real** (requiere
correrlo fuera de este sandbox, ver §0):
- Toda captura real de contenido con `lib/browser.py` (Playwright).
- Confirmar que el `resource_id` real de Socrata para el dataset de PQR de
  Superservicios existe y tiene el esquema esperado.
- `percepcion_cliente` y `expansion_negocio`: aún no tienen un módulo de
  collector propio (quedaron como categorías en `sectores.yaml` y
  `fuentes_oficiales.yaml`, pero faltan `collectors/percepcion_cliente_*.py`
  y `collectors/expansion_negocio_secop.py`). Se dejaron para una segunda
  iteración una vez validado el patrón con `regulacion` y `noticias` en un
  entorno con internet real, para no construir sobre supuestos no
  probados.
- Completar los competidores marcados `confianza: completar` en
  `config/competidores.yaml` (sobre todo los 4 sectores de nicho).

## 8. Cómo ejecutarlo (en un entorno con internet real)

```bash
cd AnalisisCompeteciaEPM/scraper
pip install -r requirements.txt
export SCRAPER_CONTACT="tu-correo-o-area@epm.com.co"

python -m scraper.cli listar-sectores
python -m scraper.cli run --sector energia_electrica --tipo-dato regulacion
python -m scraper.cli run --sector energia_electrica --tipo-dato noticias
python -m scraper.cli run --todos   # corre todo lo que tenga collector implementado
```

Antes de correr `noticias` en serio, completa `fuentes_noticias` (lista de
URLs de sala de prensa) por competidor en `config/competidores.yaml` — hoy
está vacío a propósito para no adivinar rutas.

## 9. Ruta de evolución (no implementada, para decidir después)

No se construyó ahora porque elegiste la opción "ligera dentro de Claude
Code" para arrancar. Si más adelante quieres automatizar sin depender de
correrlo manualmente:

1. **GitHub Actions con cron**: mismo código, un workflow que corre
   `python -m scraper.cli run --todos` diario/semanal y hace commit de
   `fuentes/` al repo. Sin costo de servidor propio, con salida a internet
   normal (a diferencia de este sandbox).
2. **Base de datos + alertas**: si el volumen de `fuentes/` crece mucho o
   quieres alertas ("EPM subió tarifa", "competidor X abrió licitación de
   alumbrado"), migrar el manifest de JSONL a Postgres/SQLite y añadir un
   paso que compare `cambio_detectado` entre corridas y notifique.

## 10. Cómo se integra con lo que ya existe en el repo

- `inteligencia-estrategica` (el subagente) debería, antes de salir a
  buscar en vivo, revisar `./fuentes/<sector>/` por si ya hay capturas
  recientes que evitan repetir una búsqueda que sabemos que da 403. Esto
  no se automatizó tocando la definición del subagente en este cambio —
  requiere tu visto bueno, ver la nota al final de mi respuesta.
- El output de este scraper vive en `./fuentes/`, tal como ya lo indica
  `CLAUDE.md` ("Los datos crudos y fuentes descargadas van en `./fuentes/`").
  No se tocó la ubicación ni el nombre de `./informes/`.

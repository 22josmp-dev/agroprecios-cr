# AgroPrecios CR

App web informativa (PWA) con los precios mayoristas de referencia del CENADA, publicados por
el **PIMA – SIMM** en tres boletines: diario (frutas y hortalizas), semanal (fruta importada) y
quincenal (aromáticos y gourmet). Se actualiza sola cada día: nadie carga datos a mano.

- **App pública:** https://22josmp-dev.github.io/agroprecios-cr/
- **Motor:** `ingesta/` (Python) + `.github/workflows/diario.yml` (GitHub Actions)
- Formato de las fuentes: [docs/FORMATO_BOLETIN.md](docs/FORMATO_BOLETIN.md) ·
  Esquema de datos: [docs/DATOS.md](docs/DATOS.md)

## Cómo funciona

```
11:47, 14:47 y 17:47 (hora CR)  GitHub Actions (suele llegar con 3–4 h de atraso)
  └─ python -m ingesta diario      (las 3 fuentes; una falla no detiene a las otras)
       ├─ lista de cada boletín en bpm.pima.go.cr (11 visibles de cada uno)
       ├─ descarga los que falten (1 solicitud/s) y guarda el PDF en archivo/
       ├─ parsea, valida y escribe data/ (latest, prices, rejects, meta)
       └─ si algo falla: conserva los datos buenos, anota el error en data/meta.json
  └─ python -m ingesta estacional
       ├─ PDF de índices del SIMM (se re-descargan solo si cambia la lista o el día 1 del mes)
       └─ data/seasonal.json + data/historico/ (índice propio + índice oficial de referencia)
  ├─ commit de data/ y archivo/
  ├─ arma el sitio (app + data/) y lo publica en GitHub Pages
  └─ si la ingesta falló: el workflow queda en rojo → GitHub te envía un correo
```

## Configuración inicial (una sola vez)

Ya está hecha para `22josmp-dev/agroprecios-cr`. Para montarla en otro repositorio:

1. Crear un repositorio **público** (Pages gratis y minutos de Actions ilimitados solo en
   públicos) y subir este proyecto.
2. *Settings → Pages → Build and deployment → Source:* **GitHub Actions**
   (o `gh api -X POST repos/USUARIO/REPO/pages -f build_type=workflow`).
3. *Actions →* **Prueba de fuentes PIMA** → *Run workflow*: confirma que el PIMA responde a los
   servidores de GitHub.
4. *Actions →* **Actualización diaria** → *Run workflow*: primera carga y publicación.
5. En *Settings → Notifications → System → Actions* confirmar que los avisos por correo de
   ejecuciones fallidas estén activos (ver "¿Quién recibe los correos de falla?").

## Si el proceso diario falla

GitHub te envía un correo "Run failed: Actualización diaria". La app sigue mostrando los últimos
datos buenos; si pasan más de 3 días sin actualización exitosa, avisa que pueden estar desactualizados.

1. Abrir la ejecución fallida en *Actions*; el **Summary** muestra el mensaje de `data/meta.json`.
2. Según el mensaje:

| Mensaje | Qué pasó | Qué hacer |
|---|---|---|
| `El boletín de hoy (…) no está publicado` | El PIMA no publicó (feriado, atraso) | Nada. Si publica tarde, el próximo intento lo toma. Revisar https://www.pima.go.cr/boletin/ |
| `No se pudo leer la lista… HTTP / intentos` | Sitio caído o bloqueo | Reintentar a mano más tarde. Si persiste días, ver "Plan B" |
| `No se encontró el encabezado…`, `ErrorFormato` | El PIMA cambió el formato del PDF | Ver "Actualizar el parser" |
| `Solo N registros válidos…` | El PDF trae muchos menos productos o el parser perdió filas | Revisar `data/rejects/` y el PDF en `archivo/`. Si el boletín es así de verdad, reprocesar con `UMBRAL_REGISTROS` más bajo |
| `producto no reconocido` en `data/rejects/` | Producto nuevo o renombrado | Agregarlo a `data/catalog.json` y reprocesar |

⚠️ El sitio del PIMA solo muestra los últimos 11 boletines de cada tipo: ~2 semanas del diario,
~2,5 meses de fruta importada y ~5 meses de aromáticos. Un problema sin atender por más tiempo
pierde esos boletines. Los mensajes de error indican la fuente ("Fruta importada", etc.); el
comando acepta `--fuente diario|fruta|aromaticos` para procesar o reprocesar solo una.

**Plan B (si GitHub fuera bloqueado por el PIMA):** correr el mismo motor en una computadora
propia con el Programador de tareas de Windows y hacer `git push` de `data/` y `archivo/`
(`python -m ingesta diario && git add data archivo && git commit -m Datos && git push`).
El workflow seguiría publicando el sitio.

## Verificación de punta a punta

`tests/test_e2e.py` ejecuta el comando real `python -m ingesta diario` contra un **PIMA simulado**
(`tests/pima_simulado.py`, imita el flujo del portal real) con los PDF reales archivados, en una
copia temporal del repositorio. Escenarios: instalación nueva, día nuevo, segundo intento sin
cambios, día sin boletín (pendiente → error en el último intento), cambio de formato que rompe
(error, datos intactos, PDF guardado), cambio de formato tolerable (otro orden de columnas y
`1.000,00`), sitio caído (503 con reintentos), y un boletín viejo re-subido con otra fecha
(rechazado). Corre en cada cambio en el workflow **Pruebas**.

Para comprobar que llegan los correos de falla: *Actions → Probar aviso de falla → Run workflow*
(falla a propósito, no toca datos). Verificado el 29-09-2026: el correo llegó al propietario
(22josmp-dev).

## Actualizar el parser si el PIMA cambia el formato

1. Descargar el PDF problemático (queda en `archivo/boletines/AAAA/`).
2. Ver qué lee el parser: `python -m ingesta parsear archivo/boletines/…pdf`
   (`--palabras` prueba el método de respaldo).
3. Ajustar `ingesta/parser_boletin.py`; agregar el PDF a `tests/samples/boletines/` con una prueba.
4. `pip install -r requirements-dev.txt && python -m pytest -q`
5. `python -m ingesta reprocesar` (re-lee todos los PDF archivados) y subir los cambios.

## La app (carpeta `app/`)

**Elección:** Vite + TypeScript + **Preact** (API de React en 4 KB) con **gráficos SVG propios**
en lugar de React + Recharts + Tailwind. Se logra lo mismo (componentes, tipado, gráficos
interactivos con tooltip y tabla alternativa) con **≈ 22 KB de JavaScript comprimido** en vez de
≈ 150 KB, lo que importa con datos móviles limitados. CSS propio con variables (modo claro y
oscuro), sin framework de CSS.

- Pantallas: Inicio (buscador, favoritos, resumen del día, lista), Detalle del producto, Guía de
  siembra y Ayuda. Rutas por `#/…` (funciona en GitHub Pages sin configuración).
- Lee `data/*.json` por fetch relativo; el esquema está en [docs/DATOS.md](docs/DATOS.md).
- Lógica probada (Vitest, 25 pruebas): buscador tolerante, motor de la guía de siembra, frescura
  de los datos, resumen del día, fechas y formatos (`app/src/*.test.ts`).
- **PWA:** manifiesto con íconos 192/512 y maskable (`scripts/generar_iconos.py`). El
  service worker (`sw.js`, generado en la compilación) guarda la app y, al instalarse,
  `meta`, `latest`, `catalog`, `seasonal`, `cycle_defaults` y los últimos 2 meses de precios:
  todo funciona sin conexión. El historial mensual de cada producto (`data/historico/`) se guarda
  la primera vez que se abre ese producto. Los datos se piden siempre primero a la red.
- Accesibilidad: texto base de 18 px, contrastes WCAG AA verificados en claro y oscuro, cambios
  con flecha + palabra + color, foco visible, buscador con patrón *combobox*, gráficos con
  descripción y tabla de datos, diseño desde 360 px sin desplazamiento horizontal.

## Desarrollo local

```bash
pip install -r requirements-dev.txt
python -m pytest -q
python -m ingesta diario
python -m ingesta estacional
cd app && npm ci && npm test && npm run dev    # http://localhost:5173 con los datos de ../data
npm run build && cd .. && python scripts/armar_sitio.py
```

## Límites de las plataformas gratuitas

Verificados en la documentación oficial de GitHub el 29-09-2026.

| Plataforma | Límite | Uso de este proyecto |
|---|---|---|
| **GitHub Actions** (repo público) | Gratis en runners estándar; 6 h por job; 20 jobs simultáneos | ~2 ejecuciones/día de < 1 min |
| Actions – programación (`schedule`) | Puede **retrasarse** en horas de carga y, con carga muy alta, **omitirse**; se **desactiva tras 60 días sin actividad** en repos públicos | Dos intentos diarios; ver "Inactividad" abajo |
| Actions – artefactos | 500 MB de almacenamiento (plan Free) | Artefacto del sitio ≈ 0,1 MB, vida corta |
| **GitHub Pages** | Sitio ≤ 1 GB; ancho de banda *suave* 100 GB/mes; despliegue ≤ 10 min; prohibido uso comercial/SaaS | Sitio ≈ 0,7 MB + ≈ 40 KB/mes de datos |
| Repositorio | Recomendado ≤ 1 GB | PDF originales ≈ 55 MB/año → ~15 años antes de acercarse |

**Riesgos de exceder:** ninguno previsible. El más cercano es el ancho de banda si la app se
volviera muy popular: 100 GB/mes equivalen a más de 1 millón de primeras visitas al mes
(≈ 85 KB cada una); las visitas siguientes usan la caché del teléfono. Si se acercara, publicar el mismo sitio también en Cloudflare Pages (gratis) o mover
`archivo/` a otro repositorio.

### Inactividad (desactivación a los 60 días)

GitHub desactiva los workflows programados de repos públicos tras 60 días sin actividad
("activity includes commits"). Medida aplicada: **cada ejecución hace commit de
`data/meta.json`** (cambia siempre `ultimo_intento_utc`), o sea, dos commits reales por día.

Se descartó a propósito la alternativa de llamar desde el workflow a la API
`…/actions/workflows/diario.yml/enable` (lo que hace la acción comunitaria
`gh-workflow-keepalive`): según la documentación de GitHub, tras re-habilitar un workflow
programado los avisos de falla se envían **a quien lo re-habilitó**, y eso podría desviar los
correos de falla al bot en lugar del propietario.

Si aun así la programación se desactivara, se reactiva con un clic en
*Actions → Actualización diaria → Enable workflow* (hecho por el propietario, los avisos le siguen
llegando a él).

### ¿Quién recibe los correos de falla?

Según GitHub: el usuario que creó el workflow programado o el último que modificó la línea
`cron`, o quien lo re-habilitó. Hoy es **22josmp-dev**. Si otra persona edita el `cron`, los
avisos pasan a esa persona. Configuración: *Settings → Notifications → System → Actions*
(se puede elegir "solo ejecuciones fallidas").

## Costos

**₡0.** GitHub Actions (repositorio público), GitHub Pages y el repositorio son gratuitos y no
requieren tarjeta. No hay servidor propio, base de datos, funciones en la nube ni APIs de pago.
Los usuarios solo gastan los datos móviles de cargar la app (≈ 25 KB de app + ≈ 60 KB de datos
comprimidos la primera vez; después funciona desde la caché del teléfono y solo baja los datos
nuevos).

## Datos y privacidad

- Fuente: **PIMA – SIMM** (https://www.pima.go.cr/boletin/). Precios mayoristas de referencia de
  productos de primera calidad; el precio en finca es distinto.
- La app no tiene cuentas ni formularios y no recolecta datos personales. Solo guarda en el
  teléfono (localStorage) los cultivos marcados como favoritos.
- Permiso de uso de los datos: pendiente de confirmar por escrito con simm@pima.go.cr
  (borrador en [docs/CORREO_SIMM.md](docs/CORREO_SIMM.md)).
- Los ciclos de cultivo (`data/cycle_defaults.json`) son estimaciones **no verificadas**
  (`verified: false`) hasta que un técnico del MAG/INTA las revise.

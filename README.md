# AgroPrecios CR

App web informativa (PWA) con los precios mayoristas de referencia del CENADA, publicados por
el **PIMA – SIMM**. Se actualiza sola cada día: nadie carga datos a mano.

- **App pública:** https://22josmp-dev.github.io/agroprecios-cr/
- **Motor:** `ingesta/` (Python) + `.github/workflows/diario.yml` (GitHub Actions)
- Formato de las fuentes: [docs/FORMATO_BOLETIN.md](docs/FORMATO_BOLETIN.md) ·
  Esquema de datos: [docs/DATOS.md](docs/DATOS.md)

## Cómo funciona

```
13:17 y 17:17 (hora CR)  GitHub Actions
  └─ python -m ingesta diario
       ├─ lista de boletines en bpm.pima.go.cr (≈ 2 semanas visibles)
       ├─ descarga los que falten (1 solicitud/s) y guarda el PDF en archivo/
       ├─ parsea, valida y escribe data/ (latest, prices, rejects, meta)
       └─ si algo falla: conserva los datos buenos, anota el error en data/meta.json
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

⚠️ Solo se ven ~2 semanas de boletines en el sitio del PIMA: un problema sin atender por más
tiempo pierde esos días.

**Plan B (si GitHub fuera bloqueado por el PIMA):** correr el mismo motor en una computadora
propia con el Programador de tareas de Windows y hacer `git push` de `data/` y `archivo/`
(`python -m ingesta diario && git add data archivo && git commit -m Datos && git push`).
El workflow seguiría publicando el sitio.

## Actualizar el parser si el PIMA cambia el formato

1. Descargar el PDF problemático (queda en `archivo/boletines/AAAA/`).
2. Ver qué lee el parser: `python -m ingesta parsear archivo/boletines/…pdf`
   (`--palabras` prueba el método de respaldo).
3. Ajustar `ingesta/parser_boletin.py`; agregar el PDF a `tests/samples/boletines/` con una prueba.
4. `pip install -r requirements-dev.txt && python -m pytest -q`
5. `python -m ingesta reprocesar` (re-lee todos los PDF archivados) y subir los cambios.

## Desarrollo local

```bash
pip install -r requirements-dev.txt
python -m pytest -q
python -m ingesta diario
python scripts/armar_sitio.py
```

## Límites de las plataformas gratuitas

Verificados en la documentación oficial de GitHub el 29-09-2026.

| Plataforma | Límite | Uso de este proyecto |
|---|---|---|
| **GitHub Actions** (repo público) | Gratis en runners estándar; 6 h por job; 20 jobs simultáneos | ~2 ejecuciones/día de < 1 min |
| Actions – programación (`schedule`) | Puede **retrasarse** en horas de carga y, con carga muy alta, **omitirse**; se **desactiva tras 60 días sin actividad** en repos públicos | Dos intentos diarios; ver "Inactividad" abajo |
| Actions – artefactos | 500 MB de almacenamiento (plan Free) | Artefacto del sitio ≈ 0,1 MB, vida corta |
| **GitHub Pages** | Sitio ≤ 1 GB; ancho de banda *suave* 100 GB/mes; despliegue ≤ 10 min; prohibido uso comercial/SaaS | Sitio ≈ 0,1 MB + ≈ 40 KB/mes de datos |
| Repositorio | Recomendado ≤ 1 GB | PDF originales ≈ 55 MB/año → ~15 años antes de acercarse |

**Riesgos de exceder:** ninguno previsible. El más cercano es el ancho de banda si la app se
volviera muy popular: 100 GB/mes equivalen a unas 500 000 visitas completas al mes con la app
actual. Si se acercara, publicar el mismo sitio también en Cloudflare Pages (gratis) o mover
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
Los usuarios solo gastan los datos móviles de cargar la app (≈ 100 KB la primera vez; después
funciona desde la caché del teléfono).

## Datos y privacidad

- Fuente: **PIMA – SIMM** (https://www.pima.go.cr/boletin/). Precios mayoristas de referencia de
  productos de primera calidad; el precio en finca es distinto.
- La app no tiene cuentas ni formularios y no recolecta datos personales. Solo guarda en el
  teléfono (localStorage) los cultivos marcados como favoritos.
- Permiso de uso de los datos: pendiente de confirmar por escrito con simm@pima.go.cr.

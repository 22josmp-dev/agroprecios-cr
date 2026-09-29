# Formato de las fuentes PIMA – SIMM

Análisis hecho el 28-09-2026 (hora de Costa Rica) sobre las fuentes reales. Todo lo que dice
"verificado" se probó descargando y leyendo los archivos; lo demás está marcado como pendiente.

## 1. Dónde están los datos

| Página pública | Qué contiene realmente |
|---|---|
| `https://www.pima.go.cr/boletin/` | Página WordPress que solo incrusta un iframe: `https://bpm.pima.go.cr/cm.aspx?id=4` |
| `https://www.pima.go.cr/simm/` | Texto informativo, menú y un formulario externo (form-platform.com). No trae datos. |
| `https://www.pima.go.cr/reporte-indices-estacionales/` | Iframe `https://bpm.pima.go.cr/cm.aspx?id=77` con los índices estacionales oficiales |
| `https://www.pima.go.cr/boletin-de-precios-de-fruta-importada/` | Iframe `cm.aspx?id=79` (no analizado, fuera del alcance) |
| `https://www.pima.go.cr/boletin-de-productos-aromaticos-y-goutmet/` | Iframe `cm.aspx?id=50` (no analizado) |
| `https://bpm.pima.go.cr/Visitor.aspx?id=21&idPortal=0` | Formulario de "Solicitud de Información de Mercados" con CAPTCHA. **No se automatiza.** Es la vía oficial para pedir históricos (ver `docs/CORREO_SIMM.md`, Paso 4). |

`bpm.pima.go.cr` es un portal **AuraPortal** (ASP.NET WebForms).

**No existe descarga en Excel/CSV** en las páginas públicas (verificado): la única fuente
automatizable es el PDF.

## 2. Cómo se obtiene el boletín más reciente (verificado sin navegador)

1. `GET https://bpm.pima.go.cr/cm.aspx?id=4` → `302` a `/ScreenResolution.aspx?returnURL=...`
   y entrega la cookie `ASP.NET_SessionId`.
2. `GET /ScreenResolution.aspx?...` → HTML pequeño cuyo JavaScript envía el tamaño de pantalla.
3. `POST /ScreenResolution.ashx` con cuerpo JSON `{"width":1280,"height":800}` y cabeceras
   `Content-Type: application/json; charset=UTF-8`, `X-Requested-With: XMLHttpRequest`,
   `Referer` y `Origin`. Respuesta `{"isMobile":false}`.
   **Sin `X-Requested-With` el servidor responde 302 a `/error.aspx?err=0`** (probado).
4. `GET /cm.aspx?id=4` de nuevo (con la cookie) → `200` con la lista.
5. Cada boletín es un enlace `https://bpm.pima.go.cr/AccessDoc.aspx?<token cifrado>` con el texto
   "Documentos adjuntos"; `AccessDoc` hace `302` a `/GetDoc.aspx?<token>` que devuelve
   `application/octet-stream` con
   `Content-Disposition: attachment; filename="SIMM-Boletin de Precios PIMA-Plaza AAAA-MM-DD.pdf"`.

**Los tokens de los enlaces no son predecibles** (cambian por documento), así que siempre hay
que leer la lista; no se puede construir la URL a partir de la fecha.

### Lista
- Título de cada entrada:
  `Boletín Diario de Precios sugeridos de Frutas y Hortalizas PIMA-CENADA. Plaza <Día> DD-MM-AAAA`
  (el día lleva tilde: "Miércoles"; usar `\S+`, no `\w+`, para capturarlo).
- La primera entrada es la más reciente; debajo, bajo "Historial", siguen las anteriores.
- Solo se muestran **11 boletines** (unas dos semanas hábiles). **No hay historial público más
  antiguo**: el campo de fecha que aparece en el HTML no filtra la lista (probado; navega a otra
  pantalla del portal). Si el proceso diario falla más de ~2 semanas, esos días se pierden.
- Fuente de verdad para la fecha: el nombre de archivo en `Content-Disposition` y la
  "Fecha de Plaza" dentro del PDF (se comparan entre sí).

### Frecuencia y hora de publicación (11 boletines, 14–28 sep 2026)
- Hay boletín **de lunes a viernes**; no hubo sábado ni domingo en la muestra.
- Feriados: **sí hubo boletín el martes 15-09-2026 (Día de la Independencia, feriado)**, así
  que el CENADA opera al menos algunos feriados. El motor procesa cualquier boletín que aparezca;
  la lista de feriados en `ingesta/config.py` solo evita una falsa alarma de "boletín no
  publicado" en esos días. Otros feriados: sin verificar.
- `Fecha de Plaza` a las 09:19 (ej. 28-09). El PDF se genera (`CreationDate`) entre las
  **10:22 y 11:56** hora de Costa Rica (UTC−6).
- El boletín del 28-09 tiene `ModDate` 10:59 y otro productor de PDF: **un boletín puede
  republicarse el mismo día**. Por eso la idempotencia es por SHA-256 del archivo, no por fecha.
- Propuesta de horario: 1.er intento **13:00 CR (19:00 UTC)**, 2.º intento **17:00 CR (23:00 UTC)**.

## 3. Formato del PDF del boletín (verificado en 11 archivos)

- A4 vertical, **2 páginas**, texto seleccionable (no escaneado). Metadatos `Title: DataWindow`,
  generado con "Microsoft: Print To PDF" (o "4-Heights PDF Library" si fue retocado).
- Encabezado en cada página:
  ```
  SIFPIMA
  28/09/2026
  SIMM
  SISTEMA DE INFORMACION DE MERCADOS MAYORISTAS
  BOLETIN DE PRECIOS: PRECIOS DE MAYORISTA A MINORISTA
  CENADA, HEREDIA, COSTA RICA
  Fecha de Plaza: 28/9/2026 09:19:00      <- D/M/AAAA sin ceros; la hora a veces no aparece
  Precio por unidad de comercialización
  Producto Unidad de comercialización mayorista Mínimo Máximo Moda Promedio
  ```
- Pie de página: `Fecha: 28 de Setiembre del 2026 Fecha de Plaza: 28/09/2026 Pag. 1 de 2`
  ("Setiembre", ortografía costarricense).
- **Orden real de columnas: `Producto | Unidad | Mínimo | Máximo | Moda | Promedio`.**
  ⚠️ Difiere del supuesto inicial (Promedio | Moda | Máximo | Mínimo). El parser debe ubicar las
  columnas **por el texto del encabezado**, no por posición fija, y fallar si no lo encuentra.
- Una sola sección (frutas y hortalizas juntas, orden alfabético); no hay subtítulos de sección.
- `pdfplumber.extract_tables()` devuelve filas de **6 columnas bien separadas** en los 11 archivos
  (619 filas). El encabezado de la tabla queda fuera de la tabla, en el texto. La única fila
  espuria detectada fue el pie "Fecha: 16 de Setiembre del 2026" (hay que ignorarla).
- Productos por día (cambia según la plaza, no es error):

  | Día | Filas |
  |---|---|
  | Lunes y viernes | 57 |
  | Martes y jueves | 51 |
  | Miércoles | 65 |

  → El umbral de "muy pocos registros" debe compararse con el **mismo día de la semana**
  (ej. mínimo 80 % del último boletín del mismo día), no con el boletín anterior.
- 65 nombres de producto distintos en 2 semanas. Variantes de calidad forman parte del nombre
  ("Tomate primera/segunda/tercera", "Chile dulce jumbo/primera/…", "Piña - grande").
  Un caso curioso real: "Camote Zanahoria".
- Unidades observadas: `Kilo`, `Unidad`, `Malla (45 kg)`, `Caja plástica`,
  `Caja plástica (17 kg)`, `Caja plástica (18 kg)`, `Caja plástica (27 kg)`, `Java`, `Mata`,
  `Caja`, `Rollo`, `Rollo de 10 rollitos`, `Bandeja (1 kg)`, `Bandeja (400 g)`.
  El peso a veces está en la **unidad** ("Caja plástica (17 kg)") y a veces en el **producto**
  ("Fresa (1 Kg)", "Apio verde (mata)"). Se extrae con regex `\((\d+(?:[.,]\d+)?)\s*(kg|g)\)`.
- Formato numérico: **todos los valores usan `1,000.00`** (coma de miles, punto decimal) en los
  11 boletines y en los PDF de índices. **No se encontró ningún boletín con `1.000,00`**; como no
  hay historial público más antiguo, no se pudo verificar si ese formato existió. El parser
  detecta ambos igualmente; la prueba de `1.000,00` usa una muestra **sintética marcada como tal**.
- Validaciones sobre los 619 registros reales: mínimo ≤ moda ≤ máximo, mínimo ≤ promedio ≤
  máximo y precios > 0 se cumplen en el **100 %** (0 inválidos).
- No hay volúmenes ni procedencia en el boletín diario.

## 4. Índices estacionales oficiales (cm.aspx?id=77) — verificado

- 78 documentos: 1 instructivo + 77 productos. Título: `<Producto> índice estacional de oferta y
  precio para el año 2026`. PDF de 1 página generado desde Excel, texto seleccionable.
- Cada PDF trae **dos tablas** (extract_tables las separa bien, 33 filas):
  1. Oferta en CENADA (toneladas métricas): filas Enero…Diciembre + Promedio; columnas por año
     **2018–2025** + "Índice Estacional".
  2. Precio promedio mayorista (colones por la unidad indicada en el título de la tabla, ej.
     "colones por Kilo", "colones por Caja plástica (18 kg)"): mismas filas/columnas.
- Método oficial (instructivo DEDM-SIMM-INF-007-26): "Porcentaje Promedio" — % de cada mes respecto
  al promedio de su año, promediado entre 8 años (algunos productos 4–7 años; el instructivo trae
  la tabla de años por producto).
- **Consecuencia importante:** estos PDF contienen **8 años de precios mensuales** por producto.
  Con eso se puede calcular nuestro índice (media móvil centrada + mediana) con confianza alta,
  sin esperar años de boletines diarios. Se ingieren ambos: el oficial (referencia) y el calculado.
- El nombre del producto del índice no siempre coincide con el del boletín ("Tomate Primera" vs
  "Tomate primera"; "Manga Keith" vs "Manga grande Keitt") → se resuelve en `catalog.json`
  (sinónimos).
- Se publican una vez al año (edición "Agosto 2026"). Basta revisarlos mensualmente.
- También existe un PDF "Calendario de Estacionalidad según Precios 2026" (menú del sitio);
  no se analizó porque los índices por producto ya dan la información en forma tabular.

## 5. robots.txt y términos de uso

- `www.pima.go.cr/robots.txt`: solo prohíbe `/wp-admin/` y un JSON interno. `/boletin/` y
  `/simm/` están permitidos.
- `bpm.pima.go.cr/robots.txt` no existe como tal: redirige a la pantalla de login y devuelve HTML.
  Se interpreta como "sin restricciones declaradas", pero se actúa con prudencia: ≤ 1 solicitud
  por segundo, ~25 solicitudes por ejecución, User-Agent identificable.
- **No se encontraron términos de uso** en las páginas revisadas. Los datos son públicos y de una
  institución estatal, pero **conviene confirmar el permiso de uso por escrito** con el SIMM
  (incluido en el borrador de correo del Paso 4).

## 6. Prueba desde GitHub Actions

- Local (Windows, red residencial de Costa Rica): **OK**, sin bloqueos, con
  `scripts/probe_fuentes.py` (solo biblioteca estándar).
- **GitHub Actions (`ubuntu-latest`, 29-09-2026): OK.** Ejecución
  https://github.com/22josmp-dev/agroprecios-cr/actions/runs/36525180702 del workflow
  `.github/workflows/probe-fuentes.yml`: 11 boletines listados, PDF del 28-09 descargado con el
  mismo SHA-256 que la descarga local (`089940e6b6d3963c…`), 78 índices listados y el del tomate
  descargado. No hubo bloqueo por IP de centro de datos. El servidor manda `Vary: User-Agent`,
  pero con nuestro User-Agent de bot respondió normal.
- Avisos de GitHub en esa ejecución: `actions/checkout@v4` y `actions/setup-python@v5` usan
  Node 20 (obsoleto) y `ubuntu-latest` pasa a Ubuntu 26 desde el 19-10-2026. Se actualizarán las
  versiones de las acciones en el workflow diario (Paso 3).
- El acceso puede cambiar en el futuro. **Plan B si GitHub llegara a ser bloqueado (gratis):** ejecutar el mismo script en una computadora propia
  con el Programador de tareas de Windows (o cron en Linux/Raspberry Pi) y que haga `git push`
  de `/data`; GitHub Actions solo publicaría la app. Se documentará en el README.

## 7. Riesgos detectados

1. El portal depende del paso `ScreenResolution`; si el PIMA cambia de plataforma, el descargador
   falla → el workflow termina en rojo y los datos anteriores se conservan.
2. Solo ~2 semanas de boletines visibles: una caída larga del proceso pierde días sin recuperación.
3. Columnas en orden distinto al supuesto: el parser lee el encabezado para mapearlas.
4. Posible republicación el mismo día (visto el 28-09): se reprocesa si cambia el SHA-256.

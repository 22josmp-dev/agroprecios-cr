# Esquema de los datos publicados

La app lee estos archivos por `fetch` relativo desde `/data`. Todos llevan `"esquema": 1`,
`"fuente": "PIMA – SIMM"` y `"datos_de_ejemplo"` (`false` en datos reales; `true` en cualquier
archivo de ejemplo, que la app debe rotular como **DATOS DE EJEMPLO**). Fechas en ISO
(`AAAA-MM-DD`); momentos en UTC (`AAAA-MM-DDTHH:MM:SSZ`). Precios en colones por la unidad de
comercialización indicada.

Estado: ✅ generado por el motor · ⏳ pendiente (paso indicado).

**Fuentes (boletines):** `diario` (frutas y hortalizas, lunes a viernes), `fruta` (fruta importada,
semanal) y `aromaticos` (aromáticos y gourmet, quincenal). El diario usa las rutas de siempre;
las otras dos, subcarpetas con su id: `data/prices/fruta/`, `data/rejects/aromaticos/`,
`archivo/fruta/`, etc.

## ✅ `data/meta.json` — estado del proceso

| Campo | Significado |
|---|---|
| `estado` | `ok` · `pendiente` (el boletín de hoy aún no sale; se reintenta) · `error` |
| `mensaje` | Explicación en español del último intento |
| `ultimo_intento_utc` | Última ejecución, haya salido bien o mal |
| `ultima_actualizacion_exitosa_utc` | Última ejecución sin errores. La app avisa si tiene más de 3 días |
| `fecha_boletin` | Fecha de plaza del boletín más reciente con datos válidos |
| `registros`, `rechazados` | Conteos de ese boletín |
| `sha256` | Huella del PDF de ese boletín |
| `dias_con_datos` | Días de boletín acumulados |
| `meses_precios` | Meses con archivo `data/prices/AAAA-MM.json` (la app los usa para las tendencias) |
| `fuentes` | `{fruta: {…}, aromaticos: {…}}` con `nombre`, `frecuencia`, `estado`, `mensaje`, `ultimo_intento_utc`, `ultima_actualizacion_exitosa_utc`, `fecha_boletin`, `registros`, `rechazados`, `boletines_con_datos`, `meses_precios` (meses en `data/prices/<id>/`) |
| `historial` | Últimos 30 intentos `{utc, estado, mensaje}` |

Si un intento falla, `fecha_boletin`, `registros` y `ultima_actualizacion_exitosa_utc` conservan
los valores del último éxito: los datos buenos nunca se reemplazan por datos fallidos.

## ✅ `data/latest.json` — último boletín de cada fuente con comparaciones listas

Esquema 2: `fuentes` (`{diario|fruta|aromaticos: {nombre, frecuencia, fecha_boletin,
ventana_promedio_dias, texto_promedio}}`) y, en cada producto, `fuente` y `fecha_boletin`.
`fecha_boletin` del nivel superior es la del boletín diario.

```json
{"esquema":1,"fuente":"PIMA – SIMM","datos_de_ejemplo":false,
 "fecha_boletin":"2026-09-28","generado_utc":"…",
 "productos":[{
   "id":"tomate-primera","nombre":"Tomate primera","cultivo":"Tomate","cultivo_id":"tomate",
   "categoria":"hortaliza","unidad":"Caja plástica (18 kg)","kg":18.0,
   "minimo":10000.0,"maximo":10000.0,"moda":10000.0,"promedio":10000.0,"precio_kg":555.56,
   "vs_anterior":{"fecha":"2026-09-25","promedio":15666.67,"variacion_pct":-36.2},
   "vs_semana":{"fecha":"2026-09-21","promedio":19666.67,"variacion_pct":-49.2},
   "fuente":"diario","fecha_boletin":"2026-09-28",
   "vs_promedio":{"boletines":10,"promedio":16505.0,"variacion_pct":-39.4}}]}
```

- `kg`: kilos por unidad **solo si el boletín los declara** (`Malla (45 kg)`, `Bandeja (400 g)`,
  `Kilo`). `null` para `Unidad`, `Java`, `Caja plástica`, etc.: no se inventan pesos.
  `precio_kg = promedio / kg` cuando hay `kg`.
- Comparaciones sobre el **promedio** y solo con la **misma unidad**:
  - `vs_anterior`: boletín anterior en que apareció el producto.
  - `vs_semana`: boletín más cercano entre 7 y 13 días antes (solo el diario; `null` en los demás).
  - `vs_promedio`: media de los boletines de la ventana de la fuente (diario 30 días, fruta 35,
    aromáticos 63), sin contar el actual; requiere al menos 3 boletines, si no es `null`.
  - `variacion_pct` = (hoy − referencia) / referencia × 100, con 1 decimal.

## ✅ `data/prices/AAAA-MM.json` — histórico diario por mes

```json
{"esquema":1,"mes":"2026-09","fuente":"PIMA – SIMM","datos_de_ejemplo":false,
 "columnas":["id","unidad","minimo","maximo","moda","promedio"],"dias":{
"2026-09-14":[["apio-verde-mata","Mata",1000.0,1300.0,1200.0,1150.0], …],
"2026-09-15":[…]
}}
```
Filas compactas en el orden de `columnas`; un día por línea (diferencias de git legibles).
Aproximadamente 40 KB por mes.

## ✅ `data/catalog.json` — productos

```json
{"esquema":1,"productos":[{
  "id":"camote","nombre":"Camote","cultivo":"Camote","cultivo_id":"camote","fuente":"diario",
  "categoria":"raíz y tubérculo","sinonimos":["batata","boniato"],
  "nombres_boletin":["Camote"],"unidades":[{"unidad":"Kilo","kg":1.0}]}]}
```
- `id`: identificador estable (nombre del boletín sin tildes ni signos).
- `cultivo`/`cultivo_id`: agrupa variantes (Tomate primera/segunda/tercera → Tomate) para la
  búsqueda y la guía de siembra.
- `fuente`: boletín al que pertenece (`diario`, `fruta`, `aromaticos`). El mismo nombre se busca
  solo dentro de su boletín.
- `sinonimos`: en minúscula y con su ortografía (la búsqueda ignora tildes).
- `nombres_boletin`: nombres exactos con que el PIMA publica el producto. **Para aceptar un
  producto nuevo o renombrado**, se agrega aquí (o un producto nuevo) y se corre
  `python -m ingesta reprocesar`.
- `unidades`: el proceso diario agrega solo las unidades nuevas que observa.
- Curado a mano el 29-09-2026 con los 65 productos de los boletines del 14 al 28 de setiembre;
  los sinónimos son equivalencias comunes y conservadoras.

## ✅ `data/rejects/AAAA-MM-DD.json` — registros rechazados

```json
{"esquema":1,"fecha_boletin":"2026-09-28","sha256":"…","generado_utc":"…","total":1,
 "rechazados":[{"producto":"Durián","unidad":"Kilo","valores":{"minimo":"1,000.00",…},
   "motivos":["producto no reconocido en el catálogo"],"pagina":2}]}
```
Motivos posibles: número ilegible, fila sin producto o unidad, producto no reconocido, precio ≤ 0,
mínimo > moda, moda > máximo, promedio fuera de [mínimo, máximo] (tolerancia 0,5 %), producto y
unidad repetidos, fila con columnas no reconocidas. Se genera un archivo por boletín aunque esté
vacío (`total: 0`), como constancia.

## ✅ `archivo/` — originales (en el repositorio, **no** se publica en la app)

- `archivo/boletines/AAAA/AAAA-MM-DD_<sha12>.pdf`: copia de cada PDF descargado, también de los
  que fallaron, para reprocesarlos después de corregir el parser.
- `archivo/registro.json`: una entrada por PDF: `fecha`, `sha256`, `archivo`, `nombre_original`,
  `url_lista` (el enlace AccessDoc es temporal), `descargado_utc`, `estado`
  (`procesado` · `fallido` · `reemplazado`), `registros`, `rechazados`, `formato_numerico`, `error`.
- Tamaño: ≈ 216 KB por boletín, ≈ 55 MB por año.

## ✅ `data/seasonal.json` — índices estacionales de precio

Se regenera en cada ejecución diaria (`python -m ingesta estacional`). Fuente: los PDF de
índices estacionales del SIMM (76 productos, precios mensuales 2018–2025), más los meses
completos del boletín diario desde 2026 cuando la unidad coincide.

```json
{"esquema":1,"fuente":"PIMA – SIMM","datos_de_ejemplo":false,"generado_utc":"…",
 "edicion_simm":[2026],"estado":"ok","avisos":[],"metodo":{…},
 "productos":[{
   "id":"tomate-primera","nombre":"Tomate Primera","cultivo_id":"tomate","cultivo":"Tomate",
   "productos_boletin":["tomate-primera"],"unidad_precio":"Caja plástica (18 kg)",
   "years_of_data":8,"confianza":"baja",
   "indice":[1.0937,0.8955,…],        "desviacion":[0.31,…],   "desviacion_media":0.3002,
   "n_ratios":[7,…],"metodo":"media_movil_12","meses_sin_dato":[],"motivo":null,
   "indice_oficial_simm":[1.2146,…],  "indice_oferta_oficial_simm":[0.8935,…],
   "meses_del_boletin_diario":0,"verificacion_dif_max":0.0}]}
```

| Campo | Significado |
|---|---|
| `indice` | 12 valores (enero…diciembre), promedio 1.0. `null` en meses sin mercado |
| `metodo` | `media_movil_12`: ratio = precio / media móvil centrada 2×12; índice = mediana de ratios entre años. `promedio_anual`: respaldo para frutas de temporada con meses sin dato (ratio contra el promedio de los meses con dato del año) |
| `desviacion` | Desviación estándar de los ratios de cada mes (riesgo); `desviacion_media` su promedio |
| `years_of_data` | Años con al menos 3 meses con precio (un año recién empezado no cuenta) |
| `anios` | `[primero, último]` de esos años, p. ej. `[2018, 2025]` |
| `confianza` | `alta`: ≥ 5 años y `desviacion_media` ≤ 0,15 · `media`: 3–4 años · `baja`: cualquier otro caso (incluye < 3 años y precios muy variables) |
| `indice_oficial_simm` | Índice publicado por el SIMM (método porcentaje promedio), como referencia |
| `productos_boletin` | Ids de `catalog.json` con el mismo producto y calidad; vacío si solo coincide el cultivo |
| `verificacion_dif_max` | Diferencia máxima al reproducir el índice oficial con los datos leídos (0 = lectura exacta) |

La desviación media de los 76 productos va de 0,01 a 0,83 (mediana 0,12). El umbral 0,15 se
puede cambiar con la variable `DESVIACION_BAJA`.

## ✅ `data/historico/<id>.json` — precio y oferta mensual por producto

Para los gráficos de 12 meses y la comparación entre años (≈ 2,5 KB cada uno, se carga solo al
abrir el detalle de un producto).

```json
{"id":"camote","nombre":"Camote","unidad_precio":"Kilo",
 "precio":{"2018":[619.05,640.0,…],"2019":[…]},
 "oferta_tm":{"2018":[136.6,…]},
 "meses_boletin_diario":[]}
```
`null` = mes sin dato. `meses_boletin_diario` lista los meses tomados del boletín diario
(media de la moda) en vez de las tablas del SIMM.

## ✅ `data/cycle_defaults.json` — ciclos típicos (NO verificados)

```json
{"verified":false,"altitudes":{"baja":"menos de 800 m s. n. m.",…},
 "cultivos":[{"cultivo_id":"tomate","nombre":"Tomate","tipo":"anual","referencia":"trasplante",
   "ciclo_dias":{"baja":75,"media":85,"alta":100},"ventana_cosecha_dias":50,"verified":false}]}
```
- 57 cultivos: 32 anuales con ciclo, 24 perennes (la guía de siembra no aplica) y 1 sin dato.
- Son **estimaciones agronómicas generales** para que la guía tenga un valor inicial; la app
  las muestra como "valor estimado" y el usuario puede cambiarlas. `null` = poco común a esa
  altitud. Un técnico (MAG/INTA) debe revisarlas y poner `verified: true` en cada cultivo.

## ✅ `archivo/indices/`

PDF originales de los índices del SIMM (`archivo/indices/2026/…pdf`, ≈ 8,8 MB por edición) y
`archivo/indices/registro.json` (título, sha256, archivo, fecha de descarga).

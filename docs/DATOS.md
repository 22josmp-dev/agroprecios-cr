# Esquema de los datos publicados

La app lee estos archivos por `fetch` relativo desde `/data`. Todos llevan `"esquema": 1`,
`"fuente": "PIMA – SIMM"` y `"datos_de_ejemplo"` (`false` en datos reales; `true` en cualquier
archivo de ejemplo, que la app debe rotular como **DATOS DE EJEMPLO**). Fechas en ISO
(`AAAA-MM-DD`); momentos en UTC (`AAAA-MM-DDTHH:MM:SSZ`). Precios en colones por la unidad de
comercialización indicada.

Estado: ✅ generado por el motor · ⏳ pendiente (paso indicado).

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
| `historial` | Últimos 30 intentos `{utc, estado, mensaje}` |

Si un intento falla, `fecha_boletin`, `registros` y `ultima_actualizacion_exitosa_utc` conservan
los valores del último éxito: los datos buenos nunca se reemplazan por datos fallidos.

## ✅ `data/latest.json` — último boletín con comparaciones listas

```json
{"esquema":1,"fuente":"PIMA – SIMM","datos_de_ejemplo":false,
 "fecha_boletin":"2026-09-28","generado_utc":"…",
 "productos":[{
   "id":"tomate-primera","nombre":"Tomate primera","cultivo":"Tomate","cultivo_id":"tomate",
   "categoria":"hortaliza","unidad":"Caja plástica (18 kg)","kg":18.0,
   "minimo":10000.0,"maximo":10000.0,"moda":10000.0,"promedio":10000.0,"precio_kg":555.56,
   "vs_anterior":{"fecha":"2026-09-25","promedio":15666.67,"variacion_pct":-36.2},
   "vs_semana":{"fecha":"2026-09-21","promedio":19666.67,"variacion_pct":-49.2},
   "vs_30d":{"dias":10,"promedio":16505.0,"variacion_pct":-39.4}}]}
```

- `kg`: kilos por unidad **solo si el boletín los declara** (`Malla (45 kg)`, `Bandeja (400 g)`,
  `Kilo`). `null` para `Unidad`, `Java`, `Caja plástica`, etc.: no se inventan pesos.
  `precio_kg = promedio / kg` cuando hay `kg`.
- Comparaciones sobre el **promedio** y solo con la **misma unidad**:
  - `vs_anterior`: boletín anterior en que apareció el producto.
  - `vs_semana`: boletín más cercano entre 7 y 13 días antes.
  - `vs_30d`: media de los boletines de los 30 días previos (sin contar el de hoy); requiere
    al menos 3 días, si no es `null`.
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
  "id":"camote","nombre":"Camote","cultivo":"Camote","cultivo_id":"camote",
  "categoria":"raíz y tubérculo","sinonimos":["batata","boniato"],
  "nombres_boletin":["Camote"],"unidades":[{"unidad":"Kilo","kg":1.0}]}]}
```
- `id`: identificador estable (nombre del boletín sin tildes ni signos).
- `cultivo`/`cultivo_id`: agrupa variantes (Tomate primera/segunda/tercera → Tomate) para la
  búsqueda y la guía de siembra.
- `sinonimos`: sin tildes, en minúscula; la búsqueda de la app los usa.
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

## ⏳ `data/seasonal.json` (Paso 4)
## ⏳ `data/cycle_defaults.json` (Paso 4)

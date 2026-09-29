"""Proceso de índices estacionales: descarga los PDF del SIMM, los archiva y genera
data/seasonal.json y data/historico/<id>.json.

- Los PDF se vuelven a descargar solo si cambia la lista de títulos (nueva edición), el día 1 de
  cada mes, o con --forzar. Así el proceso diario hace apenas 3 solicitudes al PIMA.
- El cálculo se rehace siempre (es instantáneo): incorpora los meses completos acumulados del
  boletín diario cuando la unidad coincide.
"""
from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, timezone
from statistics import mean

from . import config
from .almacen import FUENTE, Almacen, ahora_iso, escribir_json, leer_json
from .catalogo import Catalogo
from .estacional import indice_estacional, indice_porcentaje_promedio
from .fuente import ClientePIMA, ErrorFuente, extraer_enlaces
from .indices_simm import IndiceSIMM, parsear_indice
from .parser_boletin import ErrorFormato
from .texto import normalizar, slug

_RE_ES_INDICE = re.compile(r"ndice\s+estacional(idad)?\s+de\s+oferta", re.I)

# Nombres del SIMM que no coinciden textualmente con el boletín diario. Verificado a mano
# comparando las listas del 29-09-2026. Valor: ids del catálogo con la MISMA unidad y calidad.
MAPEO_MANUAL = {
    "manga keith": ["manga-grande-keitt"],
    "manga cavallini": ["manga-grande-cavallini"],
    "limon mandarino": ["limon-mandarina"],
    "mamon chino": ["mamon-chino-injertado"],
    "papa blanca": ["papa-blanca-primera"],
    "papa amarilla": ["papa-amarilla-primera"],
    "zanahoria": ["zanahoria-primera"],
    "naranja": ["naranja-dulce"],
    "pina grande": ["pina-grande"],
    "sandia grande de campo": ["sandia-de-campo-grande"],
    "sandia mediana de campo": ["sandia-de-campo-mediana"],
    "apio verde": ["apio-verde-mata"],
}
# Prefijo normalizado del nombre del SIMM -> cultivo_id del catálogo
ALIAS_CULTIVO = {"manga": "mango"}


def listar_indices(cliente: ClientePIMA) -> list[tuple[str, str]]:
    return [(t, u) for t, u in extraer_enlaces(cliente.pagina_contenido(config.CM_INDICES)) if _RE_ES_INDICE.search(t)]


def descargar_indices(alm: Almacen, cliente: ClientePIMA, forzar: bool, hoy: date, momento: str, log=print) -> int:
    """Descarga los PDF si hace falta. Devuelve cuántos PDF nuevos se archivaron."""
    registro_ruta = alm.archivo / "indices" / "registro.json"
    registro = leer_json(registro_ruta, [])
    lista = listar_indices(cliente)
    if not lista:
        raise ErrorFuente("La lista de índices estacionales del SIMM vino vacía")
    titulos_previos = {r["titulo"] for r in registro}
    titulos = {t for t, _ in lista}
    if not forzar and titulos <= titulos_previos and hoy.day != 1:
        log(f"Índices: {len(lista)} en la lista, sin cambios de títulos; no se descargan")
        return 0
    conocidos = {r["sha256"] for r in registro}
    nuevos = 0
    for titulo, url in lista:
        datos, nombre = cliente.descargar(url)
        sha = hashlib.sha256(datos).hexdigest()
        if sha in conocidos:
            continue
        m = re.search(r"(\d{4})\s*$", titulo)
        anio = m.group(1) if m else "sin-anio"
        ruta = alm.archivo / "indices" / anio / f"{slug(titulo)[:60]}_{sha[:12]}.pdf"
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(datos)
        registro.append({"titulo": titulo, "sha256": sha, "archivo": ruta.relative_to(alm.raiz).as_posix(),
                         "nombre_original": nombre, "descargado_utc": momento})
        conocidos.add(sha)
        nuevos += 1
    escribir_json(registro_ruta, sorted(registro, key=lambda r: (r["titulo"], r["descargado_utc"])))
    log(f"Índices: {len(lista)} en la lista, {nuevos} PDF nuevos archivados")
    return nuevos


def mapear(nombre_simm: str, catalogo: Catalogo) -> tuple[list[str], str, str]:
    """(ids de productos del boletín equivalentes, cultivo_id, cultivo) para un nombre del SIMM."""
    n = normalizar(nombre_simm)
    productos = catalogo.datos["productos"]
    ids = MAPEO_MANUAL.get(n) or [p["id"] for p in productos if normalizar(p["nombre"]) == n]
    if ids:
        p = catalogo.por_id(ids[0])
        return ids, p["cultivo_id"], p["cultivo"]
    # Sin equivalente exacto: se asocia al cultivo del catálogo cuyo nombre (o alias) es prefijo
    cultivos = {(p["cultivo_id"], p["cultivo"]) for p in productos}
    candidatos = []
    for cid, nombre in cultivos:
        prefijos = [normalizar(nombre)] + [a for a, c in ALIAS_CULTIVO.items() if c == cid]
        largo = max((len(pre) for pre in prefijos if n == pre or n.startswith(pre + " ")), default=0)
        if largo:
            candidatos.append((largo, cid, nombre))
    if candidatos:
        _, cid, nombre = max(candidatos)
        return [], cid, nombre
    # Cultivo que no está en el boletín diario (p. ej. Aguacate, Mora): primera palabra del nombre
    primera = nombre_simm.split()[0]
    return [], slug(primera), primera.capitalize()


def meses_del_boletin(alm: Almacen, ids: list[str], unidad: str | None, hoy: date) -> dict[tuple[int, int], float]:
    """Media mensual de la MODA diaria (el SIMM calcula sobre la moda) de meses completos,
    solo si hay un único producto equivalente y la unidad coincide."""
    if len(ids) != 1 or not unidad:
        return {}
    fechas = alm.fechas_con_datos()
    if not fechas:
        return {}
    por_mes: dict[tuple[int, int], list[float]] = {}
    for d, filas in alm.cargar_dias(fechas[0], fechas[-1]).items():
        if (d.year, d.month) >= (hoy.year, hoy.month):
            continue  # el mes en curso aún no está completo
        for f in filas:
            if f[0] == ids[0] and normalizar(f[1]) == normalizar(unidad):
                por_mes.setdefault((d.year, d.month), []).append(f[4])
    return {k: round(mean(v), 2) for k, v in por_mes.items() if len(v) >= config.MIN_DIAS_MES}


def ultimos_pdf(alm: Almacen) -> list[dict]:
    """La versión más reciente de cada título."""
    ultimos: dict[str, dict] = {}
    for r in sorted(leer_json(alm.archivo / "indices" / "registro.json", []), key=lambda r: r["descargado_utc"]):
        ultimos[r["titulo"]] = r
    return list(ultimos.values())


def construir(alm: Almacen, catalogo: Catalogo, hoy: date, momento: str, log=print) -> tuple[dict, list[str]]:
    productos, problemas = [], []
    ediciones = set()
    for r in ultimos_pdf(alm):
        try:
            ind: IndiceSIMM = parsear_indice((alm.raiz / r["archivo"]).read_bytes())
        except ErrorFormato as e:
            problemas.append(f"{r['titulo']}: {e}")
            continue
        ediciones.add(ind.edicion)
        ids, cultivo_id, cultivo = mapear(ind.nombre, catalogo)
        id_ = slug(ind.nombre)
        serie = dict(ind.precio.valores)
        recientes = {k: v for k, v in meses_del_boletin(alm, ids, ind.unidad_precio, hoy).items() if k not in serie}
        serie.update(recientes)
        calc = indice_estacional(serie)
        reproducido = indice_porcentaje_promedio(ind.precio.valores)
        oficial = ind.precio.indice_oficial
        verificacion = None
        if reproducido and all(o is not None for o in oficial):
            verificacion = round(max(abs(a - b) for a, b in zip(reproducido, oficial)), 4)
            if verificacion > 0.002:
                problemas.append(f"{ind.nombre}: el índice oficial no se reproduce (dif. {verificacion}); revisar lectura del PDF")
        productos.append({
            "id": id_, "nombre": ind.nombre, "cultivo_id": cultivo_id, "cultivo": cultivo,
            "productos_boletin": ids, "unidad_precio": ind.unidad_precio,
            "years_of_data": calc["years_of_data"], "confianza": calc["confianza"],
            "indice": calc["indice"], "desviacion": calc["desviacion"], "desviacion_media": calc["desviacion_media"],
            "n_ratios": calc["n_ratios"], "metodo": calc["metodo"], "meses_sin_dato": calc["meses_sin_dato"],
            "motivo": calc.get("motivo"),
            "indice_oficial_simm": oficial,
            "indice_oferta_oficial_simm": ind.oferta.indice_oficial if ind.oferta else None,
            "meses_del_boletin_diario": len(recientes),
            "verificacion_dif_max": verificacion,
        })
        historico = {
            "esquema": 1, "fuente": FUENTE, "datos_de_ejemplo": False, "id": id_, "nombre": ind.nombre,
            "unidad_precio": ind.unidad_precio, "generado_utc": momento,
            "nota": "Precio mensual: tabla del índice estacional del SIMM (promedio al por mayor). "
                    "Meses recientes marcados en 'meses_boletin_diario': media de la moda diaria del boletín.",
            "precio": _por_anio(serie), "oferta_tm": _por_anio(ind.oferta.valores) if ind.oferta else {},
            "meses_boletin_diario": sorted(f"{a:04d}-{m:02d}" for a, m in recientes),
        }
        escribir_json(alm.data / "historico" / f"{id_}.json", historico)
    productos.sort(key=lambda p: normalizar(p["nombre"]))
    seasonal = {
        "esquema": 1, "fuente": FUENTE, "datos_de_ejemplo": False, "generado_utc": momento,
        "edicion_simm": sorted(e for e in ediciones if e),
        "metodo": {
            "indice": "ratio = precio mensual / media móvil centrada 2×12; índice = mediana de los ratios "
                      "del mes entre años; normalizado a promedio 1.0",
            "desviacion": "desviación estándar de los ratios normalizados de cada mes",
            "confianza": f"alta: ≥5 años y desviación media ≤ {config.DESVIACION_BAJA}; media: 3–4 años; baja: otro caso",
            "indice_oficial_simm": "índice publicado por el SIMM (método porcentaje promedio), como referencia",
        },
        "productos": productos,
    }
    return seasonal, problemas


def _por_anio(valores: dict[tuple[int, int], float]) -> dict[str, list]:
    salida: dict[str, list] = {}
    for (a, m), v in sorted(valores.items()):
        salida.setdefault(str(a), [None] * 12)[m - 1] = v
    return salida


def ejecutar_indices(alm: Almacen, cliente: ClientePIMA, forzar: bool = False,
                     ahora: datetime | None = None, log=print) -> int:
    ahora = ahora or datetime.now(timezone.utc)
    momento = ahora_iso(ahora)
    hoy = ahora.astimezone(config.TZ_CR).date()
    catalogo = Catalogo.cargar(alm.data / "catalog.json")
    problemas = []
    try:
        descargar_indices(alm, cliente, forzar, hoy, momento, log)
    except ErrorFuente as e:
        problemas.append(f"No se pudieron descargar los índices del SIMM: {e}")
    if not ultimos_pdf(alm):
        log("ERROR: no hay PDF de índices archivados")
        return 1
    seasonal, errores = construir(alm, catalogo, hoy, momento, log)
    problemas += errores
    anterior = leer_json(alm.data / "seasonal.json")
    if anterior and len(seasonal["productos"]) < 0.8 * len(anterior["productos"]):
        problemas.append(f"Solo {len(seasonal['productos'])} índices (antes {len(anterior['productos'])}); no se reemplaza seasonal.json")
    else:
        seasonal["estado"] = "ok" if not problemas else "con_avisos"
        seasonal["avisos"] = problemas
        escribir_json(alm.data / "seasonal.json", seasonal)
    conf = {}
    for p in seasonal["productos"]:
        conf[p["confianza"]] = conf.get(p["confianza"], 0) + 1
    log(f"Índices estacionales: {len(seasonal['productos'])} productos; confianza {conf}")
    for p in problemas:
        log("AVISO:", p)
    return 1 if problemas else 0

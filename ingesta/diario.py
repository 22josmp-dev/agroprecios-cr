"""Proceso diario: descarga, parsea, valida y publica los boletines nuevos del PIMA.

Reglas (ver README y docs/FORMATO_BOLETIN.md):
- Idempotente por (fecha, SHA-256): un PDF ya procesado para esa fecha no se vuelve a procesar;
  el mismo PDF bajo otra fecha sí se revisa (y la validación de fecha lo rechaza).
- Se revisan todos los boletines de la lista (≈ 2 semanas): si un día faltó, se recupera.
- Si un boletín falla (descarga, formato, validación o muy pocos registros), sus datos NO se
  escriben; los datos buenos anteriores se conservan, la falla queda en data/meta.json y el
  proceso termina con código 1 para que GitHub avise al dueño del repositorio.
- Boletín de hoy no publicado: en el primer intento queda "pendiente" (sin error); en el
  último intento del día (--ultimo-intento) es un error.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict
from datetime import date, datetime, timezone

from . import config
from .almacen import FUENTE, Almacen, ahora_iso
from .catalogo import Catalogo
from .comparaciones import construir_latest
from .fuente import ClientePIMA, ErrorFuente, fecha_de_nombre_archivo
from .parser_boletin import ErrorFormato, parsear_pdf
from .validacion import validar


class PocosRegistros(Exception):
    pass


def referencia_registros(registro: list[dict], fecha: date) -> tuple[int, str, float] | None:
    """(registros, descripción, umbral) contra los que se compara un boletín de `fecha`.

    La cantidad de productos depende del día de la semana (lunes/viernes 57, martes/jueves 51,
    miércoles 65 en setiembre 2026), así que se usa el último boletín del mismo día de la semana
    con UMBRAL_REGISTROS. Si no lo hay, la mediana de los últimos 10 boletines con el umbral
    más holgado UMBRAL_REGISTROS_OTRO_DIA.
    """
    previos = sorted((r for r in registro if r["estado"] == "procesado" and r["fecha"] < fecha.isoformat()),
                     key=lambda r: r["fecha"])
    mismo_dia = [r for r in previos if date.fromisoformat(r["fecha"]).weekday() == fecha.weekday()]
    if mismo_dia:
        r = mismo_dia[-1]
        return r["registros"], f"el boletín del {r['fecha']}", config.UMBRAL_REGISTROS
    if previos:
        conteos = sorted(r["registros"] for r in previos[-10:])
        mediana = conteos[len(conteos) // 2]
        return mediana, f"la mediana de los últimos {len(conteos)} boletines", config.UMBRAL_REGISTROS_OTRO_DIA
    return None


def comprobar_umbral(n_validos: int, registro: list[dict], fecha: date) -> None:
    if n_validos < config.MIN_REGISTROS_ABS:
        raise PocosRegistros(f"Solo {n_validos} registros válidos (mínimo absoluto {config.MIN_REGISTROS_ABS})")
    ref = referencia_registros(registro, fecha)
    if ref and n_validos < ref[2] * ref[0]:
        raise PocosRegistros(
            f"Solo {n_validos} registros válidos; como referencia, {ref[1]} tuvo {ref[0]} (umbral {ref[2]:.0%})")


def procesar_pdf(datos: bytes, fecha_lista: date | None, catalogo: Catalogo, hoy: date, registro: list[dict]):
    """Parsea y valida. Devuelve (resultado, registros, rechazos) o levanta ErrorFormato/PocosRegistros."""
    resultado = parsear_pdf(datos)
    registros, rechazos = validar(resultado, catalogo, hoy, fecha_lista)
    comprobar_umbral(len(registros), registro, resultado.fecha_plaza)
    return resultado, registros, rechazos


def _publicar_boletin(alm: Almacen, catalogo: Catalogo, fecha: date, registros, rechazos, sha: str, momento: str) -> bool:
    """Escribe los datos de un boletín válido. Devuelve True si el catálogo cambió."""
    alm.guardar_dia(fecha, [r.como_fila() for r in registros])
    alm.guardar_rechazos(fecha, sha, [asdict(r) for r in rechazos], momento)
    cambio = False
    for r in registros:
        cambio |= catalogo.registrar_unidad(catalogo.por_id(r.id), r.unidad, r.producto)
    return cambio


def _entrada_registro(fecha: date, sha: str, ruta_pdf: str, nombre: str | None, url: str | None, momento: str) -> dict:
    return {"fecha": fecha.isoformat(), "sha256": sha, "archivo": ruta_pdf, "nombre_original": nombre,
            "url_lista": url, "descargado_utc": momento, "estado": None, "registros": 0, "rechazados": 0,
            "formato_numerico": None, "error": None}


def _actualizar_registro(registro: list[dict], entrada: dict) -> None:
    """Reemplaza la entrada con la misma fecha y SHA, o marca como 'reemplazado' la versión
    anterior del día."""
    registro[:] = [r for r in registro if (r["fecha"], r["sha256"]) != (entrada["fecha"], entrada["sha256"])]
    if entrada["estado"] == "procesado":
        for r in registro:
            if r["fecha"] == entrada["fecha"] and r["estado"] == "procesado":
                r["estado"] = "reemplazado"
    registro.append(entrada)


def escribir_meta(alm: Almacen, momento: str, estado: str, mensaje: str, exito: bool, registro: list[dict]) -> dict:
    meta = alm.meta()
    fechas = alm.fechas_con_datos()
    ultimo = fechas[-1].isoformat() if fechas else None
    entrada = next((r for r in reversed(registro) if r["fecha"] == ultimo and r["estado"] == "procesado"), None)
    historial = (meta.get("historial") or [])[-(config.HISTORIAL_META - 1):]
    historial.append({"utc": momento, "estado": estado, "mensaje": mensaje})
    nuevo = {
        "esquema": 1,
        "fuente": FUENTE,
        "datos_de_ejemplo": False,
        "estado": estado,
        "mensaje": mensaje,
        "ultimo_intento_utc": momento,
        "ultima_actualizacion_exitosa_utc": momento if exito else meta.get("ultima_actualizacion_exitosa_utc"),
        "fecha_boletin": ultimo,
        "registros": entrada["registros"] if entrada else 0,
        "rechazados": entrada["rechazados"] if entrada else 0,
        "sha256": entrada["sha256"] if entrada else None,
        "dias_con_datos": len(fechas),
        "meses_precios": sorted({f"{d.year:04d}-{d.month:02d}" for d in fechas}),
        "historial": historial,
    }
    alm.guardar_meta(nuevo)
    return nuevo


def ejecutar_diario(alm: Almacen, cliente: ClientePIMA, ahora: datetime | None = None,
                    ultimo_intento: bool = False, log=print) -> int:
    ahora = ahora or datetime.now(timezone.utc)
    momento = ahora_iso(ahora)
    hoy = ahora.astimezone(config.TZ_CR).date()
    catalogo = Catalogo.cargar(alm.data / "catalog.json")
    registro = alm.registro()
    problemas: list[str] = []
    publicados: list[str] = []

    try:
        log(cliente.verificar_robots())
        entradas = cliente.listar_boletines()
    except ErrorFuente as e:
        mensaje = f"No se pudo leer la lista de boletines del PIMA: {e}"
        log("ERROR:", mensaje)
        escribir_meta(alm, momento, "error", mensaje, False, registro)
        return 1

    log(f"Lista del PIMA: {len(entradas)} boletines ({entradas[-1].fecha} a {entradas[0].fecha})")
    # Idempotencia por (fecha, SHA-256): el mismo PDF bajo OTRA fecha (p. ej. un boletín viejo
    # re-subido por error) no se da por conocido; se procesa y la validación de fecha lo rechaza.
    procesados = {(r["fecha"], r["sha256"]) for r in registro if r["estado"] in ("procesado", "reemplazado")}
    fechas_ok = {r["fecha"] for r in registro if r["estado"] == "procesado"}
    recientes = set(sorted({e.fecha for e in entradas}, reverse=True)[:config.REVISAR_ULTIMOS])
    catalogo_cambio = False

    for entrada in sorted(entradas, key=lambda e: e.fecha):
        f = entrada.fecha.isoformat()
        if f in fechas_ok and entrada.fecha not in recientes:
            continue
        try:
            datos, nombre = cliente.descargar(entrada.url)
        except ErrorFuente as e:
            problemas.append(f"{f}: no se pudo descargar: {e}")
            continue
        sha = hashlib.sha256(datos).hexdigest()
        if (f, sha) in procesados:
            log(f"{f}: sin cambios (SHA-256 {sha[:12]} ya procesado)")
            continue
        ruta_pdf = alm.guardar_pdf(entrada.fecha, sha, datos)
        reg = _entrada_registro(entrada.fecha, sha, ruta_pdf, nombre, entrada.url, momento)
        try:
            fecha_archivo = fecha_de_nombre_archivo(nombre)
            if fecha_archivo and fecha_archivo != entrada.fecha:
                raise ErrorFormato(f"El nombre del archivo ({nombre}) no coincide con la fecha de la lista")
            resultado, registros, rechazos = procesar_pdf(datos, entrada.fecha, catalogo, hoy, registro)
        except (ErrorFormato, PocosRegistros) as e:
            reg.update(estado="fallido", error=f"{type(e).__name__}: {e}")
            _actualizar_registro(registro, reg)
            problemas.append(f"{f}: {e}")
            log(f"{f}: FALLA — {e}")
            continue
        catalogo_cambio |= _publicar_boletin(alm, catalogo, resultado.fecha_plaza, registros, rechazos, sha, momento)
        reg.update(estado="procesado", registros=len(registros), rechazados=len(rechazos),
                   formato_numerico=resultado.formato_numerico)
        _actualizar_registro(registro, reg)
        procesados.add((f, sha))
        publicados.append(f)
        log(f"{f}: {len(registros)} registros válidos, {len(rechazos)} rechazados "
            f"(formato {resultado.formato_numerico}, métodos {resultado.metodos})")

    alm.guardar_registro(registro)
    if catalogo_cambio:
        catalogo.guardar(alm.data / "catalog.json")

    fechas = alm.fechas_con_datos()
    if fechas and (publicados or not (alm.data / "latest.json").exists()):
        alm.guardar_latest(construir_latest(alm, catalogo, fechas[-1], momento))

    estado = "ok"
    ultima_lista = max(e.fecha for e in entradas)
    if config.se_espera_boletin(hoy) and ultima_lista < hoy:
        if ultimo_intento:
            problemas.append(f"El boletín de hoy ({hoy}) no está publicado en el sitio del PIMA")
        else:
            estado = "pendiente"

    if problemas:
        mensaje = " | ".join(problemas)
        escribir_meta(alm, momento, "error", mensaje, False, registro)
        log("ERROR:", mensaje)
        return 1
    if estado == "pendiente":
        mensaje = f"El boletín de hoy ({hoy}) aún no está publicado; se reintentará más tarde."
    elif publicados:
        mensaje = f"Boletines nuevos: {', '.join(publicados)}"
    else:
        mensaje = "Sin boletines nuevos; los datos están al día."
    escribir_meta(alm, momento, estado, mensaje, True, registro)
    log(mensaje)
    return 0


def reprocesar(alm: Almacen, ahora: datetime | None = None, log=print) -> int:
    """Vuelve a parsear todos los PDF guardados en /archivo (tras actualizar el parser)."""
    ahora = ahora or datetime.now(timezone.utc)
    momento = ahora_iso(ahora)
    hoy = ahora.astimezone(config.TZ_CR).date()
    catalogo = Catalogo.cargar(alm.data / "catalog.json")
    anterior = alm.registro()
    # Por fecha, la versión descargada más recientemente (sin contar las ya reemplazadas)
    ultimas: dict[str, dict] = {}
    for r in sorted(anterior, key=lambda r: r["descargado_utc"]):
        if r["estado"] != "reemplazado":
            ultimas[r["fecha"]] = r
    nuevo_registro = [r for r in anterior if r["estado"] == "reemplazado"]
    problemas = []
    catalogo_cambio = False
    for f in sorted(ultimas):
        r = dict(ultimas[f])
        datos = (alm.raiz / r["archivo"]).read_bytes()
        try:
            resultado, registros, rechazos = procesar_pdf(datos, date.fromisoformat(f), catalogo, hoy, nuevo_registro)
        except (ErrorFormato, PocosRegistros) as e:
            r.update(estado="fallido", error=f"{type(e).__name__}: {e}")
            nuevo_registro.append(r)
            problemas.append(f"{f}: {e}")
            log(f"{f}: FALLA — {e}")
            continue
        catalogo_cambio |= _publicar_boletin(alm, catalogo, resultado.fecha_plaza, registros, rechazos, r["sha256"], momento)
        r.update(estado="procesado", registros=len(registros), rechazados=len(rechazos),
                 formato_numerico=resultado.formato_numerico, error=None)
        nuevo_registro.append(r)
        log(f"{f}: {len(registros)} válidos, {len(rechazos)} rechazados")
    alm.guardar_registro(nuevo_registro)
    if catalogo_cambio:
        catalogo.guardar(alm.data / "catalog.json")
    fechas = alm.fechas_con_datos()
    if fechas:
        alm.guardar_latest(construir_latest(alm, catalogo, fechas[-1], momento))
    if problemas:
        escribir_meta(alm, momento, "error", "Reproceso con fallas: " + " | ".join(problemas), False, nuevo_registro)
        return 1
    escribir_meta(alm, momento, "ok", f"Reprocesados {len(ultimas)} boletines del archivo", True, nuevo_registro)
    return 0

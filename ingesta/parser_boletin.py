"""Lectura del PDF del boletín diario del PIMA-CENADA.

Formato verificado en docs/FORMATO_BOLETIN.md. Decisiones clave:
- El orden de las columnas de precio se lee del encabezado de la tabla ("Producto Unidad de
  comercialización mayorista Mínimo Máximo Moda Promedio"), nunca se asume.
- Método principal: pdfplumber.extract_tables(). Si una página no da filas de 6 columnas,
  se usa un respaldo por posición de palabras (útil si el PDF deja de tener líneas de tabla).
- La unidad puede venir pegada al nombre ("Papa Caja (10 kg)" con la celda de unidad vacía).
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pdfplumber

from . import numeros
from .texto import limpiar_celda, normalizar

COLUMNAS = ("minimo", "maximo", "moda", "promedio")

_RE_FECHA_PLAZA = re.compile(r"Fecha\s+de\s+Plaza:\s*(\d{1,2})/(\d{1,2})/(\d{4})", re.I)
_RE_PIE = re.compile(r"^(fecha:|pag\.?\s*\d|pagina\s*\d)", re.I)
_UNIDADES_CONOCIDAS = (
    r"caja pl[aá]stica|caja|malla|saco|java|bandeja|kilo|kg|unidad|mata|rollo|docena|"
    r"ciento|racimo|manojo|paquete|bolsa|cajeta|tarro|quintal"
)
# Líneas de texto del boletín que no son filas de precios (normalizadas, sin tildes)
_LINEAS_INFORMATIVAS = (
    "sifpima", "simm", "sistema", "boletin", "cenada", "los precios", "exclusivamente", "fecha",
    "precio por", "tipo de cambio", "informacion generada",
)
_RE_UNIDAD_PEGADA =re.compile(rf"^(?P<producto>.+?)\s+(?P<unidad>(?:{_UNIDADES_CONOCIDAS})\b.*)$", re.I)


class ErrorFormato(Exception):
    """El PDF no tiene la estructura esperada (probable cambio de formato del PIMA)."""


@dataclass
class FilaCruda:
    producto: str
    unidad: str
    valores: dict[str, str]
    pagina: int


@dataclass
class ResultadoParseo:
    fecha_plaza: date
    formato_numerico: str
    votos_formato: dict
    filas: list[FilaCruda]
    no_reconocidas: list[dict] = field(default_factory=list)
    paginas: int = 0
    metodos: list[str] = field(default_factory=list)


def _orden_columnas(texto_pagina: str) -> tuple[str, ...] | None:
    """Busca la línea de encabezado y devuelve el orden de las 4 columnas de precio."""
    for linea in texto_pagina.splitlines():
        n = normalizar(linea)
        if n.startswith("producto") and "unidad" in n:
            posiciones = {col: n.find(col) for col in COLUMNAS}
            if all(p >= 0 for p in posiciones.values()):
                return tuple(sorted(COLUMNAS, key=posiciones.get))
            raise ErrorFormato(f"Encabezado incompleto, faltan columnas de precio: '{linea.strip()}'")
    return None


def separar_unidad(producto: str, unidad: str) -> tuple[str, str]:
    """Si la celda de unidad viene vacía y la unidad está pegada al nombre, la separa."""
    producto, unidad = limpiar_celda(producto), limpiar_celda(unidad)
    if not unidad:
        m = _RE_UNIDAD_PEGADA.match(producto)
        if m:
            return m.group("producto").strip(), m.group("unidad").strip()
    return producto, unidad


def _es_pie_o_encabezado(celdas: list[str]) -> bool:
    primera = normalizar(celdas[0]) if celdas else ""
    return (not any(celdas)) or bool(_RE_PIE.match(celdas[0] if celdas else "")) or primera.startswith("producto")


def _filas_por_tablas(pagina, orden, num_pagina) -> tuple[list[FilaCruda], list[dict]]:
    filas, raras = [], []
    for tabla in pagina.extract_tables():
        for fila in tabla:
            celdas = [limpiar_celda(c) for c in fila]
            if _es_pie_o_encabezado(celdas):
                continue
            if len(celdas) == 6 and all(numeros.parece_numero(c) for c in celdas[2:]):
                producto, unidad = separar_unidad(celdas[0], celdas[1])
                filas.append(FilaCruda(producto, unidad, dict(zip(orden, celdas[2:])), num_pagina))
            elif len(celdas) == 5 and all(numeros.parece_numero(c) for c in celdas[1:]):
                # Unidad pegada al nombre en una sola celda
                producto, unidad = separar_unidad(celdas[0], "")
                filas.append(FilaCruda(producto, unidad, dict(zip(orden, celdas[1:])), num_pagina))
            else:
                raras.append({"pagina": num_pagina, "celdas": celdas, "motivo": "fila con columnas no reconocidas"})
    return filas, raras


def _filas_por_palabras(pagina, orden, num_pagina) -> tuple[list[FilaCruda], list[dict]]:
    """Respaldo: agrupa palabras por línea y usa la x de 'Unidad' del encabezado como frontera."""
    palabras = pagina.extract_words(use_text_flow=False, keep_blank_chars=False)
    lineas: dict[int, list[dict]] = {}
    for p in palabras:
        clave = round(p["top"] / 3)
        # Unir con la línea vecina si la diferencia es mínima
        for k in (clave - 1, clave + 1):
            if k in lineas:
                clave = k
                break
        lineas.setdefault(clave, []).append(p)
    filas, raras = [], []
    encabezado_visto = False
    candidatas = []  # (palabras de texto, palabras numéricas)
    for clave in sorted(lineas):
        ws = sorted(lineas[clave], key=lambda w: w["x0"])
        textos = [w["text"] for w in ws]
        n = normalizar(" ".join(textos))
        if not encabezado_visto:
            encabezado_visto = n.startswith("producto") and "unidad" in n
            continue
        if _RE_PIE.match(textos[0]):
            continue
        cola = []
        while ws and numeros.parece_numero(ws[-1]["text"]) and len(cola) < 4:
            cola.insert(0, ws.pop())
        if len(cola) < 4 or not ws:
            if n and not n.startswith(_LINEAS_INFORMATIVAS):
                raras.append({"pagina": num_pagina, "celdas": textos, "motivo": "línea sin 4 precios"})
            continue
        candidatas.append((ws, cola))
    if not candidatas:
        return filas, raras
    # Columnas alineadas a la izquierda: la x más frecuente después de la del producto es el
    # inicio de la columna de unidad.
    x_producto = min(ws[0]["x0"] for ws, _ in candidatas)
    conteo: dict[int, int] = {}
    for ws, _ in candidatas:
        for w in ws[1:]:
            if w["x0"] > x_producto + 5:
                conteo[round(w["x0"])] = conteo.get(round(w["x0"]), 0) + 1
    x_unidad = max(conteo, key=conteo.get) if conteo else None
    for ws, cola in candidatas:
        if x_unidad is None:
            producto, unidad = separar_unidad(" ".join(w["text"] for w in ws), "")
        else:
            producto = " ".join(w["text"] for w in ws if w["x0"] < x_unidad - 1.5)
            unidad = " ".join(w["text"] for w in ws if w["x0"] >= x_unidad - 1.5)
            producto, unidad = separar_unidad(producto, unidad)
        filas.append(FilaCruda(producto, unidad, dict(zip(orden, [w["text"] for w in cola])), num_pagina))
    return filas, raras


def parsear_pdf(origen: bytes | str | Path, usar_tablas: bool = True) -> ResultadoParseo:
    abierto = pdfplumber.open(io.BytesIO(origen)) if isinstance(origen, bytes) else pdfplumber.open(origen)
    with abierto as pdf:
        if not pdf.pages:
            raise ErrorFormato("El PDF no tiene páginas")
        fechas: set[date] = set()
        orden = None
        filas: list[FilaCruda] = []
        raras: list[dict] = []
        metodos: list[str] = []
        for i, pagina in enumerate(pdf.pages, start=1):
            texto = pagina.extract_text() or ""
            for d, m, a in _RE_FECHA_PLAZA.findall(texto):
                try:
                    fechas.add(date(int(a), int(m), int(d)))
                except ValueError as e:
                    raise ErrorFormato(f"Fecha de plaza inválida en página {i}: {d}/{m}/{a}") from e
            orden = _orden_columnas(texto) or orden
            if orden is None:
                if i == 1:
                    raise ErrorFormato("No se encontró el encabezado de la tabla (Producto | Unidad | precios)")
                continue
            f, r = _filas_por_tablas(pagina, orden, i) if usar_tablas else ([], [])
            metodo = "tablas"
            if not f:
                f, r = _filas_por_palabras(pagina, orden, i)
                metodo = "palabras"
            filas += f
            raras += r
            metodos.append(metodo)
        if not fechas:
            raise ErrorFormato("No se encontró 'Fecha de Plaza' en el PDF")
        if len(fechas) > 1:
            raise ErrorFormato(f"El PDF trae varias fechas de plaza distintas: {sorted(fechas)}")
        if not filas:
            raise ErrorFormato("No se extrajo ninguna fila de precios")
        formato, votos = numeros.detectar_formato([v for f in filas for v in f.valores.values()])
        return ResultadoParseo(fechas.pop(), formato, votos, filas, raras, len(pdf.pages), metodos)

"""Lectura de los PDF de índices estacionales del SIMM (bpm.pima.go.cr/cm.aspx?id=77).

Cada PDF (1 página, generado desde Excel) trae dos tablas con filas Enero…Diciembre + Promedio y
una columna por año (2018–2025 en la edición 2026) más "Índice Estacional":
  1. Oferta en el CENADA (toneladas métricas)
  2. Precio promedio al por mayor, "colones por <unidad>"
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber

from . import numeros
from .parser_boletin import ErrorFormato
from .texto import limpiar_celda, normalizar

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
_ALIAS_MES = {"setiembre": "septiembre"}
_RE_TITULO = re.compile(r"^(?P<nombre>.+?)[\s.]+[ÍI]ndice\s+[Ee]stacional(?:idad)?\s+de\s+[Oo]ferta", re.M)
_RE_UNIDAD = re.compile(r"colones\s+por\s+(?P<unidad>.+?)\.?\s*$", re.I | re.M)
_RE_EDICION = re.compile(r"para\s+el\s+a[ñn]o\s+(\d{4})", re.I)


@dataclass
class TablaSIMM:
    anios: list[int]
    valores: dict[tuple[int, int], float]      # (año, mes) -> valor
    indice_oficial: list[float | None]          # 12 valores
    promedios_anuales: dict[int, float] = field(default_factory=dict)


@dataclass
class IndiceSIMM:
    nombre: str
    edicion: int | None
    unidad_precio: str | None
    oferta: TablaSIMM | None
    precio: TablaSIMM


def _num(texto: str | None) -> float | None:
    t = limpiar_celda(texto)
    if not t or not numeros.parece_numero(t):
        return None
    return numeros.leer_numero(t, numeros.US)


def _leer_tablas(filas: list[list[str | None]]) -> dict[str, TablaSIMM]:
    """Recorre las filas de todas las tablas y arma las secciones 'oferta' y 'precio'."""
    secciones: dict[str, TablaSIMM] = {}
    seccion = None
    col_anios: dict[int, int] = {}
    col_indice = None
    for fila in filas:
        celdas = [limpiar_celda(c) for c in fila]
        unido = normalizar(" ".join(celdas))
        if "indice estacional de oferta" in unido:
            seccion, col_anios, col_indice = "oferta", {}, None
        elif "indice estacional de precio" in unido:
            seccion, col_anios, col_indice = "precio", {}, None
        if seccion is None:
            continue
        for i, c in enumerate(celdas):
            if normalizar(c) == "indice estacional":
                col_indice = i
        anios = {i: int(c) for i, c in enumerate(celdas) if re.fullmatch(r"(19|20)\d{2}", c)}
        if len(anios) >= 2:
            col_anios = anios
            continue
        mes_txt = next((normalizar(c) for c in celdas if normalizar(c) in MESES + list(_ALIAS_MES) + ["promedio"]), None)
        if not mes_txt or not col_anios:
            continue
        tabla = secciones.setdefault(seccion, TablaSIMM(sorted(col_anios.values()), {}, [None] * 12))
        if mes_txt == "promedio":
            tabla.promedios_anuales = {a: v for i, a in col_anios.items() if (v := _num(celdas[i])) is not None}
            continue
        mes = MESES.index(_ALIAS_MES.get(mes_txt, mes_txt)) + 1
        for i, anio in col_anios.items():
            v = _num(celdas[i]) if i < len(celdas) else None
            if v is not None:
                tabla.valores[(anio, mes)] = v
        if col_indice is not None and col_indice < len(celdas):
            tabla.indice_oficial[mes - 1] = _num(celdas[col_indice])
    return secciones


def parsear_indice(origen: bytes | str | Path) -> IndiceSIMM:
    abierto = pdfplumber.open(io.BytesIO(origen)) if isinstance(origen, bytes) else pdfplumber.open(origen)
    with abierto as pdf:
        texto = "\n".join(p.extract_text() or "" for p in pdf.pages)
        filas = [f for p in pdf.pages for t in p.extract_tables() for f in t]
    titulo = _RE_TITULO.search(texto)
    if not titulo:
        raise ErrorFormato("No se encontró el título '… Índice Estacional de Oferta y Precio …'")
    unidad = next((m.group("unidad").strip() for m in _RE_UNIDAD.finditer(texto)), None)
    edicion = _RE_EDICION.search(texto)
    secciones = _leer_tablas(filas)
    if "precio" not in secciones or len(secciones["precio"].valores) < 12:
        raise ErrorFormato("No se encontró la tabla de precios mensuales en el PDF del índice")
    return IndiceSIMM(
        nombre=titulo.group("nombre").strip().rstrip("."),
        edicion=int(edicion.group(1)) if edicion else None,
        unidad_precio=unidad,
        oferta=secciones.get("oferta"),
        precio=secciones["precio"],
    )

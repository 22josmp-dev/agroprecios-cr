"""Índice estacional de precios.

Método propio (el pedido en el diseño):
  ratio(mes, año) = precio(mes, año) / media móvil centrada de 12 meses (2×12)
  índice(mes)     = mediana de los ratios de ese mes entre años
  normalizado para que el promedio de los 12 índices sea 1.0
  desviación(mes) = desviación estándar de los ratios de ese mes (ya normalizados)

Método del SIMM ("porcentaje promedio", instructivo DEDM-SIMM-INF-007-26): se usa solo para
verificar que leemos bien sus tablas (debe reproducir su columna "Índice Estacional").
"""
from __future__ import annotations

from statistics import mean, median, pstdev

from . import config

Serie = dict[tuple[int, int], float]  # (año, mes 1-12) -> precio


def _secuencia(serie: Serie) -> tuple[list[tuple[int, int]], list[float | None]]:
    if not serie:
        return [], []
    (a0, m0), (a1, m1) = min(serie), max(serie)
    claves, a, m = [], a0, m0
    while (a, m) <= (a1, m1):
        claves.append((a, m))
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)
    return claves, [serie.get(k) for k in claves]


def media_movil_centrada(valores: list[float | None]) -> list[float | None]:
    """Media móvil 2×12 centrada: requiere 13 meses consecutivos sin faltantes."""
    salida: list[float | None] = [None] * len(valores)
    for t in range(6, len(valores) - 6):
        ventana = valores[t - 6:t + 7]
        if any(v is None for v in ventana):
            continue
        salida[t] = (0.5 * ventana[0] + sum(ventana[1:12]) + 0.5 * ventana[12]) / 12
    return salida


def confianza(anios: int, desviacion_media: float | None) -> str:
    """alta: ≥5 años y desviación baja; media: 3–4 años; baja: cualquier otro caso."""
    if anios >= 5 and desviacion_media is not None and desviacion_media <= config.DESVIACION_BAJA:
        return "alta"
    if 3 <= anios <= 4:
        return "media"
    return "baja"


def _ratios_media_movil(serie: Serie) -> dict[int, list[float]]:
    claves, valores = _secuencia(serie)
    ratios: dict[int, list[float]] = {m: [] for m in range(1, 13)}
    for (a, m), v, base in zip(claves, valores, media_movil_centrada(valores)):
        if v is not None and base:
            ratios[m].append(v / base)
    return ratios


def _ratios_promedio_anual(serie: Serie) -> dict[int, list[float]]:
    """Respaldo para productos de temporada (meses sin mercado): ratio contra el promedio de
    los meses con dato del mismo año. Años con menos de 3 meses no se usan."""
    por_anio: dict[int, dict[int, float]] = {}
    for (a, m), v in serie.items():
        if v is not None:
            por_anio.setdefault(a, {})[m] = v
    ratios: dict[int, list[float]] = {m: [] for m in range(1, 13)}
    for meses in por_anio.values():
        if len(meses) >= 3:
            prom = mean(meses.values())
            for m, v in meses.items():
                ratios[m].append(v / prom)
    return ratios


def indice_estacional(serie: Serie) -> dict:
    anios = len({a for (a, _), v in serie.items() if v is not None})
    ratios = _ratios_media_movil(serie)
    metodo = "media_movil_12"
    if min(len(r) for r in ratios.values()) == 0:
        # Serie con huecos (fruta de temporada): la media móvil no llega a los 12 meses
        ratios = _ratios_promedio_anual(serie)
        metodo = "promedio_anual"
    n_ratios = [len(ratios[m]) for m in range(1, 13)]
    resultado = {"years_of_data": anios, "n_ratios": n_ratios, "indice": None, "desviacion": None,
                 "desviacion_media": None, "confianza": "baja", "suficiente": False, "metodo": metodo,
                 "meses_sin_dato": [m for m in range(1, 13) if not ratios[m]]}
    con_dato = [m for m in range(1, 13) if ratios[m]]
    if len(con_dato) < 3:
        resultado["motivo"] = "Datos insuficientes para calcular un índice"
        return resultado
    bruto = {m: median(ratios[m]) for m in con_dato}
    factor = len(con_dato) / sum(bruto.values())  # promedio 1.0 sobre los meses con dato
    indice = [round(bruto[m] * factor, 4) if m in bruto else None for m in range(1, 13)]
    desv = [round(pstdev([r * factor for r in ratios[m]]), 4) if len(ratios[m]) >= 2 else None
            for m in range(1, 13)]
    conocidas = [d for d in desv if d is not None]
    desv_media = round(mean(conocidas), 4) if conocidas else None
    resultado.update(indice=indice, desviacion=desv, desviacion_media=desv_media,
                     confianza=confianza(anios, desv_media), suficiente=True)
    motivos = []
    if anios < 3:
        motivos.append(f"Solo {anios} año(s) de datos: confianza baja")
    if resultado["meses_sin_dato"]:
        motivos.append("Meses sin mercado en el CENADA: " + ", ".join(map(str, resultado["meses_sin_dato"])))
    if metodo == "promedio_anual":
        motivos.append("Serie con meses faltantes: índice contra el promedio anual (no media móvil)")
    resultado["motivo"] = "; ".join(motivos) or None
    return resultado


def indice_porcentaje_promedio(serie: Serie) -> list[float] | None:
    """Método del SIMM: % de cada mes sobre el promedio de su año (con los meses disponibles),
    promediado entre los años que tienen ese mes. Así reproduce las tablas publicadas, que
    incluyen años con meses faltantes."""
    por_anio: dict[int, dict[int, float]] = {}
    for (a, m), v in serie.items():
        if v is not None:
            por_anio.setdefault(a, {})[m] = v
    pct: dict[int, list[float]] = {m: [] for m in range(1, 13)}
    for meses in por_anio.values():
        prom = mean(meses.values())
        for m, v in meses.items():
            pct[m].append(v / prom)
    if any(not pct[m] for m in pct):
        return None
    return [round(mean(pct[m]), 4) for m in range(1, 13)]

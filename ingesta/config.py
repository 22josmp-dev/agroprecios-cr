"""Parámetros del motor de ingesta. Los umbrales se pueden cambiar con variables de entorno."""
import os
from datetime import date, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Costa Rica no usa horario de verano: UTC-6 todo el año.
TZ_CR = timezone(timedelta(hours=-6), "America/Costa_Rica")

USER_AGENT = (
    "AgroPreciosCR-bot/1.0 (+https://github.com/22josmp-dev/agroprecios-cr; "
    "app informativa sin fines de lucro; datos publicos PIMA-SIMM)"
)
BASE_URL = "https://bpm.pima.go.cr"
CM_BOLETIN = 4        # iframe de https://www.pima.go.cr/boletin/
CM_INDICES = 77       # iframe de https://www.pima.go.cr/reporte-indices-estacionales/

INTERVALO_MIN_S = 1.1   # como máximo 1 solicitud por segundo
TIMEOUT_S = 60
REINTENTOS = 3          # reintentos después del primer intento
ESPERA_BASE_S = 5       # espera creciente: 5 s, 15 s, 45 s

# Se vuelven a descargar los N boletines más recientes aunque ya estén procesados,
# para detectar republicaciones del mismo día (cambio de SHA-256).
REVISAR_ULTIMOS = int(os.environ.get("REVISAR_ULTIMOS", "2"))

# Un boletín con menos registros válidos que UMBRAL_REGISTROS × (último boletín del mismo
# día de la semana) se trata como falla de parseo.
UMBRAL_REGISTROS = float(os.environ.get("UMBRAL_REGISTROS", "0.8"))
# Si todavía no hay un boletín del mismo día de la semana: contra la mediana reciente.
UMBRAL_REGISTROS_OTRO_DIA = float(os.environ.get("UMBRAL_REGISTROS_OTRO_DIA", "0.6"))
MIN_REGISTROS_ABS = int(os.environ.get("MIN_REGISTROS_ABS", "20"))

# Tolerancia para "promedio dentro de [mínimo, máximo]" (redondeos del boletín).
TOLERANCIA_PROMEDIO = 0.005

HISTORIAL_META = 30  # entradas guardadas en meta.json -> historial


def _pascua(anio: int) -> date:
    """Domingo de Pascua (algoritmo gregoriano anónimo)."""
    a, b, c = anio % 19, anio // 100, anio % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = (h + l - 7 * m + 114) % 31 + 1
    return date(anio, mes, dia)


def feriados(anio: int) -> set[date]:
    """Feriados de Costa Rica en que se asume que puede no haber boletín.

    NO VERIFICADO: no se sabe si el CENADA opera en cada feriado. Solo se usa para no dar
    una falsa alarma de "boletín no publicado"; si el PIMA publica ese día, se procesa igual.
    Algunos feriados se trasladan a lunes por ley en ciertos años: agregarlos en
    FERIADOS_EXTRA (formato AAAA-MM-DD separados por coma) si hace falta.
    """
    fijos = [(1, 1), (4, 11), (5, 1), (7, 25), (8, 2), (8, 15), (8, 31), (9, 15), (12, 1), (12, 25)]
    dias = {date(anio, m, d) for m, d in fijos}
    pascua = _pascua(anio)
    dias |= {pascua - timedelta(days=3), pascua - timedelta(days=2)}  # Jueves y Viernes Santo
    for txt in filter(None, os.environ.get("FERIADOS_EXTRA", "").split(",")):
        f = date.fromisoformat(txt.strip())
        if f.year == anio:
            dias.add(f)
    return dias


def se_espera_boletin(dia: date) -> bool:
    """Lunes a viernes que no sean feriado."""
    return dia.weekday() < 5 and dia not in feriados(dia.year)

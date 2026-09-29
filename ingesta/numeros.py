"""Lectura de números del boletín en formato 1,000.00 (EE. UU.) o 1.000,00 (latino).

El formato se decide por documento: se cuentan los valores que solo pueden leerse de una
manera (p. ej. '1,130.00' o '300.00' son EE. UU.; '1.130,00' o '300,00' son latinos) y gana
la mayoría. Los valores ambiguos ('1,000', '1.000', '30') se leen con el formato del documento.
"""
import re

US = "1,000.00"
LATINO = "1.000,00"

_US = re.compile(r"^(\d{1,3}(,\d{3})+|\d+)(\.\d+)?$")
_LATINO = re.compile(r"^(\d{1,3}(\.\d{3})+|\d+)(,\d+)?$")
# Evidencia inequívoca de cada formato
_SOLO_US = re.compile(r"(^|\d)\.\d{1,2}$|,\d{3}\.\d+$")
_SOLO_LATINO = re.compile(r"(^|\d),\d{1,2}$|\.\d{3},\d+$")


class NumeroInvalido(ValueError):
    pass


def _limpiar(texto: str) -> str:
    return re.sub(r"[\s ₡¢]", "", texto or "")


def detectar_formato(valores: list[str]) -> tuple[str, dict]:
    votos = {US: 0, LATINO: 0}
    for v in map(_limpiar, valores):
        if _SOLO_US.search(v) and _US.match(v):
            votos[US] += 1
        elif _SOLO_LATINO.search(v) and _LATINO.match(v):
            votos[LATINO] += 1
    formato = LATINO if votos[LATINO] > votos[US] else US
    return formato, votos


def leer_numero(texto: str, formato: str) -> float:
    v = _limpiar(texto)
    if formato == US:
        if not _US.match(v):
            raise NumeroInvalido(f"'{texto}' no es un número en formato {US}")
        return float(v.replace(",", ""))
    if not _LATINO.match(v):
        raise NumeroInvalido(f"'{texto}' no es un número en formato {LATINO}")
    return float(v.replace(".", "").replace(",", "."))


def parece_numero(texto: str) -> bool:
    return bool(re.fullmatch(r"\d[\d.,]*", _limpiar(texto)))

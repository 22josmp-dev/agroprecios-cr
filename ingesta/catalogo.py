"""Catálogo de productos (data/catalog.json): nombres normalizados, sinónimos y unidades."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .texto import normalizar

_RE_PESO = re.compile(r"\(\s*(\d+(?:[.,]\d+)?)\s*(kg|kilos?|g|gr|gramos)\s*\)", re.I)


def kg_equivalente(unidad: str, producto: str = "") -> float | None:
    """Kilos por unidad de comercialización, solo si el boletín los declara.

    'Kilo' -> 1; 'Malla (45 kg)' -> 45; 'Bandeja (400 g)' -> 0.4; 'Fresa (1 Kg)' + 'Bandeja' -> 1.
    'Caja plástica', 'Unidad', 'Java', etc. sin peso escrito -> None (no se inventa un peso).
    """
    if normalizar(unidad) in ("kilo", "kilos", "kg", "kilogramo"):
        return 1.0
    for texto in (unidad, producto):
        m = _RE_PESO.search(texto or "")
        if m:
            valor = float(m.group(1).replace(",", "."))
            return valor / 1000 if m.group(2).lower().startswith("g") else valor
    return None


class Catalogo:
    def __init__(self, datos: dict):
        self.datos = datos
        # Por (fuente, nombre normalizado): el mismo nombre puede existir en dos boletines
        self._por_nombre: dict[tuple[str, str], dict] = {}
        for p in datos["productos"]:
            for nombre in [p["nombre"], *p.get("nombres_boletin", [])]:
                self._por_nombre[(p.get("fuente", "diario"), normalizar(nombre))] = p

    @classmethod
    def cargar(cls, ruta: Path) -> "Catalogo":
        return cls(json.loads(Path(ruta).read_text(encoding="utf-8")))

    def buscar(self, nombre_boletin: str, fuente: str = "diario") -> dict | None:
        return self._por_nombre.get((fuente, normalizar(nombre_boletin)))

    def por_id(self, id_: str) -> dict | None:
        return next((p for p in self.datos["productos"] if p["id"] == id_), None)

    def registrar_unidad(self, producto: dict, unidad: str, nombre_boletin: str) -> bool:
        """Agrega al catálogo una unidad observada que no estaba. Devuelve True si cambió."""
        if any(normalizar(u["unidad"]) == normalizar(unidad) for u in producto["unidades"]):
            return False
        producto["unidades"].append({"unidad": unidad, "kg": kg_equivalente(unidad, nombre_boletin)})
        return True

    def guardar(self, ruta: Path) -> None:
        from .almacen import escribir_json
        escribir_json(Path(ruta), self.datos)

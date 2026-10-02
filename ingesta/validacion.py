"""Validación de cada fila del boletín. Nada se descarta en silencio: lo inválido va a rechazos."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date

from . import config, numeros
from .catalogo import Catalogo, kg_equivalente
from .parser_boletin import ErrorFormato, ResultadoParseo
from .texto import normalizar


@dataclass
class Registro:
    id: str
    producto: str
    unidad: str
    kg: float | None
    minimo: float
    maximo: float
    moda: float
    promedio: float

    def como_fila(self) -> list:
        """Forma compacta para data/prices/AAAA-MM.json."""
        return [self.id, self.unidad, self.minimo, self.maximo, self.moda, self.promedio]


@dataclass
class Rechazo:
    producto: str
    unidad: str
    valores: dict
    motivos: list[str]
    pagina: int | None = None


def validar_fecha(fecha_plaza: date, fecha_lista: date | None, hoy: date) -> None:
    """Errores de fecha afectan a todo el documento: se levanta ErrorFormato."""
    if fecha_plaza > hoy:
        raise ErrorFormato(f"La fecha de plaza {fecha_plaza} está en el futuro (hoy {hoy})")
    if fecha_plaza.year < 2000:
        raise ErrorFormato(f"Fecha de plaza no válida: {fecha_plaza}")
    if fecha_lista and fecha_lista != fecha_plaza:
        raise ErrorFormato(f"La fecha del PDF ({fecha_plaza}) no coincide con la de la lista ({fecha_lista})")


def validar(resultado: ResultadoParseo, catalogo: Catalogo, hoy: date,
            fecha_lista: date | None = None, fuente: str = "diario") -> tuple[list[Registro], list[Rechazo]]:
    validar_fecha(resultado.fecha_plaza, fecha_lista, hoy)
    registros: list[Registro] = []
    rechazos: list[Rechazo] = []
    vistos: set[tuple[str, str]] = set()
    tol = config.TOLERANCIA_PROMEDIO

    for raro in resultado.no_reconocidas:
        rechazos.append(Rechazo(" ".join(raro["celdas"]), "", {}, [raro["motivo"]], raro["pagina"]))

    for fila in resultado.filas:
        motivos: list[str] = []
        valores: dict[str, float] = {}
        for col, texto in fila.valores.items():
            try:
                valores[col] = numeros.leer_numero(texto, resultado.formato_numerico)
            except numeros.NumeroInvalido as e:
                motivos.append(f"número ilegible en {col}: {e}")
        if not fila.producto:
            motivos.append("fila sin nombre de producto")
        if not fila.unidad:
            motivos.append("fila sin unidad de comercialización")
        producto = catalogo.buscar(fila.producto, fuente)
        if producto is None:
            motivos.append("producto no reconocido en el catálogo")
        if len(valores) == 4:
            mn, mx, mo, pr = (valores[c] for c in ("minimo", "maximo", "moda", "promedio"))
            if min(mn, mx, mo, pr) <= 0:
                motivos.append("precio menor o igual a cero")
            if mn > mo:
                motivos.append(f"mínimo ({mn}) mayor que la moda ({mo})")
            if mo > mx:
                motivos.append(f"moda ({mo}) mayor que el máximo ({mx})")
            if not (mn * (1 - tol) <= pr <= mx * (1 + tol)):
                motivos.append(f"promedio ({pr}) fuera de [mínimo {mn}, máximo {mx}]")
        clave = (normalizar(fila.producto), normalizar(fila.unidad))
        if clave in vistos:
            motivos.append("producto y unidad repetidos en el mismo boletín")
        if motivos:
            rechazos.append(Rechazo(fila.producto, fila.unidad, dict(fila.valores), motivos, fila.pagina))
            continue
        vistos.add(clave)
        registros.append(Registro(
            id=producto["id"], producto=fila.producto, unidad=fila.unidad,
            kg=kg_equivalente(fila.unidad, fila.producto),
            minimo=valores["minimo"], maximo=valores["maximo"], moda=valores["moda"], promedio=valores["promedio"],
        ))
    return registros, rechazos


def rechazo_a_dict(r: Rechazo) -> dict:
    return asdict(r)

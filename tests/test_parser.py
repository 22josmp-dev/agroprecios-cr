"""Parser con boletines REALES (tests/samples/boletines) y sintéticos (DATOS DE EJEMPLO)."""
from datetime import date

import pytest
from conftest import BOLETINES
from sinteticos import boletin_sintetico, filas_ejemplo

from ingesta.numeros import LATINO, US
from ingesta.parser_boletin import ErrorFormato, parsear_pdf, separar_unidad
from ingesta.validacion import validar

# (archivo, fecha, filas esperadas) — conteos verificados a mano en docs/FORMATO_BOLETIN.md
REALES = [
    ("boletin_2026-09-28.pdf", date(2026, 9, 28), 57),  # lunes
    ("boletin_2026-09-22.pdf", date(2026, 9, 22), 51),  # martes
    ("boletin_2026-09-23.pdf", date(2026, 9, 23), 65),  # miércoles
    ("boletin_2026-09-24.pdf", date(2026, 9, 24), 51),  # jueves
]


@pytest.mark.parametrize("archivo,fecha,n", REALES)
def test_boletines_reales(archivo, fecha, n, catalogo):
    r = parsear_pdf(BOLETINES / archivo)
    assert r.fecha_plaza == fecha
    assert len(r.filas) == n
    assert r.formato_numerico == US
    assert r.no_reconocidas == []
    registros, rechazos = validar(r, catalogo, hoy=date(2026, 9, 29), fecha_lista=fecha)
    assert len(registros) == n and rechazos == []


@pytest.mark.parametrize("archivo,fecha,n", REALES)
def test_respaldo_por_palabras_da_lo_mismo(archivo, fecha, n):
    por_tablas = parsear_pdf(BOLETINES / archivo)
    por_palabras = parsear_pdf(BOLETINES / archivo, usar_tablas=False)
    assert set(por_palabras.metodos) == {"palabras"}
    clave = lambda r: [(f.producto, f.unidad, f.valores) for f in r.filas]  # noqa: E731
    assert clave(por_palabras) == clave(por_tablas)


def test_valores_concretos_28_setiembre(catalogo):
    r = parsear_pdf(BOLETINES / "boletin_2026-09-28.pdf")
    registros, _ = validar(r, catalogo, hoy=date(2026, 9, 29))
    por_id = {x.id: x for x in registros}
    apio = por_id["apio-verde-mata"]
    assert (apio.unidad, apio.minimo, apio.maximo, apio.moda, apio.promedio) == ("Mata", 1000, 1300, 1200, 1130)
    chayote = por_id["chayote-tierno-criollo"]
    assert (chayote.unidad, chayote.minimo, chayote.maximo, chayote.moda, chayote.promedio) == ("Java", 35000, 40000, 40000, 39000)
    manga = por_id["manga-grande-cavallini"]
    assert manga.unidad == "Caja plástica (17 kg)" and manga.kg == 17
    # 'Piña - pequeña' está en la página 2
    assert por_id["pina-pequena"].promedio == 728.57


def test_sintetico_formato_latino_y_otro_orden(catalogo):
    """DATOS DE EJEMPLO: formato 1.000,00 y columnas en el orden que se había supuesto."""
    orden = ("Promedio", "Moda", "Máximo", "Mínimo")
    filas = filas_ejemplo(25)
    pdf = boletin_sintetico(date(2026, 10, 5), filas, orden=orden, formato="LATINO")
    r = parsear_pdf(pdf)
    assert r.formato_numerico == LATINO
    assert r.fecha_plaza == date(2026, 10, 5)
    registros, rechazos = validar(r, catalogo, hoy=date(2026, 10, 5))
    assert rechazos == []
    tomate = next(x for x in registros if x.id == "tomate-primera")
    assert tomate.minimo == 1000.0 and tomate.maximo == 1300.0 and tomate.moda == 1100.0 and tomate.promedio == 1120.0


def test_sintetico_unidad_pegada_al_nombre(catalogo):
    pdf = boletin_sintetico(date(2026, 10, 5), filas_ejemplo(25), unidad_pegada=True)
    registros, rechazos = validar(parsear_pdf(pdf), catalogo, hoy=date(2026, 10, 5))
    assert rechazos == []
    papa = next(x for x in registros if x.id == "papa-blanca-primera")
    assert papa.unidad == "Malla (45 kg)" and papa.kg == 45


def test_sin_encabezado_es_cambio_de_formato():
    pdf = boletin_sintetico(date(2026, 10, 5), filas_ejemplo(25), encabezado=False)
    with pytest.raises(ErrorFormato, match="encabezado"):
        parsear_pdf(pdf)


def test_encabezado_con_columna_faltante():
    pdf = boletin_sintetico(date(2026, 10, 5), filas_ejemplo(5), orden=("Mínimo", "Máximo", "Moda", "Precio"))
    with pytest.raises(ErrorFormato):
        parsear_pdf(pdf)


def test_separar_unidad():
    assert separar_unidad("Papa blanca Caja (10 kg)", "") == ("Papa blanca", "Caja (10 kg)")
    assert separar_unidad("Chile dulce primera Caja plástica", "") == ("Chile dulce primera", "Caja plástica")
    assert separar_unidad("Tomate primera", "Caja plástica (18 kg)") == ("Tomate primera", "Caja plástica (18 kg)")

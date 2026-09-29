from datetime import date

import pytest

from ingesta.numeros import US
from ingesta.parser_boletin import ErrorFormato, FilaCruda, ResultadoParseo
from ingesta.validacion import validar

HOY = date(2026, 9, 29)


def resultado(filas, fecha=date(2026, 9, 28)):
    return ResultadoParseo(fecha, US, {}, [FilaCruda(p, u, v, 1) for p, u, v in filas])


def v(mn, mx, mo, pr):
    return {"minimo": mn, "maximo": mx, "moda": mo, "promedio": pr}


def motivos(catalogo, fila):
    registros, rechazos = validar(resultado([fila]), catalogo, HOY)
    assert registros == []
    return " ".join(rechazos[0].motivos)


def test_registro_valido(catalogo):
    registros, rechazos = validar(resultado([("Camote", "Kilo", v("1,400.00", "1,600.00", "1,500.00", "1,485.71"))]), catalogo, HOY)
    assert rechazos == [] and registros[0].id == "camote" and registros[0].kg == 1.0


def test_nombre_con_tildes_o_mayusculas_distintas(catalogo):
    registros, _ = validar(resultado([("BROCOLI", "Kilo", v("1.00", "2.00", "1.50", "1.50"))]), catalogo, HOY)
    assert registros[0].id == "brocoli"


def test_minimo_mayor_que_moda(catalogo):
    assert "mínimo" in motivos(catalogo, ("Camote", "Kilo", v("1,600.00", "1,700.00", "1,500.00", "1,600.00")))


def test_moda_mayor_que_maximo(catalogo):
    assert "moda" in motivos(catalogo, ("Camote", "Kilo", v("1,400.00", "1,500.00", "1,600.00", "1,450.00")))


def test_promedio_fuera_de_rango(catalogo):
    assert "promedio" in motivos(catalogo, ("Camote", "Kilo", v("1,400.00", "1,600.00", "1,500.00", "1,900.00")))


def test_promedio_con_redondeo_tolerado(catalogo):
    registros, _ = validar(resultado([("Camote", "Kilo", v("1,000.00", "1,600.00", "1,500.00", "1,602.00"))]), catalogo, HOY)
    assert len(registros) == 1


def test_precio_cero(catalogo):
    assert "cero" in motivos(catalogo, ("Camote", "Kilo", v("0.00", "1,600.00", "1,500.00", "1,500.00")))


def test_producto_desconocido(catalogo):
    assert "no reconocido" in motivos(catalogo, ("Durián importado", "Kilo", v("1.00", "2.00", "1.50", "1.50")))


def test_numero_ilegible(catalogo):
    assert "ilegible" in motivos(catalogo, ("Camote", "Kilo", v("1.400,00", "1,600.00", "1,500.00", "1,500.00")))


def test_duplicado(catalogo):
    fila = ("Camote", "Kilo", v("1.00", "2.00", "1.50", "1.50"))
    registros, rechazos = validar(resultado([fila, fila]), catalogo, HOY)
    assert len(registros) == 1 and "repetidos" in rechazos[0].motivos[0]


def test_fecha_futura(catalogo):
    with pytest.raises(ErrorFormato, match="futuro"):
        validar(resultado([], fecha=date(2026, 10, 1)), catalogo, HOY)


def test_fecha_distinta_a_la_lista(catalogo):
    with pytest.raises(ErrorFormato, match="no coincide"):
        validar(resultado([]), catalogo, HOY, fecha_lista=date(2026, 9, 25))

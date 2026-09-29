import pytest

from ingesta import numeros
from ingesta.numeros import LATINO, US, detectar_formato, leer_numero


def test_formato_us_real():
    formato, votos = detectar_formato(["1,000.00", "1,300.00", "319.23", "30.00"])
    assert formato == US and votos[US] == 4
    assert leer_numero("35,000.00", US) == 35000.0
    assert leer_numero("1,130.00", US) == 1130.0


def test_formato_latino():
    formato, _ = detectar_formato(["1.000,00", "1.300,00", "319,23"])
    assert formato == LATINO
    assert leer_numero("35.000,00", LATINO) == 35000.0
    assert leer_numero("319,23", LATINO) == 319.23


def test_valores_ambiguos_siguen_al_documento():
    # '1,000' y '1.000' solos son ambiguos; se leen con el formato mayoritario
    assert detectar_formato(["1,000", "2,500.50"])[0] == US
    assert leer_numero("1,000", US) == 1000.0
    assert detectar_formato(["1.000", "2.500,50"])[0] == LATINO
    assert leer_numero("1.000", LATINO) == 1000.0


def test_sin_evidencia_usa_formato_observado():
    assert detectar_formato(["30", "150"])[0] == US


def test_numero_ilegible():
    with pytest.raises(numeros.NumeroInvalido):
        leer_numero("1.000,00", US)
    with pytest.raises(numeros.NumeroInvalido):
        leer_numero("12a", US)


def test_simbolo_colon_y_espacios():
    assert leer_numero(" ₡1,250.00 ", US) == 1250.0

"""Boletines SINTÉTICOS para pruebas (DATOS DE EJEMPLO, no son precios reales).

Imitan el formato del PIMA para probar casos que no aparecieron en los boletines reales
analizados: formato numérico 1.000,00, otro orden de columnas, unidad pegada al nombre,
encabezado faltante y pocos registros.
"""
from datetime import date

from fpdf import FPDF

ORDEN_REAL = ("Mínimo", "Máximo", "Moda", "Promedio")
CLAVES = {"Mínimo": "minimo", "Máximo": "maximo", "Moda": "moda", "Promedio": "promedio"}


def formatear(valor: float, formato: str) -> str:
    us = f"{valor:,.2f}"
    return us if formato == "US" else us.replace(",", "_").replace(".", ",").replace("_", ".")


def boletin_sintetico(fecha: date, filas: list[tuple[str, str, dict]], orden=ORDEN_REAL, formato="US",
                      encabezado=True, unidad_pegada=False) -> bytes:
    """filas: [(producto, unidad, {"minimo": .., "maximo": .., "moda": .., "promedio": ..})]"""
    pdf = FPDF(format="A4")
    pdf.add_page()
    pdf.set_font("Helvetica", size=8)
    lineas = [
        "DATOS DE EJEMPLO - boletin sintetico para pruebas",
        "SIMM",
        "BOLETIN DE PRECIOS: PRECIOS DE MAYORISTA A MINORISTA",
        f"Fecha de Plaza: {fecha.day}/{fecha.month}/{fecha.year} 09:00:00",
    ]
    if encabezado:
        lineas.append("Producto Unidad de comercialización mayorista " + " ".join(orden))
    for linea in lineas:
        pdf.cell(0, 5, linea, new_x="LMARGIN", new_y="NEXT")
    with pdf.table(col_widths=(70, 40, 20, 20, 20, 20), first_row_as_headings=False, line_height=5) as tabla:
        for producto, unidad, valores in filas:
            fila = tabla.row()
            if unidad_pegada:
                fila.cell(f"{producto} {unidad}")
                fila.cell("")
            else:
                fila.cell(producto)
                fila.cell(unidad)
            for col in orden:
                # Una columna con nombre desconocido (prueba de cambio de formato) repite el promedio
                fila.cell(formatear(valores[CLAVES.get(col, "promedio")], formato))
    pdf.cell(0, 5, f"Fecha: {fecha.day} Fecha de Plaza: {fecha.day:02d}/{fecha.month:02d}/{fecha.year} Pag. 1 de 1",
             new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def filas_ejemplo(n: int = 25, base: float = 1000.0) -> list[tuple[str, str, dict]]:
    """n filas con nombres reales del catálogo y precios inventados coherentes (DATOS DE EJEMPLO)."""
    nombres = [
        ("Tomate primera", "Caja plástica (18 kg)"), ("Papa blanca primera", "Malla (45 kg)"),
        ("Camote", "Kilo"), ("Chile dulce primera", "Caja plástica"), ("Brócoli", "Kilo"),
        ("Cebolla seca morada", "Kilo"), ("Chayote tierno criollo", "Java"), ("Coliflor", "Unidad"),
        ("Elote", "Unidad"), ("Lechuga Americana", "Unidad"), ("Pepino", "Kilo"),
        ("Piña - grande", "Unidad"), ("Remolacha", "Unidad"), ("Repollo verde", "Kilo"),
        ("Vainica", "Kilo"), ("Yuca parafinada", "Kilo"), ("Zanahoria primera", "Malla (45 kg)"),
        ("Zucchini", "Unidad"), ("Ñampí", "Kilo"), ("Tiquisque", "Kilo"), ("Papaya híbrida", "Kilo"),
        ("Pitahaya", "Kilo"), ("Naranja dulce", "Unidad"), ("Mandarina primera", "Unidad"),
        ("Limón mesino", "Unidad"), ("Ayote sazón", "Kilo"), ("Espinaca", "Rollo"),
        ("Culantro castilla", "Rollo de 10 rollitos"), ("Jengibre sazón", "Kilo"), ("Pitahaya", "Kilo"),
    ]
    filas = []
    for i, (p, u) in enumerate(nombres[:n]):
        b = base + 137 * i
        filas.append((p, u, {"minimo": b, "maximo": b * 1.3, "moda": b * 1.1, "promedio": b * 1.12}))
    return filas

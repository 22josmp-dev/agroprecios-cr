"""Uso:
  python -m ingesta diario [--ultimo-intento]   proceso diario (lo ejecuta GitHub Actions)
  python -m ingesta estacional [--forzar]       índices estacionales (seasonal.json, historico/)
  python -m ingesta reprocesar                  vuelve a parsear los PDF de /archivo
  python -m ingesta parsear ARCHIVO.pdf         muestra lo que el parser lee de un PDF (diagnóstico)
"""
import argparse
import sys

from . import config


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="python -m ingesta")
    sub = p.add_subparsers(dest="comando", required=True)
    d = sub.add_parser("diario", help="descarga y procesa los boletines nuevos")
    d.add_argument("--ultimo-intento", action="store_true",
                   help="si el boletín de hoy no está publicado, termina con error")
    d.add_argument("--ahora", help="momento UTC ISO a simular (solo pruebas), p. ej. 2026-09-29T19:17:00Z")
    d.add_argument("--fuente", choices=["todas", *config.FUENTES], default="todas",
                   help="boletín a procesar (por defecto todos: diario, fruta, aromaticos)")
    r = sub.add_parser("reprocesar", help="vuelve a parsear todos los PDF archivados")
    r.add_argument("--fuente", choices=list(config.FUENTES), default="diario")
    e = sub.add_parser("estacional", help="índices estacionales (seasonal.json, historico/)")
    e.add_argument("--forzar", action="store_true", help="volver a descargar todos los PDF del SIMM")
    ps = sub.add_parser("parsear", help="muestra el resultado de parsear un PDF")
    ps.add_argument("pdf")
    ps.add_argument("--palabras", action="store_true", help="usar el método de respaldo por palabras")
    a = p.parse_args(argv)

    from .almacen import Almacen
    if a.comando == "diario":
        from .diario import ejecutar_todas
        from .fuente import ClientePIMA
        from datetime import datetime
        ahora = datetime.fromisoformat(a.ahora.replace("Z", "+00:00")) if a.ahora else None
        ids = None if a.fuente == "todas" else [a.fuente]
        return ejecutar_todas(config.RAIZ, ClientePIMA(), ids, ahora=ahora, ultimo_intento=a.ultimo_intento)
    if a.comando == "estacional":
        from .fuente import ClientePIMA
        from .indices import ejecutar_indices
        return ejecutar_indices(Almacen(config.RAIZ), ClientePIMA(), forzar=a.forzar)
    if a.comando == "reprocesar":
        from .diario import reprocesar
        return reprocesar(Almacen(config.RAIZ, config.FUENTES[a.fuente]))
    from .parser_boletin import parsear_pdf
    r = parsear_pdf(a.pdf, usar_tablas=not a.palabras)
    print(f"Fecha de plaza: {r.fecha_plaza} | formato {r.formato_numerico} {r.votos_formato} | "
          f"{len(r.filas)} filas | métodos {r.metodos}")
    for f in r.filas:
        print(f"  p{f.pagina} {f.producto!r:50} {f.unidad!r:26} {f.valores}")
    for x in r.no_reconocidas:
        print("  NO RECONOCIDA", x)
    return 0


if __name__ == "__main__":
    sys.exit(main())

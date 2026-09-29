"""Arma la carpeta del sitio estático que se publica en GitHub Pages.

  _site/            <- app compilada (app/dist) o, si aún no existe, sitio_provisional/
  _site/data/*.json <- datos publicados (sin /archivo: los PDF no se publican)

Uso: python scripts/armar_sitio.py [carpeta_salida]
"""
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def armar(salida: Path) -> Path:
    if salida.exists():
        shutil.rmtree(salida)
    app = RAIZ / "app" / "dist"
    origen = app if (app / "index.html").exists() else RAIZ / "sitio_provisional"
    shutil.copytree(origen, salida)
    datos = RAIZ / "data"
    for archivo in datos.rglob("*.json"):
        destino = salida / "data" / archivo.relative_to(datos)
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(archivo, destino)
    (salida / ".nojekyll").write_text("", encoding="utf-8")  # servir archivos tal cual
    total = sum(f.stat().st_size for f in salida.rglob("*") if f.is_file())
    print(f"Sitio armado desde {origen.relative_to(RAIZ)} en {salida} ({total / 1024:.0f} KB)")
    if total > 900 * 1024 * 1024:
        raise SystemExit("El sitio supera 900 MB; GitHub Pages admite como máximo 1 GB")
    return salida


if __name__ == "__main__":
    armar(Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "_site")

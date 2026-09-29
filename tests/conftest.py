import shutil
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parent))

MUESTRAS = RAIZ / "tests" / "samples"
BOLETINES = MUESTRAS / "boletines"


@pytest.fixture
def catalogo():
    from ingesta.catalogo import Catalogo
    return Catalogo.cargar(RAIZ / "data" / "catalog.json")


@pytest.fixture
def repo_temporal(tmp_path):
    """Copia mínima del repositorio (solo el catálogo) para probar el proceso diario."""
    (tmp_path / "data").mkdir()
    shutil.copy(RAIZ / "data" / "catalog.json", tmp_path / "data" / "catalog.json")
    return tmp_path

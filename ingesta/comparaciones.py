"""Construye data/latest.json: precios del último boletín con sus comparaciones ya calculadas,
para que la app no tenga que descargar el historial solo para mostrar las flechas."""
from __future__ import annotations

from datetime import date, timedelta
from statistics import mean

from .almacen import FUENTE, Almacen
from .catalogo import Catalogo, kg_equivalente


def _variacion(actual: float, referencia: float | None) -> float | None:
    if not referencia:
        return None
    return round((actual - referencia) / referencia * 100, 1)


def construir_latest(almacen: Almacen, catalogo: Catalogo, fecha: date, generado_utc: str) -> dict:
    dias = almacen.cargar_dias(fecha - timedelta(days=45), fecha)
    if fecha not in dias:
        raise ValueError(f"No hay datos guardados para {fecha}")
    indice = {d: {(f[0], f[1]): f for f in filas} for d, filas in dias.items()}
    previas = sorted((d for d in dias if d < fecha), reverse=True)
    productos = []
    for id_, unidad, minimo, maximo, moda, promedio in dias[fecha]:
        info = catalogo.por_id(id_) or {}
        clave = (id_, unidad)
        # Solo se compara con la misma unidad de comercialización
        anterior = next((d for d in previas if clave in indice[d]), None)
        semana = next((d for d in previas if fecha - timedelta(days=13) <= d <= fecha - timedelta(days=7)
                       and clave in indice[d]), None)
        ult30 = [indice[d][clave][5] for d in previas if d >= fecha - timedelta(days=30) and clave in indice[d]]
        kg = kg_equivalente(unidad, info.get("nombre", ""))

        def ref(d):
            if d is None:
                return None
            p = indice[d][clave][5]
            return {"fecha": d.isoformat(), "promedio": p, "variacion_pct": _variacion(promedio, p)}

        prom30 = round(mean(ult30), 2) if len(ult30) >= 3 else None
        productos.append({
            "id": id_, "nombre": info.get("nombre", id_), "cultivo": info.get("cultivo"),
            "cultivo_id": info.get("cultivo_id"), "categoria": info.get("categoria"),
            "unidad": unidad, "kg": kg,
            "minimo": minimo, "maximo": maximo, "moda": moda, "promedio": promedio,
            "precio_kg": round(promedio / kg, 2) if kg else None,
            "vs_anterior": ref(anterior),
            "vs_semana": ref(semana),
            "vs_30d": {"dias": len(ult30), "promedio": prom30, "variacion_pct": _variacion(promedio, prom30)} if prom30 else None,
        })
    productos.sort(key=lambda p: p["nombre"])
    return {
        "esquema": 1, "fuente": FUENTE, "datos_de_ejemplo": False,
        "fecha_boletin": fecha.isoformat(), "generado_utc": generado_utc,
        "productos": productos,
    }

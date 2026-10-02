import { useMemo, useState } from "preact/hooks";
import type { DatosBase } from "../app";
import { Buscador, Fuente, TarjetaProducto } from "../componentes/comunes";
import { useFavoritos } from "../favoritos";
import { resumenDelDia } from "../resumen";
import { FUENTES } from "../fuentes";
import { normalizar } from "../texto";

const FILTROS = [{ id: "todas", nombre: "Todos" }, ...FUENTES.map((f) => ({ id: f.id as string, nombre: f.id === "diario" ? "Diario" : f.nombre }))];

export function Inicio({ datos }: { datos: DatosBase }) {
  const favoritos = useFavoritos();
  const [filtro, setFiltro] = useState("todas");
  const productos = datos.latest.productos;
  // El buscador incluye los sinónimos del catálogo; solo lista productos con precio hoy
  const entradas = useMemo(() => {
    const hoy = new Set(productos.map((p) => p.id));
    return datos.catalogo.productos.filter((p) => hoy.has(p.id));
  }, [datos]);
  const favs = productos.filter((p) => favoritos.includes(p.id));
  const resumen = resumenDelDia(productos, favoritos, datos.latest.fuentes);
  const lista = productos
    .filter((p) => filtro === "todas" || p.fuente === filtro)
    .sort((a, b) => normalizar(a.nombre).localeCompare(normalizar(b.nombre)));

  return (
    <>
      <div class="buscador-fijo">
        <Buscador entradas={entradas} alElegir={(e) => { location.hash = `#/producto/${e.id}`; }} />
      </div>

      <section aria-labelledby="t-fav">
        <h2 id="t-fav"><span aria-hidden="true">★ </span>Mis cultivos</h2>
        {favs.length === 0
          ? <p class="nota">Toque la estrella ☆ de un producto para verlo aquí. Se guarda solo en este teléfono.</p>
          : <ul class="lista-tarjetas">{favs.map((p) => <TarjetaProducto key={`${p.id}|${p.unidad}`} p={p} />)}</ul>}
      </section>

      <section aria-labelledby="t-resumen" class="resumen">
        <h2 id="t-resumen">Resumen del día</h2>
        <ul>{resumen.map((f) => <li key={f}>{f}</li>)}</ul>
      </section>

      <section aria-labelledby="t-todos">
        <h2 id="t-todos">Precios</h2>
        <div class="filtros" role="group" aria-label="Filtrar por boletín">
          {FILTROS.map((c) => (
            <button key={c.id} type="button" aria-pressed={filtro === c.id} onClick={() => setFiltro(c.id)}>{c.nombre}</button>
          ))}
        </div>
        <p class="nota">Precio promedio por unidad de venta y cambio frente al boletín anterior del mismo tipo.
          El boletín diario se publica de lunes a viernes; el de fruta importada, cada semana; el de aromáticos y gourmet, cada quince días.</p>
        <ul class="lista-tarjetas">{lista.map((p) => <TarjetaProducto key={`${p.id}|${p.unidad}`} p={p} />)}</ul>
      </section>
      <Fuente />
    </>
  );
}

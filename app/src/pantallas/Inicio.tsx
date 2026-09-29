import { useMemo, useState } from "preact/hooks";
import type { DatosBase } from "../app";
import { Buscador, Fuente, TarjetaProducto } from "../componentes/comunes";
import { useFavoritos } from "../favoritos";
import { resumenDelDia } from "../resumen";
import { normalizar } from "../texto";

const CATEGORIAS = [
  { id: "todas", nombre: "Todos" },
  { id: "hortaliza", nombre: "Hortalizas" },
  { id: "fruta", nombre: "Frutas" },
  { id: "raíz y tubérculo", nombre: "Raíces y tubérculos" },
];

export function Inicio({ datos }: { datos: DatosBase }) {
  const favoritos = useFavoritos();
  const [categoria, setCategoria] = useState("todas");
  const productos = datos.latest.productos;
  // El buscador incluye los sinónimos del catálogo; solo lista productos con precio hoy
  const entradas = useMemo(() => {
    const hoy = new Set(productos.map((p) => p.id));
    return datos.catalogo.productos.filter((p) => hoy.has(p.id));
  }, [datos]);
  const favs = productos.filter((p) => favoritos.includes(p.id));
  const resumen = resumenDelDia(productos, favoritos);
  const lista = productos
    .filter((p) => categoria === "todas" || p.categoria === categoria)
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
          : <ul class="lista-tarjetas">{favs.map((p) => <TarjetaProducto key={p.id} p={p} />)}</ul>}
      </section>

      <section aria-labelledby="t-resumen" class="resumen">
        <h2 id="t-resumen">Resumen del día</h2>
        <ul>{resumen.map((f) => <li key={f}>{f}</li>)}</ul>
      </section>

      <section aria-labelledby="t-todos">
        <h2 id="t-todos">Precios de hoy</h2>
        <div class="filtros" role="group" aria-label="Filtrar por tipo">
          {CATEGORIAS.map((c) => (
            <button key={c.id} type="button" aria-pressed={categoria === c.id} onClick={() => setCategoria(c.id)}>{c.nombre}</button>
          ))}
        </div>
        <p class="nota">Precio promedio por unidad de venta y cambio frente al boletín anterior.</p>
        <ul class="lista-tarjetas">{lista.map((p) => <TarjetaProducto key={p.id} p={p} />)}</ul>
      </section>
      <Fuente />
    </>
  );
}

import { useEffect, useState } from "preact/hooks";
import { AvisoEjemplo, EstadoDatos } from "./componentes/comunes";
import { cargarCatalogo, cargarLatest, cargarMeta } from "./datos";
import { frescura } from "./frescura";
import { Ayuda } from "./pantallas/Ayuda";
import { Detalle } from "./pantallas/Detalle";
import { Guia } from "./pantallas/Guia";
import { Inicio } from "./pantallas/Inicio";
import type { Catalogo, Latest, Meta } from "./tipos";

export interface DatosBase {
  meta: Meta;
  latest: Latest;
  catalogo: Catalogo;
}

function useRuta(): string[] {
  const leer = () => (location.hash.replace(/^#\/?/, "") || "").split("/").filter(Boolean).map(decodeURIComponent);
  const [ruta, setRuta] = useState(leer);
  useEffect(() => {
    const f = () => { setRuta(leer()); window.scrollTo(0, 0); };
    addEventListener("hashchange", f);
    return () => removeEventListener("hashchange", f);
  }, []);
  return ruta;
}

function useEnLinea(): boolean {
  const [enLinea, set] = useState(navigator.onLine);
  useEffect(() => {
    const on = () => set(true), off = () => set(false);
    addEventListener("online", on); addEventListener("offline", off);
    return () => { removeEventListener("online", on); removeEventListener("offline", off); };
  }, []);
  return enLinea;
}

export function App() {
  const ruta = useRuta();
  const enLinea = useEnLinea();
  const [datos, setDatos] = useState<DatosBase | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([cargarMeta(), cargarLatest(), cargarCatalogo()])
      .then(([meta, latest, catalogo]) => setDatos({ meta, latest, catalogo }))
      .catch(() => setError("No se pudieron cargar los precios. Revise su conexión e intente de nuevo."));
  }, []);

  const pantalla = ruta[0] || "inicio";
  const titulo = { inicio: "Inicio", producto: "Detalle", guia: "Guía de siembra", ayuda: "Ayuda" }[pantalla] ?? "Inicio";
  useEffect(() => { document.title = `${titulo} · AgroPrecios CR`; }, [titulo]);

  return (
    <>
      <a class="saltar" href="#contenido">Saltar al contenido</a>
      <header class="barra">
        <a href="#/" class="marca"><span aria-hidden="true">🌱</span> AgroPrecios CR</a>
      </header>
      {!enLinea && <p class="aviso sin-conexion" role="status">Sin conexión: se muestran los últimos datos guardados en el teléfono.</p>}
      <main id="contenido" tabIndex={-1}>
        {error && <p class="aviso" role="alert">{error} <button type="button" onClick={() => location.reload()}>Reintentar</button></p>}
        {!datos && !error && <p class="cargando">Cargando precios…</p>}
        {datos && (
          <>
            {(datos.meta.datos_de_ejemplo || datos.latest.datos_de_ejemplo) && <AvisoEjemplo />}
            {pantalla === "inicio" && (
              <p class="origen-datos">
                Precios mayoristas de referencia del <strong>CENADA</strong>, tomados de los boletines que publica el
                <strong> PIMA – SIMM</strong>: diario (frutas y hortalizas), semanal (fruta importada) y quincenal
                (aromáticos y gourmet). AgroPrecios CR es una app informativa independiente, no oficial del PIMA.
              </p>
            )}
            {(pantalla === "inicio" || pantalla === "producto") && <EstadoDatos f={frescura(datos.meta)} fechaDiario={datos.meta.fecha_boletin} otras={datos.meta.fuentes} />}
            {pantalla === "inicio" && <Inicio datos={datos} />}
            {pantalla === "producto" && <Detalle datos={datos} id={ruta[1]} />}
            {pantalla === "guia" && <Guia inicial={ruta[1]} />}
            {pantalla === "ayuda" && <Ayuda meta={datos.meta} />}
          </>
        )}
      </main>
      <nav class="navegacion" aria-label="Secciones">
        <a href="#/" aria-current={pantalla === "inicio" || pantalla === "producto" ? "page" : undefined}><span aria-hidden="true">🏠</span>Precios</a>
        <a href="#/guia" aria-current={pantalla === "guia" ? "page" : undefined}><span aria-hidden="true">📅</span>Guía de siembra</a>
        <a href="#/ayuda" aria-current={pantalla === "ayuda" ? "page" : undefined}><span aria-hidden="true">❔</span>Ayuda</a>
      </nav>
    </>
  );
}

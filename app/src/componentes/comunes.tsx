import { useMemo, useRef, useState } from "preact/hooks";
import { buscar, type Entrada } from "../buscar";
import { fechaCorta } from "../fechas";
import { alternarFavorito, useFavoritos } from "../favoritos";
import { colones, direccion, porcentaje } from "../formato";
import type { Frescura } from "../frescura";
import type { ProductoHoy } from "../tipos";

export function Fuente() {
  return <p class="fuente">Fuente: PIMA – SIMM. Precios mayoristas de referencia en el CENADA, productos de primera calidad.</p>;
}

export function AvisoEjemplo() {
  return <p class="aviso aviso-ejemplo" role="alert"><strong>DATOS DE EJEMPLO.</strong> Estos precios no son reales.</p>;
}

export function EstadoDatos({ f }: { f: Frescura }) {
  return (
    <section class="estado" aria-label="Estado de los datos">
      <p>{f.ultimaActualizacion}</p>
      <p><strong>{f.boletin}</strong> {f.insigniaDato && <span class="insignia">{f.insigniaDato}</span>}</p>
      {f.desactualizado && <p class="aviso" role="alert"><span aria-hidden="true">⚠ </span>{f.desactualizado}</p>}
      {!f.desactualizado && f.ultimoIntentoFallo && <p class="nota">{f.ultimoIntentoFallo}</p>}
    </section>
  );
}

const FLECHA = { sube: "▲", baja: "▼", igual: "●" } as const;
const PALABRA = { sube: "Sube", baja: "Baja", igual: "Igual" } as const;

/** Flecha + texto + color: nunca solo color. */
export function Variacion({ pct, contra, compacta = false }: { pct: number | null | undefined; contra: string; compacta?: boolean }) {
  const dir = direccion(pct);
  if (!dir || pct === null || pct === undefined) return compacta ? null : <span class="variacion sin">Sin dato {contra}</span>;
  const texto = dir === "igual" ? `${PALABRA[dir]}` : `${PALABRA[dir]} ${porcentaje(pct)}`;
  return (
    <span class={`variacion ${dir}`}>
      <span aria-hidden="true">{FLECHA[dir]} </span>{texto}{compacta ? "" : ` ${contra}`}
    </span>
  );
}

export function Estrella({ id, nombre }: { id: string; nombre: string }) {
  const favs = useFavoritos();
  const activo = favs.includes(id);
  return (
    <button type="button" class={`estrella ${activo ? "activa" : ""}`} aria-pressed={activo}
      aria-label={activo ? `Quitar ${nombre} de favoritos` : `Agregar ${nombre} a favoritos`}
      onClick={(e) => { e.preventDefault(); e.stopPropagation(); alternarFavorito(id); }}>
      <span aria-hidden="true">{activo ? "★" : "☆"}</span>
    </button>
  );
}

export function TarjetaProducto({ p }: { p: ProductoHoy }) {
  return (
    <li class="tarjeta">
      <a href={`#/producto/${p.id}`}>
        <span class="tarjeta-nombre">{p.nombre}</span>
        <span class="tarjeta-precio">{colones(p.promedio)} <small>por {p.unidad.toLowerCase()}</small></span>
        <Variacion pct={p.vs_anterior?.variacion_pct} contra={p.vs_anterior ? `vs ${fechaCorta(p.vs_anterior.fecha)}` : ""} compacta />
      </a>
      <Estrella id={p.id} nombre={p.nombre} />
    </li>
  );
}

/** Buscador con autocompletado accesible (patrón combobox de WAI-ARIA). */
export function Buscador<T extends Entrada>({ entradas, alElegir, etiqueta = "Buscar un producto" }: {
  entradas: T[]; alElegir: (e: T) => void; etiqueta?: string;
}) {
  const [texto, setTexto] = useState("");
  const [abierto, setAbierto] = useState(false);
  const [activo, setActivo] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const resultados = useMemo(() => buscar(texto, entradas, 8), [texto, entradas]);
  const elegir = (e: T) => { setTexto(""); setAbierto(false); alElegir(e); };
  const tecla = (e: KeyboardEvent) => {
    if (e.key === "ArrowDown") { setAbierto(true); setActivo((a) => Math.min(a + 1, resultados.length - 1)); e.preventDefault(); }
    else if (e.key === "ArrowUp") { setActivo((a) => Math.max(a - 1, 0)); e.preventDefault(); }
    else if (e.key === "Enter" && resultados[activo]) { elegir(resultados[activo].entrada); e.preventDefault(); }
    else if (e.key === "Escape") setAbierto(false);
  };
  return (
    <div class="buscador" role="search">
      <label for="buscar" class="visually-hidden">{etiqueta}</label>
      <span class="lupa" aria-hidden="true">🔍</span>
      <input id="buscar" ref={inputRef} type="search" autoComplete="off" placeholder="Buscar: tomate, papa, batata…"
        role="combobox" aria-expanded={abierto && resultados.length > 0} aria-controls="sugerencias" aria-autocomplete="list"
        aria-activedescendant={abierto && resultados[activo] ? `sug-${activo}` : undefined}
        value={texto} onInput={(e) => { setTexto((e.target as HTMLInputElement).value); setAbierto(true); setActivo(0); }}
        onKeyDown={tecla} onFocus={() => setAbierto(true)} onBlur={() => setTimeout(() => setAbierto(false), 150)} />
      {abierto && texto && (
        <ul id="sugerencias" role="listbox" class="sugerencias">
          {resultados.length === 0 && <li class="sin-resultados" role="option" aria-selected={false}>No se encontró "{texto}"</li>}
          {resultados.map((r, i) => (
            <li key={r.entrada.id} id={`sug-${i}`} role="option" aria-selected={i === activo}
              class={i === activo ? "activa" : ""} onMouseDown={(e) => { e.preventDefault(); elegir(r.entrada); }}>
              {r.entrada.nombre}
              {r.coincidencia !== r.entrada.nombre && r.coincidencia !== r.entrada.cultivo && (
                <small> ({r.coincidencia})</small>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

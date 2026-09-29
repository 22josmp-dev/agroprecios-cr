import { useEffect, useMemo, useState } from "preact/hooks";
import { Fuente } from "../componentes/comunes";
import { GraficoLineas, MapaCalor } from "../componentes/graficos";
import { cargarCiclos, cargarSeasonal } from "../datos";
import { diaDelAnio, MESES_CORTOS, textoDiaDelAnio } from "../fechas";
import { porcentaje } from "../formato";
import { calcularGuia, DIAS, type Recomendacion } from "../guia";
import { normalizar } from "../texto";
import type { Ciclos, IndiceProducto, Seasonal } from "../tipos";

type Altitud = "baja" | "media" | "alta";

export function Advertencias() {
  return (
    <aside class="advertencias" aria-labelledby="t-adv">
      <h2 id="t-adv"><span aria-hidden="true">⚠ </span>Antes de decidir</h2>
      <ul>
        <li>Es una <strong>guía basada en patrones de precios de años anteriores</strong>, no una garantía.</li>
        <li>No considera el clima, las plagas, el riego ni la semilla.</li>
        <li>El precio que recibe en finca es distinto al precio mayorista de referencia del CENADA.</li>
        <li>Consulte a un extensionista del MAG o del INTA antes de sembrar.</li>
      </ul>
    </aside>
  );
}

const signo = (pct: number) => `${pct >= 0 ? "+" : "−"}${porcentaje(Math.abs(pct))}`;

export function Guia({ inicial }: { inicial?: string }) {
  const [seasonal, setSeasonal] = useState<Seasonal | null>(null);
  const [ciclos, setCiclos] = useState<Ciclos | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    Promise.all([cargarSeasonal(), cargarCiclos()]).then(([s, c]) => { setSeasonal(s); setCiclos(c); }).catch(() => setError(true));
  }, []);
  if (error) return <p class="aviso" role="alert">No se pudieron cargar los datos de la guía.</p>;
  if (!seasonal || !ciclos) return <p class="cargando">Cargando…</p>;
  return <GuiaCargada seasonal={seasonal} ciclos={ciclos} inicial={inicial} />;
}

function GuiaCargada({ seasonal, ciclos, inicial }: { seasonal: Seasonal; ciclos: Ciclos; inicial?: string }) {
  const productos = useMemo(() => [...seasonal.productos].sort((a, b) =>
    normalizar(a.cultivo).localeCompare(normalizar(b.cultivo)) || normalizar(a.nombre).localeCompare(normalizar(b.nombre))), [seasonal]);
  const [id, setId] = useState(inicial && productos.some((p) => p.id === inicial) ? inicial : "tomate-primera");
  const [altitud, setAltitud] = useState<Altitud>("media");
  const [cicloTxt, setCicloTxt] = useState("");
  const [ventanaTxt, setVentanaTxt] = useState("");
  const [estimado, setEstimado] = useState(true);
  const [elegida, setElegida] = useState(0);
  const [cicloB, setCicloB] = useState("");

  // La dirección (#/guia/<id>) manda: enlaces desde el detalle o el botón Atrás
  useEffect(() => {
    if (inicial && inicial !== id && productos.some((p) => p.id === inicial)) setId(inicial);
  }, [inicial]);

  const producto = productos.find((p) => p.id === id) || productos[0];
  const ciclo = ciclos.cultivos.find((c) => c.cultivo_id === producto.cultivo_id);
  const cicloEstimado = ciclo?.ciclo_dias ? (ciclo.ciclo_dias[altitud] ?? ciclo.ciclo_dias.media ?? ciclo.ciclo_dias.baja ?? ciclo.ciclo_dias.alta) : null;
  const ventanaEstimada = ciclo?.ventana_cosecha_dias ?? 20;

  // Al cambiar de cultivo o altitud, si el usuario usa el valor estimado, se actualiza
  useEffect(() => {
    if (estimado) setCicloTxt(cicloEstimado ? String(cicloEstimado) : "");
    setVentanaTxt(String(ventanaEstimada));
    setElegida(0);
  }, [id, altitud]);

  const cicloN = parseInt(cicloTxt, 10);
  const ventanaN = Math.max(0, parseInt(ventanaTxt, 10) || 0);
  const resultado = useMemo(() => (cicloN > 0 ? calcularGuia(producto, cicloN, ventanaN) : null), [producto, cicloN, ventanaN]);
  const cicloBN = parseInt(cicloB, 10);
  const resultadoB = useMemo(() => (cicloBN > 0 ? calcularGuia(producto, cicloBN, ventanaN) : null), [producto, cicloBN, ventanaN]);

  const porCultivo = new Map<string, IndiceProducto[]>();
  for (const p of productos) porCultivo.set(p.cultivo, [...(porCultivo.get(p.cultivo) || []), p]);

  return (
    <article>
      <h1>Guía de siembra</h1>
      <p>Muestra en qué fechas sembrar para que la cosecha caiga en los meses en que, en años anteriores, el precio mayorista fue mejor.</p>
      <Advertencias />

      <section class="formulario-guia" aria-labelledby="t-datos">
        <h2 id="t-datos">Su cultivo</h2>
        <label for="g-producto">Cultivo</label>
        <select id="g-producto" value={id} onChange={(e) => { setId((e.target as HTMLSelectElement).value); location.hash = `#/guia/${(e.target as HTMLSelectElement).value}`; }}>
          {[...porCultivo.entries()].map(([cultivo, lista]) => (
            <optgroup key={cultivo} label={cultivo}>
              {lista.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
            </optgroup>
          ))}
        </select>

        {ciclo?.tipo === "perenne" ? (
          <p class="aviso">{producto.nombre} es un cultivo perenne: la guía de fechas de siembra no aplica. Vea en el detalle del producto en qué meses suele estar mejor el precio.</p>
        ) : (
          <>
            <fieldset>
              <legend>Altitud de su finca</legend>
              {(["baja", "media", "alta"] as Altitud[]).map((a) => (
                <label key={a} class="opcion">
                  <input type="radio" name="altitud" value={a} checked={altitud === a} onChange={() => setAltitud(a)} />
                  {a[0].toUpperCase() + a.slice(1)} <small>({ciclos.altitudes[a]})</small>
                </label>
              ))}
            </fieldset>

            <label for="g-ciclo">Días desde la {ciclo?.referencia === "trasplante" ? "siembra o el trasplante" : "siembra"} hasta empezar a cosechar</label>
            <div class="fila-campo">
              <input id="g-ciclo" type="number" inputMode="numeric" min={1} max={900} value={cicloTxt}
                aria-describedby="g-ciclo-nota" onInput={(e) => { setCicloTxt((e.target as HTMLInputElement).value); setEstimado(false); }} />
              <button type="button" class="boton-secundario" disabled={!cicloEstimado}
                onClick={() => { setCicloTxt(String(cicloEstimado)); setEstimado(true); }}>No sé</button>
            </div>
            <p id="g-ciclo-nota" class="nota">
              {estimado && cicloEstimado
                ? <>Usando un <strong>valor estimado</strong> de {cicloEstimado} días para altitud {altitud} (no verificado por un técnico). Puede cambiarlo.</>
                : !cicloEstimado ? "No hay un valor estimado para esta altitud: escriba los días de su cultivo." : "Usando el ciclo que usted indicó."}
            </p>

            <label for="g-ventana">Días que dura la cosecha</label>
            <input id="g-ventana" type="number" inputMode="numeric" min={0} max={365} value={ventanaTxt}
              onInput={(e) => setVentanaTxt((e.target as HTMLInputElement).value)} />
          </>
        )}
      </section>

      {ciclo?.tipo !== "perenne" && resultado && !resultado.valido && <p class="aviso">{resultado.motivo}</p>}
      {ciclo?.tipo !== "perenne" && resultado?.valido && (
        <>
          <section aria-labelledby="t-mejores">
            <h2 id="t-mejores">Las 3 mejores fechas para sembrar</h2>
            {producto.years_of_data < 3 && <p class="aviso">Hay pocos años de datos: la confianza es baja.</p>}
            <ol class="recomendaciones">
              {resultado.mejores.map((r, i) => (
                <TarjetaRecomendacion key={r.siembra} r={r} n={i + 1} activa={elegida === i} alElegir={() => setElegida(i)} />
              ))}
            </ol>
          </section>

          <section aria-labelledby="t-linea">
            <h2 id="t-linea">Precio esperado a lo largo del año</h2>
            <p class="nota">La franja sombreada es la cosecha de la opción {elegida + 1}.</p>
            <LineaIndice resultado={resultado} r={resultado.mejores[elegida]} />
          </section>

          <section aria-labelledby="t-mapa">
            <h2 id="t-mapa">Mapa del año: ¿qué tal es cada fecha de siembra?</h2>
            <p class="nota">Cada cuadro es un día de siembra. El color indica el precio esperado en su cosecha. Toque un cuadro para ver el detalle.</p>
            <MapaCalor titulo="Precio esperado de la cosecha según el día de siembra"
              valores={resultado.candidatos.map((c) => (c ? c.indiceEsperado / resultado.promedioAnual - 1 : null))}
              marcas={resultado.mejores.map((m) => m.siembra)}
              etiquetaCelda={(d, v) => v === null
                ? `Siembra ${textoDiaDelAnio(d)}: la cosecha caería en meses sin mercado`
                : `Siembra ${textoDiaDelAnio(d)}: precio esperado ${signo(v * 100)} frente al promedio`} />
            <TablaMensual resultado={resultado} />
          </section>

          <section aria-labelledby="t-comparar">
            <h2 id="t-comparar">Comparar dos ciclos</h2>
            <p class="nota">Por ejemplo, una variedad más rápida o más lenta.</p>
            <label for="g-ciclo-b">Otro ciclo (días)</label>
            <input id="g-ciclo-b" type="number" inputMode="numeric" min={1} max={900} value={cicloB}
              placeholder={String(cicloN + 20)} onInput={(e) => setCicloB((e.target as HTMLInputElement).value)} />
            <div class="comparador">
              <Escenario titulo={`Ciclo de ${cicloN} días`} r={resultado.mejores[0]} />
              {resultadoB?.valido ? <Escenario titulo={`Ciclo de ${cicloBN} días`} r={resultadoB.mejores[0]} />
                : <div class="escenario vacio"><p>Escriba otro ciclo para comparar.</p></div>}
            </div>
          </section>
        </>
      )}
      <p class="nota">Índice de precios: {producto.nombre}, {producto.years_of_data} años de datos del SIMM. Ciclos: valores estimados, sin verificar por un técnico.</p>
      <Fuente />
    </article>
  );
}

const CONFIANZA = {
  alta: { icono: "●●●", texto: "Confianza alta" },
  media: { icono: "●●○", texto: "Confianza media" },
  baja: { icono: "●○○", texto: "Confianza baja" },
};

function TarjetaRecomendacion({ r, n, activa, alElegir }: { r: Recomendacion; n: number; activa: boolean; alElegir: () => void }) {
  return (
    <li class={`recomendacion ${activa ? "activa" : ""}`}>
      <button type="button" onClick={alElegir} aria-pressed={activa}>
        <span class="numero" aria-hidden="true">{n}</span>
        <span class="rec-cuerpo">
          <span class="rec-fecha">Sembrar el {textoDiaDelAnio(r.siembra)}</span>
          <span>Cosecha: {textoDiaDelAnio(r.cosechaInicio)} al {textoDiaDelAnio(r.cosechaFin)}</span>
          <span>Precio esperado: <strong>{signo(r.difPromedioPct)}</strong> frente al promedio del año · {signo(r.difPeorPct)} frente a la peor fecha</span>
          <span class={`insignia confianza-${r.confianza}`}><span aria-hidden="true">{CONFIANZA[r.confianza].icono} </span>{CONFIANZA[r.confianza].texto}</span>
          <span class="rec-explicacion">{r.explicacion}</span>
        </span>
      </button>
    </li>
  );
}

function LineaIndice({ resultado, r }: { resultado: ReturnType<typeof calcularGuia>; r: Recomendacion }) {
  const puntos = resultado.indiceDiario.map((v, d) => ({ x: d, y: v === null ? null : (v / resultado.promedioAnual - 1) * 100 }));
  const sombreado = r.cosechaInicio <= r.cosechaFin
    ? [{ desde: r.cosechaInicio, hasta: r.cosechaFin }]
    : [{ desde: r.cosechaInicio, hasta: DIAS - 1 }, { desde: 0, hasta: r.cosechaFin }];
  const inicios = Array.from({ length: 12 }, (_, m) => diaDelAnio(m + 1, 1));
  return (
    <GraficoLineas titulo="Precio esperado según la época del año" descripcion="Porcentaje sobre o bajo el promedio anual, día por día."
      series={[{ id: "i", nombre: "Precio frente al promedio del año", color: "var(--serie-1)", puntos }]}
      etiquetaX={(d) => (inicios.includes(d) ? MESES_CORTOS[inicios.indexOf(d)] : textoDiaDelAnio(d))}
      ticksX={inicios.filter((_, m) => m % 2 === 0)} formatoY={(v) => (Math.abs(v) < 0.5 ? "0 %" : signo(v))}
      sombreado={sombreado} lineaRef={{ y: 0, etiqueta: "promedio" }} />
  );
}

function TablaMensual({ resultado }: { resultado: ReturnType<typeof calcularGuia> }) {
  const filas = MESES_CORTOS.map((mes, m) => {
    const inicio = diaDelAnio(m + 1, 1);
    const fin = m === 11 ? DIAS : diaDelAnio(m + 2, 1);
    const cs = resultado.candidatos.slice(inicio, fin).filter((c) => c !== null);
    if (!cs.length) return [mes, "—", "sin mercado en la cosecha"];
    const mejor = cs.reduce((a, b) => (b!.puntaje > a!.puntaje ? b : a))!;
    return [mes, textoDiaDelAnio(mejor.siembra), signo((mejor.indiceEsperado / resultado.promedioAnual - 1) * 100)];
  });
  return (
    <details class="tabla-datos">
      <summary>Ver el mejor día de cada mes en una tabla</summary>
      <div class="tabla-scroll">
        <table>
          <thead><tr><th scope="col">Mes de siembra</th><th scope="col">Mejor día</th><th scope="col">Precio esperado</th></tr></thead>
          <tbody>{filas.map((f) => <tr key={f[0]}><th scope="row">{f[0]}</th><td>{f[1]}</td><td>{f[2]}</td></tr>)}</tbody>
        </table>
      </div>
    </details>
  );
}

function Escenario({ titulo, r }: { titulo: string; r: Recomendacion }) {
  return (
    <div class="escenario">
      <h3>{titulo}</h3>
      <p>Mejor siembra: <strong>{textoDiaDelAnio(r.siembra)}</strong></p>
      <p>Cosecha: {textoDiaDelAnio(r.cosechaInicio)} al {textoDiaDelAnio(r.cosechaFin)}</p>
      <p>Precio esperado: <strong>{signo(r.difPromedioPct)}</strong></p>
      <p>{CONFIANZA[r.confianza].texto}</p>
    </div>
  );
}

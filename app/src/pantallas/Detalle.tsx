import { useEffect, useMemo, useState } from "preact/hooks";
import type { DatosBase } from "../app";
import { Estrella, Fuente, Variacion } from "../componentes/comunes";
import { GraficoIndice, GraficoLineas, type Serie } from "../componentes/graficos";
import { cargarHistorico, cargarSeasonal, serieDiaria } from "../datos";
import { diasEntre, fechaCorta, fechaLarga, MESES, MESES_CORTOS } from "../fechas";
import { colones } from "../formato";
import { normalizar } from "../texto";
import type { Historico, IndiceProducto } from "../tipos";

/** Kilos por unidad solo si están escritos: "Kilo" -> 1, "Caja plástica (18 kg)" -> 18. */
export function kgDeUnidad(unidad: string | null | undefined): number | null {
  if (!unidad) return null;
  if (["kilo", "kilos", "kg"].includes(normalizar(unidad))) return 1;
  const m = unidad.match(/\((\d+(?:[.,]\d+)?)\s*(kg|g)\)/i);
  if (!m) return null;
  const v = parseFloat(m[1].replace(",", "."));
  return m[2].toLowerCase() === "g" ? v / 1000 : v;
}

type Rango = "7d" | "30d" | "12m" | "anios";
const RANGOS: { id: Rango; nombre: string }[] = [
  { id: "7d", nombre: "7 días" }, { id: "30d", nombre: "30 días" }, { id: "12m", nombre: "12 meses" }, { id: "anios", nombre: "Años anteriores" },
];

export function Detalle({ datos, id }: { datos: DatosBase; id: string }) {
  const p = datos.latest.productos.find((x) => x.id === id);
  const cat = datos.catalogo.productos.find((x) => x.id === id);
  const [porKilo, setPorKilo] = useState(false);
  const [rango, setRango] = useState<Rango>("30d");
  const [diaria, setDiaria] = useState<{ fecha: string; promedio: number }[]>([]);
  // undefined = cargando · null = no existe · "error" = no se pudo cargar (p. ej. sin conexión)
  const [indice, setIndice] = useState<IndiceProducto | null | undefined | "error">(undefined);
  const [historico, setHistorico] = useState<Historico | null>(null);

  useEffect(() => {
    if (!p) return;
    // Meses con precios diarios: de meta.json o, si falta, los 13 meses hasta el boletín
    const [a, m] = datos.latest.fecha_boletin.split("-").map(Number);
    const respaldo = Array.from({ length: 13 }, (_, i) => {
      const k = a * 12 + m - 1 - (12 - i);
      return `${Math.floor(k / 12)}-${String((k % 12) + 1).padStart(2, "0")}`;
    });
    serieDiaria(datos.meta.meses_precios?.slice(-13) ?? respaldo, p.id, p.unidad).then(setDiaria).catch(() => setDiaria([]));
    cargarSeasonal().then((s) => {
      const exacto = s.productos.find((x) => x.productos_boletin.includes(p.id));
      const delCultivo = s.productos.find((x) => x.cultivo_id === p.cultivo_id);
      const elegido = exacto || delCultivo || null;
      setIndice(elegido);
      if (elegido) cargarHistorico(elegido.id).then(setHistorico).catch(() => setHistorico(null));
    }).catch(() => setIndice("error"));
  }, [id]);

  if (!p) {
    return (
      <section>
        <h1>{cat?.nombre ?? "Producto"}</h1>
        <p class="aviso">Este producto no aparece en el boletín más reciente ({fechaLarga(datos.latest.fecha_boletin)}).</p>
        <p><a href="#/">Volver a los precios</a></p>
        <Fuente />
      </section>
    );
  }

  const kg = p.kg;
  const factor = porKilo && kg ? 1 / kg : 1;
  const unidadTexto = porKilo && kg ? "kilo" : p.unidad.toLowerCase();
  const hoyBoletin = datos.latest.fecha_boletin;
  const exacto = !!indice && indice !== "error" && indice.productos_boletin.includes(p.id);
  const mismaUnidad = !!historico && normalizar(historico.unidad_precio || "") === normalizar(p.unidad);
  const kgHistorico = kgDeUnidad(historico?.unidad_precio);

  return (
    <article>
      <p class="migas"><a href="#/">Precios</a> › {p.cultivo}</p>
      <div class="titulo-producto">
        <h1>{p.nombre}</h1>
        <Estrella id={p.id} nombre={p.nombre} />
      </div>

      {kg && kg !== 1 && (
        <div class="selector-unidad" role="radiogroup" aria-label="Ver precio">
          <button type="button" role="radio" aria-checked={!porKilo} onClick={() => setPorKilo(false)}>Por {p.unidad.toLowerCase()}</button>
          <button type="button" role="radio" aria-checked={porKilo} onClick={() => setPorKilo(true)}>Por kilo</button>
        </div>
      )}
      {!kg && <p class="nota">Unidad de venta: {p.unidad}. El boletín no indica su peso, así que no se calcula el precio por kilo.</p>}

      <section class="precios" aria-label={`Precios del ${fechaLarga(hoyBoletin)}`}>
        <div class="precio-principal">
          <span class="etiqueta">Precio promedio por {unidadTexto}</span>
          <span class="valor">{colones(p.promedio * factor)}</span>
        </div>
        <dl class="precios-secundarios">
          <div><dt>Moda <small>(el más repetido)</small></dt><dd>{colones(p.moda * factor)}</dd></div>
          <div><dt>Mínimo</dt><dd>{colones(p.minimo * factor)}</dd></div>
          <div><dt>Máximo</dt><dd>{colones(p.maximo * factor)}</dd></div>
        </dl>
        <p class="nota">Boletín del {fechaLarga(hoyBoletin)} · {p.unidad}{kg && !/\d\s*k?g/i.test(p.unidad) && kg !== 1 ? ` (${kg} kg)` : ""}</p>
      </section>

      <section aria-labelledby="t-cambios">
        <h2 id="t-cambios">¿Cómo cambió el precio?</h2>
        <ul class="cambios">
          <li><span>Boletín anterior{p.vs_anterior ? ` (${fechaCorta(p.vs_anterior.fecha)})` : ""}</span>
            <Variacion pct={p.vs_anterior?.variacion_pct} contra="" /></li>
          <li><span>Semana pasada{p.vs_semana ? ` (${fechaCorta(p.vs_semana.fecha)})` : ""}</span>
            <Variacion pct={p.vs_semana?.variacion_pct} contra="" /></li>
          <li><span>Promedio de 30 días{p.vs_30d ? ` (${p.vs_30d.dias} boletines)` : ""}</span>
            <Variacion pct={p.vs_30d?.variacion_pct} contra="" /></li>
        </ul>
      </section>

      <section aria-labelledby="t-tendencia">
        <h2 id="t-tendencia">Tendencia</h2>
        <div class="filtros" role="group" aria-label="Período">
          {RANGOS.map((r) => <button key={r.id} type="button" aria-pressed={rango === r.id} onClick={() => setRango(r.id)}>{r.nombre}</button>)}
        </div>
        {(rango === "7d" || rango === "30d") && (
          <TendenciaDiaria puntos={diaria} dias={rango === "7d" ? 7 : 30} hasta={hoyBoletin} factor={factor} unidad={unidadTexto} />
        )}
        {rango === "12m" && (
          <DoceMeses historico={mismaUnidad ? historico : null} diaria={diaria} hasta={hoyBoletin} factor={factor} unidad={unidadTexto} />
        )}
        {rango === "anios" && (
          historico
            ? <AniosAnteriores historico={historico} factor={porKilo && kgHistorico ? 1 / kgHistorico : 1}
                unidad={porKilo && kgHistorico ? "kilo" : (historico.unidad_precio || "").toLowerCase()}
                nota={exacto ? null : `Datos de "${historico.nombre}", el producto del mismo cultivo con historial en el SIMM.`} />
            : <p class="sin-datos">No hay historial mensual del SIMM para este producto.</p>
        )}
      </section>

      <section aria-labelledby="t-indice">
        <h2 id="t-indice">¿En qué meses suele estar mejor el precio?</h2>
        {indice === undefined && <p class="cargando">Cargando…</p>}
        {indice === null && <p class="sin-datos">El SIMM no publica índice estacional para este producto.</p>}
        {indice === "error" && <p class="sin-datos">No se pudo cargar esta información. Revise su conexión e intente de nuevo.</p>}
        {indice && indice !== "error" && <BloqueIndice indice={indice} exacto={exacto} />}
      </section>

      {historico && Object.keys(historico.oferta_tm).length > 0 && (
        <section aria-labelledby="t-oferta">
          <h2 id="t-oferta">Oferta en el CENADA</h2>
          <Oferta historico={historico} />
          <p class="nota">Procedencia: el boletín del PIMA no la publica.</p>
        </section>
      )}
      <Fuente />
    </article>
  );
}

function TendenciaDiaria({ puntos, dias, hasta, factor, unidad }: {
  puntos: { fecha: string; promedio: number }[]; dias: number; hasta: string; factor: number; unidad: string;
}) {
  const desde = -(dias - 1);
  const visibles = puntos.filter((q) => { const d = diasEntre(hasta, q.fecha); return d >= desde && d <= 0; });
  if (visibles.length < 2) return <p class="sin-datos">Aún no hay suficientes boletines en este período.</p>;
  const x = (f: string) => diasEntre(hasta, f);
  const serie: Serie = { id: "p", nombre: `Precio promedio por ${unidad}`, color: "var(--serie-1)",
    puntos: visibles.map((q) => ({ x: x(q.fecha), y: q.promedio * factor })) };
  const etiqueta = (v: number) => fechaCorta(new Date(Date.parse(hasta) + v * 86_400_000).toISOString().slice(0, 10));
  const ticks = dias === 7 ? [-6, -3, 0] : [-28, -21, -14, -7, 0];
  return <GraficoLineas titulo={`Precio promedio de los últimos ${dias} días`} descripcion={`Precio promedio por ${unidad} en cada boletín.`}
    series={[serie]} etiquetaX={etiqueta} ticksX={ticks.filter((t) => t >= desde)} formatoY={colones} />;
}

function DoceMeses({ historico, diaria, hasta, factor, unidad }: {
  historico: Historico | null; diaria: { fecha: string; promedio: number }[]; hasta: string; factor: number; unidad: string;
}) {
  const [a, m] = hasta.split("-").map(Number);
  const fin = a * 12 + (m - 1);
  const porMes = new Map<number, number[]>();
  for (const q of diaria) {
    const [qa, qm] = q.fecha.split("-").map(Number);
    const k = qa * 12 + qm - 1;
    porMes.set(k, [...(porMes.get(k) || []), q.promedio]);
  }
  const puntos = Array.from({ length: 12 }, (_, i) => {
    const k = fin - 11 + i;
    const deDia = porMes.get(k);
    const delSimm = historico?.precio[String(Math.floor(k / 12))]?.[k % 12] ?? null;
    const y = deDia ? deDia.reduce((s, v) => s + v, 0) / deDia.length : delSimm;
    return { x: k, y: y === null ? null : y * factor };
  });
  const hayDatos = puntos.filter((q) => q.y !== null).length;
  if (hayDatos < 2) {
    return <p class="sin-datos">Todavía no hay 12 meses de datos para este producto. El historial mensual del SIMM llega hasta
      diciembre de 2025 y el boletín diario se recopila desde setiembre de 2026; los meses intermedios se irán completando.</p>;
  }
  return (
    <>
      <GraficoLineas titulo="Precio mensual de los últimos 12 meses" descripcion={`Promedio mensual por ${unidad}.`}
        series={[{ id: "m", nombre: `Promedio mensual por ${unidad}`, color: "var(--serie-1)", puntos }]}
        etiquetaX={(k) => `${MESES_CORTOS[k % 12]} ${String(Math.floor(k / 12)).slice(2)}`}
        ticksX={puntos.filter((_, i) => i % 3 === 2).map((q) => q.x)} formatoY={colones} />
      <p class="nota">Meses sin dato quedan en blanco. Hasta 2025: promedio mensual del SIMM; desde setiembre de 2026: promedio de los boletines diarios.</p>
    </>
  );
}

function AniosAnteriores({ historico, factor, unidad, nota }: { historico: Historico; factor: number; unidad: string; nota: string | null }) {
  const anios = Object.keys(historico.precio).sort();
  const ultimo = anios[anios.length - 1];
  const previos = anios.slice(0, -1);
  const promedioPrevios = Array.from({ length: 12 }, (_, m) => {
    const v = previos.map((a) => historico.precio[a][m]).filter((x): x is number => x !== null);
    return v.length ? v.reduce((s, x) => s + x, 0) / v.length : null;
  });
  const puntos = (vals: (number | null)[]) => vals.map((y, m) => ({ x: m + 1, y: y === null ? null : y * factor }));
  const series: Serie[] = [
    { id: ultimo, nombre: `${ultimo}`, color: "var(--serie-1)", puntos: puntos(historico.precio[ultimo]) },
    { id: "prom", nombre: `Promedio ${previos[0]}–${previos[previos.length - 1]}`, color: "var(--serie-2)", puntos: puntos(promedioPrevios) },
    ...previos.map((a) => ({ id: a, nombre: a, color: "var(--contexto)", puntos: puntos(historico.precio[a]), enfasis: false })),
  ];
  return (
    <>
      {nota && <p class="nota">{nota}</p>}
      <GraficoLineas titulo="Comparación con años anteriores" descripcion={`Precio mensual por ${unidad}, un trazo por año.`}
        series={series} etiquetaX={(m) => MESES_CORTOS[m - 1]} ticksX={[1, 3, 5, 7, 9, 11]} formatoY={colones}
        leyenda={[{ nombre: ultimo, color: "var(--serie-1)" }, { nombre: series[1].nombre, color: "var(--serie-2)" },
          { nombre: "Cada año anterior", color: "var(--contexto)" }]} />
      <p class="nota">Precio mensual publicado por el SIMM ({historico.unidad_precio}).</p>
    </>
  );
}

function BloqueIndice({ indice, exacto }: { indice: IndiceProducto; exacto: boolean }) {
  const valores = indice.indice || [];
  const conDato = valores.map((v, i) => ({ v, i })).filter((x): x is { v: number; i: number } => x.v !== null);
  const alto = conDato.reduce((a, b) => (b.v > a.v ? b : a), conDato[0]);
  const bajo = conDato.reduce((a, b) => (b.v < a.v ? b : a), conDato[0]);
  const pct = (v: number) => Math.round(Math.abs(v - 1) * 100);
  const confianza = { alta: "Confianza alta", media: "Confianza media", baja: "Confianza baja" }[indice.confianza];
  return (
    <>
      {!exacto && <p class="nota">Índice de "{indice.nombre}", del mismo cultivo.</p>}
      {alto && bajo && (
        <p>Históricamente el precio suele estar más alto en <strong>{MESES[alto.i]}</strong> ({pct(alto.v)} % sobre el promedio del año)
          y más bajo en <strong>{MESES[bajo.i]}</strong> ({pct(bajo.v)} % bajo el promedio).</p>
      )}
      <p><span class={`insignia confianza-${indice.confianza}`}>{confianza}</span> {indice.years_of_data} años de datos.
        {indice.confianza === "baja" && " Los precios de este producto varían mucho de un año a otro: tómelo como una referencia general."}</p>
      <GraficoIndice titulo={`Índice estacional de precio de ${indice.nombre}`} meses={MESES_CORTOS} indice={valores} oficial={indice.indice_oficial_simm} />
      {indice.meses_sin_dato.length > 0 && <p class="nota">"s/d": meses en que casi no hay venta de este producto en el CENADA.</p>}
      <p><a class="boton-secundario" href={`#/guia/${indice.id}`}>Ver la guía de siembra de {indice.nombre.toLowerCase()} →</a></p>
    </>
  );
}

function Oferta({ historico }: { historico: Historico }) {
  const anios = Object.keys(historico.oferta_tm);
  const promedio = useMemo(() => Array.from({ length: 12 }, (_, m) => {
    const v = anios.map((a) => historico.oferta_tm[a][m]).filter((x): x is number => x !== null);
    return v.length ? v.reduce((s, x) => s + x, 0) / v.length : null;
  }), [historico]);
  const t = (v: number) => `${Math.round(v).toLocaleString("es-CR")} t`;
  return (
    <GraficoLineas titulo="Oferta promedio por mes" descripcion={`Toneladas que entran al CENADA, promedio ${anios[0]}–${anios[anios.length - 1]}.`}
      series={[{ id: "o", nombre: "Toneladas por mes (promedio)", color: "var(--serie-1)", puntos: promedio.map((y, m) => ({ x: m + 1, y })) }]}
      etiquetaX={(m) => MESES_CORTOS[m - 1]} ticksX={[1, 3, 5, 7, 9, 11]} formatoY={t} yDesdeCero alto={180} />
  );
}

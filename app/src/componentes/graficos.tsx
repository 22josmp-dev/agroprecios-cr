// Gráficos SVG livianos (sin librerías) con tooltip, leyenda y tabla alternativa.
// Se dibujan al ancho real del contenedor (1 unidad = 1 px) para que el texto se lea a su tamaño.
import { useLayoutEffect, useRef, useState } from "preact/hooks";
import type { ComponentChildren, RefObject } from "preact";

const M = { izq: 62, der: 12, arr: 12, abj: 30 };

function useAncho(): [RefObject<HTMLDivElement>, number] {
  const ref = useRef<HTMLDivElement>(null);
  const [ancho, setAncho] = useState(340);
  useLayoutEffect(() => {
    if (!ref.current) return;
    setAncho(Math.round(ref.current.clientWidth) || 340);
    if (typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver((e) => setAncho(Math.round(e[0].contentRect.width) || 340));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, ancho];
}

export function ticksLindos(min: number, max: number, cantidad = 4): number[] {
  if (min === max) { min -= 1; max += 1; }
  const paso0 = (max - min) / cantidad;
  const mag = 10 ** Math.floor(Math.log10(paso0));
  const paso = [1, 2, 2.5, 5, 10].map((f) => f * mag).find((p) => p >= paso0) ?? paso0;
  const ticks = [];
  for (let v = Math.floor(min / paso) * paso; v <= max + paso * 1e-9; v += paso) ticks.push(+v.toFixed(10));
  if (ticks[ticks.length - 1] < max) ticks.push(ticks[ticks.length - 1] + paso);
  return ticks;
}

export interface Serie {
  id: string;
  nombre: string;
  color: string; // variable CSS, p. ej. "var(--serie-1)"
  puntos: { x: number; y: number | null }[];
  enfasis?: boolean;
}

interface PropsLineas {
  titulo: string;
  descripcion: string;
  series: Serie[];
  etiquetaX: (x: number) => string;
  ticksX: number[];
  formatoY: (y: number) => string;
  alto?: number;
  sombreado?: { desde: number; hasta: number }[];
  lineaRef?: { y: number; etiqueta: string };
  leyenda?: { nombre: string; color: string }[];
  yDesdeCero?: boolean;
}

function Leyenda({ items }: { items: { nombre: string; color: string }[] }) {
  return (
    <ul class="leyenda" aria-label="Leyenda">
      {items.map((i) => (
        <li key={i.nombre}><span class="muestra" style={{ background: i.color }} aria-hidden="true" />{i.nombre}</li>
      ))}
    </ul>
  );
}

function TablaDatos({ encabezados, filas }: { encabezados: string[]; filas: (string | number)[][] }) {
  return (
    <details class="tabla-datos">
      <summary>Ver datos en tabla</summary>
      <div class="tabla-scroll">
        <table>
          <thead><tr>{encabezados.map((e, i) => <th key={i} scope="col">{e}</th>)}</tr></thead>
          <tbody>{filas.map((f, i) => <tr key={i}>{f.map((c, j) => j === 0 ? <th key={j} scope="row">{c}</th> : <td key={j}>{c}</td>)}</tr>)}</tbody>
        </table>
      </div>
    </details>
  );
}

function Tooltip({ x, ancho, children }: { x: number; ancho: number; children: ComponentChildren }) {
  const izquierda = Math.min(Math.max((x / ancho) * 100, 22), 78);
  return <div class="tooltip" role="status" style={{ left: `${izquierda}%` }}>{children}</div>;
}

export function GraficoLineas(p: PropsLineas) {
  const alto = p.alto ?? 230;
  const [contRef, ancho] = useAncho();
  const svgRef = useRef<SVGSVGElement>(null);
  const [cursor, setCursor] = useState<number | null>(null);
  const xs = [...new Set(p.series.flatMap((s) => s.puntos.filter((q) => q.y !== null).map((q) => q.x)))].sort((a, b) => a - b);
  const ys = p.series.flatMap((s) => s.puntos.map((q) => q.y)).filter((y): y is number => y !== null);
  if (!xs.length || !ys.length) return <p class="sin-datos">Aún no hay datos suficientes para este gráfico.</p>;
  if (p.lineaRef) ys.push(p.lineaRef.y);
  const ticksY = ticksLindos(p.yDesdeCero ? 0 : Math.min(...ys), Math.max(...ys));
  const [y0, y1] = [ticksY[0], ticksY[ticksY.length - 1]];
  const todosX = p.series.flatMap((s) => s.puntos.map((q) => q.x));
  const [x0, x1] = [Math.min(...todosX, ...p.ticksX), Math.max(...todosX, ...p.ticksX)];
  const sx = (x: number) => M.izq + ((x - x0) / (x1 - x0 || 1)) * (ancho - M.izq - M.der);
  const sy = (y: number) => M.arr + (1 - (y - y0) / (y1 - y0 || 1)) * (alto - M.arr - M.abj);

  const camino = (puntos: Serie["puntos"]) => {
    let d = "", abierto = false;
    for (const q of puntos) {
      if (q.y === null) { abierto = false; continue; }
      d += `${abierto ? "L" : "M"}${sx(q.x).toFixed(1)},${sy(q.y).toFixed(1)}`;
      abierto = true;
    }
    return d;
  };
  // Puntos aislados (sin vecinos) se dibujan como marcadores para que no desaparezcan
  const aislados = (puntos: Serie["puntos"]) => puntos.filter((q, i) =>
    q.y !== null && (puntos[i - 1]?.y ?? null) === null && (puntos[i + 1]?.y ?? null) === null);

  const mover = (e: PointerEvent) => {
    const r = svgRef.current!.getBoundingClientRect();
    const xv = x0 + ((e.clientX - r.left) - M.izq) / (ancho - M.izq - M.der) * (x1 - x0);
    setCursor(xs.reduce((a, b) => (Math.abs(b - xv) < Math.abs(a - xv) ? b : a)));
  };
  const teclado = (e: KeyboardEvent) => {
    const i = cursor === null ? xs.length - 1 : xs.indexOf(cursor);
    if (e.key === "ArrowLeft") { setCursor(xs[Math.max(0, i - 1)]); e.preventDefault(); }
    if (e.key === "ArrowRight") { setCursor(xs[Math.min(xs.length - 1, i + 1)]); e.preventDefault(); }
    if (e.key === "Escape") setCursor(null);
  };
  const valoresCursor = cursor === null ? [] : p.series
    .map((s) => ({ s, y: s.puntos.find((q) => q.x === cursor)?.y ?? null }))
    .filter((v) => v.y !== null);
  const leyenda = p.leyenda ?? (p.series.length >= 2 ? p.series.map((s) => ({ nombre: s.nombre, color: s.color })) : []);

  return (
    <figure class="grafico">
      {leyenda.length > 0 && <Leyenda items={leyenda} />}
      <div class="lienzo" ref={contRef}>
        <svg ref={svgRef} width={ancho} height={alto} viewBox={`0 0 ${ancho} ${alto}`} role="img" aria-label={`${p.titulo}. ${p.descripcion}`}
          tabIndex={0} onPointerMove={mover} onPointerDown={mover} onPointerLeave={() => setCursor(null)}
          onKeyDown={teclado} onBlur={() => setCursor(null)}>
          {(p.sombreado || []).map((s, i) => (
            <rect key={i} class="sombreado" x={sx(s.desde)} y={M.arr} width={Math.max(2, sx(s.hasta) - sx(s.desde))} height={alto - M.arr - M.abj} />
          ))}
          {ticksY.map((t) => (
            <g key={t}>
              <line class="rejilla" x1={M.izq} x2={ancho - M.der} y1={sy(t)} y2={sy(t)} />
              <text class="eje" x={M.izq - 6} y={sy(t) + 4} text-anchor="end">{p.formatoY(t)}</text>
            </g>
          ))}
          {p.ticksX.map((t, i) => (
            <text key={t} class="eje" x={sx(t)} y={alto - 8}
              text-anchor={i === 0 && sx(t) - M.izq < 20 ? "start" : i === p.ticksX.length - 1 && ancho - M.der - sx(t) < 20 ? "end" : "middle"}>
              {p.etiquetaX(t)}
            </text>
          ))}
          {p.lineaRef && (
            <g>
              <line class="linea-ref" x1={M.izq} x2={ancho - M.der} y1={sy(p.lineaRef.y)} y2={sy(p.lineaRef.y)} />
              <text class="eje" x={ancho - M.der} y={sy(p.lineaRef.y) - 5} text-anchor="end">{p.lineaRef.etiqueta}</text>
            </g>
          )}
          {[...p.series].sort((a, b) => Number(a.enfasis !== false) - Number(b.enfasis !== false)).map((s) => (
            <g key={s.id}>
              <path d={camino(s.puntos)} fill="none" stroke={s.color} stroke-width={s.enfasis === false ? 1.5 : 2}
                stroke-linejoin="round" stroke-linecap="round" />
              {aislados(s.puntos).map((q) => <circle key={q.x} cx={sx(q.x)} cy={sy(q.y!)} r={s.enfasis === false ? 2.5 : 4} fill={s.color} class="punto" />)}
            </g>
          ))}
          {p.series.filter((s) => s.enfasis !== false).map((s) => {
            const ult = [...s.puntos].reverse().find((q) => q.y !== null);
            return ult ? <circle key={s.id} cx={sx(ult.x)} cy={sy(ult.y!)} r={4} fill={s.color} class="punto" /> : null;
          })}
          {cursor !== null && (
            <g>
              <line class="cursor" x1={sx(cursor)} x2={sx(cursor)} y1={M.arr} y2={alto - M.abj} />
              {valoresCursor.map(({ s, y }) => <circle key={s.id} cx={sx(cursor)} cy={sy(y!)} r={5} fill={s.color} class="punto" />)}
            </g>
          )}
        </svg>
        {cursor !== null && valoresCursor.length > 0 && (
          <Tooltip x={sx(cursor)} ancho={ancho}>
            <strong>{p.etiquetaX(cursor)}</strong>
            {valoresCursor.slice(0, 4).map(({ s, y }) => (
              <span key={s.id}><span class="muestra" style={{ background: s.color }} aria-hidden="true" />{s.nombre}: {p.formatoY(y!)}</span>
            ))}
          </Tooltip>
        )}
      </div>
      <figcaption class="visually-hidden">{p.descripcion}</figcaption>
      <TablaDatos encabezados={["", ...p.series.map((s) => s.nombre)]}
        filas={xs.map((x) => [p.etiquetaX(x), ...p.series.map((s) => {
          const y = s.puntos.find((q) => q.x === x)?.y;
          return y === null || y === undefined ? "—" : p.formatoY(y);
        })])} />
    </figure>
  );
}

/** Barras del índice estacional desde la línea 1,0 (promedio del año). */
export function GraficoIndice({ meses, indice, oficial, titulo }: {
  meses: string[]; indice: (number | null)[]; oficial?: (number | null)[] | null; titulo: string;
}) {
  const alto = 230;
  const [contRef, ancho] = useAncho();
  const [activo, setActivo] = useState<number | null>(null);
  const vals = [...indice, ...(oficial || [])].filter((v): v is number => v !== null);
  if (!vals.length) return <p class="sin-datos">Sin índice estacional para este producto.</p>;
  const ticks = ticksLindos(Math.min(...vals, 1), Math.max(...vals, 1), 4);
  const [y0, y1] = [ticks[0], ticks[ticks.length - 1]];
  const sy = (y: number) => M.arr + (1 - (y - y0) / (y1 - y0)) * (alto - M.arr - M.abj);
  const izq = 76;
  const banda = (ancho - izq - M.der) / 12;
  const anchoBarra = Math.max(6, Math.min(24, banda - 4));
  const cx = (i: number) => izq + banda * i + banda / 2;
  const pct = (v: number) => (Math.abs(v - 1) < 0.005 ? "0 %" : `${v >= 1 ? "+" : "−"}${Math.abs(Math.round((v - 1) * 100))} %`);
  const leyenda = [{ nombre: "Índice calculado", color: "var(--serie-1)" }, ...(oficial ? [{ nombre: "Índice oficial SIMM", color: "var(--serie-2)" }] : [])];
  return (
    <figure class="grafico">
      <Leyenda items={leyenda} />
      <div class="lienzo" ref={contRef}>
        <svg width={ancho} height={alto} viewBox={`0 0 ${ancho} ${alto}`} role="img" aria-label={titulo}>
          {ticks.map((t) => (
            <g key={t}>
              <line class={Math.abs(t - 1) < 1e-9 ? "linea-ref" : "rejilla"} x1={izq} x2={ancho - M.der} y1={sy(t)} y2={sy(t)} />
              <text class="eje" x={izq - 6} y={sy(t) + 4} text-anchor="end">{Math.abs(t - 1) < 1e-9 ? "promedio" : pct(t)}</text>
            </g>
          ))}
          {indice.map((v, i) => {
            if (v === null) return <text key={i} class="eje" x={cx(i)} y={sy(1) - 4} text-anchor="middle">s/d</text>;
            const [ya, yb] = [sy(Math.max(v, 1)), sy(Math.min(v, 1))];
            const r = Math.min(4, (yb - ya) / 2);
            const x = cx(i) - anchoBarra / 2;
            // Extremo de datos redondeado (4 px), cuadrado en la línea base
            const d = v >= 1
              ? `M${x},${yb} V${ya + r} q0,-${r} ${r},-${r} H${x + anchoBarra - r} q${r},0 ${r},${r} V${yb} Z`
              : `M${x},${ya} V${yb - r} q0,${r} ${r},${r} H${x + anchoBarra - r} q${r},0 ${r},-${r} V${ya} Z`;
            return (
              <g key={i} onPointerEnter={() => setActivo(i)} onPointerDown={() => setActivo(i)} onPointerLeave={() => setActivo(null)}>
                <rect x={cx(i) - banda / 2} y={M.arr} width={banda} height={alto - M.arr - M.abj} fill="transparent" />
                <path d={d} fill="var(--serie-1)" opacity={activo === null || activo === i ? 1 : 0.55} />
              </g>
            );
          })}
          {oficial?.map((v, i) => v === null ? null : <circle key={i} cx={cx(i)} cy={sy(v)} r={4} fill="var(--serie-2)" class="punto" pointer-events="none" />)}
          {meses.map((m, i) => (i % (banda < 24 ? 2 : 1) === 0 ? <text key={m} class="eje" x={cx(i)} y={alto - 8} text-anchor="middle">{m}</text> : null))}
        </svg>
        {activo !== null && (
          <Tooltip x={cx(activo)} ancho={ancho}>
            <strong>{meses[activo]}</strong>
            <span>Calculado: {indice[activo] === null ? "sin mercado" : pct(indice[activo]!)}</span>
            {oficial && oficial[activo] !== null && <span>Oficial SIMM: {pct(oficial[activo]!)}</span>}
          </Tooltip>
        )}
      </div>
      <TablaDatos encabezados={["Mes", "Índice calculado", ...(oficial ? ["Índice oficial SIMM"] : [])]}
        filas={meses.map((m, i) => [m, indice[i] === null ? "sin dato" : pct(indice[i]!), ...(oficial ? [oficial[i] === null ? "sin dato" : pct(oficial[i]!)] : [])])} />
    </figure>
  );
}

/** Mapa de calor anual: filas = meses, columnas = días; color divergente alrededor del promedio. */
export function MapaCalor({ valores, etiquetaCelda, marcas, titulo }: {
  valores: (number | null)[]; // 365 valores (relativos al promedio: 0 = promedio)
  etiquetaCelda: (dia: number, v: number | null) => string;
  marcas: number[]; // días marcados 1, 2, 3
  titulo: string;
}) {
  const [contRef, ancho] = useAncho();
  const [activo, setActivo] = useState<number | null>(null);
  const izq = 36, gap = 1;
  const celda = Math.max(6, (ancho - izq) / 31 - gap);
  const altoFila = Math.max(celda, 16);
  const alto = 12 * (altoFila + 2);
  const inicioMes = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 365];
  const nombres = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "set", "oct", "nov", "dic"];
  const maxAbs = Math.max(0.05, ...valores.filter((v): v is number => v !== null).map(Math.abs));
  const color = (v: number) => {
    const t = Math.min(1, Math.abs(v) / maxAbs);
    return `color-mix(in oklab, var(--div-neutro), ${v >= 0 ? "var(--div-alto)" : "var(--div-bajo)"} ${Math.round(t * 100)}%)`;
  };
  const pos = (dia: number) => {
    const m = inicioMes.filter((i) => i <= dia).length - 1;
    return { m, x: izq + (dia - inicioMes[m]) * (celda + gap), y: m * (altoFila + 2) };
  };
  return (
    <figure class="grafico">
      <ul class="leyenda" aria-label="Leyenda">
        <li><span class="muestra" style={{ background: "var(--div-bajo)" }} aria-hidden="true" />Precio bajo el promedio</li>
        <li><span class="muestra" style={{ background: "var(--div-neutro)", border: "1px solid var(--borde)" }} aria-hidden="true" />Cerca del promedio</li>
        <li><span class="muestra" style={{ background: "var(--div-alto)" }} aria-hidden="true" />Precio sobre el promedio</li>
        <li><span class="muestra marca-leyenda" aria-hidden="true">1</span>Mejores fechas</li>
        {valores.some((v) => v === null) && <li><span class="muestra" style={{ border: "1px solid var(--eje)" }} aria-hidden="true" />Cosecha en meses sin mercado</li>}
      </ul>
      <div class="lienzo" ref={contRef}>
        <svg width={ancho} height={alto} viewBox={`0 0 ${ancho} ${alto}`} role="img" aria-label={titulo}>
          {nombres.map((n, m) => (
            <text key={n} class="eje" x={izq - 6} y={m * (altoFila + 2) + altoFila / 2 + 4} text-anchor="end">{n}</text>
          ))}
          {valores.map((v, dia) => {
            const { x, y } = pos(dia);
            return (
              <rect key={dia} x={x} y={y} width={celda} height={altoFila} rx={2}
                fill={v === null ? "none" : color(v)}
                class={`${v === null ? "celda-vacia" : "celda"}${activo === dia ? " activa" : ""}`}
                onPointerEnter={() => setActivo(dia)} onPointerDown={() => setActivo(dia)} onPointerLeave={() => setActivo(null)} />
            );
          })}
          {marcas.map((dia, i) => {
            const { x, y } = pos(dia);
            return (
              <g key={dia} pointer-events="none">
                <circle cx={x + celda / 2} cy={y + altoFila / 2} r={9} class="marca-circulo" />
                <text x={x + celda / 2} y={y + altoFila / 2 + 4} class="marca" text-anchor="middle">{i + 1}</text>
              </g>
            );
          })}
        </svg>
        {activo !== null && <Tooltip x={pos(activo).x} ancho={ancho}>{etiquetaCelda(activo, valores[activo])}</Tooltip>}
      </div>
    </figure>
  );
}

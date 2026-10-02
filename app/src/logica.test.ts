import { describe, expect, it } from "vitest";
import { buscar, distancia } from "./buscar";
import { fechaLarga, hoyCR, momentoCR, textoDiaDelAnio } from "./fechas";
import { colones, direccion, porcentaje } from "./formato";
import { frescura } from "./frescura";
import { resumenDelDia } from "./resumen";
import type { Meta, ProductoHoy } from "./tipos";

const CATALOGO = [
  { id: "camote", nombre: "Camote", cultivo: "Camote", sinonimos: ["batata", "boniato"] },
  { id: "tomate-primera", nombre: "Tomate primera", cultivo: "Tomate", sinonimos: ["jitomate"] },
  { id: "chile-dulce-primera", nombre: "Chile dulce primera", cultivo: "Chile dulce", sinonimos: ["pimiento", "chile morron"] },
  { id: "nampi", nombre: "Ñampí", cultivo: "Ñampí", sinonimos: ["nampi"] },
  { id: "brocoli", nombre: "Brócoli", cultivo: "Brócoli", sinonimos: [] },
  { id: "papa-blanca-primera", nombre: "Papa blanca primera", cultivo: "Papa", sinonimos: ["patata"] },
  { id: "papaya-hibrida", nombre: "Papaya híbrida", cultivo: "Papaya", sinonimos: [] },
];
const primero = (q: string) => buscar(q, CATALOGO)[0]?.entrada.id;

describe("buscador", () => {
  it("sinónimos: batata -> camote", () => expect(primero("batata")).toBe("camote"));
  it("tildes y mayúsculas", () => {
    expect(primero("BROCOLI")).toBe("brocoli");
    expect(primero("nampi")).toBe("nampi");
    expect(primero("Ñampí")).toBe("nampi");
  });
  it("errores leves", () => {
    expect(primero("tomtae")).toBe("tomate-primera"); // letras intercambiadas
    expect(primero("tomste")).toBe("tomate-primera"); // letra cambiada
    expect(primero("brocooli")).toBe("brocoli");       // letra de más
    expect(primero("pimento")).toBe("chile-dulce-primera");
  });
  it("mientras se escribe (prefijo)", () => {
    expect(primero("tom")).toBe("tomate-primera");
    expect(primero("chile d")).toBe("chile-dulce-primera");
  });
  it("papa no confunde con papaya al escribir completo", () => {
    expect(primero("papa")).toBe("papa-blanca-primera");
    expect(primero("papaya")).toBe("papaya-hibrida");
  });
  it("sin coincidencias", () => expect(buscar("zzzz", CATALOGO)).toEqual([]));
  it("distancia de Damerau-Levenshtein", () => {
    expect(distancia("tomate", "tomate")).toBe(0);
    expect(distancia("tomtae", "tomate")).toBe(1);
    expect(distancia("camote", "camotes")).toBe(1);
    expect(distancia("camote", "camion")).toBe(3);
  });
});

describe("fechas y formato", () => {
  it("setiembre y hora de Costa Rica", () => {
    expect(fechaLarga("2026-09-28")).toBe("28 de setiembre");
    expect(momentoCR("2026-09-29T05:33:44Z")).toBe("28 de setiembre, 11:33 p. m.");
    expect(hoyCR(new Date("2026-09-29T05:00:00Z"))).toBe("2026-09-28");
    expect(textoDiaDelAnio(0)).toBe("1 de enero");
    expect(textoDiaDelAnio(-1)).toBe("31 de diciembre");
  });
  it("colones y porcentajes", () => {
    expect(colones(10000).replace(/\s/g, " ")).toMatch(/^₡10.000$|^₡10 000$/);
    expect(colones(319.23)).toBe("₡319,23");
    expect(porcentaje(-36.2, true)).toBe("−36 %");
    expect(porcentaje(5.25)).toBe("5,3 %");
    expect(direccion(0.4)).toBe("igual");
    expect(direccion(-3)).toBe("baja");
    expect(direccion(null)).toBe(null);
  });
});

const meta = (m: Partial<Meta>): Meta => ({
  estado: "ok", mensaje: "", datos_de_ejemplo: false, ultimo_intento_utc: "2026-09-28T20:00:00Z",
  ultima_actualizacion_exitosa_utc: "2026-09-28T20:00:00Z", fecha_boletin: "2026-09-28", registros: 57, rechazados: 0, ...m,
});

describe("frescura de los datos", () => {
  it("dato de hoy: sin insignia ni aviso", () => {
    const f = frescura(meta({}), new Date("2026-09-28T22:00:00Z"));
    expect(f.insigniaDato).toBeNull();
    expect(f.desactualizado).toBeNull();
    expect(f.boletin).toBe("Boletín del 28 de setiembre de 2026");
    expect(f.revisado).toBe("Revisado hoy a las 2:00 p. m.");
    expect(f.resultadoRevision).toBe("no hay boletines más nuevos en el PIMA.");
    const f1 = frescura(meta({ ultimo_intento_utc: "2026-09-28T19:17:00Z" }), new Date("2026-09-28T22:00:00Z"));
    expect(f1.revisado).toBe("Revisado hoy a la 1:17 p. m.");
  });
  it("dato de otro día: insignia 'Dato del …' y revisión con fecha", () => {
    const f = frescura(meta({}), new Date("2026-09-29T20:00:00Z"));
    expect(f.revisado).toBe("Revisado el 28 de setiembre a las 2:00 p. m.");
    expect(f.insigniaDato).toBe("Dato del 28 de setiembre");
    expect(f.desactualizado).toBeNull();
  });
  it("más de 3 días sin actualización exitosa: aviso", () => {
    const f = frescura(meta({ estado: "error" }), new Date("2026-10-02T21:00:00Z"));
    expect(f.desactualizado).toMatch(/desactualizada.*4 días/);
    expect(f.ultimoIntentoFallo).not.toBeNull();
    expect(f.resultadoRevision).toBe("la revisión no se completó; se muestran los últimos datos válidos.");
    const g = frescura(meta({ fuentes: { fruta: { nombre: "Fruta importada", frecuencia: "semanal", estado: "error", mensaje: "",
      ultima_actualizacion_exitosa_utc: null, fecha_boletin: "2026-09-30", meses_precios: [] } } }), new Date("2026-09-28T22:00:00Z"));
    expect(g.resultadoRevision).toBe("la revisión no se completó para fruta importada; se muestran los últimos datos válidos.");
  });
});

const prod = (id: string, nombre: string, v30: number | null, vAnt: number | null, fuente: ProductoHoy["fuente"] = "diario"): ProductoHoy => ({
  id, nombre, cultivo: null, cultivo_id: null, categoria: null, unidad: "Kilo", kg: 1, minimo: 1, maximo: 2, moda: 1.5,
  promedio: 1.5, precio_kg: 1.5, fuente, fecha_boletin: "2026-09-28",
  vs_anterior: vAnt === null ? null : { fecha: "2026-09-25", promedio: 1, variacion_pct: vAnt },
  vs_semana: null, vs_promedio: v30 === null ? null : { boletines: 10, promedio: 1, variacion_pct: v30 },
});

describe("resumen del día", () => {
  const productos = [prod("tomate-primera", "Tomate primera", -39.4, -36.2), prod("camote", "Camote", 12, 0.5),
    prod("brocoli", "Brócoli", 3, 2), prod("pepino", "Pepino", null, null)];
  it("frases simples con la mayor alza y la mayor baja", () => {
    const r = resumenDelDia(productos);
    expect(r).toContain("Hoy el precio de camote está 12 % por encima de su promedio de los últimos 30 días.");
    expect(r).toContain("Hoy el precio de tomate primera está 39 % por debajo de su promedio de los últimos 30 días.");
    expect(r.at(-1)).toBe("Frente al boletín diario anterior: 1 producto subió, 1 bajó y 1 se mantuvo igual.");
    const muchos = resumenDelDia([...productos, prod("a", "A", 1, 5), prod("b", "B", 1, -5)]);
    expect(muchos.at(-1)).toBe("Frente al boletín diario anterior: 2 productos subieron, 2 bajaron y 1 se mantuvo igual.");
  });
  it("los favoritos van primero", () => {
    expect(resumenDelDia(productos, ["brocoli"])[0]).toMatch(/brócoli está 3 % por encima/);
  });
  it("fuentes semanal y quincenal: sin 'Hoy' y con su propia ventana", () => {
    const kiwi = prod("kiwi", "Kiwi", -8, 2, "fruta");
    expect(resumenDelDia([kiwi], ["kiwi"])[0]).toBe("El precio de kiwi está 8 % por debajo de su promedio de las últimas 5 semanas.");
    // No entra en la cuenta del boletín diario
    expect(resumenDelDia([kiwi], ["kiwi"]).some((f) => f.startsWith("Frente"))).toBe(false);
  });
});

import { diasEntre, fechaLarga, horaCR, hoyCR } from "./fechas";
import type { Meta } from "./tipos";

export const DIAS_AVISO_DESACTUALIZADO = 3;

export interface Frescura {
  /** "Revisado hoy a las 8:16 p. m." (con el día si no fue hoy). */
  revisado: string;
  /** Resultado de esa revisión en palabras simples. */
  resultadoRevision: string;
  boletin: string;               // "Boletín del 28 de setiembre"
  insigniaDato: string | null;   // "Dato del 28 de setiembre" si el boletín no es de hoy
  desactualizado: string | null; // aviso si la última actualización exitosa tiene > 3 días
  ultimoIntentoFallo: string | null;
}

export function frescura(meta: Meta, ahora: Date = new Date()): Frescura {
  const hoy = hoyCR(ahora);
  const exito = meta.ultima_actualizacion_exitosa_utc;
  const revision = meta.ultimo_intento_utc;
  let revisado = "Sin revisiones registradas";
  if (revision) {
    const hora = horaCR(revision);
    const aLas = hora.startsWith("1:") ? `a la ${hora}` : `a las ${hora}`; // "a la 1:17", "a las 8:16"
    const dia = hoyCR(new Date(revision));
    revisado = dia === hoy ? `Revisado hoy ${aLas}` : `Revisado el ${fechaLarga(dia)} ${aLas}`;
  }
  const boletin = meta.fecha_boletin ? `Boletín del ${fechaLarga(meta.fecha_boletin, true)}` : "Sin boletín disponible";
  const insigniaDato = meta.fecha_boletin && meta.fecha_boletin !== hoy ? `Dato del ${fechaLarga(meta.fecha_boletin)}` : null;
  const horas = exito ? (ahora.getTime() - Date.parse(exito)) / 3_600_000 : Infinity;
  const desactualizado = horas > DIAS_AVISO_DESACTUALIZADO * 24
    ? `La información puede estar desactualizada: la última actualización exitosa fue hace ${
        exito ? Math.floor(horas / 24) + " días" : "más de 3 días"}.`
    : null;
  const ultimoIntentoFallo = meta.estado === "error"
    ? "El último intento de actualización no se completó; se muestran los últimos datos válidos."
    : null;
  // Solo se afirma "no hay boletines más nuevos" si la revisión terminó bien
  const fuentesConError = Object.values(meta.fuentes || {}).filter((f) => f.estado === "error").map((f) => f.nombre.toLowerCase());
  const resultadoRevision = meta.estado === "error" || fuentesConError.length
    ? `la revisión no se completó${meta.estado !== "error" ? ` para ${fuentesConError.join(" y ")}` : ""}; se muestran los últimos datos válidos.`
    : "no hay boletines más nuevos en el PIMA.";
  return { revisado, resultadoRevision, boletin, insigniaDato, desactualizado, ultimoIntentoFallo };
}

export function esDeHoy(fechaIso: string | null, ahora: Date = new Date()): boolean {
  return !!fechaIso && diasEntre(fechaIso, hoyCR(ahora)) === 0;
}

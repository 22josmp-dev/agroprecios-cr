import { diasEntre, fechaLarga, hoyCR, momentoCR } from "./fechas";
import type { Meta } from "./tipos";

export const DIAS_AVISO_DESACTUALIZADO = 3;

export interface Frescura {
  ultimaActualizacion: string;   // "Última actualización: 28 de setiembre, 11:33 p. m."
  boletin: string;               // "Boletín del 28 de setiembre"
  insigniaDato: string | null;   // "Dato del 28 de setiembre" si el boletín no es de hoy
  desactualizado: string | null; // aviso si la última actualización exitosa tiene > 3 días
  ultimoIntentoFallo: string | null;
}

export function frescura(meta: Meta, ahora: Date = new Date()): Frescura {
  const hoy = hoyCR(ahora);
  const exito = meta.ultima_actualizacion_exitosa_utc;
  const ultimaActualizacion = exito ? `Última actualización: ${momentoCR(exito)}` : "Última actualización: sin datos";
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
  return { ultimaActualizacion, boletin, insigniaDato, desactualizado, ultimoIntentoFallo };
}

export function esDeHoy(fechaIso: string | null, ahora: Date = new Date()): boolean {
  return !!fechaIso && diasEntre(fechaIso, hoyCR(ahora)) === 0;
}

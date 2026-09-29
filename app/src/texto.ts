/** Minúsculas, sin tildes (ñ -> n), sin signos, espacios simples. */
export function normalizar(texto: string): string {
  return (texto || "")
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

/** "tomate primera" -> "Tomate primera" */
export function capitalizar(texto: string): string {
  return texto ? texto[0].toUpperCase() + texto.slice(1) : texto;
}

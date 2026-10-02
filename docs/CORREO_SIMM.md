# Borrador de correo al SIMM (configuración inicial, una sola vez)

**Situación del histórico (29-09-2026):**
- Precios **mensuales 2018–2025** de 76 productos: ya disponibles y usados, leídos de los PDF de
  índices estacionales que el SIMM publica (ver docs/FORMATO_BOLETIN.md §4). Con eso el índice
  estacional se calcula con 4 a 8 años de datos.
- Precios **diarios**: solo desde el 14-09-2026 (el sitio muestra ~2 semanas de boletines).
  Enero–agosto de 2026 no están en ninguna fuente pública.

Por eso el pedido ya no es "enviar todo el histórico", sino confirmar el permiso de uso y
completar lo que falta. Lo envía el desarrollador desde su correo; **no es una tarea diaria ni
del agricultor.**

---

**Para:** simm@pima.go.cr
**Asunto:** Solicitud de permiso de uso y datos históricos del boletín CENADA para app informativa gratuita

Estimado equipo del SIMM:

Mi nombre es [NOMBRE] y desarrollo, sin fines de lucro, una aplicación web gratuita para
productores agrícolas que muestra los precios del Boletín Diario de Precios del CENADA y los
índices estacionales publicados por el SIMM, siempre citando "Fuente: PIMA – SIMM". La app no
tiene publicidad, no cobra y no recolecta datos personales:
https://22josmp-dev.github.io/agroprecios-cr/

Les escribo para:

1. **Confirmar el permiso de uso** de los boletines diarios y de los índices estacionales
   publicados en www.pima.go.cr para mostrarlos en la app, y si desean que la cita a la fuente
   tenga alguna forma específica.

2. **Solicitar, si es posible, en formato tabular (CSV o Excel):**
   a. Los precios diarios del boletín (producto, unidad, mínimo, máximo, moda, promedio) desde
      enero de 2026 hasta la fecha, o del período más amplio que puedan compartir.
   b. Los volúmenes de oferta mensuales y, si existe, la procedencia de los productos.
   c. Los índices estacionales de la edición vigente en formato tabular.

3. **Consultar** si la columna de precios de los índices estacionales corresponde al promedio
   mensual de la moda diaria (como indica el instructivo DEDM-SIMM-INF-007-26) o al promedio
   general, para combinarla correctamente con el boletín diario.

4. **Pedirles que, si planean cambiar** el formato del boletín o la forma de publicarlo en el
   sitio, nos lo avisen por este medio para ajustar la app a tiempo.

La app consulta el sitio del PIMA como máximo tres veces al día, a un ritmo de una solicitud por
segundo, e identificándose como "AgroPreciosCR-bot". Si prefieren otro horario o mecanismo, con
gusto lo ajustamos.

Muchas gracias por su trabajo y por la información que ponen a disposición del sector.

Saludos cordiales,
[NOMBRE]
[CORREO DE CONTACTO]

---

## Qué hacer con la respuesta

- **Permiso confirmado:** anotarlo en README → "Datos y privacidad" con la fecha.
- **Si envían datos diarios:** guardar el archivo en `archivo/historico_simm/` y escribir un
  importador de una sola vez que genere `data/prices/AAAA-MM.json` con el mismo esquema
  (docs/DATOS.md), marcando la procedencia. Luego `python -m ingesta estacional`.
- **Si piden no usar los datos o cambiar algo:** detener el workflow (*Actions → Disable
  workflow*) y ajustar antes de reanudar.

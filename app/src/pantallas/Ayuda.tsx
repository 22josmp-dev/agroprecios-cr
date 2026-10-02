import { Fuente } from "../componentes/comunes";
import { momentoCR } from "../fechas";
import type { Meta } from "../tipos";

export function Ayuda({ meta }: { meta: Meta }) {
  return (
    <article class="ayuda">
      <h1>Ayuda</h1>

      <section aria-labelledby="t-glosario">
        <h2 id="t-glosario">Palabras que usamos</h2>
        <dl>
          <dt>Precio mayorista de referencia</dt>
          <dd>Lo que se paga en el CENADA cuando un mayorista le vende a un minorista. No es el precio en finca ni el del supermercado.</dd>
          <dt>Promedio</dt>
          <dd>El precio medio de todas las ventas registradas ese día.</dd>
          <dt>Moda</dt>
          <dd>El precio que más se repitió ese día. Suele ser el precio "normal" del mercado.</dd>
          <dt>Mínimo y máximo</dt>
          <dd>El precio más bajo y el más alto registrados ese día.</dd>
          <dt>Unidad de venta</dt>
          <dd>Cómo se vende en el CENADA: kilo, caja, malla, java o unidad.</dd>
          <dt>Índice estacional</dt>
          <dd>Muestra en qué meses el precio suele estar por encima o por debajo del promedio del año, según los años anteriores.
            Por ejemplo, "+20 % en diciembre" significa que en diciembre el precio suele ser 20 % más alto que el promedio del año.</dd>
          <dt>Confianza</dt>
          <dd><strong>Alta</strong>: 5 años o más de datos y precios que se repiten parecido cada año.
            <strong> Media</strong>: 3 o 4 años de datos. <strong>Baja</strong>: pocos datos o precios que cambian mucho de un año a otro.</dd>
        </dl>
      </section>

      <section aria-labelledby="t-instalar">
        <h2 id="t-instalar">Instalar la app en el celular</h2>
        <p>No necesita tienda de aplicaciones ni cuenta. Después de instalarla funciona sin internet con los últimos datos guardados.</p>
        <h3>Android (Chrome)</h3>
        <ol>
          <li>Abra esta página en Chrome.</li>
          <li>Toque el menú <strong>⋮</strong> (arriba a la derecha).</li>
          <li>Toque <strong>Instalar aplicación</strong> o <strong>Agregar a la pantalla principal</strong>.</li>
        </ol>
        <h3>iPhone (Safari)</h3>
        <ol>
          <li>Abra esta página en Safari.</li>
          <li>Toque el botón <strong>Compartir</strong> (el cuadro con una flecha hacia arriba).</li>
          <li>Toque <strong>Agregar a inicio</strong> y luego <strong>Agregar</strong>.</li>
        </ol>
      </section>

      <section aria-labelledby="t-datos">
        <h2 id="t-datos">¿De dónde vienen los datos?</h2>
        <ul>
          <li><strong>Frutas y hortalizas:</strong> Boletín Diario de Precios del CENADA, publicado por el PIMA – SIMM
            (<a href="https://www.pima.go.cr/boletin/" rel="noopener">pima.go.cr/boletin</a>). Hay boletín de lunes a viernes.</li>
          <li><strong>Fruta importada:</strong> boletín semanal del PIMA – SIMM
            (<a href="https://www.pima.go.cr/boletin-de-precios-de-fruta-importada/" rel="noopener">ver en pima.go.cr</a>), normalmente los miércoles.</li>
          <li><strong>Aromáticos y gourmet:</strong> boletín quincenal del PIMA – SIMM
            (<a href="https://www.pima.go.cr/boletin-de-productos-aromaticos-y-goutmet/" rel="noopener">ver en pima.go.cr</a>), normalmente los jueves.</li>
          <li><strong>Índices estacionales e historial mensual:</strong> publicados por el SIMM con datos desde 2018.</li>
          <li><strong>Actualización:</strong> la app revisa automáticamente el sitio del PIMA-CENADA todos los días dos veces al día.</li>
          <li><strong>Ciclos de cultivo de la guía:</strong> valores estimados de referencia (se deben de verificar con un profesional o llenar según la experiencia).</li>
          {meta.ultima_actualizacion_exitosa_utc && <li>Última actualización correcta: {momentoCR(meta.ultima_actualizacion_exitosa_utc)}.</li>}
        </ul>
      </section>

      <section aria-labelledby="t-privacidad">
        <h2 id="t-privacidad">Privacidad</h2>
        <p>La app no tiene cuentas ni formularios y no recolecta datos personales. Lo único que guarda, y solo en su teléfono,
          son los cultivos que usted marca con la estrella.</p>
      </section>
      <Fuente />
    </article>
  );
}

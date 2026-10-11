# Observatorio 360 · Actualización para el equipo investigador

**9 de octubre de 2026**

Hola, equipo:

Les contamos en qué va la plataforma después del pedido del 6 de octubre. Ya implementamos todo lo que pidieron. Lo nuevo y sensible (alertas y Cuidadores para la comunidad) quedó listo, pero **apagado** en la versión pública hasta que ustedes aprueben los textos y las rutas.

Para avanzar necesitamos tres cosas de ustedes: **aprobar textos y rutas**, **enviarnos dos archivos** y **resolver algunas preguntas de método**. Están más abajo.

---

## 1. Lo que hicimos

### Grados y colegios

- **Los grados con 10 o más estudiantes ya se ven**, también dentro de cada colegio. Por ejemplo, Laura Vicuña de sexto a décimo, y la comparación por grado dentro del colegio.
- **Hay una sola tabla de colegios** para todos los módulos. La unidad es el colegio; la sede es un detalle que solo ven los investigadores.
- **Primaria ya usa el archivo actualizado** (hasta el 6 de octubre, 352 respuestas válidas).
- **Secundaria sigue con la exportación del 18 de septiembre.** Por eso todavía no aparecen CdP sexto y séptimo, JJC décimo ni SJMEB sexto (ver §3).

### Navegación

- «Dashboard» ahora se llama **«Docentes»**.
- El menú queda así: Docentes, Estudiantes 360, Cuidadores 360, Triangulación 360, Chat, Cargar Datos, Tendencias y Reportes.
- El colegio y el rol que uno elige se mantienen al cambiar de página.

### Privacidad: ninguna cifra delata a una persona

Revisando lo publicado encontramos porcentajes por grupo que, con la *n*, dejaban saber que eran 1 o 2 estudiantes. Uno de ellos era sobre pensamientos de muerte en un grado de un colegio. Lo corregimos con una regla general:

- Un porcentaje se muestra solo si el grupo tiene **al menos 3 casos y al menos 3 estudiantes sin el caso**.
- Además, se ocultan cifras vecinas cuando hace falta, para que nada se pueda despejar restando.
- Nunca se publica el número de casos.
- En pantalla, la cifra oculta aparece como **«—»**, con la nota «cifras muy pequeñas para mostrarse sin riesgo de identificar a alguien».
- **Ya está publicada (corrida 7).** Los totales de primaria y secundaria no cambian. Por colegio y por grado se oculta una parte importante: cerca de la mitad de las bandas del SDQ por grupo y un tercio de los cortes por grado dentro de cada colegio.

### Alertas de estudiantes: «Señales para actuar a tiempo» (listas, apagadas)

Es un panel por **grupo**, nunca individual, que aparece arriba de las tarjetas.

- **Señales de malestar:** respuesta «Muy cierto» en 3 o más de los 6 ítems del SDQ que ustedes marcaron con `*`. Hoy da 8,8 % en secundaria y 15,1 % en primaria.
- **Señales de desesperanza y pensamientos de muerte** (solo secundaria): RCADS 18 en «Siempre», o RCADS 18 y RCADS 16 en «Con frecuencia» o más. Hoy da 17,0 %.
- **Estados:**
  - «Para tener presente».
  - «Prioridad»: el grupo queda claramente por encima del resto del municipio. Hoy ningún grupo está en Prioridad.
  - «Sin estado: cifras pequeñas».
- **Lenguaje:**
  - Siempre dice «No es un diagnóstico: indica dónde mirar primero».
  - Nunca usa la palabra «suicidio» ni el color rojo.
- **Quién ve qué:**
  - Colegio y municipio ven las dos alertas; el panel reemplaza la tarjeta de muerte.
  - Familia solo ve malestar.
- **Dónde más aparecen:** en el informe del colegio, en el de la Secretaría, en el PDF de una página y en una pestaña para investigadores con la sensibilidad a distintos umbrales.

### Cuidadores 360: «Cuidando al Cuidador»

**Vista de investigadores (ya disponible en la plataforma del equipo).** Se trabajó con 756 respuestas válidas: 734 cuidadores distintos y 886 niños.

- **Nombres y teléfonos:** se descartan al leer el archivo.
- **Escalas:** estrés (PSS-10), ánimo (EPDS), apoyo social por fuente, riesgo del barrio, y SDQ y ARI de padres.
- **Del APQ** solo se reporta castigo físico y grito, hasta tener el libro de códigos.
- **El mínimo de 10** se cuenta en cuidadores distintos, no en niños.

**Vista para colegios, familias y municipio (lista, apagada).**

- **Tarjetas:** estrés, apoyo, crianza, barrio y cómo ve el cuidador al hijo.
- **Panel «Señales para cuidar a quienes cuidan»:**
  - **Ánimo** (EPDS ≥ 13): por grupo.
  - **Pensamientos de hacerse daño** (ítem 10): **solo como cifra de todo el municipio**, nunca por colegio.
  - **Colegio:** ve un estado general fijo, sin esa cifra.
  - **Familia:** ve un mensaje de autocuidado con la ruta, sin cifras.
- **Informes:** del colegio, de la Secretaría y PDF de una página.

### Triangulación 360 (solo investigadores)

**Por colegio.** Entran los 4 colegios con 10 o más personas de cada actor: JJC, La Balsa, LauV y SJMEB.

- Se compara cada actor con el resto del municipio.
- Solo se habla de **tensión** o **coincidencia** cuando los dos actores miden lo mismo:
  - El SDQ del niño frente al de su cuidador.
  - El clima escolar según estudiantes y según docentes.
- Lo demás se describe como **co-ocurrencia**.
- Con 4 colegios, es descriptivo y ecológico.

**Díadas niño–cuidador** (solo en el computador que procesa los datos). Son 208 parejas enlazadas por un código cifrado y verificadas con el colegio. Resultados preliminares:

- El acuerdo entre lo que dice el niño y lo que dice su cuidador es **bajo** (CCI entre 0,07 y 0,29).
- Los niños reportan **más dificultades** que las que ve su cuidador: 3,6 puntos más en el total del SDQ.
- En el **17 %** de las díadas el niño muestra malestar y el cuidador no lo ve.
- Ninguna asociación (ánimo, estrés, castigo físico o barrio del cuidador con los resultados del niño) se sostiene al corregir por comparaciones múltiples.

### Calidad

- Cada fase pasó por pruebas automáticas (más de 1 100) y por una revisión independiente de privacidad.
- También se revisó en el navegador, en computador y en celular.
- Nada individual sale a la base de datos pública: solo agregados de grupos con 10 o más personas.

---

## 2. Lo que necesitamos que aprueben

Todos estos textos son **provisionales**. Mientras no los aprueben, las alertas y la página de Cuidadores no aparecen en la versión pública. Si les sirve, les enviamos un documento con todos los textos juntos para que los revisen y comenten.

1. **Textos del panel de alertas de estudiantes:** qué significa cada alerta y qué hacer, por rol (colegio, municipio y familia).
2. **Rutas de atención para Chía**, con las líneas exactas:
   - Para estudiantes. Hoy aparece la «Línea 106», que es de Bogotá. ¿Va la 192 opción 4, el ICBF 141 u otra?
   - Para adultos (cuidadores). Hoy solo aparecen la Secretaría de Salud y la Comisaría, sin teléfonos.
3. **Umbrales de las alertas.**
   - Malestar: ¿3 de 6? Con 2 de 6 subiría a 22 % en secundaria y 32 % en primaria.
   - Desesperanza: ¿la regla estricta o la amplia?
   - En la pestaña de investigadores está la sensibilidad completa.
4. **Ítems con `*` de secundaria.** Hoy solo está marcado el formulario de primaria.
5. **Cuidadores:**
   - Los textos de las tarjetas y del panel.
   - El uso de la EPDS fuera del periodo perinatal: aquí se lee como tamizaje.
   - El título «Estrés de crianza», cuando la PSS mide estrés general del día a día. ¿Lo dejamos o lo cambiamos?
   - El estado general fijo para el rol colegio.
   - Que familia no tenga tarjeta de ánimo.
6. **Informes:** ¿nos quedamos con el PDF (como el de docentes) o con el HTML imprimible (como el de estudiantes)? Es la prueba A/B que teníamos pendiente.

---

## 3. Lo que necesitamos que nos envíen

1. **El libro de códigos de cuidadores (`Códigos.xlsx`).** Sin él no podemos puntuar las subescalas del APQ (crianza positiva) ni el estrés parental. En este último, las columnas 103 a 107 parecen una sola pregunta partida en cinco, y la 117 está redactada en positivo.
2. **La exportación actualizada del formulario de secundaria.** Es lo único que falta para que aparezcan los grados de su lista.

---

## 4. Preguntas de método

No frenan nada (hoy hay un valor provisional en cada caso), pero queremos su criterio:

1. En 72 respuestas, el «hijo 2» tiene el mismo nombre que el hijo 1. Hoy se descarta como duplicado. ¿Correcto?
2. Un cuidador con dos hijos se ubica en el colegio y grado del **primer** hijo. Afecta a 217 cuidadores. ¿Está bien?
3. ¿La ola es el año calendario (2025 y 2026)?
4. ¿El ARI de padres tiene un punto de corte?
5. En docentes, ¿qué cuenta como «clima» para triangular? Hoy usamos apoyo del líder y de los compañeros. ¿Y el desgaste va con la escala de 4 ítems o con la BAT de 12?
6. ¿La definición de «malestar que el cuidador no ve» les parece adecuada (niño en banda alta o con señal de malestar, y cuidador en banda promedio)?
7. ¿Agregamos un análisis de díadas solo con secundaria? 41 de las 208 díadas son de primaria, por debajo de la edad validada del SDQ.
8. ¿Quieren la capa por colegio de la triangulación también en la plataforma del equipo, y no solo en el computador que procesa?

---

## 5. Próximas actualizaciones de datos: las suben ustedes

La idea es que **las próximas actualizaciones de docentes y de estudiantes las suban ustedes** desde **«Cargar Datos»**, en la plataforma del equipo, sin pasar por nosotros.

- Los nombres y demás datos que identifican se descartan al procesar y **no se guardan**.
- **Docentes** ya se puede subir por ahí. Estamos ajustando la página para que acepte la exportación tal como sale de Google Forms.
- **Estudiantes** lo estamos habilitando ahora.
- Cuando quede listo les enviamos una guía corta, paso a paso.

Mientras tanto, la exportación de secundaria pueden enviárnosla directamente.

---

## 6. Qué pasa cuando aprueben

1. Marcamos los textos y las rutas como aprobados.
2. Publicamos una corrida nueva de estudiantes (con alertas) y la primera de cuidadores.
3. Se habilita Cuidadores en la versión pública.

Cada paso se revisa antes en la plataforma del equipo.

Quedamos atentos.

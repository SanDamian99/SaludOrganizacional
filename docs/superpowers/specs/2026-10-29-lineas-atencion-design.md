# Líneas de atención en salud mental — diseño

Fecha: 29-oct-2026 · Rama: `feature/lineas-atencion` (worktree aparte, desde `origin/main`)
Fuente: «Líneas de atención en salud mental.docx», enviado por la Secretaría de Salud.
Decisión del usuario: las líneas están confirmadas; se adopta la combinación A + D con B como destino.

## Objetivo
Que quien use la plataforma encuentre la línea correcta en el momento correcto, sin una lista
de 30 filas en pantalla. Las líneas salen cuando se necesitan (cuadro corto y alertas) y se
pueden consultar completas cuando se quiera (pestaña).

## Piezas

### 1. Catálogo único — `src/core/lineas_atencion.py`
Una sola fuente de verdad, sin Streamlit. Cada línea es un `dataclass` congelado:
`clave`, `nombre`, `telefono` (texto para mostrar), `marcado` (número para `tel:`; None si
hay varios o extensión), `whatsapp` (opcional), `horario`, `descripcion`, `municipio`
(`nacional`, `chia`, `cajica`, `sopo`, `zipaquira`, `cota`, `tenjo`, `tabio`, `tocancipa`,
`bogota`), `tipo` (`linea`, `escucha`, `urgencias`), `para` (subconjunto de `estudiante`,
`familia`, `docente`), `temas` (subconjunto de `crisis`, `violencia`, `menores`, `consumo`,
`orientacion`, `victimas`), `direccion` (opcional), `nota` (p. ej. «confirmar sede y horario
antes de asistir»), `fuente`, `fecha`.
Funciones: `todas()`, `por_municipio()`, `para_senal(senal)`, `ahora()`, `filtrar(para, tema,
municipio)`. Regla de pago: las de pago (Clínica Montserrat) llevan `nota` que lo dice.
Los datos se transcriben del documento sin reinterpretar; lo que el documento marca como
«confirmar», conserva esa nota visible.

### 2. A — cuadro «Si necesitas ayuda» (reemplaza las listas escritas a mano)
`alertas_catalogo._RUTA_*`, `catalog.RUTA_ATENCION` y `comunidad_catalogo.ruta` leen del
catálogo. Tres niveles: **Ahora mismo** (106, 123), **Hoy** (orientación escolar, Centros de
Escucha de Chía, 141 si es menor), **Esta semana** (PAPSIVI, EPS). Enlace «Ver todas las
líneas» a la pestaña. Se conserva la firma de `ruta(rol, tipo)` y las entradas que no están
en el documento (orientación escolar, Comisaría de Familia).

### 3. D — líneas según la señal
En el panel de alertas, cada alerta de grupo muestra solo las líneas de su tema
(ideación/autolesión → crisis; violencia en el hogar → menores/violencia; consumo →
orientación/consumo). Mapa `alerta → temas` en el catálogo de alertas. Es información de
grupo: nunca nombra un caso ni se condiciona al colegio.

### 4. B — pestaña pública «Dónde pedir ayuda»
Nueva página `PAGINA_LINEAS` en `navegacion.py`, pública y también en el modo completo. Chía
primero; selectores «¿Para quién?», «¿Qué pasa?», «¿Dónde vive?»; municipios distintos de
Chía plegados; tarjeta por línea con botón de llamar (`tel:`), horario y nota. Sin lectura
de datos ni de Supabase: la página no depende de la red. Módulo nuevo `src/ui/lineas.py`
(regla de despliegue de `navegacion.py`: símbolos nuevos en módulos nuevos, `getattr` para
lo existente).

### 5. Extras
Tarjeta de una página imprimible (HTML) con las líneas de Chía; sin cambios en los informes
existentes salvo que lean la ruta del catálogo.

## Fuera de alcance
Capa de servicios en el mapa (opción C): se pospone; exige verificar coordenadas una por una.

## Candado `RUTAS_VALIDADAS`
El usuario confirmó las líneas. Al integrarlas, `alertas_catalogo.RUTAS_VALIDADAS` y
`comunidad_catalogo.RUTAS_VALIDADAS` pasan a True en un commit propio y visible. Eso retira
el aviso interno «ruta pendiente»; **no** publica Cuidadores (`CUIDADORES_PUBLICO` y
`TEXTOS_APROBADOS` siguen a mano) ni activa `VIDEO_RUTAS`.

## Pruebas
- Catálogo: campos obligatorios, teléfonos no vacíos, claves únicas, municipios y temas
  válidos, notas de «confirmar» conservadas, de pago marcadas.
- Rutas: `ruta(rol, tipo)` mantiene su forma y trae 106 y 123 primero.
- D: cada alerta existente tiene temas definidos y devuelve al menos una línea.
- Página: filtra sin error con todas las combinaciones; sin datos no falla.
- Navegación: la página aparece en el menú público y en el completo.
- Privacidad: ningún texto de líneas se arma con cifras de grupo.

## Riesgos
- Despliegue con módulos rancios en memoria: seguir la regla de `navegacion.py` y hacer
  Reboot app tras fusionar.
- Datos de contacto que cambian: cada línea lleva `fecha`; se revisa en cada corrida.

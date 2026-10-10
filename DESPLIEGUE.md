# Desplegar el Observatorio 360

## Netlify no sirve, y conviene saber por qué

Netlify sirve archivos estáticos y funciones que responden en segundos. Esta
aplicación es un servidor Python que se mantiene vivo mientras alguien la mira y
habla con el navegador por websocket. No hay forma de encajarla ahí sin
reescribirla como sitio estático, y entonces dejaría de ser interactiva.

**Streamlit Community Cloud** es la opción. Es gratis, arranca desde un
repositorio de GitHub y permite apps privadas con lista de invitados.

## De dónde saca los datos la aplicación desplegada

Dos fuentes, en este orden:

1. **Los formularios en disco.** Es lo que se usa en la máquina de quien procesa.
   Puntúa desde los ítems y permite filtrar por colegio y grado.
2. **La corrida publicada en Supabase.** Es lo que usa el despliegue. Solo trae
   resultados agregados.

Los CSV originales **no se despliegan**: traen nombres de menores y están
ignorados por git. Por eso el despliegue depende de que haya una corrida
aprobada; si no la hay, la aplicación lo dice y no muestra cifras.

La segunda fuente no tiene fila por estudiante, y no debería: un despliegue no
puede recalcular nada sobre individuos. Para que aun así se pueda ver un colegio
o un grado, el pipeline calcula por adelantado las tablas de la vista comunidad
de cada grupo que llega a 10 respuestas y el publicador las sube (tipos
`banda_grupo`, `corte_grupo`, `contraste_grupo`, `item_grupo`). Con esa fuente
se filtra por colegio **o** por grado, uno a la vez; un grado dentro de un
colegio no se publica y la pantalla lo explica. Esto existe desde la corrida 5;
una corrida anterior se lee igual, solo que sin selectores.

Para ver en local exactamente lo que mostrará el despliegue:

```bash
OBS360_FUENTE=supabase OBS360_MODO=investigador streamlit run main.py
```

> Streamlit copia sus secretos a las variables de entorno al arrancar, así que
> exportar `SUPABASE_KEY` no tiene efecto: el secreto lo sobrescribe. Para
> previsualizar con otra clave están `OBS360_SUPABASE_URL` y
> `OBS360_SUPABASE_KEY`, que tienen precedencia.

## Versiones del archivo de docentes

Los xlsx de docentes están fuera de git, así que el despliegue no los tiene. En
su lugar, la aplicación carga al arrancar la **versión activa** del almacén de
Supabase: bucket `datasets` (privado) y tabla `obs360.conjuntos_versiones`, que
registra cada subida con fecha, filas, hash, notas y quién la subió. Si no hay
versión activa, ni credenciales, o la red falla, la aplicación cae a los
archivos en disco como hasta ahora.

Solo el despliegue privado (A) lleva en sus secretos las credenciales del
usuario de carga:

```toml
OBS360_CARGA_EMAIL = "cargador@…"
OBS360_CARGA_CLAVE = "…"
```

Sin ellas, *Cargar Datos* sigue funcionando pero la carga vive solo en la
sesión y se pierde al reiniciar; la propia página lo dice.

**Preparar la exportación cruda del formulario.** Lo que sale de Google Forms
trae nombres, las respuestas como texto y a quienes dijeron «No» al
consentimiento. Antes de subirlo se pasa por:

```bash
python -m scripts.preparar_docentes "360 - Profesores (respuestas).xlsx" Docentes_codificado.xlsx
```

Descarta las filas sin consentimiento, quita el nombre, codifica los ítems con
sus inversiones, suma los totales por escala, normaliza el colegio y marca en
cada fila la versión del formulario (en marzo de 2026 cambió la escala de
acuerdo de 6 a 5 opciones y desapareció el bloque de bienestar psicosocial). Si
el formulario cambia el orden de las preguntas, el script se detiene en vez de
codificar mal. El archivo resultante es el que se sube.

Para publicar una versión nueva: *Cargar Datos* → subir el archivo → *Procesar y
Cargar* → elegir el conjunto (`docentes` o `cuidadores`), anotar qué cambió y
*Guardar en Supabase y activar*. **Antes de guardar se retiran las columnas que
identifican personas** (nombre, documento, cédula, teléfono, correo, marca
temporal); la pantalla lista cuáles se quitaron. El archivo que queda en Storage
no puede volver a asociarse a nadie.

Para volver a una versión anterior: en la misma página, tabla *Versiones
guardadas* → botón *Activar* en la fila deseada. Solo hay una activa por
conjunto; la nueva se carga en el siguiente arranque (o al recargar la página,
porque el guardado vacía el caché).

## Los dos despliegues

Conviene hacer dos, del mismo repositorio, con distinta configuración.

### A · Para el equipo investigador (privado)

En este modo el investigador ve **toda** la plataforma: Docentes, tendencias,
carga de datos, informes y las dos vistas de estudiantes. La única diferencia
con el modo local es con qué vista abre el módulo de estudiantes. Es deliberado:
quien revisa también va a enseñar la herramienta, y conviene que la conozca
entera. El candado es para los actores que no son del equipo.

| Ajuste | Valor |
|---|---|
| Rama | `feature/vistas-investigador-comunidad` (o `main` tras la fusión) |
| Archivo principal | `main.py` |
| Visibilidad | privada, con lista de correos en *Settings → Sharing* |

Secretos (*Advanced settings → Secrets*):

```toml
OBS360_MODO = "investigador"
SUPABASE_URL = "https://nkjyuviycatgrzqjnsoa.supabase.co"
SUPABASE_KEY = "clave-anon"
OBS360_CARGA_EMAIL = "usuario de carga (ver «Versiones del archivo de docentes»)"
OBS360_CARGA_CLAVE = "su contraseña"
```

Quien entre aterriza en la vista de investigación, con las ocho pestañas, las
tablas exportables y el ZIP de la corrida, y puede moverse al resto de la
plataforma desde la navegación.

### B · Para colegios, familias y municipio (público)

```toml
OBS360_MODO = "comunidad"
SUPABASE_URL = "https://nkjyuviycatgrzqjnsoa.supabase.co"
SUPABASE_KEY = "clave-anon"
```

En este modo el punto de entrada corta antes de importar la vista de
investigación, el cargador de archivos, el chat, los informes y el panel
técnico: no están escondidos, no existen en esa ejecución. `?debug=1` no abre
nada. Un valor mal escrito en `OBS360_MODO` cae en `comunidad`, el más
restrictivo.

En el menú solo aparecen las páginas públicas: Estudiantes 360 y, cuando se
habilite, Cuidadores 360. Con más de una hay un selector de página; con una sola
no hay menú. El título de la pestaña es «Observatorio 360 · Comunidad».

Acepta `?colegio=LauV` para dar a cada colegio su propio enlace.

**Este despliegue no debería abrirse antes de que exista la ruta de derivación
acordada con los colegios.** Con un 25 % de estudiantes que reportan pensar en
la muerte con frecuencia o siempre, encontrar casos sin tener a dónde remitirlos
es peor que no medir.

### Lo que nunca va en los secretos del despliegue

`SUPABASE_SERVICE_KEY` y `SUPABASE_ACCESS_TOKEN`. La primera escribe en la base;
la segunda administra el proyecto. Las dos se quedan en el equipo de quien
publica.

`OBS360_CLAVE_HMAC` tampoco: **nunca va en los secretos del despliegue**
(ni en `.streamlit/secrets.toml` de Streamlit Cloud, ni en variables de
entorno de un servidor público). Es la clave local con la que Cuidadores 360
(y la triangulación de la fase 5) convierte nombres en seudónimos HMAC (`C…`
para el cuidador, `N…` para el niño). Solo la necesita la máquina que procesa
los formularios; un despliegue nunca lee archivos crudos.

- **Los seudónimos `C…` y `N…` nunca van a Supabase** ni a ningún archivo
  publicado o compartido: solo existen en memoria, en la máquina local. Lo que
  se publica son agregados.
- **Respaldo privado de la clave.** Si se pierde, se puede crear otra y la
  aplicación sigue funcionando, pero los seudónimos ya no se pueden
  reproducir: el mismo nombre da otro `C…`/`N…`, así que no se pueden enlazar
  cuidadores ni niños con cargas anteriores (por ejemplo, entre olas o en la
  triangulación de la fase 5). Guarde una copia en un gestor de contraseñas o
  bóveda privada del equipo de investigación, nunca en el repositorio, en un
  correo ni en los secretos del despliegue.

## Pasos

1. **Subir y aprobar la corrida.** Desde la máquina que tiene los formularios:

   ```bash
   python -m src.estudiantes.publicar --notas "qué cambió"
   ```

   Queda con `publicada = false`. Se aprueba en el SQL Editor de Supabase:

   ```sql
   UPDATE obs360.corridas SET publicada = true WHERE id = <id nuevo>;
   ```

   Sin esto, la aplicación desplegada no muestra ninguna cifra. La corrida 4
   (803 filas, secundaria 943 y primaria 282) es la aprobada; la siguiente
   añade los resultados por colegio y por grado.

2. **Subir la rama a GitHub.**

   ```bash
   git push -u origin feature/vistas-investigador-comunidad
   ```

3. **Crear la app** en share.streamlit.io: *New app* → este repositorio → rama →
   `main.py` → pegar los secretos del bloque A o B → *Deploy*.

4. **Invitar a quien deba revisar** (despliegue A), en *Settings → Sharing*.

5. **Comprobar** que la app dice «Fuente: corrida publicada» y que el N coincide
   con 943 y 282.

**Después de fusionar a `main`, haz siempre *Manage app → Reboot app*.** Si no,
la aplicación puede quedar con módulos viejos en memoria.

## Publicar alertas

Mientras no se publique una corrida nueva, el despliegue sigue con la tarjeta de
muerte y sin panel de alertas.

`--publicar-ya` **no sube** las filas `alerta` y `alerta_grupo` mientras
`alertas_catalogo.TEXTOS_APROBADOS` y `RUTAS_VALIDADAS` no estén en `True`:
avisa, publica el resto y el panel no aparece en público. `--ensayo` las deja en
el JSON y avisa. Una corrida subida sin `--publicar-ya` sí las guarda (oculta):
no se abre a mano antes de la aprobación.

1. El equipo aprueba textos, umbrales y rutas. **Solo entonces** se ponen en
   `True` `alertas_catalogo.TEXTOS_APROBADOS` y `RUTAS_VALIDADAS` (un commit
   aparte, nunca antes de esa aprobación).
2. Correr la migración `2026-10-07c` (SQL Editor → Run).
3. `python -m src.estudiantes.publicar --ensayo` y revisar (tiene que salir con
   código 0 y ya sin el aviso de alertas no aprobadas).
4. Publicar con `--publicar-ya`.
5. «Reboot app».
6. Los mensajes por rol de las alertas se suben a `obs360.mensajes` en un paso
   aparte, cuando el equipo apruebe los textos.

## Vista previa para el equipo

Sirve para que el equipo revise en el despliegue **privado** la última corrida
**oculta** (subida sin `--publicar-ya`) de cada módulo antes de aprobarla: el
panel de alertas de Estudiantes y la vista de comunidad de Cuidadores con sus
señales, aunque los textos y las rutas todavía no estén aprobados. Lo público no
cambia: la clave anon sigue viendo solo la última corrida publicada de cada
módulo.

**Cómo funciona.** Cuando la página lee de Supabase (no hay archivos en disco) y
existe una corrida oculta más nueva que la publicada, la barra lateral muestra
el interruptor «Vista previa: corrida en revisión (N)», encendido por defecto en
el modo `investigador` (apagado en `completo`). Encendido, la página lee esa
corrida con el usuario de carga y pone arriba una franja: «Vista previa para el
equipo: esta corrida no está publicada; los textos de alertas y de Cuidadores
son provisionales y están pendientes de aprobación. Lo público sigue mostrando
la corrida X.» También aparece el aviso interno «ruta pendiente de validación».
Apagado, la página muestra lo publicado, como siempre. Las banderas
`TEXTOS_APROBADOS` / `RUTAS_VALIDADAS` siguen siendo la puerta de lo público y
de `--publicar-ya`; la vista previa no las toca.

**Qué necesita.**

1. Ningún secreto nuevo: los que el despliegue privado ya tiene
   (`OBS360_CARGA_EMAIL` / `OBS360_CARGA_CLAVE`, del usuario con
   `app_metadata.obs360_rol = 'cargador'`, más `SUPABASE_URL` / `SUPABASE_KEY`).
   El despliegue público no los tiene y en modo `comunidad` el módulo
   `src/core/vista_previa.py` ni se importa.
2. La migración `supabase/migraciones/2026-10-10-vista-previa-cargador.sql`
   aplicada (SQL Editor → Run). Da al cargador **solo lectura** de todas las
   corridas y sus resultados. Sin ella el interruptor no aparece: el cargador
   no ve ninguna corrida oculta.
3. «Reboot app» después de fusionar.

**Cómo dejar una corrida en revisión** (en la máquina que procesa, con
`SUPABASE_SERVICE_KEY`):

```bash
python -m src.estudiantes.publicar --notas "revisión equipo"      # sin --publicar-ya
python -m src.cuidadores.publicar --notas "revisión equipo"       # sin --publicar-ya
```

Sin `--publicar-ya` la corrida queda oculta **con** sus filas de alertas
(estudiantes) y de señales del adulto (cuidadores), aunque los textos no estén
aprobados; el despliegue del equipo la muestra en hasta dos minutos (o al
recargar la sesión). No se abre a mano con `UPDATE … publicada = true`: cuando
el equipo apruebe, se ponen las banderas en `True` (commit aparte) y se publica
de nuevo con `--publicar-ya`, como en «Publicar alertas».

## Qué esperar del arranque

La primera carga tarda unos segundos: lee la corrida completa y rearma las
tablas. Después queda en caché mientras el proceso viva. Streamlit Community
Cloud duerme las apps sin uso; la siguiente visita las despierta, con la misma
espera.

`requirements.txt` incluye `chromadb`, que es pesado y solo lo necesita el chat.
Si la instalación en el despliegue tarda demasiado o falla, se puede quitar: en
los modos `comunidad` e `investigador` la aplicación nunca importa el chat.

## Dónde viven los datos fuente

Los archivos con respuestas individuales no están en el repositorio: viven en
la carpeta hermana `../datos_fuente_360` (subcarpetas `estudiantes`, `docentes`,
`cuidadores`), o en la que diga la variable `OBS360_DATOS_DIR`. El módulo
`src/core/rutas.py` es el único que lo sabe; la aplicación local, el publicador
de estudiantes y las pruebas le preguntan a él. En el despliegue esa carpeta no
existe y la aplicación lee Supabase, que es lo previsto.

**Cuidadores 360 (fases 4a y 4b).** En local (archivo
`cuidadores/Cuidando al Cuidador … .xlsx` y clave `OBS360_CLAVE_HMAC`) la
página tiene dos vistas, como Estudiantes: comunidad (colegio, familia,
municipio) e investigadores (con el filtro de ola, que nunca se publica). Sin
archivo, la página lee la corrida publicada de cuidadores (solo agregados de
todas las olas); sin corrida dice «Cuidadores aún no está publicado».

Publicar (en la máquina que procesa, con la clave):

```bash
python -m src.cuidadores.publicar --ensayo --salida /tmp/lote_cuidadores.json   # revisar
python -m src.cuidadores.publicar --notas "cuidadores" --publicar-ya
```

`--ensayo` sale con código 2 si la auditoría encuentra algo. Mientras
`comunidad_catalogo.TEXTOS_APROBADOS` y `RUTAS_VALIDADAS` sean False,
`--publicar-ya` no sube las filas de las señales del adulto. Publicar
cuidadores solo cierra las corridas viejas de cuidadores: la de estudiantes no
se toca. Informes para imprimir: `python -m scripts.generar_informes_cuidadores`
(audita antes de escribir).

En el despliegue público la página **solo aparece** cuando se cumplen las dos
llaves, y en este orden:

1. El equipo aprueba los textos y la ruta de atención.
2. Solo después de esa aprobación, un commit propio pone en `True`
   `comunidad_catalogo.TEXTOS_APROBADOS` y `RUTAS_VALIDADAS` (las dos).
3. Con las dos banderas ya en `True`, se publica la corrida con
   `--publicar-ya`. Una corrida publicada antes no trae las filas de las
   señales del adulto: hay que volver a publicarla.
4. Solo entonces, otro commit propio pone `navegacion.CUIDADORES_PUBLICO = True`.
   Luego, «Reboot app».

La página pública nunca se muestra sin el panel de señales: si la corrida
publicada no trae sus filas (por ejemplo, se publicó antes del paso 3), dice
«Cuidadores aún no está publicado», igual que sin corrida, y no falla. En
público solo se carga la vista de comunidad
(`cuidadores_comunidad.render_publico`); nunca la carga del formulario, el
pipeline ni la vista de investigadores.

**Triangulación 360 (fase 5)** solo funciona en la máquina que tiene los tres
archivos (estudiantes, cuidadores y docentes, de preferencia el codificado por
`scripts/preparar_docentes.py`) y la clave `OBS360_CLAVE_HMAC`. Las díadas
niño–cuidador nunca salen de esa máquina y nada de la triangulación sube a
Supabase. En el despliegue del equipo la página explica que la capa por
colegio necesitará los agregados publicados de cuidadores (fase 4b); en el
público no aparece en el menú ni se importa.

## Antes de dar por terminado

- Revocar el token de acceso de Supabase de la sesión de trabajo.
- Fusionar la rama a `main` y apuntar el despliegue ahí.

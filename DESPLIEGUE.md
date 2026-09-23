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

En este modo el investigador ve **toda** la plataforma: dashboard, tendencias,
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

Acepta `?colegio=LauV` para dar a cada colegio su propio enlace.

**Este despliegue no debería abrirse antes de que exista la ruta de derivación
acordada con los colegios.** Con un 25 % de estudiantes que reportan pensar en
la muerte con frecuencia o siempre, encontrar casos sin tener a dónde remitirlos
es peor que no medir.

### Lo que nunca va en los secretos del despliegue

`SUPABASE_SERVICE_KEY` y `SUPABASE_ACCESS_TOKEN`. La primera escribe en la base;
la segunda administra el proyecto. Las dos se quedan en el equipo de quien
publica.

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

## Qué esperar del arranque

La primera carga tarda unos segundos: lee la corrida completa y rearma las
tablas. Después queda en caché mientras el proceso viva. Streamlit Community
Cloud duerme las apps sin uso; la siguiente visita las despierta, con la misma
espera.

`requirements.txt` incluye `chromadb`, que es pesado y solo lo necesita el chat.
Si la instalación en el despliegue tarda demasiado o falla, se puede quitar: en
los modos `comunidad` e `investigador` la aplicación nunca importa el chat.

## Antes de dar por terminado

- Sacar los CSV de la raíz del repositorio a una carpeta fuera del proyecto.
  Están ignorados por git, pero su sitio no es este.
- Revocar el token de acceso de Supabase de la sesión de trabajo.
- Fusionar la rama a `main` y apuntar el despliegue ahí.

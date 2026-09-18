# Supabase · Observatorio 360

Estado al 18 de septiembre de 2026.

| Qué | Valor |
|---|---|
| Organización | LaSabana |
| Proyecto | `nkjyuviycatgrzqjnsoa` · us-west-2 · Postgres 17 |
| URL | `https://nkjyuviycatgrzqjnsoa.supabase.co` |
| Estado | activo (estaba pausado; se reactivó) |
| Esquema de estudiantes | `obs360`, aplicado y verificado |

## El principio

**A Supabase solo suben resultados agregados.** Los dos CSV de estudiantes traen
nombre y respuesta a respuesta sobre salud mental de menores de edad: no salen de
la máquina de quien procesa. Lo que se publica es lo que ya se puede mostrar en
pantalla, con un mínimo de 10 estudiantes por grupo.

No es una preferencia de estilo. El riesgo real no es que alguien vea un
promedio, es que alguien reconstruya el caso de un estudiante concreto cruzando
colegio, grado, sexo y edad. Con agregados y el mínimo por grupo, eso no se puede
hacer ni con acceso total a la base.

## Lo que quedó montado

### Esquema `obs360`
- **`corridas`** — una fila por publicación, con la versión del análisis, el N de
  cada nivel y una bandera `publicada`. Una corrida entra **oculta**; se abre
  cuando el equipo la aprueba.
- **`resultados`** — los agregados: una fila por nivel, grupo, tipo e indicador,
  con su N, su valor, su intervalo de confianza y un `detalle` en JSONB.
- **`mensajes`** — los textos de la vista comunidad, con quién los revisó y
  cuándo. Se versionan aquí para que el equipo pueda corregirlos sin tocar código.
- **`ultima_corrida`** y **`resultados_vigentes`** — vistas con
  `security_invoker`, para que respeten las políticas de quien consulta en vez de
  saltárselas.

### Seguridad, verificada contra la base
| Control | Estado |
|---|---|
| RLS activo en las tres tablas nuevas | sí |
| Políticas de lectura para el rol anónimo | solo de corridas con `publicada = true` |
| Políticas de escritura para el rol anónimo | **ninguna** |
| Concesiones `INSERT/UPDATE/DELETE` a `anon` en `public` y `obs360` | **ninguna** |
| Tablas sin RLS en `public` y `obs360` | ninguna |
| `CHECK` que rechaza filas con `n < 10` | probado: rechaza una fila con n = 3 |
| `CHECK` que rechaza identificadores con forma `E########` | activo |

Escribir exige la clave `service_role`, que se queda en el equipo de quien
publica y **nunca se despliega**.

### Lo que se corrigió de lo que ya existía
La tabla `processed_data` tenía **dos** políticas que permitían inserción
anónima, con nombres distintos (`Allow anonymous inserts` y `Permitir inserción
anónima`). Cualquiera con la clave que viaja en el cliente podía escribir en
ella. El script las elimina recorriendo `pg_policies`, sin depender del nombre, y
revoca los permisos de escritura. La lectura queda intacta, que es lo que la
aplicación necesita.

## Cómo publicar una corrida

```bash
# 1. Ensayo: no toca la red, deja el lote en un JSON para revisarlo
python -m src.estudiantes.publicar --ensayo --salida /tmp/lote.json

# 2. Publicación (exige SUPABASE_URL y SUPABASE_SERVICE_KEY en el entorno)
export SUPABASE_URL="https://nkjyuviycatgrzqjnsoa.supabase.co"
export SUPABASE_SERVICE_KEY="$(python -c "import tomllib;print(tomllib.load(open('.streamlit/secrets.toml','rb'))['SUPABASE_SERVICE_KEY'])")"
python -m src.estudiantes.publicar --notas "primera carga"
```

La corrida queda **oculta**. Para abrirla al público, en el SQL Editor:

```sql
UPDATE obs360.corridas SET publicada = true WHERE id = <id de la corrida>;
```

El último ensayo dio **797 filas agregadas**, con un N mínimo de 15 en el lote
frente a un umbral de 10.

### Las tres guardas antes de subir
1. `aplanar` construye las filas solo desde tablas ya agregadas del objeto
   `Analisis`; nunca toca `Analisis.datos`.
2. `verificar` **rechaza el lote completo** si aparece un grupo con n < 10, una
   columna de identificación o algo con forma de identificador de estudiante.
   Falla el lote entero y no la fila: si una guarda salta hay un error de
   programación, y publicar «lo que se pueda» lo esconde.
3. La base tiene el `CHECK` y no da escritura al rol anónimo, así que rechazaría
   el error aunque las dos guardas anteriores fallaran.

Están probadas en `tests/test_estudiantes_publicar.py`, incluida la verificación
de que ningún nombre del dataset ni ningún identificador derivado aparece en el
lote.

## Secretos

Todo vive en `.streamlit/secrets.toml`, que está en `.gitignore` y se verificó
que nunca entró al historial de git.

| Clave | Para qué | Se despliega |
|---|---|---|
| `SUPABASE_URL` | endpoint del proyecto | sí |
| `SUPABASE_KEY` | clave `anon`, solo lectura de lo publicado | sí |
| `SUPABASE_SERVICE_KEY` | publicar resultados | **no** |
| `SUPABASE_ACCESS_TOKEN` | administrar el proyecto (API de gestión) | **no** |
| `YOUR_API_KEY` | Gemini, para el chat | sí |

El token de acceso de esta sesión es temporal: conviene **revocarlo** en
`Supabase → Account → Access Tokens` cuando termine el trabajo.

## Estado de la carga

**Corrida 2**, versión `2026-09-18-3a83c4639ca7`: 797 filas agregadas
(secundaria 943, primaria 282) y 20 mensajes por rol. Está **sin aprobar**, y se
verificó que la puerta funciona:

| Con la corrida sin aprobar | Resultado |
|---|---|
| Clave pública leyendo `corridas` | 0 filas |
| Clave pública leyendo `resultados` | 0 filas |
| Clave pública intentando escribir | HTTP 401 |
| Clave de servicio leyendo `resultados` | 797 filas |

Para aprobarla, en el SQL Editor:

```sql
UPDATE obs360.corridas SET publicada = true WHERE id = 2;
```

Desde ese momento la clave pública ve las 797 filas, y solo esas: una corrida
posterior vuelve a entrar oculta.

> El esquema `obs360` tuvo que añadirse a los esquemas expuestos de la API REST
> (*Settings → API → Exposed schemas*), y el rol `service_role` necesitó permisos
> propios sobre él. Las dos cosas están en el script.

## Cómo se abre la vista de comunidad a quien tenga que verla

Hay dos puertas distintas y conviene no confundirlas.

**La puerta del contenido** es la bandera `publicada` de la corrida. Mientras esté
en false, la aplicación no muestra ninguna cifra, ni siquiera desplegada en
público. Es reversible en una línea de SQL.

**La puerta del acceso** es el modo de despliegue, en `src/core/modo.py`:

| `OBS360_MODO` | Qué existe en esa ejecución |
|---|---|
| `completo` (por defecto) | todo; estudiantes abre en la vista de comunidad |
| `investigador` | todo; estudiantes abre en la vista de investigación |
| `comunidad` | **solo** la vista de estudiantes para colegios, familias y municipio |

En modo `comunidad` el punto de entrada corta **antes** de importar la vista de
investigación, el cargador de archivos, el chat, los informes y el panel técnico:
no están escondidos, no existen. Un visitante no llega a ellos ni escribiendo la
URL, y `?debug=1` no abre nada. Un valor mal escrito en la configuración cae en
`comunidad`, el más restrictivo, nunca en el más permisivo.

### Los tres caminos, según quién tenga que ver

1. **Equipo investigador, rectores y orientación escolar.** Un despliegue
   privado en Streamlit Community Cloud con `OBS360_MODO = "investigador"` y la
   lista de correos autorizados (*Settings → Sharing → invite viewers*). Entran
   con su correo; no hay contraseñas que repartir. Ven la plataforma completa y
   aterrizan en la vista de investigación.
2. **Cada colegio, su propio enlace.** El mismo despliegue público admite
   `?colegio=LauV`, que deja ese colegio preseleccionado. Un código inexistente o
   un colegio con menos de 10 respuestas se ignora, así que el parámetro no sirve
   para sondear la base. Es comodidad, no seguridad: cualquiera puede cambiar el
   código y ver a otro colegio, y eso es aceptable porque todo lo que se muestra
   es agregado.
3. **Familias.** Lo más práctico y lo más seguro es que **no** necesiten entrar:
   la vista de comunidad genera un informe de una página descargable, y el colegio
   lo reparte. Nadie tiene que crear una cuenta para leer cuatro cifras y una ruta
   de atención. Si aun así se quiere dar acceso, el despliegue público con
   `OBS360_MODO = "comunidad"` ya es seguro por construcción.

### Desplegar en Streamlit Community Cloud

Conectar el repositorio, apuntar a `main.py` y pegar en *Advanced settings →
Secrets* **solo** esto:

```toml
OBS360_MODO = "comunidad"        # o "investigador" para el despliegue del equipo
SUPABASE_URL = "https://nkjyuviycatgrzqjnsoa.supabase.co"
SUPABASE_KEY = "clave-anon"
YOUR_API_KEY = "clave-de-gemini"  # opcional; el modo comunidad no usa IA
```

La clave `service_role` y el token de acceso **no** van ahí. Nunca.

## Lo que falta

1. **Aprobar la corrida 2** (la línea de SQL de arriba). Es tu decisión en persona.
2. **La ruta de derivación con los colegios.** El plan aprobado la puso como
   condición previa para abrir la vista de comunidad. Con un 25 % de estudiantes
   que reportan pensar en la muerte con frecuencia o siempre, encontrar casos sin
   tener a dónde remitirlos es peor que no medir.
3. **Sacar los CSV de la raíz del repositorio.** Están ignorados por git, pero
   contienen nombres de menores: su sitio es una carpeta fuera del proyecto, como
   ya se hizo con los datos de cuidadores.
4. **Revocar el token de acceso** de esta sesión cuando termine el trabajo.

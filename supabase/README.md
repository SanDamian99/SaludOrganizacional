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
| Políticas de lectura para el rol anónimo | solo la **última** corrida con `publicada = true` de cada módulo (función `obs360.es_ultima_publicada`, desde la migración 2026-10-07) |
| Lectura de corridas ocultas | solo el usuario de carga (`obs360.es_cargador()`, migración 2026-10-10), para la vista previa del equipo |
| Triangulación 360 (`modulo = nivel = 'triangulacion'`) | **nunca** para anon ni para otros autenticados (`obs360_interno.es_publica`, migración 2026-10-10b); solo el usuario de carga, aunque la corrida esté publicada |
| Políticas de escritura para el rol anónimo | **ninguna** |
| Concesiones `INSERT/UPDATE/DELETE` a `anon` en `public` y `obs360` | **ninguna** |
| Tablas sin RLS en `public` y `obs360` | ninguna |
| `CHECK` que rechaza filas con `n < 10` | probado: rechaza una fila con n = 3 |
| `CHECK` que rechaza identificadores con forma `E########`, `C########` o `N########` | activo |

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

La corrida queda **oculta**. Para abrirla al público, lo seguro es publicarla
directamente con `--publicar-ya` (se abre la nueva y se cierran las demás del
módulo):

```bash
python -m src.estudiantes.publicar --notas "fase 1" --publicar-ya
```

o, si se quiere revisar antes, aprobar **esa misma corrida nueva** en el SQL
Editor (`UPDATE obs360.corridas SET publicada = true WHERE id = <id de la
corrida recién creada>;`).

**Alertas de grupo.** Mientras el equipo no apruebe textos y rutas
(`alertas_catalogo.TEXTOS_APROBADOS` y `RUTAS_VALIDADAS`, que solo se ponen en
`True` después de esa aprobación), `--publicar-ya` no sube las filas `alerta`
ni `alerta_grupo`: avisa y publica el resto, y el panel no aparece en público.
`--ensayo` las deja en el JSON con un aviso. Una corrida subida sin
`--publicar-ya` sí las guarda: **no aprobarla a mano** con el `UPDATE` de arriba
antes de esa aprobación; volver a publicar con `--publicar-ya`.

> **Atención: nunca aprobar una corrida vieja.** Las corridas anteriores a la
> fase 1 (la 2 incluida) se generaron **sin** la base publicable por
> colegio×grado ni el enmascaramiento todo-o-nada por columna: sus cifras
> permiten restas entre grupos que pueden aislar a menos de 10 estudiantes.
> Aprobar una de ellas reabre ese riesgo.

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

> **Atención: la corrida 2 NO se debe aprobar.** Es anterior a la base
> publicable y al enmascaramiento por columna de la fase 1. En su lugar:
>
> 1. Correr la migración `supabase/migraciones/2026-10-07-modulo-y-ultima-corrida.sql`
>    (o re-ejecutar `estudiantes_schema.sql`, que ya la incluye).
> 2. Publicar una corrida **nueva**:
>    `python -m src.estudiantes.publicar --notas "fase 1" --publicar-ya`
>    (o publicarla sin `--publicar-ya` y aprobar esa corrida nueva tras revisarla).
>
> Nunca aprobar corridas viejas.

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

## Migración: corridas por módulo (7 oct 2026)

Archivo: `supabase/migraciones/2026-10-07-modulo-y-ultima-corrida.sql`.

- **Cuándo:** correrla en el SQL Editor **antes** de desplegar esta rama.
- **Qué hace:** admite el nivel `cuidadores`, extiende el CHECK de identificadores
  a `E`/`C`/`N`, y hace que el público (y las vistas `ultima_corrida` y
  `resultados_vigentes`) vea solo la última corrida publicada **de cada módulo**,
  no una sola global. Añade `modulo` a `mensajes`.
- **Verificar:** `SELECT modulo, id, creada_en FROM obs360.ultima_corrida;` debe
  dar una fila por módulo con corrida publicada (hoy, solo `estudiantes`).
- **Compatibilidad:** el código funciona con o sin la migración, porque el filtro
  `modulo = 'estudiantes'` usa una columna que ya existe. Sin ella, simplemente no
  hay aislamiento entre módulos en el lado de la base.

## Migración: alertas sin conteo de casos (7 oct 2026, c)

Archivo: `supabase/migraciones/2026-10-07c-alertas-sin-casos.sql`.

- **Qué hace:** ninguna fila nueva puede guardar un conteo de casos (`casos`,
  `k_bajo`, `k_alto`) en `detalle`, y el estado de una alerta solo existe donde
  hay porcentaje.
- **`NOT VALID`:** las corridas viejas todavía guardan `casos` en las filas
  «corte»; no se validan ni se tocan. La restricción rige para toda fila nueva.
  Por eso `ALTER TABLE … VALIDATE CONSTRAINT` fallará mientras queden filas
  viejas con `casos`: primero hay que borrar esas corridas viejas (sus filas de
  `resultados` y la corrida). Nunca hacer `UPDATE` sobre filas viejas de
  `resultados` para que pasen.
- **Opcional pero recomendada:** publicar funciona sin ella, porque
  `publicar.verificar` ya rechaza esos campos en Python; la migración es la
  última barrera en la base.

## Cuidadores 360 (fase 4b): sin migración nueva

Publicar cuidadores no necesita ningún cambio en la base: usa las tablas de
siempre con `modulo = 'cuidadores'` y `nivel = 'cuidadores'` (que el CHECK ya
admite desde la migración 2026-10-07). El marco (cuidador o niño) va en
`detalle.marco`. Requisitos: las migraciones 2026-10-07 y 2026-10-07b aplicadas
(la última corrida publicada **por módulo**); la 2026-10-07c es la última
barrera contra conteos de casos y se recomienda antes de la primera corrida.

- **Verificar después de publicar:** `SELECT modulo, id, creada_en FROM
  obs360.ultima_corrida;` debe dar una fila de `estudiantes` y otra de
  `cuidadores`. La de estudiantes no cambia al publicar cuidadores.

## Migración: vista previa del cargador (10 oct 2026)

Archivo: `supabase/migraciones/2026-10-10-vista-previa-cargador.sql` (ya
incluida en `estudiantes_schema.sql`).

- **Qué hace:** añade dos políticas `FOR SELECT TO authenticated USING
  (obs360.es_cargador())`, en `corridas` y en `resultados`: el usuario de carga
  (`app_metadata.obs360_rol = 'cargador'`, solo en los secretos del despliegue
  privado) lee cualquier corrida, publicada u oculta. Es lo que usa la vista
  previa del equipo (`src/core/vista_previa.py`, ver DESPLIEGUE.md).
- **Qué no cambia:** las políticas públicas (`es_ultima_publicada`) siguen
  igual, así que anon y cualquier otro usuario autenticado solo ven la última
  corrida publicada de cada módulo. No se crea ninguna política de escritura.
  `mensajes` no se toca: la aplicación no la lee.
- **Verificar:** `SELECT tablename, policyname, cmd, roles FROM pg_policies
  WHERE schemaname = 'obs360' AND tablename IN ('corridas', 'resultados');`
  debe listar, por tabla, la política pública y la del cargador, ambas `SELECT`.
- **Sin ella:** la aplicación funciona igual que antes; el interruptor de vista
  previa simplemente no aparece.

## Migración: triangulación solo para el equipo (10 oct 2026)

Archivo: `supabase/migraciones/2026-10-10b-triangulacion-privada.sql` (ya
incluida en `estudiantes_schema.sql`). Requiere 2026-10-07b y 2026-10-10.

- **Qué hace:** (1) el CHECK `resultados_nivel_valido` admite
  `'triangulacion'`; (2) crea `obs360_interno.es_publica(id)` = última corrida
  publicada de su módulo **y** módulo distinto de `triangulacion` (SECURITY
  DEFINER, `search_path` fijo, dueño `postgres`, en el esquema que la API REST
  no expone, como `es_ultima_publicada`); (3) recrea las dos políticas públicas
  con `es_publica`, y la de `resultados` además exige `nivel <> 'triangulacion'`.
- **Resultado:** la clave pública (anon) y cualquier autenticado que no sea el
  cargador nunca leen filas de triangulación, ni siquiera de una corrida
  publicada. El usuario de carga (despliegue privado) las lee con su política
  de la migración 2026-10-10, que no cambia.
- **Qué no cambia:** Estudiantes y Cuidadores se leen igual que antes (para
  ellos `es_publica` = `es_ultima_publicada`). No se crea ninguna política de
  escritura. Los CHECK de n ≥ 10, identificadores y conteos valen también para
  las filas de triangulación.
- **Verificar:** como anon, `SELECT count(*) FROM obs360.resultados WHERE
  nivel = 'triangulacion';` debe dar 0 aunque haya una corrida publicada;
  `pg_policies` debe mostrar `es_publica` en las dos políticas públicas.
- **Sin ella:** `python -m src.triangulacion.publicar` falla en el CHECK de
  `nivel` y deshace la corrida; nada queda a medias. **No publicar triangulación
  sin esta migración.**

## Lo que falta

1. **Correr la migración y publicar una corrida nueva** de la fase 1
   (`python -m src.estudiantes.publicar --notas "fase 1" --publicar-ya`, o
   aprobar esa corrida nueva tras revisarla). Es tu decisión en persona.
   **No aprobar la corrida 2 ni ninguna corrida vieja.**
2. **La ruta de derivación con los colegios.** El plan aprobado la puso como
   condición previa para abrir la vista de comunidad. Con un 25 % de estudiantes
   que reportan pensar en la muerte con frecuencia o siempre, encontrar casos sin
   tener a dónde remitirlos es peor que no medir.
3. **Sacar los CSV de la raíz del repositorio.** Están ignorados por git, pero
   contienen nombres de menores: su sitio es una carpeta fuera del proyecto, como
   ya se hizo con los datos de cuidadores.
4. **Revocar el token de acceso** de esta sesión cuando termine el trabajo.

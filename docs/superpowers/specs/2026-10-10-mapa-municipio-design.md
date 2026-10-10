# Mapa del municipio — diseño y plan

Fecha: 10 de octubre de 2026 · Estado: **propuesta, pendiente de aprobación**

Protagonista: **el mapa** (fases A y B). Complementos, en este orden y sin
protagonismo: **avance de datos** (C), **video** (D) y **Supabase** (E).

## 1. Por qué

La vista de municipio hoy son tarjetas y tablas. Falta lo que un secretario de
educación o un rector entiende de un vistazo: **dónde** está cada colegio y
**dónde todavía no hay cifras**. El mapa no calcula nada nuevo. Dibuja lo que la
plataforma ya publica.

Regla heredada de la arquitectura: **las vistas no calculan**. El mapa lee el
mismo `Analisis` (de los CSV en local o de la corrida publicada en el
despliegue) y respeta `grupos_visibles()`. Si una cifra sale como «—» en las
tarjetas, sale igual en el mapa.

## 2. Qué hay hoy (verificado el 10 de octubre)

- Corrida publicada 7 (estudiantes). Cifras por colegio: primaria CdP 41, JJC 28,
  La Balsa 84, LauV 183, SJMEB 14; secundaria JJC 297, La Balsa 137, LauV 435,
  SJMEB 63. **Cinco colegios con cifras de 13 en la tabla** (`core/colegios.py`).
- Cada colegio trae 15–17 indicadores (`grupo`): SDQ, MSPSS, PSSM, ARI, TD, ERQ y,
  en secundaria, RCADS.
- Cuidadores no está publicado (apagado hasta la aprobación del equipo).
- El repo **no tiene coordenadas** de colegios ni geometría del municipio.

## 3. Diseño del mapa

### 3.1 Dónde vive

Sección «Mapa de Chía» en la página Estudiantes 360, vista comunidad, para los
roles **municipio** y **colegio** (`ve_colegios(rol)`). **Familia no lo ve**:
no ve desagregación por colegio, y el mapa es una desagregación por colegio.
Va debajo del panel de señales y encima de las tarjetas.

```
┌─ Mapa de Chía ─────────────────────────────────────────────────────┐
│ Mostrar:  (●) Respuestas   ( ) Sentirse parte   ( ) Apoyo social   │
│ Nivel:    (●) Secundaria   ( ) Primaria                            │
│                                                                    │
│  ┌──────────────────────────────────────┐   Leyenda                │
│  │      contorno del municipio          │   ● 100 o más            │
│  │        ◯ Fagua      ● LauV           │   ● 30 a 99              │
│  │   ◯ Fonquetá          ● JJC          │   ● 10 a 29              │
│  │            ● La Balsa                │   ○ Sin cifras todavía   │
│  │   ◯ Fusca      ● SJMEB               │                          │
│  └──────────────────────────────────────┘   Los colores comparan   │
│                                             con el resto del        │
│  Al pasar el cursor por un colegio:         municipio. No es un     │
│  nombre · respuestas · cifra e intervalo    ranking.                │
│  · «similar / por encima / por debajo       Nota de cifras          │
│    del resto del municipio»                 ocultas (la de siempre) │
└────────────────────────────────────────────────────────────────────┘
```

### 3.2 Capas

| Capa | Qué dibuja | Tamaño | Color |
|---|---|---|---|
| **Respuestas** (por defecto) | `n` publicado del colegio, en el nivel elegido | por tramo: 10–29, 30–99, 100+ | un solo tono |
| **Sentirse parte** (`PSSM_Total`) | media del colegio con su IC | fijo | un tono, más oscuro = más alto |
| **Apoyo social** (`MSPSS_Total`) | igual | fijo | igual |
| *(después)* **Cuidadores** | estrés y apoyo por colegio | — | solo cuando Cuidadores esté publicado y aprobado |

Las dos capas de cifras muestran factores **protectores**. La capa por defecto
es de cobertura, que no juzga a ningún colegio.

### 3.3 Qué el mapa nunca dibuja

- Bandas del SDQ, RCADS, alertas, pensamientos de muerte, ni nada de «Señales
  para actuar a tiempo». Un colegio coloreado por malestar es un ranking implícito
  y estigmatiza. Hoy además ningún grupo está en «Prioridad».
- Sedes. El punto es **la sede principal del colegio**. La sede sigue siendo un
  detalle solo de investigadores.
- Un número de casos, o una cifra de un grupo oculto.
- Rojo, ni escala semáforo. Un solo tono, con la lectura accesible en gris/azul.

### 3.4 Colegios sin cifra

Colegio presente en la tabla pero sin cifra publicable (los otros 8): círculo
vacío gris con la nota «cifras muy pequeñas para mostrarse sin riesgo de
identificar a alguien» o «sin formulario recibido». Se distinguen los dos casos,
porque no significan lo mismo.

### 3.5 Comparación con el municipio

Al pasar el cursor se muestra el valor del colegio y, al lado, el de todo el
municipio (parámetro `MAPA_MOSTRAR_COMPARACION`). **No hay «por encima / por
debajo»:** el intervalo de confianza por colegio no existe en `por_colegio` y
calcularlo en la vista rompería la regla «las vistas no calculan».

## 4. Enfoques considerados

1. **Plotly interactivo (OpenStreetMap) + figura estática gemela (matplotlib).**
   Recomendado. Plotly ya está en el proyecto. La gemela estática dibuja sobre el
   mismo contorno, sin tiles y sin red, y sirve para el PDF, el informe y el
   video. Para `scatter_map` hay que subir `plotly>=5.24` (**verificar** que esa
   versión lo trae antes de fijar el requisito).
2. **Folium o pydeck.** Más bonito, pero suma una dependencia nueva y complica el
   PDF (hay que renderizar en navegador). Descartado.
3. **Solo imagen estática.** Sin interacción; pierde el «pasar el cursor».
   Descartado para la vista, pero es lo que usamos en PDF y video.

## 5. Datos geográficos

- `src/geo/colegios_geo.csv`: `codigo, lat, lon, fuente, verificado`. Una fila por
  código de `core/colegios.py`. Los códigos son la llave, como en el resto de la
  plataforma.
- `src/geo/chia_limite.geojson`: contorno del municipio, de la capa oficial
  del DANE (MGN), simplificado.
- **Las coordenadas las verifica una persona del equipo** antes de que `verificado`
  pase a `true`; un punto sin verificar no se dibuja. Fuentes candidatas: el
  directorio de establecimientos educativos del MEN y OpenStreetMap. Si una
  coordenada no aparece, se marca a mano con el rector o la Secretaría.
- Es información pública de ubicación de instituciones, no de personas. Aun así,
  no incluye sedes ni direcciones.

## 6. Componentes (cada uno con un solo propósito)

| Archivo | Qué hace | De qué depende |
|---|---|---|
| `src/geo/colegios_geo.py` | Carga CSV y contorno; devuelve solo los puntos verificados | `core/colegios.py` |
| `src/geo/mapa_datos.py` | Arma la tabla del mapa (una fila por colegio: n, valor, IC, estado, comparación) desde un `Analisis`. **No calcula estadística:** lee `por_colegio`/`subgrupos` | `grupos_visibles`, `comparar` |
| `src/geo/mapa_figura.py` | `figura_interactiva(tabla, capa)` (plotly) y `figura_estatica(tabla, capa)` (matplotlib) | `mapa_datos` |
| `src/ui/views/estudiantes_mapa.py` | La sección de Streamlit: selector de capa y nivel, leyenda, notas | las tres anteriores |
| `src/geo/auditoria_mapa.py` | Verifica que ningún punto lleve una cifra oculta, un conteo de casos o un indicador prohibido | `mapa_datos` |

La vista se enchufa en `estudiantes_comunidad.py` con una sola llamada; no se
reescribe lo existente.

## 7. Pruebas

Mismo estilo del repo (`tests/`, datos sintéticos de resultado conocido, más
regresión contra la corrida real que se omite sola si faltan los datos).

- Un colegio con n < 10 sale como «sin cifra», nunca con valor.
- La capa solo acepta indicadores de la lista permitida (cobertura, PSSM, MSPSS);
  pedir SDQ o RCADS falla.
- Rol familia: la sección no se dibuja.
- Punto con `verificado = false`: no se dibuja.
- La auditoría rechaza una tabla del mapa con una cifra de grupo oculto.
- La figura estática se genera sin red.
- Regresión con la corrida 7: 4 colegios con cifra en secundaria, 5 en primaria;
  los demás, vacíos y distinguiendo la causa.
- Navegador (computador y celular): el mapa no desborda y la leyenda es legible.

## 8. Plan por fases

**Fase A — Datos y mapa en la vista (núcleo).**
1. Reunir y verificar coordenadas de los 13 colegios y el contorno del municipio
   (tarea del equipo; yo preparo el CSV con candidatos y fuente).
2. `colegios_geo`, `mapa_datos`, `auditoria_mapa` con sus pruebas.
3. `mapa_figura` (interactiva y estática) y `estudiantes_mapa` en la vista.
4. Revisión en el navegador, en computador y celular.

**Fase B — El mapa fuera de la pantalla.**
1. Figura estática en el informe de la Secretaría y en el de una página.
2. Misma auditoría antes de generar (como ya hacen los informes).
3. Capa de Cuidadores, **detrás de la misma llave** que ya gobierna esa página
   (`cuidadores_publico()`); no se enciende sola.

**Fase C — Avance de datos (apoyo, solo investigadores).**
Pestaña «Avance» en la vista de investigadores de Estudiantes: matriz colegio ×
grado con tres estados (**visible**, **falta n**, **sin formulario**), lista de
corridas (id, fecha, publicada, n por nivel) y los pendientes de datos de la
actualización del 9 de octubre (CdP 6.º y 7.º, JJC 10.º, SJMEB 6.º).
- Se hace en Streamlit con lo que ya está. Lee `corridas` y el `Analisis`.
- **Claude Dashboards no se usa por ahora:** no se confirma conector para
  Postgres/Supabase, y sacar datos por un servicio externo pide una decisión de
  privacidad del equipo. Se revisa de nuevo si confirman el conector, y solo
  sobre agregados de `obs360`.

**Fase D — Video del municipio (apoyo, opcional).**
**Público: la Secretaría de Educación y los rectores.** Es un público externo y
con poder de decisión, no el equipo investigador. Eso fija lo siguiente.

`scripts/generar_video_municipio.py`: lee la última corrida publicada, pasa por la
**misma auditoría del mapa** y renderiza con las figuras estáticas y ffmpeg
(el montaje de `video_assets/build_video.py` ya hace lo parecido).
- **60–90 s, sin audio, con rótulos grandes.** Lo verán en reunión, por correo o
  por WhatsApp, a menudo sin sonido. Formato 16:9 (reunión) y una variante 1:1
  (celular).
- **Guion en tres ideas, para decidir, no para diagnosticar:**
  1. *Dónde hemos escuchado:* el mapa de respuestas, con los colegios sin cifra
     visibles y la causa. Es una invitación a completar, no un reproche.
  2. *Qué protege:* sentirse parte del colegio y el apoyo social, con su lectura
     «los estudiantes que se sienten parte reportan menos malestar».
  3. *Qué puede hacer cada quién:* una acción para el colegio y una para la
     Secretaría, **tomadas de `catalog.MENSAJES`** (`accion_colegio`,
     `accion_municipio`). Texto fijo, revisado por personas; no lo escribe la IA.
- **Lo que no incluye:** alertas, malestar, pensamientos de muerte, cifras de
  grupos ocultos y rutas de atención. Las rutas no se incluyen mientras el equipo
  no las valide (hoy aparece la Línea 106, que es de Bogotá).
- **Lenguaje:** el de la plataforma. «No es un diagnóstico», sin rojo, sin la
  palabra «suicidio».
- **Aprobación (dos llaves, a mano, en un commit propio):** `VIDEO_APROBADO` para
  el guion y que los textos de las acciones estén aprobados. Hasta entonces el
  script solo genera una versión marcada «BORRADOR» para el equipo.
- **Ante rectores, el video nombra a los colegios.** Es coherente con que el rol
  colegio ya ve a los demás (§10), pero conviene que el equipo lo confirme
  explícitamente, porque un video circula con más facilidad que una pantalla.
- **Variante opcional (no entra en la primera entrega):** un video por colegio
  con solo ese colegio y el municipio, como ya hace el informe del colegio.
- Sale a una carpeta fuera del repo. **Motion** (si tienen plan Team) puede pulir
  el acabado sobre ese guion, pero no es requisito ni fuente de cifras.
- Quién lo comparte y cómo (reunión con la Secretaría, correo, WhatsApp de
  rectores) lo decide el equipo; el script no publica nada por sí mismo.

**Fase E — Supabase (apoyo).**
1. Tabla `obs360.colegios_geo` con la misma forma que el CSV, para que el equipo
   corrija coordenadas sin tocar código (como `mensajes`), con RLS de solo
   lectura anónima de filas `verificado`. **Sin PostGIS:** con 13 puntos y sin
   consultas espaciales bastan `lat` y `lon`. Lo reconsideramos solo si se
   quieren polígonos por vereda.
2. Avisos del asesor de seguridad: confirmar que nada usa GraphQL y, si es así,
   deshabilitar `pg_graphql` (corrige los 13 avisos de exposición); revisar qué
   contiene `public.processed_data` antes de decidir.
3. Migración en `supabase/migraciones/`, como las anteriores. **Probarla en una
   rama de Supabase antes de la base real**; crear la rama puede tener costo,
   se confirma antes.

## 8b. Parámetros que decide el equipo

Todo lo que es una **decisión de presentación** va en un solo archivo,
`src/geo/opciones.py`, con valores por defecto prudentes (lo sensible, apagado).
Cambiar uno es un commit de una línea, a mano, igual que `TEXTOS_APROBADOS`.

| Parámetro | Por defecto | Qué controla |
|---|---|---|
| `MAPA_CAPAS` | las tres de estudiantes | Qué capas se ofrecen: `respuestas`, `sentirse_parte`, `apoyo_social` (`cuidadores` llega en la fase B) |
| `MAPA_CAPA_INICIAL` | `"respuestas"` | La que se ve al abrir |
| `MAPA_MOSTRAR_NOMBRES` | `True` | Rótulo con el nombre del colegio junto al punto |
| `MAPA_MOSTRAR_SIN_CIFRA` | `True` | Dibujar los círculos grises de los colegios sin cifra |
| `MAPA_MOSTRAR_CAUSA_SIN_CIFRA` | `True` | Decir por qué no hay cifra (pequeñas / sin formulario) |
| `MAPA_MOSTRAR_COMPARACION` | `True` | Valor de todo el municipio junto al del colegio |
| `MAPA_ROLES` | `("municipio", "colegio")` | Quién ve el mapa |
| `VIDEO_NOMBRES_COLEGIOS` | `False` | El video nombra a los colegios (si no, solo puntos y totales) |
| `VIDEO_ACCIONES` | `True` | La escena «qué puede hacer cada quién» (de `catalog.MENSAJES`) |
| `VIDEO_RUTAS` | `False` | Rutas de atención en el cierre; solo se activa con `RUTAS_VALIDADAS` |
| `VIDEO_VARIANTE_CELULAR` | `True` | También genera la versión 1:1 |
| `VIDEO_SELLO_BORRADOR` | `True` | Marca «BORRADOR» hasta que `VIDEO_APROBADO` sea `True` |
| `VIDEO_APROBADO` | `False` | Llave de publicación del guion |

**Lo que NO es un parámetro** (cambiarlo exige tocar el código y sus pruebas,
a propósito): la lista de indicadores permitidos en el mapa, la supresión de
cifras pequeñas y vecinas, que no se dibujen conteos de casos, alertas,
malestar, sedes ni cifras de grupos ocultos, que familia no vea el mapa, y la
auditoría previa. Un parámetro mal puesto puede cambiar **qué se ve**, nunca
**qué puede delatar a alguien**.

Las pruebas cubren cada combinación relevante: con todo apagado, el mapa y el
video siguen pasando la auditoría.

## 9. Fuera de alcance

- Mapa de malestar o de alertas, por colegio o por vereda.
- Sedes y direcciones.
- Cualquier dato por persona en Dashboards o Motion.
- Compartir fuera de la organización dashboards o videos sin aprobación del equipo.

## 10. Riesgos y decisiones que quedan abiertas

| Tema | Riesgo | Decisión pendiente |
|---|---|---|
| Estigma | Un mapa de colegios se lee como ranking | Confirmar que el equipo acepta solo cobertura y factores protectores |
| Pocos puntos | 5 de 13 colegios tienen cifras; el mapa se verá casi vacío | Es información honesta: mostrar los grises y la causa |
| Coordenadas | Pueden estar mal o no existir | Una persona del equipo las verifica |
| Rol colegio | ¿Debe ver los otros colegios, o solo el suyo y el municipio? | Hoy `ve_colegios` los deja ver todos; mantener |
| Rol familia | Sin mapa | Mantener |
| Video ante rectores | Nombra colegios y puede circular fuera de contexto | El equipo confirma nombres de colegios y canal de difusión; aprobación del guion antes de publicar |
| Video y rutas | Las rutas de atención de Chía no están validadas | El video no las incluye hasta que el equipo las confirme |
| Plotly | La versión para `scatter_map` | Verificar y fijar el requisito |
| Despliegue | Streamlit puede conservar módulos viejos en memoria | Módulos nuevos (`src/geo/`) y Reboot tras fusionar, como dice `navegacion.py` |

## 10b. Coordinación con la otra sesión (vista previa privada)

Otra sesión trabaja en `feature/vista-previa-privada` (módulo `vista_previa`,
lectores con `corrida_id`, migración `2026-10-10-vista-previa-cargador.sql`).
Reglas para no pisarnos:

- **Carpetas separadas.** Esa sesión usa `SaludOrganizacional/`; el mapa usa el
  worktree `SaludOrganizacional-mapa/` en `feature/mapa-municipio`, desde `main`.
  Ninguna sesión hace `git add -A`, commits ni merges en la carpeta de la otra.
- **Solo archivos nuevos:** `src/geo/`, `src/ui/views/estudiantes_mapa.py`,
  `tests/test_mapa_*.py`. La única edición de un archivo compartido es **una
  llamada** al final de `estudiantes_comunidad.py`, y se hace **después** de que
  la otra rama esté fusionada, rebasando sobre `main`.
- **No se tocan** `lectura.py` (estudiantes ni cuidadores), `vista_previa.py` ni
  `supabase/` hasta que esa rama se fusione. La fase E usa un número de migración
  posterior al de ella.
- **El mapa hereda la vista previa sin código extra:** lee por los mismos
  lectores y `Analisis`, así que una corrida no publicada vista con el interruptor
  de vista previa también se ve en el mapa.
- **Una sola base de Supabase.** Ninguna migración corre en la base real sin
  rama de prueba y sin que la otra sesión haya terminado la suya.
- **Si dos sesiones necesitan el mismo archivo,** gana la que ya lo tiene
  abierto; la otra espera o le pide el cambio por mensaje.

## 11. Orden de entrega

A → B → C → D → E. Cada fase deja la plataforma funcionando y es revisable por
separado, en rama propia. C, D y E son independientes entre sí y pueden cambiar
de orden o caer sin afectar el mapa.

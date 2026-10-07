-- ════════════════════════════════════════════════════════════════════════════
-- Observatorio 360 · corridas por módulo y solo la última publicada por módulo
--
-- Ejecutar en Supabase → SQL Editor → Run, ANTES de desplegar la rama.
-- Aditiva e idempotente: se puede volver a ejecutar sin perder datos.
-- Las filas actuales (nivel secundaria/primaria, sin identificadores) cumplen
-- las restricciones nuevas, así que los ADD CONSTRAINT no fallan.
-- ════════════════════════════════════════════════════════════════════════════

-- 1. Niveles: se admite el módulo de cuidadores (fase 4)
ALTER TABLE obs360.resultados DROP CONSTRAINT IF EXISTS resultados_nivel_valido;
ALTER TABLE obs360.resultados ADD CONSTRAINT resultados_nivel_valido
    CHECK (nivel IN ('secundaria', 'primaria', 'cuidadores'));

-- 2. Ningún identificador de estudiante (E), cuidador (C) ni niño (N)
ALTER TABLE obs360.resultados DROP CONSTRAINT IF EXISTS resultados_sin_id_estudiante;
ALTER TABLE obs360.resultados ADD CONSTRAINT resultados_sin_id_estudiante CHECK (
    (grupo IS NULL OR grupo !~* '^[ECN][0-9a-f]{8}$')
    AND clave !~* '^[ECN][0-9a-f]{8}$');

-- 3. ¿Es esta la última corrida publicada de su módulo?
-- SECURITY DEFINER: la política de `corridas` llama a esta función, y la función
-- lee `corridas`; sin SECURITY DEFINER la política se evaluaría a sí misma (y
-- `anon` solo vería la fila que ya pasó el filtro). Corre con los permisos de su
-- dueño, que debe saltarse RLS: desde el SQL Editor el dueño es `postgres`
-- (dueño de las tablas, por lo tanto exento de RLS). Se fija explícito abajo.
-- `search_path` fijo para que nadie sustituya objetos con un esquema propio.
CREATE OR REPLACE FUNCTION obs360.es_ultima_publicada(p_id bigint) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = obs360, pg_temp AS $$
  SELECT p_id = (SELECT c.id FROM obs360.corridas c
                 WHERE c.publicada
                   AND c.modulo = (SELECT m.modulo FROM obs360.corridas m
                                   WHERE m.id = p_id)
                 ORDER BY c.creada_en DESC, c.id DESC LIMIT 1);
$$;
ALTER FUNCTION obs360.es_ultima_publicada(bigint) OWNER TO postgres;
REVOKE ALL ON FUNCTION obs360.es_ultima_publicada(bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION obs360.es_ultima_publicada(bigint)
    TO anon, authenticated, service_role;

-- 4. El público solo lee la última corrida publicada de cada módulo
DROP POLICY IF EXISTS "lectura publica de corridas publicadas" ON obs360.corridas;
CREATE POLICY "lectura publica de corridas publicadas" ON obs360.corridas
    FOR SELECT TO anon, authenticated USING (obs360.es_ultima_publicada(id));

DROP POLICY IF EXISTS "lectura publica de resultados publicados" ON obs360.resultados;
CREATE POLICY "lectura publica de resultados publicados" ON obs360.resultados
    FOR SELECT TO anon, authenticated
    USING (obs360.es_ultima_publicada(corrida_id));

-- 5. Vistas por módulo. Mismas columnas y orden que antes (`*` de corridas):
-- CREATE OR REPLACE VIEW no admite quitar ni renombrar columnas. `resultados_vigentes`
-- (JOIN con esta vista) no cambia y pasa a devolver la última corrida de CADA módulo.
CREATE OR REPLACE VIEW obs360.ultima_corrida
WITH (security_invoker = true) AS
SELECT DISTINCT ON (modulo) * FROM obs360.corridas
WHERE publicada = true
ORDER BY modulo, creada_en DESC, id DESC;

-- 6. Mensajes por módulo
ALTER TABLE obs360.mensajes ADD COLUMN IF NOT EXISTS modulo TEXT NOT NULL DEFAULT 'estudiantes';
ALTER TABLE obs360.mensajes DROP CONSTRAINT IF EXISTS mensajes_unicos;
ALTER TABLE obs360.mensajes ADD CONSTRAINT mensajes_unicos UNIQUE (modulo, clave, accion_rol);

-- 7. Comprobación: una fila por módulo con una corrida publicada
-- SELECT modulo, id, creada_en FROM obs360.ultima_corrida;

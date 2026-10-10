-- ════════════════════════════════════════════════════════════════════════════
-- Observatorio 360 · Triangulación 360 en el despliegue del equipo (10 oct 2026)
--
-- La triangulación (estudiantes × cuidadores × docentes) es SOLO para el equipo
-- investigador. Hasta ahora solo existía en la máquina que procesa los
-- formularios; con esta migración sus AGREGADOS (`python -m
-- src.triangulacion.publicar`) se guardan en `obs360.resultados` con
-- `modulo = 'triangulacion'` y `nivel = 'triangulacion'`, y los lee únicamente
-- el usuario de carga del despliegue privado (política del cargador, migración
-- 2026-10-10). El rol anónimo NUNCA los lee, ni aunque la corrida esté marcada
-- como publicada.
--
--   1. El CHECK `resultados_nivel_valido` admite 'triangulacion'. Los demás CHECK
--      (n >= 10, ningún identificador E/C/N, ningún conteo de casos) no cambian
--      y valen también para estas filas.
--   2. `obs360_interno.es_publica(id)`: la última corrida publicada de su módulo
--      (`es_ultima_publicada`) Y que no sea de triangulación. SECURITY DEFINER,
--      search_path fijo, dueño postgres y en `obs360_interno`, que la API REST no
--      expone (no se puede llamar como /rpc): igual que `es_ultima_publicada` en
--      la migración 2026-10-07b.
--   3. Las dos políticas PÚBLICAS (anon, authenticated) de `corridas` y
--      `resultados` pasan a usar `es_publica`; la de `resultados` además exige
--      `nivel <> 'triangulacion'` (aunque una fila de triangulación cayera en
--      una corrida de otro módulo, el público no la lee).
--
-- Lo que NO cambia:
--   · Estudiantes y Cuidadores: el público sigue leyendo exactamente la última
--     corrida publicada de cada módulo (para ellos es_publica = es_ultima_publicada).
--   · El usuario de carga sigue leyendo todas las corridas y resultados
--     (políticas «cargador lee …» de la migración 2026-10-10, que no se tocan).
--   · Nadie gana escritura: solo se recrean políticas FOR SELECT.
--
-- Ejecutar en Supabase → SQL Editor → Run, ANTES de publicar la primera corrida
-- de triangulación (sin el punto 1, la base rechaza sus filas y el publicador
-- deshace la corrida). Idempotente.
-- ════════════════════════════════════════════════════════════════════════════

-- ── 1. Nivel 'triangulacion' ───────────────────────────────────────────────
ALTER TABLE obs360.resultados DROP CONSTRAINT IF EXISTS resultados_nivel_valido;
ALTER TABLE obs360.resultados ADD CONSTRAINT resultados_nivel_valido
    CHECK (nivel IN ('secundaria', 'primaria', 'cuidadores', 'triangulacion'));

-- ── 2. ¿Puede el público leer esta corrida? ────────────────────────────────
CREATE SCHEMA IF NOT EXISTS obs360_interno;
REVOKE ALL ON SCHEMA obs360_interno FROM PUBLIC;
GRANT USAGE ON SCHEMA obs360_interno TO anon, authenticated, service_role;

CREATE OR REPLACE FUNCTION obs360_interno.es_publica(p_id bigint) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = obs360, pg_temp AS $$
  SELECT coalesce(
    EXISTS (SELECT 1 FROM obs360.corridas m
            WHERE m.id = p_id
              AND lower(btrim(m.modulo)) <> 'triangulacion')
    AND obs360_interno.es_ultima_publicada(p_id),
    false);
$$;
ALTER FUNCTION obs360_interno.es_publica(bigint) OWNER TO postgres;
REVOKE ALL ON FUNCTION obs360_interno.es_publica(bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION obs360_interno.es_publica(bigint)
    TO anon, authenticated, service_role;

-- ── 3. Políticas públicas: nunca triangulación ─────────────────────────────
DROP POLICY IF EXISTS "lectura publica de corridas publicadas" ON obs360.corridas;
CREATE POLICY "lectura publica de corridas publicadas" ON obs360.corridas
    FOR SELECT TO anon, authenticated USING (obs360_interno.es_publica(id));

DROP POLICY IF EXISTS "lectura publica de resultados publicados" ON obs360.resultados;
CREATE POLICY "lectura publica de resultados publicados" ON obs360.resultados
    FOR SELECT TO anon, authenticated
    USING (obs360_interno.es_publica(corrida_id) AND nivel <> 'triangulacion');

COMMENT ON FUNCTION obs360_interno.es_publica(bigint) IS
  'Última corrida publicada de su módulo y que no es de triangulación: lo único '
  'que lee el público. La triangulación solo la lee el usuario de carga.';

-- ── Comprobación ───────────────────────────────────────────────────────────
--   SELECT tablename, policyname, cmd, roles, qual FROM pg_policies
--    WHERE schemaname = 'obs360' AND tablename IN ('corridas', 'resultados')
--    ORDER BY tablename, policyname;
-- Por tabla: la política pública con es_publica (anon, authenticated) y la del
-- cargador (authenticated), ambas SELECT; ninguna de escritura.
--   SELECT pg_get_constraintdef(oid) FROM pg_constraint
--    WHERE conname = 'resultados_nivel_valido';   -- incluye 'triangulacion'
-- Como anon (clave pública), esto debe devolver 0 filas aunque haya una corrida
-- de triangulación publicada:
--   SELECT count(*) FROM obs360.resultados WHERE nivel = 'triangulacion';

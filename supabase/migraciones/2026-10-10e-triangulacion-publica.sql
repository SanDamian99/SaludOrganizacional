-- ════════════════════════════════════════════════════════════════════════════
-- Observatorio 360 · Triangulación 360 también en el despliegue público (10 oct 2026)
--
-- Decisión del usuario (10 oct 2026), explícita y por encima de la regla
-- «nunca público» de la spec (§5.6) y de la migración 2026-10-10b: la
-- Triangulación 360 se ve en el despliegue PÚBLICO (modo comunidad) «todo como
-- lo ve el equipo» — todas las pestañas, díadas, asociaciones y la descarga ZIP —
-- leída con la clave anon de la última corrida de triangulación PUBLICADA.
--
-- Lo que se publica sigue siendo solo agregados: los CHECK de `resultados`
-- (n >= 10, ningún identificador E/C/N, ningún conteo de casos) no cambian y
-- valen para estas filas; ninguna díada ni seudónimo sale de la máquina que
-- procesa.
--
--   1. `obs360_interno.es_publica(id)` vuelve a ser exactamente
--      `es_ultima_publicada(id)`: la última corrida publicada de su módulo, sin
--      excluir el módulo 'triangulacion'. Sigue SECURITY DEFINER, search_path
--      fijo, dueño postgres y en `obs360_interno` (no se llama por /rpc).
--   2. La política pública de `resultados` deja de exigir
--      `nivel <> 'triangulacion'`. La de `corridas` ya usa `es_publica` y no se
--      toca (al cambiar la función cambia lo que deja ver).
--
-- Lo que NO cambia:
--   · Las corridas ocultas (`publicada = false`) siguen ocultas para el público,
--     de triangulación y de cualquier módulo: solo la última publicada de cada
--     módulo es legible con la clave anon.
--   · Estudiantes y Cuidadores: el público lee lo mismo que antes.
--   · El usuario de carga sigue leyendo todas las corridas (vista previa de las
--     ocultas; políticas «cargador lee …» de la migración 2026-10-10).
--   · Nadie gana escritura: solo se recrea una política FOR SELECT.
--
-- Requiere las migraciones 2026-10-07b y 2026-10-10b (ya aplicadas).
-- Ejecutar en Supabase → SQL Editor → Run. Idempotente. Después, «Reboot app»
-- en el despliegue público para que cargue el menú con «Triangulación 360».
-- ════════════════════════════════════════════════════════════════════════════

-- ── 1. ¿Puede el público leer esta corrida? La última publicada, de cualquier módulo
CREATE SCHEMA IF NOT EXISTS obs360_interno;
REVOKE ALL ON SCHEMA obs360_interno FROM PUBLIC;
GRANT USAGE ON SCHEMA obs360_interno TO anon, authenticated, service_role;

CREATE OR REPLACE FUNCTION obs360_interno.es_publica(p_id bigint) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = obs360, pg_temp AS $$
  SELECT coalesce(obs360_interno.es_ultima_publicada(p_id), false);
$$;
ALTER FUNCTION obs360_interno.es_publica(bigint) OWNER TO postgres;
REVOKE ALL ON FUNCTION obs360_interno.es_publica(bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION obs360_interno.es_publica(bigint)
    TO anon, authenticated, service_role;

COMMENT ON FUNCTION obs360_interno.es_publica(bigint) IS
  'Última corrida publicada de su módulo (triangulación incluida desde la '
  'migración 2026-10-10e, por decisión del usuario): lo único que lee el público.';

-- ── 2. Políticas públicas (lectura): sin excepción para triangulación ───────
DROP POLICY IF EXISTS "lectura publica de corridas publicadas" ON obs360.corridas;
CREATE POLICY "lectura publica de corridas publicadas" ON obs360.corridas
    FOR SELECT TO anon, authenticated USING (obs360_interno.es_publica(id));

DROP POLICY IF EXISTS "lectura publica de resultados publicados" ON obs360.resultados;
CREATE POLICY "lectura publica de resultados publicados" ON obs360.resultados
    FOR SELECT TO anon, authenticated
    USING (obs360_interno.es_publica(corrida_id));

-- ── Comprobación ───────────────────────────────────────────────────────────
--   SELECT tablename, policyname, cmd, roles, qual FROM pg_policies
--    WHERE schemaname = 'obs360' AND tablename IN ('corridas', 'resultados')
--    ORDER BY tablename, policyname;
-- Por tabla: la política pública con es_publica (anon, authenticated) y la del
-- cargador (authenticated), ambas SELECT; ninguna de escritura.
-- Como anon (clave pública), con una corrida de triangulación publicada:
--   SELECT count(*) FROM obs360.resultados WHERE nivel = 'triangulacion';  -- > 0
-- y solo de esa corrida; una corrida oculta (publicada = false) sigue sin verse:
--   SELECT count(*) FROM obs360.corridas WHERE publicada = false;            -- 0

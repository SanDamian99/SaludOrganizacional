-- ════════════════════════════════════════════════════════════════════════════
-- Observatorio 360 · endurecimiento tras los avisos de seguridad de Supabase
-- (aplicada en producción el 7-oct-2026, después de 2026-10-07-modulo-y-ultima-corrida).
--
-- 1. `es_ultima_publicada` pasa a `obs360_interno`, un esquema que la API REST no
--    expone: deja de poder llamarse como /rest/v1/rpc. Las políticas la siguen usando.
-- 2. `min_grupo` y `es_cargador` fijan su search_path.
-- Idempotente.
-- ════════════════════════════════════════════════════════════════════════════
CREATE SCHEMA IF NOT EXISTS obs360_interno;
REVOKE ALL ON SCHEMA obs360_interno FROM PUBLIC;
GRANT USAGE ON SCHEMA obs360_interno TO anon, authenticated, service_role;

CREATE OR REPLACE FUNCTION obs360_interno.es_ultima_publicada(p_id bigint) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = obs360, pg_temp AS $$
  SELECT p_id = (SELECT c.id FROM obs360.corridas c
                 WHERE c.publicada
                   AND c.modulo = (SELECT m.modulo FROM obs360.corridas m
                                   WHERE m.id = p_id)
                 ORDER BY c.creada_en DESC, c.id DESC LIMIT 1);
$$;
ALTER FUNCTION obs360_interno.es_ultima_publicada(bigint) OWNER TO postgres;
REVOKE ALL ON FUNCTION obs360_interno.es_ultima_publicada(bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION obs360_interno.es_ultima_publicada(bigint)
    TO anon, authenticated, service_role;

DROP POLICY IF EXISTS "lectura publica de corridas publicadas" ON obs360.corridas;
CREATE POLICY "lectura publica de corridas publicadas" ON obs360.corridas
    FOR SELECT TO anon, authenticated USING (obs360_interno.es_ultima_publicada(id));
DROP POLICY IF EXISTS "lectura publica de resultados publicados" ON obs360.resultados;
CREATE POLICY "lectura publica de resultados publicados" ON obs360.resultados
    FOR SELECT TO anon, authenticated
    USING (obs360_interno.es_ultima_publicada(corrida_id));

DROP FUNCTION IF EXISTS obs360.es_ultima_publicada(bigint);

ALTER FUNCTION obs360.min_grupo() SET search_path = obs360, pg_temp;
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
             WHERE n.nspname = 'obs360' AND p.proname = 'es_cargador') THEN
    EXECUTE (SELECT format('ALTER FUNCTION %s SET search_path = obs360, pg_temp',
                           p.oid::regprocedure)
             FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
             WHERE n.nspname = 'obs360' AND p.proname = 'es_cargador' LIMIT 1);
  END IF;
END $$;

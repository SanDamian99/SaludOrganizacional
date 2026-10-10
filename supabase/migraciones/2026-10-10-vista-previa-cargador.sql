-- ════════════════════════════════════════════════════════════════════════════
-- Observatorio 360 · vista previa para el equipo (10 oct 2026)
--
-- El usuario de carga (Supabase Auth, app_metadata.obs360_rol = 'cargador',
-- credenciales solo en los secretos del despliegue PRIVADO) puede LEER cualquier
-- corrida y sus resultados, publicada o no. Así el equipo revisa la corrida
-- oculta (alertas de estudiantes, vista de comunidad de Cuidadores) en el
-- despliegue privado antes de aprobarla.
--
-- Lo que NO cambia:
--   · Las políticas públicas siguen intactas: anon (y cualquier authenticated que
--     no sea cargador) solo lee la ÚLTIMA corrida publicada de cada módulo
--     (`obs360_interno.es_ultima_publicada`). Las políticas de un mismo comando se
--     combinan con OR: la nueva solo añade filas para quien es cargador.
--   · Nadie gana escritura: solo se crean políticas FOR SELECT. Escribir en
--     `corridas` y `resultados` sigue exigiendo service_role.
--   · `mensajes` no se toca: la aplicación no lee esa tabla.
--
-- `obs360.es_cargador()` ya existe (supabase/almacen_schema.sql, endurecida en la
-- migración 2026-10-07b); se repite aquí, idéntica, para que la migración no
-- dependa del orden en que se corrieron los scripts. Idempotente.
-- ════════════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION obs360.es_cargador() RETURNS boolean
LANGUAGE sql STABLE SET search_path = obs360, pg_temp AS $$
    SELECT coalesce((auth.jwt() -> 'app_metadata' ->> 'obs360_rol') = 'cargador', false)
$$;

DROP POLICY IF EXISTS "cargador lee todas las corridas" ON obs360.corridas;
CREATE POLICY "cargador lee todas las corridas" ON obs360.corridas
    FOR SELECT TO authenticated USING (obs360.es_cargador());

DROP POLICY IF EXISTS "cargador lee todos los resultados" ON obs360.resultados;
CREATE POLICY "cargador lee todos los resultados" ON obs360.resultados
    FOR SELECT TO authenticated USING (obs360.es_cargador());

-- ── Comprobación ───────────────────────────────────────────────────────────
--   SELECT tablename, policyname, cmd, roles FROM pg_policies
--    WHERE schemaname = 'obs360' AND tablename IN ('corridas', 'resultados')
--    ORDER BY tablename, policyname;
-- Debe haber, por tabla, la política pública de siempre (anon, authenticated)
-- y la nueva del cargador (authenticated), ambas SELECT; ninguna de escritura.

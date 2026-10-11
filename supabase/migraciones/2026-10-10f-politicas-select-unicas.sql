-- ════════════════════════════════════════════════════════════════════════════
-- Observatorio 360 · Una sola política SELECT por rol (10 oct 2026, rendimiento)
--
-- El linter de Supabase avisaba de «multiple permissive policies»: en
-- `obs360.corridas` y `obs360.resultados` el rol `authenticated` tenía DOS
-- políticas SELECT («lectura publica de … publicadas», para anon y
-- authenticated, y «cargador lee …», solo authenticated), y Postgres evalúa
-- todas en cada consulta. Aquí se dejan dos políticas por tabla, una por rol,
-- con exactamente lo que cada rol veía antes:
--
--   · anon:           es_publica(...)                      (sin cambios)
--   · authenticated:  es_publica(...) OR obs360.es_cargador()
--
-- Nadie ve más que antes: anon sigue limitado a la última corrida publicada
-- de cada módulo; el usuario de carga sigue viendo todas las corridas (vista
-- previa de las ocultas). Nadie gana escritura: solo políticas FOR SELECT.
-- Las funciones es_publica (SECURITY DEFINER, search_path fijo) y es_cargador
-- no se tocan.
--
-- También `public.processed_data` (esquema antiguo, ya sin código que lo use)
-- tenía dos políticas SELECT idénticas para anon; se deja una.
--
-- Requiere 2026-10-10 (vista previa del cargador) y 2026-10-10e. Idempotente.
-- Comprobación al final.
-- ════════════════════════════════════════════════════════════════════════════

-- ── corridas ────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "lectura publica de corridas publicadas" ON obs360.corridas;
DROP POLICY IF EXISTS "cargador lee todas las corridas" ON obs360.corridas;

CREATE POLICY "lectura publica de corridas publicadas" ON obs360.corridas
    FOR SELECT TO anon USING (obs360_interno.es_publica(id));

CREATE POLICY "lectura autenticada de corridas" ON obs360.corridas
    FOR SELECT TO authenticated
    USING (obs360_interno.es_publica(id) OR obs360.es_cargador());

-- ── resultados ──────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "lectura publica de resultados publicados" ON obs360.resultados;
DROP POLICY IF EXISTS "cargador lee todos los resultados" ON obs360.resultados;

CREATE POLICY "lectura publica de resultados publicados" ON obs360.resultados
    FOR SELECT TO anon USING (obs360_interno.es_publica(corrida_id));

CREATE POLICY "lectura autenticada de resultados" ON obs360.resultados
    FOR SELECT TO authenticated
    USING (obs360_interno.es_publica(corrida_id) OR obs360.es_cargador());

-- ── processed_data (esquema antiguo): una sola política ─────────────────────
DROP POLICY IF EXISTS "Permitir lectura anónima" ON public.processed_data;

-- ── Comprobación ───────────────────────────────────────────────────────────
--   SELECT tablename, policyname, roles, qual FROM pg_policies
--    WHERE schemaname = 'obs360' AND tablename IN ('corridas', 'resultados')
--    ORDER BY tablename, policyname;
-- Dos políticas SELECT por tabla, una para {anon} y otra para {authenticated}.
-- Como anon: solo la última corrida publicada de cada módulo; ninguna con
-- publicada = false. Como usuario de carga: también las ocultas.

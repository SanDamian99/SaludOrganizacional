-- ════════════════════════════════════════════════════════════════════════════
-- Observatorio 360 · ningún conteo de casos y alertas con estado solo donde hay
-- cifra (fase 3, spec §5.4)
--
-- Ejecutar en Supabase → SQL Editor → Run, ANTES de publicar una corrida con
-- alertas. Aditiva e idempotente.
-- Publicar funciona sin ella: `publicar.verificar` ya rechaza en Python los
-- campos de conteo y el estado sin porcentaje. Esta es la última barrera: aunque
-- el código fallara, la base rechaza la fila.
--
-- NOT VALID: las corridas viejas (anteriores a la supresión de cifras pequeñas)
-- todavía guardan `casos` en las filas «corte». No se validan ni se tocan; la
-- restricción vale para toda fila nueva.
-- ════════════════════════════════════════════════════════════════════════════

-- Ninguna fila publica el número de casos (ni los de un contraste por tercil).
ALTER TABLE obs360.resultados DROP CONSTRAINT IF EXISTS resultados_sin_conteos;
ALTER TABLE obs360.resultados ADD CONSTRAINT resultados_sin_conteos CHECK (
    NOT (detalle ?| ARRAY['casos', 'k_bajo', 'k_alto'])) NOT VALID;

-- Una alerta sin porcentaje publicado no lleva estado («Prioridad» / «Para
-- tener presente»): el estado solo se muestra donde se muestra la cifra.
ALTER TABLE obs360.resultados DROP CONSTRAINT IF EXISTS resultados_alerta_estado_con_cifra;
ALTER TABLE obs360.resultados ADD CONSTRAINT resultados_alerta_estado_con_cifra CHECK (
    tipo NOT LIKE 'alerta%'
    OR valor IS NOT NULL
    OR coalesce(detalle->>'estado', 'sin_estado') = 'sin_estado') NOT VALID;

COMMENT ON COLUMN obs360.resultados.tipo IS
  'descriptivo | banda | corte | correlacion | grupo | modelo | tercil | percentil | '
  'item | icc | contraste | muestra | solapamiento | ingesta | *_grupo | '
  'alerta | alerta_grupo (alertas de grupo: n, % e IC donde se pueden mostrar y '
  'estado en detalle; nunca casos)';

-- Comprobación: dos filas
-- SELECT conname FROM pg_constraint
--  WHERE conname IN ('resultados_sin_conteos', 'resultados_alerta_estado_con_cifra');

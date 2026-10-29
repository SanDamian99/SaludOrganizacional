-- Aplicada el 29-10-2026 vía MCP. Una versión «legacy» sigue en Storage y en la
-- tabla (para auditar de dónde salió una cifra) pero la app ya no la lista ni
-- permite activarla. Se marcan así las tres versiones de docentes anteriores a
-- la depuración del archivo (189, 479 y 479 filas).
ALTER TABLE obs360.conjuntos_versiones
    ADD COLUMN IF NOT EXISTS legacy boolean NOT NULL DEFAULT false;
COMMENT ON COLUMN obs360.conjuntos_versiones.legacy IS
  'true: versión retirada. No se lista en la app ni se puede activar; el archivo se conserva.';
UPDATE obs360.conjuntos_versiones SET legacy = true, activa = false
 WHERE conjunto = 'docentes' AND id IN (2, 3, 4);

-- Aplicada el 10-10-2026 vía MCP. Los formularios crudos de estudiantes y
-- cuidadores pueden vivir en el almacén como copias desidentificadas
-- (seudónimos HMAC en lugar de nombres, sin contacto). Ver src/data/desidentificar.py.
ALTER TABLE obs360.conjuntos_versiones DROP CONSTRAINT IF EXISTS conjuntos_versiones_conjunto_check;
ALTER TABLE obs360.conjuntos_versiones
    ADD CONSTRAINT conjuntos_versiones_conjunto_check
    CHECK (conjunto IN ('docentes', 'cuidadores', 'estudiantes_secundaria', 'estudiantes_primaria'));
COMMENT ON TABLE obs360.conjuntos_versiones IS
  'Versiones de los archivos fuente en Storage (bucket datasets, privado). «docentes» es el codificado sin nombres; los demás son copias desidentificadas de los formularios: seudónimos HMAC en vez de nombres y sin datos de contacto. Solo una activa por conjunto.';

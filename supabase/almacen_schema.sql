-- Almacén de versiones de los archivos de docentes y cuidadores — Observatorio 360.
--
-- El archivo se guarda en Storage (bucket `datasets`, PRIVADO) sin columnas de
-- identificación, y cada subida queda registrada aquí. Escribe y lee un único
-- usuario de Auth marcado con app_metadata.obs360_rol = 'cargador'; ese usuario
-- solo existe en los secretos del despliegue privado del equipo. Ni la clave
-- anon ni el público llegan a estos archivos.

UPDATE storage.buckets SET public = false WHERE id = 'datasets';

CREATE TABLE IF NOT EXISTS obs360.conjuntos_versiones (
    id              bigserial PRIMARY KEY,
    conjunto        text NOT NULL CHECK (conjunto IN ('docentes', 'cuidadores')),
    ruta            text NOT NULL UNIQUE,
    nombre_original text,
    filas           integer NOT NULL CHECK (filas >= 0),
    columnas        integer NOT NULL CHECK (columnas >= 0),
    hash            text NOT NULL,
    notas           text DEFAULT '',
    subido_por      text,
    activa          boolean NOT NULL DEFAULT false,
    creada_en       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS conjuntos_versiones_activa
    ON obs360.conjuntos_versiones (conjunto) WHERE activa;

ALTER TABLE obs360.conjuntos_versiones ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION obs360.es_cargador() RETURNS boolean
LANGUAGE sql STABLE AS $$
    SELECT coalesce((auth.jwt() -> 'app_metadata' ->> 'obs360_rol') = 'cargador', false)
$$;

DROP POLICY IF EXISTS "cargador gestiona versiones" ON obs360.conjuntos_versiones;
CREATE POLICY "cargador gestiona versiones" ON obs360.conjuntos_versiones
    FOR ALL TO authenticated USING (obs360.es_cargador()) WITH CHECK (obs360.es_cargador());

GRANT USAGE ON SCHEMA obs360 TO authenticated;
GRANT SELECT, INSERT, UPDATE ON obs360.conjuntos_versiones TO authenticated;
GRANT USAGE, SELECT ON SEQUENCE obs360.conjuntos_versiones_id_seq TO authenticated;

DROP POLICY IF EXISTS "cargador lee datasets" ON storage.objects;
CREATE POLICY "cargador lee datasets" ON storage.objects
    FOR SELECT TO authenticated USING (bucket_id = 'datasets' AND obs360.es_cargador());
DROP POLICY IF EXISTS "cargador sube datasets" ON storage.objects;
CREATE POLICY "cargador sube datasets" ON storage.objects
    FOR INSERT TO authenticated WITH CHECK (bucket_id = 'datasets' AND obs360.es_cargador());

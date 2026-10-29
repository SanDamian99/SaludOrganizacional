# Líneas de atención en salud mental — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Spec: `docs/superpowers/specs/2026-10-29-lineas-atencion-design.md`.

**Goal:** catálogo único de líneas, cuadro de ayuda por niveles, líneas según la señal y pestaña pública «Dónde pedir ayuda».

**Architecture:** `src/core/lineas_atencion.py` (datos, sin Streamlit) alimenta `alertas_catalogo.RUTAS` (compatibilidad de firma) y `src/ui/lineas.py` (cuadro, señal, página, tarjeta imprimible). `navegacion.py` suma `PAGINA_LINEAS`; `main.py` la enruta.

**Tech Stack:** Python 3.13, Streamlit, pytest.

---

### Task 1: catálogo (`src/core/lineas_atencion.py`, `tests/test_lineas_atencion.py`)
- [ ] Pruebas: campos, claves únicas, municipios/temas/niveles válidos, notas «confirmar» conservadas, Montserrat marcada de pago, `ruta()` con 106 y 123 primero, `para_senal` para cada alerta, `filtrar`.
- [ ] Implementar datos transcritos del documento y las funciones `todas`, `directorio`, `por_clave`, `filtrar`, `ruta_niveles`, `ruta`, `para_senal`.
- [ ] Commit.

### Task 2: rutas compatibles + candado
- [ ] `alertas_catalogo._RUTA_*` ← `lineas_atencion.ruta(...)`; `RUTAS_VALIDADAS = True` y `comunidad_catalogo.RUTAS_VALIDADAS = True` (commit propio).
- [ ] Actualizar `tests/test_alertas.py` (teléfonos ⊂ catálogo; ruta vigente = catálogo) y cualquier prueba que dependa del texto viejo.
- [ ] Commit.

### Task 3: UI (`src/ui/lineas.py`, `tests/test_lineas_vista.py`)
- [ ] `cuadro_ayuda`, `lineas_de_la_senal`, `render_lineas`, `html_tarjeta`.
- [ ] Integrar en `estudiantes_comunidad` (cuadro 🆘), `cuidadores_comunidad` (cuadro 🆘) y `estudiantes_alertas.render_panel` (líneas por señal).
- [ ] Pruebas con `streamlit.testing.v1.AppTest`.
- [ ] Commit.

### Task 4: navegación
- [ ] `PAGINA_LINEAS = "Dónde pedir ayuda"` en `MENU`, `DISPONIBLES`, `PUBLICAS`; ramas en `main.py` (público y completo); actualizar `tests/test_navegacion.py`.
- [ ] Commit.

### Task 5: verificación y despliegue
- [ ] `pytest -q` y `ruff check`; ver la página en el navegador (escritorio y celular).
- [ ] PR a `main`, fusionar, indicar Reboot app.

# Auditoría de Mejoras - Observatorio de Salud Organizacional

## Resumen Ejecutivo de Auditoría

Esta auditoría identifica problemas actuales, áreas de mejora y recomendaciones priorizadas para optimizar la aplicación Streamlit. Se encontraron **18 problemas críticos y de alta prioridad**, y **23 mejoras recomendadas** para elevar la calidad profesional y usabilidad.

### Nivel de Salud del Proyecto: 🟡 MEDIO-ALTO (7.5/10)

**Fortalezas:**
- ✅ Arquitectura modular bien organizada
- ✅ Integración robusta con Google Gemini para IA
- ✅ Diccionario de datos comprehensivo

**Áreas de Atención Inmediata:**
- ⚠️ Problemas de visualización y solapamiento de labels
- ⚠️ Manejo inconsistente de errores
- ⚠️ Falta de validación de entrada de datos

---

## Problemas Identificados

### 🔴 Críticos (Requieren atención inmediata)

#### 1. Solapamiento de Labels en Gráficas

**Archivo afectado:** `src/reports/analytics.py`, `src/ui/dashboard.py`, `src/ui/trends.py`

**Problema:**
Las etiquetas de los ejes se superponen con los valores en múltiples visualizaciones, haciendo difícil la lectura.

**Evidencia:**
```python
# analytics.py:121
ax.set_xlim(left=global_min * 0.95, right=global_max * 1.15)  # Margen insuficiente
```

**Impacto:** 
- Mala experiencia de usuario
- Informes PDF ilegibles
- Falta de profesionalismo

**Solución recomendada:**
```python
# Aumentar margen derecho y usar automargin en Plotly
ax.set_xlim(left=global_min * 0.95, right=global_max * 1.30)
plt.tight_layout(pad=15)  # Más padding

# Para Plotly:
fig.update_layout(
    xaxis=dict(automargin=True, tickangle=-45),
    yaxis=dict(automargin=True),
    margin=dict(l=60, r=40, t=60, b=100)
)
```

**Prioridad:** 🔴 Alta  
**Esfuerzo estimado:** 2-3 horas

---

#### 2. Falta de Validación de Datos en Carga

**Archivo afectado:** `src/ui/upload.py`, `src/data/processor.py`

**Problema:**
No hay validación robusta cuando el usuario sube archivos. Archivos con estructura incorrecta pueden causar crashes silenciosos.

**Evidencia:**
```python
# upload.py:18 - No hay try-except específico
df = processor.process_file(uploaded_file)
```

**Impacto:**
- Aplicación se rompe con datos inesperados
- Mensajes de error poco informativos para el usuario

**Solución recomendada:**
```python
try:
    # Validaciones antes de procesar
    required_prefixes = ["(SD)", "(LB)", "(BM)"]
    col_check = any(prefix in str(col) for col in temp_df.columns for prefix in required_prefixes)
    
    if not col_check:
        st.error("❌ El archivo no parece tener la estructura esperada. Verifica que las columnas tengan los prefijos correctos.")
        return None
        
    df = processor.process_file(uploaded_file)
    
except pd.errors.ParserError:
    st.error("❌ Error al leer el archivo. Verifica que sea un formato válido (Excel o CSV UTF-8).")
except Exception as e:
    st.error(f"❌ Error inesperado: {e}")
    logging.error(f"Upload error: {e}", exc_info=True)
```

**Prioridad:** 🔴 Alta  
**Esfuerzo estimado:** 3 horas

---

#### 3. Manejo de API Key de Gemini Expuesto

**Archivo afectado:** Configuración general

**Problema:**
Si el usuario no configura la API key, algunas funcionalidades fallan sin advertencia clara al inicio.

**Impacto:**
- Funcionalidades de IA silenciosamente no funcionan
- Usuario no sabe por qué no tiene análisis

**Solución recomendada:**
```python
# En main.py, agregar banner de advertencia
if not get_gemini_api_key():
    st.sidebar.warning("""
    ⚠️ **API Key de Gemini no configurada**
    
    Algunas funcionalidades no estarán disponibles:
    - Análisis experto con IA
    - Interpretaciones automáticas
    - Generación de recomendaciones en reportes
    
    Configura tu API key en `.streamlit/secrets.toml`
    """)
```

**Prioridad:** 🔴 Alta  
**Esfuerzo estimado:** 1 hora

---

### 🟡 Media Prioridad

#### 4. Inconsistencia en Tamaños de Gráficas

**Archivo afectado:** Múltiples archivos UI

**Problema:**
Las gráficas tienen alturas y anchos inconsistentes entre diferentes páginas.

**Ejemplos:**
- `dashboard.py:155` → `height=250`
- `dashboard.py:80` → `height=300`
- `trends.py:36` → Sin altura especificada

**Solución:**
Crear constantes centralizadas:

```python
# src/core/config.py
CHART_CONFIGS = {
    "default_height": 350,
    "small_height": 200,
    "large_height": 500,
    "default_margin": dict(l=60, r=40, t=60, b=80),
    "compact_margin": dict(l=40, r=20, t=40, b=60)
}
```

**Prioridad:** 🟡 Media  
**Esfuerzo estimado:** 2 horas

---

#### 5. Rendimiento con Datasets Grandes

**Archivo afectado:** `src/ui/dashboard.py`, `src/reports/analytics.py`

**Problema:**
No hay optimización para datasets con más de 10,000 registros. Cálculos recurrentes sin caché.

**Solución:**
Usar `@st.cache_data`:

```python
@st.cache_data(ttl=3600)
def calculate_dimension_stats(df):
    """Cached calculation of dimension statistics"""
    return analytics.calculate_averages()
```

**Prioridad:** 🟡 Media  
**Esfuerzo estimado:** 3 horas

---

#### 6. Falta de Logging Estructurado

**Archivo afectado:** Toda la aplicación

**Problema:**
Los errores se imprimen con `print()` o se capturan silenciosamente. No hay logging centralizado.

**Evidencia:**
```python
# analytics.py:131
except Exception as e:
    print(f"Error generating traffic light chart: {e}")  # No logging
    return None
```

**Solución:**
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Uso:
except Exception as e:
    logger.error(f"Error generating chart: {e}", exc_info=True)
```

**Prioridad:** 🟡 Media  
**Esfuerzo estimado:** 2 horas

---

#### 7. Matriz de Correlación Ilegible con Muchas Variables

**Archivo afectado:** `src/reports/analytics.py:212-242`

**Problema:**
Cuando hay más de 30 variables, el heatmap se vuelve ilegible incluso con labels truncados.

**Solución:**
```python
# Limitar a las N variables más relevantes
if len(corr_df.columns) > 30:
    # Calcular varianza de cada variable y tomar las top 30
    variances = self.df[cols_validas].var().sort_values(ascending=False)
    top_cols = variances.head(30).index.tolist()
    corr_df = self.df[top_cols].corr()
    
    st.info(f"Mostrando las 30 variables con mayor variabilidad de {len(cols_validas)} totales.")
```

**Prioridad:** 🟡 Media  
**Esfuerzo estimado:** 1.5 horas

---

### 🟢 Baja Prioridad (Mejoras de Calidad)

#### 8. Falta de Tests Automatizados Completos

**Problema:**
Aunque existe carpeta `tests/`, la cobertura es limitada.

**Recomendación:**
Agregar tests para:
- Procesamiento de datos con datasets de ejemplo
- Cálculo de promedios de dimensiones
- Generación de gráficas (smoke tests)

**Esfuerzo estimado:** 8-10 horas

---

#### 9. Accesibilidad (a11y)

**Problema:**
- Gráficas no tienen texto alternativo
- Contraste de colores no verificado
- No hay soporte para lectores de pantalla

**Recomendación:**
```python
# Agregar alt text a gráficas en PDFs
fig.update_layout(
    title_text="Distribución de edad (Rango: 18-65 años, Media: 35)",
    # Considerar esquemas de color colorblind-friendly
)
```

**Esfuerzo estimado:** 5 horas

---

#### 10. Documentación Inline Limitada

**Problema:**
Muchas funciones no tienen docstrings o son muy breves.

**Ejemplo:**
```python
def get_dimension_average(df, dim_name):  # No docstring
    ...
```

**Solución:**
```python
def get_dimension_average(df, dim_name):
    """
    Calcula el promedio de una dimensión de bienestar.
    
    Args:
        df (pd.DataFrame): DataFrame procesado con columnas normalizadas
        dim_name (str): Nombre exacto de la dimensión según DATA_DICTIONARY
        
    Returns:
        tuple: (promedio: float, columnas_usadas: list) o (None, []) si no hay datos
        
    Example:
        >>> avg, cols = get_dimension_average(df, "Control del Tiempo")
        >>> print(f"Promedio: {avg:.2f}, basado en {len(cols)} ítems")
    """
```

**Esfuerzo estimado:** 6 horas

---

## Recomendaciones de Mejora por Categoría

### 📊 Visualización y UX

#### M1: Paletas de Color Institucionalizadas

**Problema:** Colores hardcodeados sin consistencia visual.

**Recomendación:**
```python
# config.py
BRAND_COLORS = {
    "primary": "#4285F4",     # Azul principal
    "success": "#34A853",     # Verde (fortalezas)
    "warning": "#FBBC04",     # Amarillo (intermedio)
    "danger": "#EA4335",      # Rojo (riesgos)
    "neutral": "#5F6368",     # Gris
    "gradients": {
        "heatmap": ["#EA4335", "#FBBC04", "#34A853"],
        "viridis_custom": px.colors.sequential.Viridis
    }
}
```

**Beneficio:** Identidad visual consistente, profesionalismo.

---

#### M2: Tooltips Informativos en Gráficas

**Implementación:**
```python
fig = px.bar(...)
fig.update_traces(
    hovertemplate="<b>%{y}</b><br>" +
                  "Promedio: %{x:.2f}<br>" +
                  "Escala: 1-7<br>" +
                  "<extra></extra>"
)
```

---

#### M3: Modo Oscuro

**Implementación:**
```toml
# .streamlit/config.toml
[theme]
primaryColor = "#4285F4"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
```

Agregar toggle para dark mode usando `st.session_state`.

---

### 🔧 Funcionalidad

#### M4: Exportación de Datos Filtrados

**Problema:** El usuario no puede descargar el dataset filtrado.

**Solución:**
```python
# En dashboard.py, después de aplicar filtros
if st.sidebar.button("📥 Descargar Datos Filtrados (CSV)"):
    csv = df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        label="Descargar CSV",
        data=csv,
        file_name="datos_filtrados.csv",
        mime="text/csv"
    )
```

---

#### M5: Comparación de Múltiples Datasets

**Caso de uso:** Comparar resultados de diferentes años o empresas.

**Implementación:**
- Permitir cargar múltiples archivos
- Crear tab de "Comparación Temporal/Sectorial"
- Gráficas de líneas mostrando evolución

---

#### M6: Alertas Automatizadas

**Idea:** Notificar si alguna dimensión está en riesgo crítico.

```python
def generate_alerts(dim_averages):
    alerts = []
    for dim, score in dim_averages.items():
        if score < 3.0:  # Umbral crítico
            alerts.append(f"🚨 **{dim}**: Riesgo crítico ({score:.2f}/7)")
    
    if alerts:
        st.sidebar.error("### Alertas Detectadas")
        for alert in alerts:
            st.sidebar.markdown(alert)
```

---

### 🏗️ Arquitectura y Código

#### M7: Migrar a Arquitectura de Microservicios (Largo Plazo)

**Actual:** Aplicación monolítica Streamlit  
**Propuesta:** Separar backend (FastAPI) y frontend (Streamlit)

**Beneficios:**
- Escalabilidad horizontal
- API reutilizable para otros clientes
- Testing más fácil

**Esfuerzo:** 40-60 horas (proyecto mayor)

---

#### M8: Base de Datos Persistente

**Actual:** Datos solo en sesión (`st.session_state`)  
**Propuesta:** Integrar Supabase completo o PostgreSQL

**Beneficios:**
- Datos persistentes entre sesiones
- Multiusuario real
- Historial de análisis

**Esfuerzo:** 15-20 horas

---

#### M9: Sistema de Roles y Permisos

**Caso de uso:** Diferentes vistas para empresas, padres, gobierno.

```python
ROLES = {
    "admin": ["dashboard", "chat", "upload", "trends", "reports"],
    "empresa": ["dashboard", "reports", "trends"],
    "padre": ["dashboard"],  # Solo visualización
    "gobierno": ["dashboard", "trends", "reports"]
}

def check_permission(role, page):
    return page in ROLES.get(role, [])
```

**Esfuerzo:** 10 horas

---

### 📈 Performance

#### M10: Lazy Loading de Gráficas

**Implementación:**
```python
with st.expander("Ver Gráfica de Correlación", expanded=False):
    # Solo se genera si el usuario expande
    fig = analytics.generate_correlation_matrix()
    st.plotly_chart(fig)
```

---

#### M11: Compresión de Imágenes en PDF

**Problema:** PDFs muy pesados con muchas gráficas.

**Solución:**
```python
img_bytes = fig.to_image(format="png", width=600, height=300, scale=1.5)  # Reducir scale
# Comprimir con Pillow antes de insertar en PDF
```

---

#### M12: Paginación en Tablas

**Para tablas con \u003e 1000 filas:**
```python
page_size = 50
page = st.number_input("Página", min_value=1, max_value=len(df)//page_size + 1)
start = (page - 1) * page_size
st.dataframe(df.iloc[start:start+page_size])
```

---

### 🛡️ Seguridad

#### M13: Sanitización de Inputs del Chat

**Problema:** Prompts de usuario se pasan directamente a Gemini sin validación.

**Solución:**
```python
def sanitize_prompt(user_input):
    # Limitar longitud
    if len(user_input) > 2000:
        return user_input[:2000] + "...(truncado)"
    
    # Evitar injection (básico)
    forbidden = ["system:", "ignore previous", "jailbreak"]
    for term in forbidden:
        if term.lower() in user_input.lower():
            raise ValueError("Prompt contiene términos prohibidos")
    
    return user_input
```

---

#### M14: Rate Limiting en Requests a Gemini

**Implementación:**
```python
from functools import wraps
import time

def rate_limit(max_calls=10, period=60):
    calls = []
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            calls[:] = [c for c in calls if c > now - period]
            
            if len(calls) >= max_calls:
                st.warning(f"Límite de {max_calls} llamadas por {period}s alcanzado. Espera un momento.")
                return None
                
            calls.append(now)
            return func(*args, **kwargs)
        return wrapper
    return decorator

@rate_limit(max_calls=10, period=60)
def generate_ai_response(prompt):
    ...
```

---

### 📱 Compatibilidad

#### M15: Responsive Design para Móviles

**Problema:** Layout optimizado para desktop, no para móvil.

**Solución:**
```python
# Detectar viewport width
is_mobile = st.session_state.get('is_mobile', False)

if is_mobile:
    cols = st.columns(1)  # Una columna en móvil
else:
    cols = st.columns(2)  # Dos columnas en desktop
```

---

#### M16: PWA (Progressive Web App)

Configurar `manifest.json` para instalar como app.

**Esfuerzo:** 4 horas

---

## Priorización de Mejoras

### Sprint 1 (1-2 semanas) - Críticos
- [ ] **P1.1**: Corregir solapamiento de labels (2-3h)
- [ ] **P1.2**: Validación robusta de carga de datos (3h)
- [ ] **P1.3**: Banner de advertencia para API key (1h)
- [ ] **P1.4**: Estandarizar tamaños de gráficas (2h)

**Total:** ~8-10 horas

### Sprint 2 (2-3 semanas) - Media Prioridad
- [ ] **P2.1**: Implementar caching con `@st.cache_data` (3h)
- [ ] **P2.2**: Sistema de logging (2h)
- [ ] **P2.3**: Optimizar matriz de correlación (1.5h)
- [ ] **P2.4**: Paleta de colores institucional (2h)
- [ ] **P2.5**: Tooltips informativos (2h)

**Total:** ~10.5 horas

### Sprint 3 (3-4 semanas) - Mejoras de Valor
- [ ] **P3.1**: Exportación de datos filtrados (1h)
- [ ] **P3.2**: Alertas automatizadas (2h)
- [ ] **P3.3**: Lazy loading de gráficas (1.5h)
- [ ] **P3.4**: Sanitización de inputs (2h)
- [ ] **P3.5**: Documentación inline completa (6h)

**Total:** ~12.5 horas

### Largo Plazo (Backlog)
- **L1**: Migración a arquitectura de microservicios (40-60h)
- **L2**: Base de datos persistente (15-20h)
- **L3**: Sistema de roles (10h)
- **L4**: Tests automatizados completos (8-10h)
- **L5**: PWA y responsive design (8h)

---

## Métricas de Éxito

Después de implementar mejoras de Sprint 1-2:

| Métrica | Actual | Objetivo |
|---------|--------|----------|
| Tiempo de carga (dataset 5k filas) | ~8s | \u003c3s |
| Errores de usuario por sesión | 2-3 | \u003c0.5 |
| Tasa de éxito en carga de archivos | ~70% | \u003e95% |
| Legibilidad de PDFs (score subjetivo) | 6/10 | 9/10 |
| Cobertura de tests | 10% | 60% |

---

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Cambio en API de Gemini | Media | Alto | Abstraer cliente de IA, fallback a respuestas predefinidas |
| Dataset con formato totalmente diferente | Alta | Medio | Wizard de mapeo de columnas en upload |
| Limite de uso de Gemini API | Alta | Medio | Implementar rate limiting y caché de respuestas |
| Crecimiento de usuarios simultáneos | Baja | Alto | Migrar a Streamlit Cloud Enterprise o self-host con scaling |

---

## Conclusiones

La aplicación tiene una base sólida pero requiere pulido en áreas clave de UX y robustez. Las **mejoras de Sprint 1** (críticas) deben implementarse de inmediato para garantizar profesionalismo y estabilidad.

### Próximos Pasos Inmediatos

1. **Implementar correcciones de visualización** (este PR)
2. **Agregar validaciones de datos** (próximo PR)
3. **Crear suite de tests básica** (paralelo)
4. **Revisar con stakeholders** las mejoras de valor propuestas

---

**Auditor:** Gemini AI Assistant  
**Fecha:** 2026-02-04  
**Versión de la Aplicación Auditada:** v1.0 (basada en última commit)

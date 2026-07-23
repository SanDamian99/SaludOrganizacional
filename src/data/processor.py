import pandas as pd
import numpy as np
import io
import unicodedata
import re
import difflib
from collections import Counter
from src.core.config import (
    DATA_DICTIONARY, 
    RESPONSE_SETS, 
    REVERSE_PATTERNS,
    COLUMN_ORDERED_OPTIONS_EXACT,
    COLUMN_ORDERED_OPTIONS_KEYWORD
)

# --- Helper Functions ---

def normalize_text(s: str) -> str:
    if pd.isna(s): return ''
    s = str(s)
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower().strip()
    s = re.sub(r'\s+', ' ', s)
    s = s.replace('“','"').replace('”','"').replace("’","'").replace("´", "'")
    s = s.replace(' sólo ', ' solo ')
    return s

def yn_canon(s):
    YES_SYNS = {'si','sí','si.','sí.','si autoriza','sí autoriza','si autorizo','sí autorizo'}
    NO_SYNS  = {'no','no.','no autorizo','no autoriza'}
    t = normalize_text(s)
    if t in YES_SYNS: return 'sí'
    if t in NO_SYNS:  return 'no'
    return t

def canonicalize_extra(t: str) -> str:
    if pd.isna(t): return t
    x = normalize_text(t)
    # typos/frecuencias
    x = re.sub(r'\bamenudo\b', 'a menudo', x)
    x = x.replace('simpre', 'siempre')
    x = x.replace('sobrell', 'sobrelle')
    x = x.replace('llevarllas', 'llevarlas')
    x = re.sub(r'\bmuy seguidoa\b', 'muy seguido', x)
    x = re.sub(r'\bseguido\(a\)\b', 'seguido', x)
    x = re.sub(r'\bmuy seguido\(a\)\b', 'muy seguido', x)
    # "no estoy segur@" / "no estoy segura" / "no estoy seguro(a)"
    x = re.sub(r'no estoy segur[oa@x]\b', 'no estoy seguro', x)
    x = re.sub(r'no estoy seguro\s*\(?a\)?', 'no estoy seguro', x)
    # coma con sí
    x = x.replace('si, ', 'sí, ')
    return x

def coerce_numeric_flexible(series: pd.Series) -> pd.Series:
    s = series.astype(str)
    nums = s.str.extract(r'^\s*(-?\d+(?:[.,]\d+)?)', expand=False)
    nums = nums.str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    return pd.to_numeric(nums, errors='coerce')

def fuzzy_map_to_allowed(series: pd.Series, allowed_values, cutoff=0.75):
    allowed_norm = [normalize_text(canonicalize_extra(v)) for v in allowed_values]
    idx_by_norm = {v:i for i,v in enumerate(allowed_norm)}
    mapped = {}
    for v in series.dropna().unique():
        key = normalize_text(canonicalize_extra(v))
        if key in idx_by_norm:
            mapped[v] = idx_by_norm[key]
        else:
            best = difflib.get_close_matches(key, allowed_norm, n=1, cutoff=cutoff)
            mapped[v] = idx_by_norm[best[0]] if best else np.nan
    codes = series.map(mapped)
    return codes, mapped

def try_map_with_set(series: pd.Series, mapping: dict):
    s = series.dropna()
    if s.empty:
        return pd.Series(index=series.index, dtype='float'), 1.0

    s_norm = s.map(yn_canon).map(canonicalize_extra).map(normalize_text)
    mapped = s_norm.map(mapping)
    coverage = float(mapped.notna().mean())

    out = pd.Series(index=series.index, dtype='float')
    out.loc[s.index] = mapped
    return out, coverage

def best_response_set(series: pd.Series):
    best_name, best_cov, best_mapped = None, -1.0, None
    for name, mapping in RESPONSE_SETS.items():
        mapped, cov = try_map_with_set(series, mapping)
        if cov > best_cov:
            best_cov, best_name, best_mapped = cov, name, mapped
    return best_name, best_mapped, best_cov

def reverse_numeric(series: pd.Series):
    if series.dropna().empty:
        return series
    mn = series.min(skipna=True)
    mx = series.max(skipna=True)
    return mx - series + mn

def is_reverse_column(colname: str):
    n = normalize_text(colname)
    REVERSE_REGEX = [re.compile(p) for p in REVERSE_PATTERNS]
    for i, rx in enumerate(REVERSE_REGEX):
        if rx.search(n):
            return True, i
    if '(r)' in n:
        return True, '(r)'
    return False, None

def extract_bracket_keyword(colname: str) -> str:
    m = re.search(r'\[(.*?)\]', colname)
    if m:
        return normalize_text(m.group(1))
    return ''

def try_column_override(colname: str, series: pd.Series):
    ncol = normalize_text(colname)
    
    # Exact match
    if ncol in COLUMN_ORDERED_OPTIONS_EXACT:
        levels = COLUMN_ORDERED_OPTIONS_EXACT[ncol]
        codes, _ = fuzzy_map_to_allowed(series, levels)
        cov = float(codes.notna().mean())
        return codes.astype('float'), cov, f'override_exact', levels

    # Keyword match
    key = extract_bracket_keyword(colname)
    if key and key in COLUMN_ORDERED_OPTIONS_KEYWORD:
        levels = COLUMN_ORDERED_OPTIONS_KEYWORD[key]
        codes, _ = fuzzy_map_to_allowed(series, levels)
        cov = float(codes.notna().mean())
        return codes.astype('float'), cov, f'override_keyword[{key}]', levels

    # Fuzzy exact match
    exact_keys = list(COLUMN_ORDERED_OPTIONS_EXACT.keys())
    best = difflib.get_close_matches(ncol, exact_keys, n=1, cutoff=0.88)
    if best:
        levels = COLUMN_ORDERED_OPTIONS_EXACT[best[0]]
        codes, _ = fuzzy_map_to_allowed(series, levels)
        cov = float(codes.notna().mean())
        return codes.astype('float'), cov, f'override_fuzzy_exact', levels

    # Contains keyword
    for kw, levels in COLUMN_ORDERED_OPTIONS_KEYWORD.items():
        if kw in ncol:
            codes, _ = fuzzy_map_to_allowed(series, levels)
            cov = float(codes.notna().mean())
            return codes.astype('float'), cov, f'override_contains[{kw}]', levels

    return None, 0.0, None, None

def guess_type(series: pd.Series):
    MIN_NUMERIC_RATIO = 0.60
    num = pd.to_numeric(series, errors='coerce')
    if num.notna().mean() < MIN_NUMERIC_RATIO:
        num2 = coerce_numeric_flexible(series)
        if num2.notna().mean() > num.notna().mean():
            num = num2
    if num.notna().mean() >= MIN_NUMERIC_RATIO:
        return 'Continua', num
    return 'Categórica', None


# Columnas que NUNCA se numerizan ni se imputan (identificadores / metadatos).
_PROTECTED_EXACT = {
    'id', 'nombre', 'correo electronico', 'correo', 'email',
    'hora de inicio', 'hora de finalizacion', 'marca temporal', 'timestamp',
}
_PROTECTED_KEYWORDS = ('correo', 'email', 'timestamp', 'marca temporal')


def is_protected_column(colname: str) -> bool:
    """True si la columna es un identificador/metadato que debe conservarse intacto."""
    n = normalize_text(colname)
    if n in _PROTECTED_EXACT:
        return True
    return any(kw in n for kw in _PROTECTED_KEYWORDS)


class ExcelProcessor:
    def __init__(self):
        self.report = {
            "n_rows_original": 0,
            "n_rows_final": 0,
            "n_cols_original": 0,
            "n_cols_mapped": 0,
            "n_cols_unmapped": 0,
            "n_cells_imputed": 0,
            "encoding_detected": "utf-8",
            "scale_ranges_detected": {},
            "warnings": [],
            "extra_variables": []
        }

    def _impute_missing(self, df: pd.DataFrame, protected=None) -> pd.DataFrame:
        """Imputación responsable: solo ítems numéricos/escala (mediana).

        Columnas protegidas (identificadores) y categóricas/texto NO se imputan;
        sus faltantes se conservan y quedan visibles en el diagnóstico.
        """
        protected = protected or set()
        imputations = 0
        by_col = {}
        for col in df.columns:
            if col in protected:
                continue
            missing_count = int(df[col].isna().sum())
            if missing_count <= 0:
                continue
            if pd.api.types.is_numeric_dtype(df[col]):
                median_val = df[col].median()
                if pd.isna(median_val):
                    continue  # columna totalmente vacía: no se inventan datos
                df[col] = df[col].fillna(median_val)
                imputations += missing_count
                by_col[col] = missing_count
            # categóricas/texto: se preservan los NaN (no se imputan)
        self.report["n_cells_imputed"] = int(imputations)
        self.report["imputation_by_column"] = by_col
        return df

    def _detect_likert_and_ranges(self, df: pd.DataFrame):
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                unique_vals = df[col].dropna().unique()
                if len(unique_vals) <= 10 and len(unique_vals) > 1:
                    is_integer = all(float(x).is_integer() for x in unique_vals)
                    if is_integer:
                        min_val = float(df[col].min())
                        max_val = float(df[col].max())
                        self.report["scale_ranges_detected"][col] = [min_val, max_val]

    def _map_columns(self, df: pd.DataFrame, reference_schema=None):
        mapped_columns = {}
        schema_cols = (
            reference_schema.columns.tolist()
            if isinstance(reference_schema, pd.DataFrame) else []
        )
        
        # Build list of known keys from DATA_DICTIONARY
        known_keys = ['ID']
        for cat, vars_dict in DATA_DICTIONARY.items():
            if cat == "Dimensiones de Bienestar y Salud Mental":
                 for dim, details in vars_dict.items():
                     if isinstance(details, dict):
                         known_keys.extend(details.get("Preguntas", []))
            else:
                if isinstance(vars_dict, dict):
                    known_keys.extend(vars_dict.keys())
        
        if not schema_cols:
            schema_cols = known_keys

        clean_schema_map = {normalize_text(sc): sc for sc in schema_cols}
        unmapped = 0
        mapped = 0

        for col in df.columns:
            if col in schema_cols:
                mapped_columns[col] = col
                mapped += 1
                continue
            
            norm_col = normalize_text(col)
            if norm_col in clean_schema_map:
                mapped_columns[col] = clean_schema_map[norm_col]
                mapped += 1
                continue
            
            # Remove prefixes like (SD), (LB), (BM)
            s_clean_col = re.sub(r'^\([a-z0-9]+\)', '', norm_col).strip()
            
            found = False
            for s_norm, s_orig in clean_schema_map.items():
                s_clean_schema = re.sub(r'^\([A-Za-z0-9]+\)', '', s_norm).strip()
                if s_clean_schema == s_clean_col:
                    mapped_columns[col] = s_orig
                    found = True
                    self.report["warnings"].append(f"Mapped {col} to {s_orig} ignoring prefixes.")
                    mapped += 1
                    break
            if found: continue

            # Fuzzy Match
            matches = difflib.get_close_matches(norm_col, clean_schema_map.keys(), n=1, cutoff=0.75)
            if matches:
                 best_match = clean_schema_map[matches[0]]
                 mapped_columns[col] = best_match
                 self.report["warnings"].append(f"Fuzzy mapped '{col}' to '{best_match}'.")
                 mapped += 1
            else:
                 mapped_columns[col] = col
                 unmapped += 1
                 self.report["extra_variables"].append(col)
                 # No se emite advertencia por columna: muchas columnas legítimas
                 # (indicadores/ítems de otros instrumentos) no siguen el esquema de
                 # bienestar y se conservan igual. El diagnóstico las clasifica aparte.

        df = df.rename(columns=mapped_columns)
        self.report["n_cols_mapped"] = mapped
        self.report["n_cols_unmapped"] = unmapped
        return df

    COVERAGE_MIN = 0.60  # cobertura mínima para aceptar una conversión de escala

    def process_complex_excel(self, file_path_or_buffer, reference_schema=None,
                              df_input=None, skip_unmapped=False, encoding='utf-8'):
        try:
            if df_input is not None:
                df = df_input.copy()
            else:
                df = pd.read_excel(file_path_or_buffer)
            if len(df) == 0:
                raise ValueError("El archivo está vacío.")

            self.report["n_rows_original"] = len(df)
            self.report["n_cols_original"] = len(df.columns)
            self.report["encoding_detected"] = encoding

            df = self._map_columns(df, reference_schema=reference_schema)

            # Opcional: descartar columnas no reconocidas
            if skip_unmapped:
                drop = [c for c in self.report["extra_variables"] if c in df.columns]
                df = df.drop(columns=drop)

            # Columnas protegidas: identificadores / metadatos → intactas
            protected = {c for c in df.columns if is_protected_column(c)}
            self.report["protected_columns"] = sorted(protected)

            # Transformación de escalas: cascada override → numérico → response-set
            scale_map = {}
            for col in df.columns:
                if col in protected:
                    continue
                series = df[col]
                if not pd.api.types.is_numeric_dtype(series):
                    codes, cov, method_o, _levels = try_column_override(col, series)
                    if codes is not None and cov >= self.COVERAGE_MIN:
                        df[col] = codes
                        scale_map[col] = {"method": method_o, "coverage": round(cov, 3)}
                    else:
                        typ, num = guess_type(series)
                        if typ == 'Continua':
                            df[col] = num
                            scale_map[col] = {"method": "numeric_flexible"}
                        else:
                            name, mapped, cov2 = best_response_set(series)
                            if cov2 >= self.COVERAGE_MIN:
                                df[col] = mapped
                                scale_map[col] = {"method": name, "coverage": round(cov2, 3)}
                            # else: se conserva como categórica/texto (sin pérdida)

                # Reverse-coding intrínseco (patrones), solo si quedó numérica
                is_rev, _ = is_reverse_column(col)
                if is_rev and pd.api.types.is_numeric_dtype(df[col]):
                    df[col] = reverse_numeric(df[col])
                    scale_map.setdefault(col, {})["reversed"] = True

            self.report["scale_map"] = scale_map
            self.report["n_cols_scaled"] = len(scale_map)

            df = self._impute_missing(df, protected=protected)
            self._detect_likert_and_ranges(df)

            self.report["n_rows_final"] = len(df)
            # Alias de compatibilidad (contratos de tests / diagnósticos)
            self.report["rows_cleaned"] = len(df)
            self.report["columns_processed"] = len(df.columns)
            return df, self.report

        except Exception as e:
            raise ValueError(f"Error procesando los datos: {str(e)}")


class DataCleaner:
    def __init__(self):
        self.report = {}

    def _detect_encoding(self, file_buffer):
        import chardet
        if hasattr(file_buffer, 'getvalue'):
             raw_data = file_buffer.getvalue()
        elif hasattr(file_buffer, 'read'):
             pos = file_buffer.tell()
             raw_data = file_buffer.read()
             file_buffer.seek(pos)
        else:
             with open(file_buffer, 'rb') as f:
                 raw_data = f.read()
        res = chardet.detect(raw_data)
        return res['encoding'] or 'utf-8'

    def process_file(self, file_buffer) -> tuple:
        """
        Procesa archivo y retorna (dataframe, ingestion_report).
        Wrapper seguro sobre clean_and_process.
        """
        report = {
            "n_rows_original": 0, "n_rows_final": 0,
            "n_cols_original": 0, "n_cols_mapped": 0,
            "n_cols_unmapped": 0, "n_cells_imputed": 0,
            "encoding_detected": "unknown",
            "unmapped_columns": [], "warnings": [],
            "success": False
        }
        try:
            df, inner_report = self.clean_and_process(file_buffer)
            # Merge inner report into our standard format
            report.update(inner_report)
            report["unmapped_columns"] = inner_report.get("extra_variables", [])
            report["success"] = True
            return df, report
        except ValueError as e:
            report["warnings"].append(str(e))
            return pd.DataFrame(), report
        except Exception as e:
            report["warnings"].append(f"Error crítico: {str(e)}")
            return pd.DataFrame(), report

    def clean_and_process(self, file_buffer):
        try:
            filename = getattr(file_buffer, 'name', '').lower()
            processor = ExcelProcessor()

            if filename.endswith(('.xlsx', '.xls')):
                 df, report = processor.process_complex_excel(file_buffer)
                 self.report = report
                 return df, self.report
            else:
                 if hasattr(file_buffer, 'read'):
                     pos = file_buffer.tell()
                     encoding = self._detect_encoding(file_buffer)
                     file_buffer.seek(pos)
                     df = pd.read_csv(file_buffer, dayfirst=False, encoding=encoding)
                 else:
                     encoding = self._detect_encoding(file_buffer)
                     df = pd.read_csv(file_buffer, dayfirst=False, encoding=encoding)
                 
                 df, report = processor.process_complex_excel(None, df_input=df, encoding=encoding)
                 self.report = report
                 return df, self.report

        except Exception as e:
            if "vacío" in str(e).lower() or "empty" in str(e).lower() or "no columns" in str(e).lower():
                 raise ValueError("El archivo proporcionado está vacío.")
            raise Exception(f"Error procesando data: {str(e)}")

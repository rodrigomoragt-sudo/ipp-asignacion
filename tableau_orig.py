"""
descarga_cuota_trad.py — Descarga la vista "Cuota Trad" desde Tableau Server,
filtra desc_pais = GUATEMALA y guarda el resultado en Parquet.

Basado en el patrón de descarga de tableau_orig.py, pero:
  - Usa el token 'presupuesto' (PAT distinto al del bot).
  - Descarga como CSV (datos tabulares de la vista) en lugar de Excel crosstab.
  - Convierte a Parquet con pandas/pyarrow -> archivo pequeño y de lectura rápida.

Uso:
    py -m pip install "tableauserverclient>=0.25" pandas pyarrow

    # Descarga por API toda Guatemala -> cuota_trad_guatemala.parquet
    py descarga_cuota_trad.py

    # Prueba rápida filtrando una sucursal:
    #   PowerShell:  $env:COD_SUCURSAL="17"; py descarga_cuota_trad.py
    # Procesar un CSV/crosstab ya bajado a mano en vez de la API:
    #   $env:SOURCE_CSV="Cuota Trad.csv"; py descarga_cuota_trad.py

Variables de entorno útiles:
    ANIOS          años a barrer (default "2025,2026"); filtro de campo YEAR(fecha_liquidacion)
    TIPO_VOLUMEN   qué tipos barrer (default "2,3" = Caja Unitaria + Valorizado;
                   "1,2,3" incluye Caja Física)
    COD_SUCURSAL   filtra por cod_sucursal (ej. "17")
    OUTPUT_PARQUET nombre del parquet de salida
    SOURCE_CSV     ruta de un CSV local a procesar (en vez de descargar)
    FORCE_API      "1" para descargar aunque exista SOURCE_CSV
    KEEP_STRINGS   "1" guarda todo como texto (sin conversión numérica)
    FORCE_DECIMAL  "comma"|"dot" fuerza el separador decimal en todas las columnas
"""

from __future__ import annotations

import io
import os
import re
import sys

import pandas as pd

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
# IMPORTANTE: Configurar estas variables en el entorno de producción
TOKEN_NAME  = os.environ.get("TABLEAU_TOKEN_NAME",  "")
TOKEN_VALUE = os.environ.get("TABLEAU_TOKEN_VALUE", "")
SERVER_URL  = os.environ.get("TABLEAU_SERVER_URL",  "https://bitableau.ajegroup.com/")
SITE_ID     = os.environ.get("TABLEAU_SITE_ID",     "Cam")

# Del breadcrumb: Inteligencia Comercial / Reportería CAM / Avance Cuota / Cuota Trad_
WORKBOOK_NAME = os.environ.get("TABLEAU_WORKBOOK", "Avance Cuota")
VIEW_NAME     = os.environ.get("TABLEAU_VIEW",     "Cuota Trad_")

# Filtros para la descarga por API (vf=valueFilter sobre la vista).
#   Siempre desc_pais=GUATEMALA. Opcional cod_sucursal vía env COD_SUCURSAL (ej. "17").
FILTERS = {"desc_pais": "GUATEMALA"}
_cod_suc = os.environ.get("COD_SUCURSAL", "").strip()
if _cod_suc:
    FILTERS["cod_sucursal"] = _cod_suc

# Fuerza la descarga por API aunque exista un CSV local (FORCE_API=1).
FORCE_API = os.environ.get("FORCE_API", "").strip() == "1"

OUTPUT_PARQUET = os.environ.get("OUTPUT_PARQUET", "cuota_trad_guatemala.parquet")

# Overrides opcionales para el parseo numérico:
#   FORCE_DECIMAL = "comma" | "dot"  -> fuerza el separador decimal en TODAS las columnas.
#   KEEP_STRINGS  = "1"              -> no convierte nada; todo queda como texto (100% seguro).
FORCE_DECIMAL = os.environ.get("FORCE_DECIMAL", "").strip().lower()
KEEP_STRINGS  = os.environ.get("KEEP_STRINGS", "").strip() == "1"


# ---------------------------------------------------------------------------
# Parseo numérico robusto (coma/punto decimal, miles, delimitador)
# ---------------------------------------------------------------------------

def _decode_bytes(raw: bytes) -> str:
    """Decodifica según el BOM. El crosstab manual de Tableau viene en UTF-16 LE."""
    if raw[:2] == b"\xff\xfe":
        return raw.decode("utf-16-le", errors="replace")
    if raw[:2] == b"\xfe\xff":
        return raw.decode("utf-16-be", errors="replace")
    if raw[:3] == b"\xef\xbb\xbf":
        return raw.decode("utf-8-sig", errors="replace")
    return raw.decode("utf-8", errors="replace")


def _sniff_delimiter(text: str) -> str:
    """Detecta el delimitador (TAB en el crosstab de Tableau) mirando la primera línea con datos."""
    for ln in text.splitlines():
        if ln.strip():
            counts = {sep: ln.count(sep) for sep in ("\t", ";", ",", "|")}
            best = max(counts, key=counts.get)
            if counts[best] > 0:
                return best
    return "\t"


def _find_header_row(lines: list[str], sep: str) -> int:
    """
    El crosstab de Tableau antepone una fila 'banner' antes de los encabezados reales.
    Devuelve el índice de la fila que contiene los nombres de campo (la que trae 'desc_pais').
    """
    for i, ln in enumerate(lines[:10]):
        campos = [c.strip().lower() for c in ln.split(sep)]
        if "desc_pais" in campos:
            return i
    return 0  # si no lo encuentra, asume la primera


def _detect_decimal(sample: list[str]) -> str | None:
    """
    Decide el separador decimal de una columna a partir de una muestra de valores.

    Formato REAL confirmado en este Tableau (verificado con datos):
      - Medidas (p.ej. [Volumen]): formato latino -> COMA = decimal, PUNTO = miles
        (ej. 1.154,333 = 1154.333 ; 0,606 = 0.606 ; 47,268 = 47.268).
      - Dimensiones tipo [desc_formato]: formato US -> PUNTO = decimal
        (ej. 0.250 = 0.25 ; 1.000 = 1.0).
    Por eso se decide COLUMNA POR COLUMNA. La coma nunca es separador de miles aquí,
    así 0,606 no se convierte por error en 606.

    Devuelve: '.' (punto decimal), ',' (coma decimal) o None (enteros).
    """
    if FORCE_DECIMAL == "comma":
        return ","
    if FORCE_DECIMAL == "dot":
        return "."

    has_comma = any("," in v for v in sample)
    has_dot   = any("." in v for v in sample)

    # Ambos separadores -> el que aparece más a la derecha es el decimal.
    # Cubre latino (1.154,333 -> ',') y US (1,234.56 -> '.').
    if has_comma and has_dot:
        for v in sample:
            if "," in v and "." in v:
                return "," if v.rfind(",") > v.rfind(".") else "."
        return ","

    # Solo comas: SIEMPRE decimal en este origen (0,606 = 0.606, no 606).
    if has_comma:
        return ","

    # Solo puntos: decimal (0.250 = 0.25). El punto no es miles en columnas de dimensión.
    if has_dot:
        return "."

    return None  # enteros sin separadores


def _normalize(v: str, dec: str | None) -> str:
    """Lleva un valor a formato canónico con '.' decimal y sin separadores de miles."""
    v = v.strip()
    if v == "":
        return v
    if dec == ",":
        return v.replace(".", "").replace(",", ".")   # . = miles, , = decimal
    if dec == ".":
        return v.replace(",", "")                      # , = miles, . = decimal
    if dec == "int_comma":
        return v.replace(",", "")                      # , = miles -> entero
    if dec == "int_dot":
        return v.replace(".", "")                      # . = miles -> entero
    return v


def _looks_like_code(sample: list[str]) -> bool:
    """Cero a la izquierda sin decimales -> es un código, NO convertir (007 != 7)."""
    return any(
        re.fullmatch(r"0\d+", v) for v in sample
    )


def _convert_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte a numérico solo las columnas que lo son de forma segura; reporta el criterio."""
    print("  Conversión numérica por columna:")
    for col in df.columns:
        s = df[col].astype(str).str.strip()
        sample = [v for v in s.tolist() if v not in ("", "nan", "None")]
        if not sample:
            print(f"    - {col:<24} texto (vacía)")
            continue

        # Los códigos (cod_*, INDEZX) se dejan como texto: nunca son operaciones
        # y suelen traer ceros a la izquierda (01, 007, 002) que no deben perderse.
        nombre = str(col).strip().lower()
        if nombre.startswith("cod_") or nombre in ("indezx", "index"):
            print(f"    - {col:<24} texto (columna de código)")
            continue

        if _looks_like_code(sample):
            print(f"    - {col:<24} texto (código con cero a la izquierda)")
            continue

        dec = _detect_decimal(sample)
        norm = s.map(lambda v: _normalize(v, dec))
        num = pd.to_numeric(norm.replace({"": None, "nan": None, "None": None}), errors="coerce")

        # ¿Cuántos valores reales se perdieron al convertir?
        original_no_vacio = norm.replace({"": None, "nan": None, "None": None}).notna()
        perdidos = int((original_no_vacio & num.isna()).sum())
        ratio = perdidos / max(1, int(original_no_vacio.sum()))

        if ratio <= 0.02:  # <=2% no convertible -> es numérica
            df[col] = num
            etiqueta = {",": "coma decimal", ".": "punto decimal",
                        "int_comma": "entero (coma=miles)", "int_dot": "entero (punto=miles)",
                        None: "entero"}[dec]
            print(f"    - {col:<24} NUMÉRICA [{etiqueta}]"
                  + (f"  ⚠ {perdidos} no convertibles" if perdidos else ""))
        else:
            print(f"    - {col:<24} texto ({ratio:.0%} no numérico)")
    return df


# ---------------------------------------------------------------------------
# Descarga
# ---------------------------------------------------------------------------

def _download_view_csv(workbook_name: str, view_name: str, filters: dict) -> bytes:
    """Sign-in, localiza la vista, aplica filtros y devuelve los datos como CSV (bytes)."""
    try:
        import tableauserverclient as TSC
    except ImportError:
        raise RuntimeError(
            "tableauserverclient no está instalado. "
            "Ejecuta: pip install tableauserverclient>=0.25"
        )

    auth   = TSC.PersonalAccessTokenAuth(TOKEN_NAME, TOKEN_VALUE, SITE_ID)
    server = TSC.Server(SERVER_URL, use_server_version=False)

    with server.auth.sign_in(auth):
        server.use_server_version()  # detecta la versión real post-auth

        all_wbs, _ = server.workbooks.get()
        wb = next((w for w in all_wbs if w.name == workbook_name), None)
        if not wb:
            disponibles = ", ".join(sorted(w.name for w in all_wbs))
            raise RuntimeError(
                f"Workbook no encontrado: {workbook_name!r}.\n"
                f"Workbooks disponibles: {disponibles}"
            )

        server.workbooks.populate_views(wb)
        view = next((v for v in wb.views if v.name == view_name), None)
        if not view:
            disponibles = ", ".join(v.name for v in wb.views)
            raise RuntimeError(
                f"Vista no encontrada: {view_name!r} en {workbook_name!r}.\n"
                f"Vistas disponibles: {disponibles}"
            )

        opts = TSC.CSVRequestOptions()
        opts.max_age = 0
        for campo, valor in filters.items():
            opts.vf(campo, valor)

        server.views.populate_csv(view, opts)
        raw = b"".join(view.csv)

    if not raw:
        raise RuntimeError("Tableau devolvió datos vacíos (¿el filtro dejó todo fuera?)")
    return raw


# ---------------------------------------------------------------------------
# Pipeline: bytes CSV -> DataFrame limpio -> Parquet
# ---------------------------------------------------------------------------

def csv_bytes_to_df(raw: bytes, mostrar_reporte: bool = True) -> pd.DataFrame:
    """Convierte los bytes crudos de un CSV/crosstab de Tableau a un DataFrame tipado."""
    # 1) Decodificar según BOM (UTF-16 en el crosstab manual) y detectar delimitador.
    text = _decode_bytes(raw)
    sep = _sniff_delimiter(text)
    print(f"  Delimitador detectado: {sep!r}")

    # 2) Localizar la fila de encabezados reales (saltando el banner del crosstab).
    lines = text.splitlines()
    hdr = _find_header_row(lines, sep)
    if hdr > 0:
        print(f"  Saltando {hdr} fila(s) de banner; encabezados en la fila {hdr + 1}.")

    # 3) Leer TODO como texto -> ningún valor se pierde ni se reinterpreta al leer.
    df = pd.read_csv(
        io.StringIO(text),
        sep=sep,
        dtype=str,
        keep_default_na=False,   # no convertir "" ni "NA" a NaN automáticamente
        engine="python",
        skiprows=hdr,
    )
    df.columns = [str(c).strip() for c in df.columns]  # 'desc_pais ' -> 'desc_pais'
    print(f"  DataFrame: {df.shape[0]:,} filas x {df.shape[1]} columnas.")

    # 4) Filtro de respaldo en cliente por si viniera algo distinto de GUATEMALA.
    if "desc_pais" in df.columns:
        antes = len(df)
        df = df[df["desc_pais"].astype(str).str.strip().str.upper() == "GUATEMALA"]
        if len(df) != antes:
            print(f"  Filtro cliente desc_pais=GUATEMALA: {antes:,} -> {len(df):,} filas.")

    # 5) Convertir a numérico de forma segura (o dejar todo como texto).
    if KEEP_STRINGS:
        print("  KEEP_STRINGS=1 -> todo se guarda como texto.")
    elif mostrar_reporte:
        df = _convert_numeric(df)
    else:
        # mismo parseo, sin imprimir el reporte columna por columna
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            df = _convert_numeric(df)

    return df


# ---------------------------------------------------------------------------
# Parámetro Tipo_Volumen — el campo calculado [Volumen] cambia de fórmula según
# este PARÁMETRO (no es un filtro de campo). La API lo fija con vf_Tipo_Volumen,
# así que barremos los 3 valores en una sola corrida y los unimos.
# ---------------------------------------------------------------------------
VOLUMEN_LABELS = {"1": "Caja Fisica", "2": "Caja Unitaria", "3": "Valorizado"}

# Por defecto baja Caja Unitaria (2) y Valorizado (3) — que son los que se necesitan.
# Puedes cambiarlo: TIPO_VOLUMEN="2" solo unitaria, o "1,2,3" para incluir Caja Física.
TIPOS_VOLUMEN = [t.strip() for t in os.environ.get("TIPO_VOLUMEN", "2,3").split(",") if t.strip()]

# Parámetro Tipo Moneda (1=Moneda Extranjera, 2=Moneda Local). El campo [cuota_moneda]
# solo lo usa en el VALORIZADO (tipo 3); en cajas es irrelevante. Por eso se envía SOLO
# cuando tipo=3. Default: Moneda Local (2).
MONEDA_VALORIZADO = os.environ.get("TIPO_MONEDA", "2").strip()
MONEDA_LABELS = {"1": "Moneda Extranjera", "2": "Moneda Local"}

# Año: FILTRO DE CAMPO (no parámetro). El nombre exacto del campo es YEAR(fecha_liquidacion).
# Por defecto baja 2025 y 2026. Cambia con ANIOS="2026" o "2024,2025,2026".
YEAR_FIELD = "YEAR(fecha_liquidacion)"
ANIOS = [a.strip() for a in os.environ.get("ANIOS", "2025,2026").split(",") if a.strip()]

# Mes: FILTRO DE CAMPO MONTH(fecha_liquidacion), valores numéricos 1..12. Algunas vistas
# (ej. "Cuota otros canales") traen el Mes fijado en uno solo por default; forzamos los 12
# para bajar el año completo. Inofensivo en vistas con Mes=Todo. Desactiva con TODOS_MESES=0.
MONTH_FIELD = "MONTH(fecha_liquidacion)"
TODOS_LOS_MESES = ",".join(str(i) for i in range(1, 13))
INCLUIR_TODOS_LOS_MESES = os.environ.get("TODOS_MESES", "1").strip() != "0"


# ---------------------------------------------------------------------------
# Main — por defecto descarga por API. Solo usa un CSV local si pasas SOURCE_CSV.
# ---------------------------------------------------------------------------

# Opcional: procesa un CSV/crosstab ya bajado a mano (SOURCE_CSV="Cuota Trad.csv").
LOCAL_CSV = os.environ.get("SOURCE_CSV", "").strip()


def _descargar() -> pd.DataFrame:
    """Baja cada (año × Tipo_Volumen) por API y los une con columnas anio/tipo_volumen/tipo_moneda."""
    partes = []
    primera = True
    for anio in ANIOS:
        for tipo in TIPOS_VOLUMEN:
            etiqueta = VOLUMEN_LABELS.get(tipo, tipo)
            filtros = dict(FILTERS)
            filtros[YEAR_FIELD] = anio               # filtro de campo (vf_YEAR(fecha_liquidacion))
            if INCLUIR_TODOS_LOS_MESES:
                filtros[MONTH_FIELD] = TODOS_LOS_MESES   # fuerza los 12 meses (override del default)
            filtros["Tipo_Volumen"] = tipo           # parámetro (vf_Tipo_Volumen)

            # Tipo Moneda solo importa en el Valorizado (tipo 3): fijar Moneda Local.
            moneda_et = ""
            if tipo == "3" and MONEDA_VALORIZADO:
                filtros["Tipo Moneda"] = MONEDA_VALORIZADO   # parámetro (vf_Tipo Moneda)
                moneda_et = MONEDA_LABELS.get(MONEDA_VALORIZADO, MONEDA_VALORIZADO)

            print(f"\n→ Año={anio} | Tipo_Volumen={tipo} ({etiqueta})"
                  + (f" | Tipo Moneda={MONEDA_VALORIZADO} ({moneda_et})" if moneda_et else ""))
            raw = _download_view_csv(WORKBOOK_NAME, VIEW_NAME, filtros)
            print(f"  {len(raw):,} bytes recibidos.")
            df = csv_bytes_to_df(raw, mostrar_reporte=primera)
            primera = False
            df.insert(0, "anio", anio)
            df.insert(1, "tipo_volumen_cod", tipo)
            df.insert(2, "tipo_volumen", etiqueta)
            df.insert(3, "tipo_moneda", moneda_et)   # vacío salvo en Valorizado
            partes.append(df)
            print(f"  {len(df):,} filas para {anio} / {etiqueta}.")
    return pd.concat(partes, ignore_index=True)


def main() -> int:
    if LOCAL_CSV and os.path.exists(LOCAL_CSV) and not FORCE_API:
        print(f"→ Procesando CSV local: {LOCAL_CSV}")
        raw = open(LOCAL_CSV, "rb").read()
        print(f"  {len(raw):,} bytes leídos.")
        df = csv_bytes_to_df(raw)
    else:
        print(f"→ Descargando vía API: vista {VIEW_NAME!r} del workbook {WORKBOOK_NAME!r}")
        print(f"  Barriendo Años = {ANIOS} × Tipo_Volumen = {TIPOS_VOLUMEN}")
        df = _descargar()

    df.to_parquet(OUTPUT_PARQUET, engine="pyarrow", index=False)
    print(f"\n✓ Guardado: {OUTPUT_PARQUET}  ({os.path.getsize(OUTPUT_PARQUET):,} bytes)")
    print(f"  Total: {len(df):,} filas.")
    if "anio" in df.columns and "tipo_volumen" in df.columns:
        print("  Por año / tipo_volumen:")
        for (a, tv), n in df.groupby(["anio", "tipo_volumen"]).size().items():
            print(f"    - {a} / {tv}: {n:,} filas")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"✗ Error: {exc}", file=sys.stderr)
        sys.exit(1)

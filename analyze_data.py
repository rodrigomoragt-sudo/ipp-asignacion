import pandas as pd
import json
from datetime import datetime

# Leer los excels
print("=" * 80)
print("ANALIZANDO ESTRUCTURA DE DATOS")
print("=" * 80)

# 1. Clientes CEDIS
print("\n1. CLIENTES CEDIS")
print("-" * 80)
df_cedis = pd.read_excel("Clientes cedis (2).xlsx")
print(f"Columnas: {df_cedis.columns.tolist()}")
print(f"Primeras filas:\n{df_cedis.head()}")
print(f"Forma: {df_cedis.shape}")

# 2. Clientes IPP
print("\n2. CLIENTES IPP")
print("-" * 80)
df_ipp = pd.read_excel("Clientes IPP_.xlsx")
print(f"Columnas: {df_ipp.columns.tolist()}")
print(f"Primeras filas:\n{df_ipp.head()}")
print(f"Forma: {df_ipp.shape}")

# 3. Data EF (Equipo Frio)
print("\n3. DATA EF (EQUIPO FRIO)")
print("-" * 80)
df_ef = pd.read_excel("Data EF - Julio 2026.xlsx")
print(f"Columnas: {df_ef.columns.tolist()}")
print(f"Primeras filas:\n{df_ef.head()}")
print(f"Forma: {df_ef.shape}")

# Información adicional
print("\n" + "=" * 80)
print("INFORMACIÓN ADICIONAL")
print("=" * 80)

# Códigos de zona (Supervisores)
if "Código Zona" in df_cedis.columns:
    print(f"\nZonas (Supervisores): {df_cedis['Código Zona'].unique().tolist()}")
    print(f"Total de supervisores: {df_cedis['Código Zona'].nunique()}")

# Segmentos
if "Segmento" in df_cedis.columns or "Cliente:Segmento" in df_cedis.columns:
    seg_col = "Segmento" if "Segmento" in df_cedis.columns else "Cliente:Segmento"
    print(f"\nSegmentos: {df_cedis[seg_col].unique().tolist()}")

# Tipos de datos
print("\nTipos de datos (CEDIS):")
print(df_cedis.dtypes)

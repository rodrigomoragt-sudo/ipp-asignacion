#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import traceback
import os

# Set encoding for stdout
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("Python version:", sys.version)
print("Current directory:", sys.path[0])

try:
    print("\n[1] Importing pandas...")
    import pandas as pd
    print("    OK - pandas imported")

    print("\n[2] Reading Excel files...")
    df_cedis = pd.read_excel("datos/Clientes CEDIS.xlsx")
    print(f"    OK - Clientes CEDIS: {len(df_cedis)} rows")

    df_ef = pd.read_excel("datos/Clientes Equipo Frío.xlsx")
    print(f"    OK - Clientes EF: {len(df_ef)} rows")

    print("\n[3] Importing GeneradorPlanVisitas...")
    from generar_plan import GeneradorPlanVisitas
    print("    OK - GeneradorPlanVisitas imported")

    print("\n[4] Initializing GeneradorPlanVisitas...")
    gen = GeneradorPlanVisitas()
    print("    OK - GeneradorPlanVisitas initialized successfully")
    print(f"      EF clients loaded: {len(gen.clientes_ef_ids)}")

    print("\n[5] Importing Flask...")
    from flask import Flask
    print("    OK - Flask imported")

    print("\n=== SUCCESS - Server should start without problems ===")

except Exception as e:
    print(f"\n=== ERROR: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
    sys.exit(1)

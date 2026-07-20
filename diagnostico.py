#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

print("=" * 60)
print("DIAGNOSTICO - Planificador de Visitas")
print("=" * 60)

print("\n1. Verificando archivos de datos...")
archivos = [
    "Clientes cedis (2).xlsx",
    "Clientes IPP_.xlsx",
    "Data EF - Julio 2026.xlsx"
]

for archivo in archivos:
    existe = os.path.exists(archivo)
    status = "[OK]" if existe else "[FALTA]"
    print(f"   {status} {archivo}")

print("\n2. Importando pandas...")
try:
    import pandas as pd
    print("   [OK] pandas importado")
except Exception as e:
    print(f"   [ERROR] pandas: {e}")
    sys.exit(1)

print("\n3. Cargando datos Excel...")
try:
    df_cedis = pd.read_excel("Clientes cedis (2).xlsx")
    print(f"   [OK] CEDIS: {len(df_cedis)} registros")
except Exception as e:
    print(f"   [ERROR] CEDIS: {e}")

try:
    df_ipp = pd.read_excel("Clientes IPP_.xlsx")
    print(f"   [OK] IPP: {len(df_ipp)} registros")
except Exception as e:
    print(f"   [ERROR] IPP: {e}")

try:
    df_ef = pd.read_excel("Data EF - Julio 2026.xlsx")
    print(f"   [OK] EF: {len(df_ef)} registros")
except Exception as e:
    print(f"   [ERROR] EF: {e}")

print("\n4. Inicializando GeneradorPlanVisitas...")
try:
    from generar_plan import GeneradorPlanVisitas
    print("   [OK] Modulo importado")

    gen = GeneradorPlanVisitas()
    print("   [OK] Generador inicializado exitosamente")

except Exception as e:
    print(f"   [ERROR] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n5. Generando plan de prueba...")
try:
    plan = gen.generar_plan(
        mes=7,
        ano=2026,
        inicio_visitas=5,
        visitas_por_dia=20,
        dias_exclusion=[28, 29, 30, 31],
        dias_sin_visita=[5, 6],
        supervisor=1
    )
    print(f"   [OK] Plan generado para zona 1")
    print(f"       Clientes planificados: {plan['supervisores']['1']['clientes_planificados']}")
except Exception as e:
    print(f"   [ERROR] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("DIAGNOSTICO COMPLETADO")
print("=" * 60)

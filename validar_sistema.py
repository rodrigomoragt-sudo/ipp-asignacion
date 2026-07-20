#!/usr/bin/env python3
"""
Script de validación del sistema de planificador de visitas
Verifica que todos los componentes estén funcionando correctamente
"""

import os
import sys
import json

def validar_archivos():
    """Validar que todos los archivos necesarios existan"""
    print("\n1. Validando archivos...")
    print("-" * 50)

    archivos_requeridos = {
        'Clientes cedis (2).xlsx': 'Base de datos CEDIS',
        'Clientes IPP_.xlsx': 'Base de datos IPP',
        'Data EF - Julio 2026.xlsx': 'Clientes con equipo frío',
        'index.html': 'Interfaz web',
        'app.py': 'Servidor Flask',
        'generar_plan.py': 'Motor de planificación',
        'config.json': 'Configuración del sistema'
    }

    archivos_encontrados = 0
    for archivo, descripcion in archivos_requeridos.items():
        existe = os.path.exists(archivo)
        estado = "[OK]" if existe else "[X]"
        print(f"  {estado} {archivo:<30} ({descripcion})")
        if existe:
            archivos_encontrados += 1

    print(f"\nTotal: {archivos_encontrados}/{len(archivos_requeridos)} archivos")
    return archivos_encontrados == len(archivos_requeridos)

def validar_dependencias():
    """Validar que las dependencias de Python estén instaladas"""
    print("\n2. Validando dependencias Python...")
    print("-" * 50)

    dependencias = ['pandas', 'openpyxl', 'flask']
    instaladas = 0

    for paquete in dependencias:
        try:
            __import__(paquete)
            print(f"  [OK] {paquete:<20} instalado")
            instaladas += 1
        except ImportError:
            print(f"  [X] {paquete:<20} NO instalado")

    print(f"\nTotal: {instaladas}/{len(dependencias)} dependencias")

    if instaladas < len(dependencias):
        print("\nInstalar dependencias faltantes con:")
        print("  pip install pandas openpyxl flask")
        return False

    return True

def validar_datos():
    """Validar que los datos se puedan leer correctamente"""
    print("\n3. Validando integridad de datos...")
    print("-" * 50)

    try:
        import pandas as pd

        # Validar CEDIS
        df_cedis = pd.read_excel("Clientes cedis (2).xlsx")
        print(f"  [OK] CEDIS: {len(df_cedis):,} registros")

        # Validar IPP
        df_ipp = pd.read_excel("Clientes IPP_.xlsx")
        print(f"  [OK] IPP: {len(df_ipp):,} registros")

        # Validar EF
        df_ef = pd.read_excel("Data EF - Julio 2026.xlsx")
        print(f"  [OK] EF: {len(df_ef):,} registros")

        return True

    except Exception as e:
        print(f"  [X] Error al leer datos: {e}")
        return False

def validar_generador():
    """Validar que el motor de planificación funciona"""
    print("\n4. Validando motor de planificación...")
    print("-" * 50)

    try:
        from generar_plan import GeneradorPlanVisitas

        gen = GeneradorPlanVisitas()
        print("  [OK] Generador inicializado")

        # Generar un plan pequeño de prueba
        plan = gen.generar_plan(
            mes=7,
            ano=2026,
            inicio_visitas=5,
            visitas_por_dia=20,
            dias_exclusion=[28, 29, 30, 31],
            dias_sin_visita=[5, 6],
            supervisor=1  # Solo zona 1 para prueba rapida
        )

        print("  [OK] Plan generado exitosamente")

        # Verificar estructura
        if 'supervisores' in plan and '1' in plan['supervisores']:
            zona = plan['supervisores']['1']
            print(f"  [OK] Zona 1: {zona['clientes_planificados']} clientes planificados")
            return True
        else:
            print("  [X] Estructura del plan incorrecta")
            return False

    except Exception as e:
        print(f"  [X] Error en el generador: {e}")
        return False

def mostrar_resumen(resultados):
    """Mostrar resumen de validación"""
    print("\n" + "=" * 50)
    print("RESUMEN DE VALIDACION")
    print("=" * 50)

    total = len(resultados)
    aprobadas = sum(1 for r in resultados if r)

    for i, resultado in enumerate(resultados, 1):
        estado = "[OK] APROBADA" if resultado else "[FALLO]"
        print(f"Validacion {i}: {estado}")

    print(f"\nResultado Final: {aprobadas}/{total} validaciones aprobadas")

    if aprobadas == total:
        print("\n¡Sistema listo para usar! Ejecuta:")
        print("  py app.py")
        print("\nO usa:")
        print("  install_y_ejecutar.bat")
        return True
    else:
        print("\nSoluciona los errores antes de continuar.")
        return False

if __name__ == "__main__":
    print("\n" + "="*50)
    print("VALIDADOR - Planificador de Visitas")
    print("Verifica integridad del sistema")
    print("="*50)

    resultados = [
        validar_archivos(),
        validar_dependencias(),
        validar_datos(),
        validar_generador()
    ]

    exito = mostrar_resumen(resultados)

    print("\n")
    sys.exit(0 if exito else 1)

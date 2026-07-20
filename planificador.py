import pandas as pd
import json
from datetime import datetime, timedelta
from collections import defaultdict

class PlanificadorVisitas:
    def __init__(self):
        self.df_cedis = pd.read_excel("Clientes cedis (2).xlsx")
        self.df_ipp = pd.read_excel("Clientes IPP_.xlsx")
        self.df_ef = pd.read_excel("Data EF - Julio 2026.xlsx")

        # Usar directamente las columnas originales
        self.cod_zona_col = 'Código Zona'
        self.seg_col = 'Cliente: Segmento'
        self.cod_cliente_col = 'Cliente: Código de Cliente'
        self.ruta_col = 'Ruta'
        self.dias_visita_col = 'Días de visita'

        print(f"Columnas CEDIS: {self.df_cedis.columns.tolist()}")
        print(f"Usando: cod_zona={self.cod_zona_col}, seg={self.seg_col}, cliente={self.cod_cliente_col}")

    def obtener_clientes_por_supervisor(self):
        """Retorna diccionario de clientes agrupados por supervisor (Código Zona)"""
        supervisores = defaultdict(list)

        # Obtener IDs de clientes con equipo frío
        ef_ids = set(self.df_ef['Cliente_id'].unique())

        # Procesar clientes CEDIS
        for idx, row in self.df_cedis.iterrows():
            codigo_cliente = row[self.cod_cliente_col]
            cliente = {
                'codigo': codigo_cliente,
                'zona': int(row[self.cod_zona_col]),
                'ruta': row[self.ruta_col],
                'segmento': row[self.seg_col] if pd.notna(row[self.seg_col]) else 'Mantener',
                'dias_visita': row[self.dias_visita_col] if pd.notna(row[self.dias_visita_col]) else '',
                'tiene_ef': codigo_cliente in ef_ids,
                'tiene_ipp': codigo_cliente in self.df_ipp['Cod Cliente'].values,
            }
            supervisores[cliente['zona']].append(cliente)

        return supervisores

    def procesar_datos_json(self):
        """Procesa datos y retorna como JSON para la interfaz web"""
        supervisores = self.obtener_clientes_por_supervisor()

        datos = {
            'cedis_total': len(self.df_cedis),
            'ipp_total': len(self.df_ipp),
            'ef_total': len(self.df_ef),
            'supervisores': {}
        }

        for zona, clientes in supervisores.items():
            ef_count = sum(1 for c in clientes if c['tiene_ef'])
            datos['supervisores'][int(zona)] = {
                'zona': int(zona),
                'total_clientes': len(clientes),
                'clientes_ef': ef_count,
                'clientes': len(clientes)
            }

        return datos

# Ejecutar análisis
print("Iniciando análisis de datos para planificador...")
planificador = PlanificadorVisitas()
datos = planificador.procesar_datos_json()

print("\nDatos resumidos:")
print(json.dumps(datos, indent=2))

# Guardar datos para la interfaz web
with open('datos_planificador.json', 'w', encoding='utf-8') as f:
    json.dump(datos, f, indent=2, ensure_ascii=False)

print("\nDatos guardados en datos_planificador.json")

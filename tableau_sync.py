"""
tableau_sync.py - Sincronización automática de datos desde Tableau
Extrae datos IPP del reporte "CLIENTES IPP" en Tableau
"""

import os
import pandas as pd
from datetime import datetime
from db_manager import DatabaseManager

# Configuración Tableau
# IMPORTANTE: Configurar estas variables en el entorno de producción
TABLEAU_TOKEN_NAME = os.environ.get("TABLEAU_TOKEN_NAME", "")
TABLEAU_TOKEN_VALUE = os.environ.get("TABLEAU_TOKEN_VALUE", "")
TABLEAU_SERVER_URL = os.environ.get("TABLEAU_SERVER_URL", "https://bitableau.ajegroup.com/")
TABLEAU_SITE_ID = os.environ.get("TABLEAU_SITE_ID", "Cam")

WORKBOOK_IPP = "GTM"
VIEW_IPP_CURRENT = "Clientes IPP"


class TableauSync:
    def __init__(self):
        self.db = DatabaseManager()

    def descargar_ipp_mes_actual(self, mes=None, ano=None):
        """Descarga clientes IPP del mes actual desde Tableau"""
        if not mes:
            mes = datetime.now().month
        if not ano:
            ano = datetime.now().year

        try:
            import tableauserverclient as TSC
        except ImportError:
            return {
                "success": False,
                "error": "tableauserverclient no instalado. Ejecuta: pip install tableauserverclient"
            }

        try:
            auth = TSC.PersonalAccessTokenAuth(TABLEAU_TOKEN_NAME, TABLEAU_TOKEN_VALUE, TABLEAU_SITE_ID)
            server = TSC.Server(TABLEAU_SERVER_URL, use_server_version=False)

            with server.auth.sign_in(auth):
                server.use_server_version()

                # Obtener workbook
                all_wbs, _ = server.workbooks.get()
                wb = next((w for w in all_wbs if w.name == WORKBOOK_IPP), None)
                if not wb:
                    return {"success": False, "error": f"Workbook '{WORKBOOK_IPP}' no encontrado"}

                # Obtener vista
                server.workbooks.populate_views(wb)
                view = next((v for v in wb.views if v.name == VIEW_IPP_CURRENT), None)
                if not view:
                    return {"success": False, "error": f"Vista '{VIEW_IPP_CURRENT}' no encontrada"}

                # Descargar como CSV con filtros
                opts = TSC.CSVRequestOptions()
                opts.max_age = 0
                # Filtrar por mes y año si es necesario
                # opts.vf("MONTH(fecha)", str(mes))
                # opts.vf("YEAR(fecha)", str(ano))

                server.views.populate_csv(view, opts)
                raw = b"".join(view.csv)

                if not raw:
                    return {"success": False, "error": "Tableau devolvió datos vacíos"}

                # Procesar CSV
                df = pd.read_csv(pd.io.common.BytesIO(raw), encoding='utf-8')

                # Normalizar columnas
                df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]

                # Guardar en DB
                version = self.db.registrar_carga(
                    'Clientes IPP Mes Actual',
                    len(df),
                    f"Tableau_IPP_{mes}_{ano}.csv",
                    f"Descargado de Tableau - Mes {mes}/{ano}"
                )

                # Limpiar nombres de columnas para compatibilidad
                if 'cod_cliente' in df.columns or 'codigo_cliente' in df.columns:
                    col_cod = 'cod_cliente' if 'cod_cliente' in df.columns else 'codigo_cliente'
                    df = df.rename(columns={col_cod: 'codigo_cliente'})

                df['version_id'] = version
                df['fecha_carga'] = datetime.now()

                # Guardar en SQLite
                conn = __import__('sqlite3').connect(self.db.db_path)
                df.to_sql('clientes_ipp_mes_actual', conn, if_exists='append', index=False)
                conn.close()

                return {
                    "success": True,
                    "version": version,
                    "registros": len(df),
                    "mes": mes,
                    "ano": ano
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def descargar_ipp_ultimos_meses(self, meses=[7, 8, 9], ano=2026):
        """Descarga clientes IPP de los últimos N meses desde Tableau"""
        try:
            import tableauserverclient as TSC
        except ImportError:
            return {
                "success": False,
                "error": "tableauserverclient no instalado"
            }

        try:
            auth = TSC.PersonalAccessTokenAuth(TABLEAU_TOKEN_NAME, TABLEAU_TOKEN_VALUE, TABLEAU_SITE_ID)
            server = TSC.Server(TABLEAU_SERVER_URL, use_server_version=False)

            dfs = []

            with server.auth.sign_in(auth):
                server.use_server_version()

                all_wbs, _ = server.workbooks.get()
                wb = next((w for w in all_wbs if w.name == WORKBOOK_IPP), None)
                if not wb:
                    return {"success": False, "error": f"Workbook no encontrado"}

                server.workbooks.populate_views(wb)
                view = next((v for v in wb.views if v.name == VIEW_IPP_CURRENT), None)
                if not view:
                    return {"success": False, "error": f"Vista no encontrada"}

                # Descargar para cada mes
                for mes in meses:
                    opts = TSC.CSVRequestOptions()
                    opts.max_age = 0
                    # Filtros opcionales por mes
                    server.views.populate_csv(view, opts)
                    raw = b"".join(view.csv)

                    if raw:
                        df = pd.read_csv(pd.io.common.BytesIO(raw), encoding='utf-8')
                        df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]
                        df['mes_original'] = mes
                        dfs.append(df)

            if not dfs:
                return {"success": False, "error": "No se descargaron datos"}

            df_combined = pd.concat(dfs, ignore_index=True)

            version = self.db.registrar_carga(
                'Clientes IPP Últimos 3 Meses',
                len(df_combined),
                f"Tableau_IPP_3meses_{ano}.csv",
                f"Descargado de Tableau - Últimos 3 meses"
            )

            df_combined['version_id'] = version
            df_combined['fecha_carga'] = datetime.now()

            conn = __import__('sqlite3').connect(self.db.db_path)
            df_combined.to_sql('clientes_ipp_3meses', conn, if_exists='append', index=False)
            conn.close()

            return {
                "success": True,
                "version": version,
                "registros": len(df_combined),
                "meses": meses,
                "ano": ano
            }

        except Exception as e:
            return {"success": False, "error": str(e)}


if __name__ == "__main__":
    sync = TableauSync()
    print("Descargando IPP Mes Actual...")
    resultado = sync.descargar_ipp_mes_actual()
    print(resultado)

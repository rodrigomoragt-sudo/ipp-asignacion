"""
tableau_sync.py - Sincronización automática de datos IPP desde Tableau

Reemplaza la carga manual de "Clientes IPP Mes Actual.xlsx" y
"Clientes IPP Últimos 3 Meses.xlsx": descarga la vista "Clientes IPP"
(workbook GTM) directamente desde Tableau Server, filtrando por mes(es)
y año elegidos, y la guarda vía db_manager (snapshot + historial +
archivo canónico).
"""

import os
import io
import pandas as pd
from db_manager import DatabaseManager

# Configuración Tableau — usar variables de entorno, nunca hardcodear.
TABLEAU_TOKEN_NAME = os.environ.get("TABLEAU_TOKEN_NAME", "")
TABLEAU_TOKEN_VALUE = os.environ.get("TABLEAU_TOKEN_VALUE", "")
TABLEAU_SERVER_URL = os.environ.get("TABLEAU_SERVER_URL", "https://bitableau.ajegroup.com/")
TABLEAU_SITE_ID = os.environ.get("TABLEAU_SITE_ID", "Cam")

WORKBOOK_IPP = "GTM"
VIEW_IPP = "Clientes IPP"

# Nombres para mostrar/loguear (español)
MESES_NOMBRE = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
    7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}

# El filtro "Mes" de la vista en Tableau espera el nombre del mes en INGLÉS
# (confirmado probando contra el servidor: "Julio" no filtra, "July" sí).
MESES_FILTRO_TABLEAU = {
    1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
    7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December",
}


class TableauSync:
    def __init__(self):
        self.db = DatabaseManager()

    def _validar_credenciales(self):
        if not TABLEAU_TOKEN_NAME or not TABLEAU_TOKEN_VALUE:
            return {
                "success": False,
                "error": (
                    "Credenciales de Tableau no configuradas. Define las variables de "
                    "entorno TABLEAU_TOKEN_NAME y TABLEAU_TOKEN_VALUE."
                ),
            }
        return None

    def _descargar_vista_csv(self, ano, meses):
        """Sign-in a Tableau, aplica filtros Año/Mes sobre la vista Clientes IPP y devuelve un DataFrame."""
        import tableauserverclient as TSC

        auth = TSC.PersonalAccessTokenAuth(TABLEAU_TOKEN_NAME, TABLEAU_TOKEN_VALUE, TABLEAU_SITE_ID)
        server = TSC.Server(TABLEAU_SERVER_URL, use_server_version=False)

        with server.auth.sign_in(auth):
            server.use_server_version()

            all_wbs, _ = server.workbooks.get(TSC.RequestOptions(pagesize=1000))
            wb = next((w for w in all_wbs if w.name == WORKBOOK_IPP), None)
            if not wb:
                disponibles = ", ".join(sorted(w.name for w in all_wbs))
                raise RuntimeError(f"Workbook '{WORKBOOK_IPP}' no encontrado. Disponibles: {disponibles}")

            server.workbooks.populate_views(wb)
            view = next((v for v in wb.views if v.name == VIEW_IPP), None)
            if not view:
                disponibles = ", ".join(v.name for v in wb.views)
                raise RuntimeError(f"Vista '{VIEW_IPP}' no encontrada. Disponibles: {disponibles}")

            opts = TSC.CSVRequestOptions()
            opts.max_age = 0
            opts.vf("Año", str(ano))
            opts.vf("Mes", ",".join(MESES_FILTRO_TABLEAU[m] for m in meses))

            server.views.populate_csv(view, opts)
            raw = b"".join(view.csv)

        if not raw:
            raise RuntimeError("Tableau devolvió datos vacíos para los filtros indicados.")

        df = pd.read_csv(io.BytesIO(raw), encoding="utf-8-sig")
        df.columns = [str(c).strip() for c in df.columns]
        return df

    def descargar_ipp_mes_actual(self, mes, ano):
        """Descarga clientes IPP encuestados en un mes específico -> tabla 'Clientes IPP Mes Actual'."""
        error = self._validar_credenciales()
        if error:
            return error

        try:
            df = self._descargar_vista_csv(ano, [mes])
            resultado = self.db.guardar_snapshot_y_actualizar(
                "Clientes IPP Mes Actual", df,
                archivo_original_nombre=f"Tableau_{MESES_NOMBRE[mes]}_{ano}.csv",
                origen="tableau",
                notas=f"Sync automático desde Tableau — {MESES_NOMBRE[mes]} {ano}",
            )
            return {"success": True, "mes": mes, "ano": ano, **resultado}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def descargar_ipp_ultimos_meses(self, meses, ano):
        """Descarga clientes IPP para varios meses -> tabla 'Clientes IPP Últimos 3 Meses'."""
        error = self._validar_credenciales()
        if error:
            return error

        try:
            df = self._descargar_vista_csv(ano, meses)
            nombres_meses = ", ".join(MESES_NOMBRE[m] for m in meses)
            resultado = self.db.guardar_snapshot_y_actualizar(
                "Clientes IPP Últimos 3 Meses", df,
                archivo_original_nombre=f"Tableau_{'-'.join(str(m) for m in meses)}_{ano}.csv",
                origen="tableau",
                notas=f"Sync automático desde Tableau — {nombres_meses} {ano}",
            )
            return {"success": True, "meses": meses, "ano": ano, **resultado}
        except Exception as e:
            return {"success": False, "error": str(e)}


if __name__ == "__main__":
    from datetime import datetime
    sync = TableauSync()
    hoy = datetime.now()
    print(f"Descargando IPP mes actual ({hoy.month}/{hoy.year})...")
    print(sync.descargar_ipp_mes_actual(hoy.month, hoy.year))

import sqlite3
import json
from datetime import datetime
from pathlib import Path
import pandas as pd

class DatabaseManager:
    def __init__(self, db_path="datos_planificador.db"):
        self.db_path = db_path
        self.conn = None
        self.init_db()

    def init_db(self):
        """Inicializa base de datos con tablas"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Tabla de historial de cargas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS carga_historial (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tabla_nombre TEXT NOT NULL,
                fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                num_registros INTEGER,
                archivo_nombre TEXT,
                version_numero INTEGER,
                estado TEXT,
                notas TEXT
            )
        """)

        # Tabla para Clientes CEDIS
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes_cedis (
                id INTEGER PRIMARY KEY,
                codigo_cliente TEXT UNIQUE,
                nombre_cliente TEXT,
                zona INTEGER,
                ruta INTEGER,
                segmento TEXT,
                compania TEXT,
                sucursal TEXT,
                version_id INTEGER,
                fecha_carga TIMESTAMP
            )
        """)

        # Tabla para Clientes Equipo Frío
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes_equipo_frio (
                id INTEGER PRIMARY KEY,
                cliente_id TEXT UNIQUE,
                nombre_cliente TEXT,
                zona INTEGER,
                ruta INTEGER,
                segmento TEXT,
                marca TEXT,
                modelo TEXT,
                version_id INTEGER,
                fecha_carga TIMESTAMP
            )
        """)

        # Tabla para Clientes IPP Mes Actual
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes_ipp_mes_actual (
                id INTEGER PRIMARY KEY,
                codigo_cliente TEXT,
                nombre_cliente TEXT,
                zona INTEGER,
                ruta INTEGER,
                segmento TEXT,
                mes_encuesta INTEGER,
                ano_encuesta INTEGER,
                version_id INTEGER,
                fecha_carga TIMESTAMP
            )
        """)

        # Tabla para Clientes IPP Últimos 3 Meses
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes_ipp_3meses (
                id INTEGER PRIMARY KEY,
                codigo_cliente TEXT,
                nombre_cliente TEXT,
                zona INTEGER,
                ruta INTEGER,
                segmento TEXT,
                mes_encuesta INTEGER,
                ano_encuesta INTEGER,
                version_id INTEGER,
                fecha_carga TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def registrar_carga(self, tabla_nombre, num_registros, archivo_nombre=None, notas=None):
        """Registra una carga en el historial"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Obtener siguiente versión
        cursor.execute(
            "SELECT MAX(version_numero) FROM carga_historial WHERE tabla_nombre = ?",
            (tabla_nombre,)
        )
        max_version = cursor.fetchone()[0] or 0
        version_numero = max_version + 1

        cursor.execute("""
            INSERT INTO carga_historial
            (tabla_nombre, num_registros, archivo_nombre, version_numero, estado, notas)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (tabla_nombre, num_registros, archivo_nombre, version_numero, "OK", notas))

        conn.commit()
        conn.close()

        return version_numero

    def cargar_excel_a_db(self, tabla_nombre, archivo_path, encoding='utf-8'):
        """Carga datos de Excel a la base de datos"""
        try:
            df = pd.read_excel(archivo_path)
            version_id = self.registrar_carga(
                tabla_nombre,
                len(df),
                Path(archivo_path).name,
                "Cargado desde Excel"
            )

            # Mapeo de tablas
            tabla_db = {
                'Clientes CEDIS': 'clientes_cedis',
                'Clientes Equipo Frío': 'clientes_equipo_frio',
                'Clientes IPP Mes Actual': 'clientes_ipp_mes_actual',
                'Clientes IPP Últimos 3 Meses': 'clientes_ipp_3meses'
            }.get(tabla_nombre)

            if not tabla_db:
                raise ValueError(f"Tabla desconocida: {tabla_nombre}")

            # Normalizar columnas
            df.columns = [col.lower().replace(' ', '_').replace('á', 'a').replace('é', 'e')
                         for col in df.columns]
            df['version_id'] = version_id
            df['fecha_carga'] = datetime.now()

            conn = sqlite3.connect(self.db_path)
            df.to_sql(tabla_db, conn, if_exists='append', index=False)
            conn.close()

            return {"success": True, "version": version_id, "registros": len(df)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def obtener_historial(self, tabla_nombre=None):
        """Obtiene historial de cargas"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if tabla_nombre:
            cursor.execute("""
                SELECT id, tabla_nombre, fecha_carga, num_registros, archivo_nombre,
                       version_numero, estado, notas
                FROM carga_historial
                WHERE tabla_nombre = ?
                ORDER BY fecha_carga DESC
            """, (tabla_nombre,))
        else:
            cursor.execute("""
                SELECT id, tabla_nombre, fecha_carga, num_registros, archivo_nombre,
                       version_numero, estado, notas
                FROM carga_historial
                ORDER BY fecha_carga DESC
            """)

        historial = cursor.fetchall()
        conn.close()

        return historial

    def obtener_datos_tabla(self, tabla_nombre, version_id=None):
        """Obtiene datos de una tabla específica"""
        tabla_db = {
            'Clientes CEDIS': 'clientes_cedis',
            'Clientes Equipo Frío': 'clientes_equipo_frio',
            'Clientes IPP Mes Actual': 'clientes_ipp_mes_actual',
            'Clientes IPP Últimos 3 Meses': 'clientes_ipp_3meses'
        }.get(tabla_nombre)

        if not tabla_db:
            return None

        conn = sqlite3.connect(self.db_path)

        if version_id:
            df = pd.read_sql_query(
                f"SELECT * FROM {tabla_db} WHERE version_id = ? ORDER BY fecha_carga DESC",
                conn,
                params=(version_id,)
            )
        else:
            df = pd.read_sql_query(
                f"SELECT * FROM {tabla_db} WHERE version_id = (SELECT MAX(version_id) FROM {tabla_db})",
                conn
            )

        conn.close()
        return df

    def limpiar_tabla(self, tabla_nombre, excepto_version=None):
        """Limpia datos antiguos manteniendo opcionalmente una versión"""
        tabla_db = {
            'Clientes CEDIS': 'clientes_cedis',
            'Clientes Equipo Frío': 'clientes_equipo_frio',
            'Clientes IPP Mes Actual': 'clientes_ipp_mes_actual',
            'Clientes IPP Últimos 3 Meses': 'clientes_ipp_3meses'
        }.get(tabla_nombre)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if excepto_version:
            cursor.execute(f"DELETE FROM {tabla_db} WHERE version_id != ?", (excepto_version,))
        else:
            cursor.execute(f"DELETE FROM {tabla_db}")

        conn.commit()
        conn.close()


if __name__ == "__main__":
    db = DatabaseManager()
    print("Base de datos inicializada correctamente")

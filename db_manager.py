"""
db_manager.py - Gestión de historial de cargas de datos con SQLite

Cada carga (upload manual o sync desde Tableau) queda registrada como una
fila nueva en el historial (nunca se sobreescribe), y se guarda un snapshot
completo del archivo en datos/_history/<tabla>/. Además se actualiza el
archivo canónico en datos/<Tabla>.xlsx, que es el que lee generar_plan.py.

Todo (excels canónicos, snapshots, base de datos SQLite) vive bajo datos/
a propósito: en un despliegue en contenedor, montar UN solo volumen
persistente ahí adentro es suficiente para que nada se pierda al reiniciar.
"""

import sqlite3
import shutil
import os
import time
import uuid
from datetime import datetime
from pathlib import Path

# Todo lo que necesita sobrevivir un restart del contenedor vive bajo
# datos/: el Excel canónico (obligatorio, generar_plan.py lo lee de ahí),
# el historial de snapshots y la base de datos SQLite. Así, en producción
# (Easypanel u otro host de contenedores) basta con montar UN volumen
# persistente en /app/datos para que nada se pierda entre restarts —
# sin volumen, cualquier archivo subido o sincronizado desaparece en el
# siguiente restart/redeploy, aunque la subida en sí haya "funcionado".
DATOS_DIR = Path("datos")
HISTORY_DIR = DATOS_DIR / "_history"
DB_PATH = str(DATOS_DIR / "planificador.db")

# Nombre de tabla lógica -> nombre de archivo canónico esperado por generar_plan.py
TABLAS = {
    "Clientes CEDIS": "Clientes CEDIS.xlsx",
    "Clientes Equipo Frío": "Clientes Equipo Frío.xlsx",
    "Clientes IPP Mes Actual": "Clientes IPP Mes Actual.xlsx",
    "Clientes IPP Últimos 3 Meses": "Clientes IPP Últimos 3 Meses.xlsx",
}


def _reemplazar_con_reintentos(tmp_path, destino, intentos=5, espera=0.4):
    """
    os.replace(tmp_path, destino) con reintentos: en Windows el antivirus a
    veces bloquea brevemente un .xlsx recién escrito (WinError 5 / 32).
    """
    for intento in range(1, intentos + 1):
        try:
            os.replace(tmp_path, destino)  # atómico en Windows y POSIX
            return
        except PermissionError:
            if intento == intentos:
                raise
            time.sleep(espera)


def _copiar_atomico(origen, destino, intentos=5, espera=0.4):
    """
    Copia origen -> destino sin dejar nunca un archivo a medias en destino:
    escribe a un temporal ÚNICO (sufijo aleatorio) en el mismo directorio y
    hace un rename atómico. El sufijo único evita que dos cargas concurrentes
    (dos requests, o dos procesos del servidor corriendo a la vez) se pisen
    escribiendo el mismo archivo temporal. Si el proceso se interrumpe a
    mitad de camino, destino queda intacto o completamente reemplazado,
    nunca corrupto.
    """
    destino = Path(destino)
    tmp_destino = destino.with_name(f".{destino.name}.{uuid.uuid4().hex[:8]}.tmp")
    try:
        shutil.copy(origen, tmp_destino)
        _reemplazar_con_reintentos(tmp_destino, destino, intentos, espera)
    finally:
        tmp_destino.unlink(missing_ok=True)  # por si el replace falló y quedó huérfano


def _slug(tabla_nombre: str) -> str:
    return (
        tabla_nombre.lower()
        .replace(" ", "_")
        .replace("í", "i").replace("é", "e").replace("á", "a")
        .replace("ó", "o").replace("ú", "u")
    )


class DatabaseManager:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        DATOS_DIR.mkdir(parents=True, exist_ok=True)
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS carga_historial (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tabla_nombre TEXT NOT NULL,
                fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                num_registros INTEGER,
                archivo_original_nombre TEXT,
                ruta_snapshot TEXT,
                version_numero INTEGER,
                origen TEXT,
                estado TEXT,
                notas TEXT
            )
        """)
        conn.commit()
        conn.close()

    def _siguiente_version(self, cursor, tabla_nombre):
        cursor.execute(
            "SELECT MAX(version_numero) FROM carga_historial WHERE tabla_nombre = ?",
            (tabla_nombre,),
        )
        max_version = cursor.fetchone()[0] or 0
        return max_version + 1

    def registrar_carga(self, tabla_nombre, snapshot_path, num_registros,
                         archivo_original_nombre=None, origen="upload", notas=None):
        """Inserta una fila nueva de historial (nunca reemplaza filas anteriores)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        version_numero = self._siguiente_version(cursor, tabla_nombre)

        cursor.execute("""
            INSERT INTO carga_historial
            (tabla_nombre, num_registros, archivo_original_nombre, ruta_snapshot,
             version_numero, origen, estado, notas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (tabla_nombre, num_registros, archivo_original_nombre, str(snapshot_path),
              version_numero, origen, "OK", notas))

        conn.commit()
        version_id = cursor.lastrowid
        conn.close()
        return version_id, version_numero

    def guardar_snapshot_y_actualizar(self, tabla_nombre, df, archivo_original_nombre=None,
                                       origen="upload", notas=None):
        """
        Guarda snapshot con fidelidad completa (columnas originales), actualiza
        el archivo canónico en datos/ y registra la carga en el historial.
        """
        if tabla_nombre not in TABLAS:
            raise ValueError(f"Tabla desconocida: {tabla_nombre}")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        version_numero = self._siguiente_version(cursor, tabla_nombre)
        conn.close()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        tabla_dir = HISTORY_DIR / _slug(tabla_nombre)
        tabla_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = tabla_dir / f"v{version_numero}_{timestamp}.xlsx"

        # Escribir snapshot a un temporal único y renombrar: nunca queda un .xlsx a medias
        tmp_snapshot = snapshot_path.with_name(f".{snapshot_path.name}.{uuid.uuid4().hex[:8]}.tmp")
        try:
            df.to_excel(tmp_snapshot, index=False)
            _reemplazar_con_reintentos(tmp_snapshot, snapshot_path)
        finally:
            tmp_snapshot.unlink(missing_ok=True)

        # Actualizar archivo canónico que lee generar_plan.py (copia atómica desde el snapshot ya validado)
        canonical_path = DATOS_DIR / TABLAS[tabla_nombre]
        _copiar_atomico(snapshot_path, canonical_path)

        version_id, version_numero = self.registrar_carga(
            tabla_nombre, snapshot_path, len(df),
            archivo_original_nombre, origen, notas
        )

        return {
            "version_id": version_id,
            "version_numero": version_numero,
            "registros": len(df),
            "snapshot": str(snapshot_path),
        }

    def cargar_excel_subido(self, tabla_nombre, archivo_path_temporal, archivo_original_nombre):
        """
        Procesa un archivo Excel subido por el usuario para una tabla específica.
        Copia el archivo tal cual (sin pasar por pandas) para snapshot y canónico:
        más rápido y preserva el archivo original con fidelidad total.
        """
        import pandas as pd
        if tabla_nombre not in TABLAS:
            raise ValueError(f"Tabla desconocida: {tabla_nombre}")

        # Validar que el archivo es un Excel legible y contar registros
        df = pd.read_excel(archivo_path_temporal)
        num_registros = len(df)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        version_numero = self._siguiente_version(cursor, tabla_nombre)
        conn.close()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        tabla_dir = HISTORY_DIR / _slug(tabla_nombre)
        tabla_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = tabla_dir / f"v{version_numero}_{timestamp}.xlsx"
        canonical_path = DATOS_DIR / TABLAS[tabla_nombre]

        _copiar_atomico(archivo_path_temporal, snapshot_path)
        _copiar_atomico(archivo_path_temporal, canonical_path)

        version_id, version_numero = self.registrar_carga(
            tabla_nombre, snapshot_path, num_registros,
            archivo_original_nombre, origen="upload"
        )

        return {
            "version_id": version_id,
            "version_numero": version_numero,
            "registros": num_registros,
            "snapshot": str(snapshot_path),
        }

    def obtener_historial(self, tabla_nombre=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if tabla_nombre:
            cursor.execute("""
                SELECT id, tabla_nombre, fecha_carga, num_registros,
                       archivo_original_nombre, ruta_snapshot, version_numero,
                       origen, estado, notas
                FROM carga_historial
                WHERE tabla_nombre = ?
                ORDER BY fecha_carga DESC
            """, (tabla_nombre,))
        else:
            cursor.execute("""
                SELECT id, tabla_nombre, fecha_carga, num_registros,
                       archivo_original_nombre, ruta_snapshot, version_numero,
                       origen, estado, notas
                FROM carga_historial
                ORDER BY fecha_carga DESC
            """)
        columnas = [d[0] for d in cursor.description]
        filas = [dict(zip(columnas, row)) for row in cursor.fetchall()]
        conn.close()
        return filas

    def obtener_snapshot_path(self, version_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT ruta_snapshot, tabla_nombre FROM carga_historial WHERE id = ?", (version_id,))
        row = cursor.fetchone()
        conn.close()
        return row  # (ruta_snapshot, tabla_nombre) o None

    def restaurar_version(self, version_id):
        """Copia un snapshot histórico como el archivo canónico actual (rollback)."""
        row = self.obtener_snapshot_path(version_id)
        if not row:
            raise ValueError("Versión no encontrada")
        ruta_snapshot, tabla_nombre = row
        if tabla_nombre not in TABLAS:
            raise ValueError(f"Tabla desconocida: {tabla_nombre}")

        canonical_path = DATOS_DIR / TABLAS[tabla_nombre]
        _copiar_atomico(ruta_snapshot, canonical_path)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT num_registros FROM carga_historial WHERE id = ?", (version_id,))
        num_registros = cursor.fetchone()[0]
        conn.close()

        version_id_nueva, version_numero = self.registrar_carga(
            tabla_nombre, ruta_snapshot, num_registros,
            archivo_original_nombre=f"Restaurado de v.{version_id}",
            origen="rollback",
            notas=f"Restaurada versión #{version_id}"
        )
        return {"version_id": version_id_nueva, "version_numero": version_numero, "tabla": tabla_nombre}


if __name__ == "__main__":
    db = DatabaseManager()
    print("Base de datos inicializada correctamente")
    print("Historial actual:", db.obtener_historial())

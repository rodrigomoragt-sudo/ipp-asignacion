from dotenv import load_dotenv
load_dotenv()  # carga .env (credenciales de Tableau, etc.) antes de leer os.environ abajo

from flask import Flask, render_template, jsonify, request, send_file
from generar_plan import GeneradorPlanVisitas
from db_manager import DatabaseManager, TABLAS
import json
import os
import calendar
import tempfile
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.dirname(__file__)

db = DatabaseManager()

# Inicializar generador
try:
    print("Cargando GeneradorPlanVisitas...")
    generador = GeneradorPlanVisitas()
    datos_cargados = True
    print("GeneradorPlanVisitas cargado correctamente")
except Exception as e:
    print(f"Error al cargar GeneradorPlanVisitas: {e}")
    import traceback
    traceback.print_exc()
    datos_cargados = False
    generador = None

@app.route('/')
def index():
    """Sin cache: durante desarrollo el HTML/JS cambia seguido y el navegador
    no debe servir una versión vieja después de un cambio."""
    response = app.response_class(
        open('index.html', 'r', encoding='utf-8').read(),
        mimetype='text/html'
    )
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    return response

@app.route('/plantillas/<filename>')
def descargar_plantilla(filename):
    """Servir plantillas desde carpeta plantillas/"""
    try:
        return send_file(
            os.path.join('plantillas', filename),
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except FileNotFoundError:
        return jsonify({'error': 'Plantilla no encontrada'}), 404

@app.route('/api/data', methods=['GET'])
def obtener_datos():
    """
    Retorna estadísticas del dashboard calculadas en vivo desde los datos
    cargados actualmente en memoria (generador) — no desde un archivo
    estático, para que subir/sincronizar una tabla se refleje de inmediato.
    """
    if not datos_cargados or not generador:
        return jsonify({'error': 'No hay datos disponibles'}), 500

    try:
        df_cedis = generador.df_cedis
        zonas = df_cedis['Código Zona'].astype(int)
        codigos = df_cedis['Cliente: Código de Cliente'].astype(int)
        es_ef = codigos.isin(generador.clientes_ef_ids)

        supervisores = {}
        totales = codigos.groupby(zonas).count()
        ef_por_zona = codigos[es_ef].groupby(zonas[es_ef]).count()
        for zona, total in totales.items():
            supervisores[str(zona)] = {
                'zona': int(zona),
                'total_clientes': int(total),
                'clientes_ef': int(ef_por_zona.get(zona, 0)),
            }

        return jsonify({
            'cedis_total': len(df_cedis),
            'ef_total': len(generador.clientes_ef_ids),
            'ipp_mes_actual_total': len(generador.clientes_ipp_mes_actual),
            'ipp_3meses_total': len(generador.clientes_ipp_dict),
            'supervisores': supervisores,
        })
    except Exception as e:
        return jsonify({'error': f'Error calculando estadísticas: {e}'}), 500

@app.route('/api/generar-plan', methods=['POST'])
def generar_plan():
    """Genera un plan con los parámetros especificados"""
    if not datos_cargados or not generador:
        return jsonify({'error': 'Datos no cargados'}), 500

    try:
        datos = request.json

        mes = int(datos.get('mes', 7))
        ano = int(datos.get('ano', 2026))
        inicio_visitas = int(datos.get('inicio_visitas', 5))
        fin_visitas = int(datos.get('fin_visitas', 27))
        visitas_por_dia = int(datos.get('visitas_por_dia', 20))

        # Procesar días de exclusión
        # Si el usuario define fin_visitas, excluir automáticamente los días después
        num_dias_mes = calendar.monthrange(ano, mes)[1]  # Obtener días reales del mes
        dias_exclusion_raw = datos.get('dias_exclusion', [])

        if isinstance(dias_exclusion_raw, str):
            dias_exclusion = [int(d.strip()) for d in dias_exclusion_raw.split(',') if d.strip().isdigit()]
        else:
            dias_exclusion = [int(d) for d in dias_exclusion_raw if isinstance(d, (int, float)) and not (d != d)]  # Filtrar NaN

        # Agregar automáticamente días después del fin_visitas a la exclusión
        # IMPORTANTE: Respeta el fin_visitas especificado por el usuario
        for dia in range(fin_visitas + 1, num_dias_mes + 1):
            if dia not in dias_exclusion:
                dias_exclusion.append(dia)

        # Procesar días sin visita
        dias_sin_visita_raw = datos.get('dias_sin_visita', [5, 6])
        if isinstance(dias_sin_visita_raw, str):
            dias_sin_visita = [int(d.strip()) for d in dias_sin_visita_raw.split(',') if d.strip().isdigit()]
        else:
            dias_sin_visita = [int(d) for d in dias_sin_visita_raw if isinstance(d, (int, float)) and not (d != d)]  # Filtrar NaN

        supervisor = datos.get('supervisor', None)

        if supervisor == '' or supervisor == 'undefined':
            supervisor = None
        elif supervisor:
            supervisor = int(supervisor)

        plan = generador.generar_plan(
            mes=mes,
            ano=ano,
            inicio_visitas=inicio_visitas,
            fin_visitas=fin_visitas,
            visitas_por_dia=visitas_por_dia,
            dias_exclusion=dias_exclusion,
            dias_sin_visita=dias_sin_visita,
            supervisor=supervisor
        )

        # Limpiar plan de valores NaN/infinitos antes de serializar
        def limpiar_plan(obj):
            if isinstance(obj, dict):
                return {k: limpiar_plan(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [limpiar_plan(item) for item in obj]
            elif isinstance(obj, float):
                if obj != obj or obj == float('inf') or obj == float('-inf'):  # NaN o infinito
                    return None
                return obj
            else:
                return obj

        plan_limpio = limpiar_plan(plan)

        # Guardar plan para exportación
        with open('plan_actual.json', 'w', encoding='utf-8') as f:
            json.dump(plan_limpio, f, indent=2, ensure_ascii=False)

        return jsonify({
            'success': True,
            'plan': plan_limpio,
            'mensaje': 'Plan generado exitosamente'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/exportar-excel', methods=['POST'])
def exportar_excel():
    """Exporta el plan actual a Excel"""
    try:
        with open('plan_actual.json', 'r', encoding='utf-8') as f:
            plan = json.load(f)

        archivo = generador.exportar_excel(plan, 'plan_visitas_generado.xlsx')
        if not archivo or not os.path.exists(archivo):
            return jsonify({'error': 'Error al generar Excel'}), 500

        return send_file(
            archivo,
            as_attachment=True,
            download_name='plan_visitas.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except FileNotFoundError:
        return jsonify({'error': 'No hay plan generado. Genere uno primero.'}), 400
    except Exception as e:
        print(f"Error en exportar_excel: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/exportar-csv', methods=['POST'])
def exportar_csv():
    """Exporta el plan actual a CSV"""
    try:
        with open('plan_actual.json', 'r', encoding='utf-8') as f:
            plan = json.load(f)

        # Crear CSV
        csv_content = "Zona,Fecha,Dia,Cliente,Ruta,Clasificacion\n"

        for zona, datos in plan['supervisores'].items():
            for dia in datos['cronograma']:
                for visita in dia['visitas']:
                    csv_content += f"{zona},{dia['fecha']},{dia['dia_semana']},{visita['codigo_cliente']},{visita['ruta']},{visita['clasificacion']}\n"

        # Guardar archivo
        with open('plan_visitas.csv', 'w', encoding='utf-8') as f:
            f.write(csv_content)

        return send_file(
            'plan_visitas.csv',
            as_attachment=True,
            download_name='plan_visitas.csv',
            mimetype='text/csv'
        )

    except FileNotFoundError:
        return jsonify({'error': 'No hay plan generado.'}), 400
    except Exception as e:
        print(f"Error en exportar_csv: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/estadisticas', methods=['GET'])
def obtener_estadisticas():
    """Retorna estadísticas del plan generado"""
    try:
        with open('plan_actual.json', 'r', encoding='utf-8') as f:
            plan = json.load(f)

        stats = {
            'mes': plan['mes'],
            'ano': plan['ano'],
            'fecha_generacion': plan['fecha_generacion'],
            'total_supervisores': len(plan['supervisores']),
            'dias_habiles': plan['dias_habiles'],
            'total_clientes_planificados': 0,
            'resumen_por_segmento': {}
        }

        for zona, datos in plan['supervisores'].items():
            stats['total_clientes_planificados'] += datos['clientes_planificados']
            for seg, cantidad in datos['resumen_segmentos'].items():
                if seg not in stats['resumen_por_segmento']:
                    stats['resumen_por_segmento'][seg] = 0
                stats['resumen_por_segmento'][seg] += cantidad

        return jsonify(stats)

    except FileNotFoundError:
        return jsonify({'error': 'No hay plan generado'}), 400

def _recargar_generador():
    """Reinicia el generador para que tome los archivos canónicos más recientes"""
    global generador, datos_cargados
    try:
        generador = GeneradorPlanVisitas()
        datos_cargados = True
        return True, None
    except Exception as e:
        datos_cargados = False
        return False, str(e)


@app.route('/api/tablas', methods=['GET'])
def listar_tablas():
    """Lista las tablas disponibles para cargar/actualizar"""
    return jsonify({'tablas': list(TABLAS.keys())})


@app.route('/api/cargar-tabla', methods=['POST'])
def cargar_tabla():
    """
    Sube un Excel para UNA tabla específica elegida por el usuario.
    No importa el nombre del archivo: se guarda como nueva versión en el
    historial y se actualiza el archivo canónico que usa el planificador.
    """
    try:
        tabla_nombre = request.form.get('tabla', '').strip()
        if tabla_nombre not in TABLAS:
            return jsonify({'success': False, 'error': f'Tabla inválida: {tabla_nombre}'}), 400

        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No se envió ningún archivo'}), 400

        file = request.files['file']
        if not file or not file.filename.endswith('.xlsx'):
            return jsonify({'success': False, 'error': 'El archivo debe ser .xlsx'}), 400

        fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
        os.close(fd)  # liberar el handle antes de que file.save() escriba en la misma ruta (Windows la bloquea si sigue abierta)
        file.save(tmp_path)

        try:
            resultado = db.cargar_excel_subido(tabla_nombre, tmp_path, file.filename)
        finally:
            os.unlink(tmp_path)

        ok, error = _recargar_generador()
        if not ok:
            return jsonify({
                'success': False,
                'error': f'Archivo guardado pero falló al recargar datos: {error}'
            }), 500

        return jsonify({
            'success': True,
            'mensaje': f'{tabla_nombre} actualizado (v{resultado["version_numero"]}) — {resultado["registros"]} registros',
            **resultado
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/historial', methods=['GET'])
def historial():
    """Devuelve el historial de cargas, opcionalmente filtrado por tabla"""
    tabla_nombre = request.args.get('tabla')
    filas = db.obtener_historial(tabla_nombre)
    return jsonify({'historial': filas})


@app.route('/api/historial/restaurar/<int:version_id>', methods=['POST'])
def restaurar_version(version_id):
    """Restaura una versión anterior como la actual (rollback)"""
    try:
        resultado = db.restaurar_version(version_id)
        ok, error = _recargar_generador()
        if not ok:
            return jsonify({'success': False, 'error': f'Restaurado pero falló al recargar: {error}'}), 500
        return jsonify({'success': True, **resultado})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/sync-tableau/ipp-mes-actual', methods=['POST'])
def sync_tableau_ipp_actual():
    """Descarga desde Tableau los clientes IPP encuestados en un mes específico"""
    try:
        from tableau_sync import TableauSync
        datos = request.json or {}
        hoy = datetime.now()
        mes = int(datos.get('mes', hoy.month))
        ano = int(datos.get('ano', hoy.year))

        sync = TableauSync()
        resultado = sync.descargar_ipp_mes_actual(mes, ano)

        if not resultado.get('success'):
            return jsonify(resultado), 400

        ok, error = _recargar_generador()
        if not ok:
            return jsonify({'success': False, 'error': f'Sincronizado pero falló al recargar: {error}'}), 500

        return jsonify(resultado)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/sync-tableau/ipp-3meses', methods=['POST'])
def sync_tableau_ipp_3meses():
    """Descarga desde Tableau los clientes IPP de los meses seleccionados (ej: 3 meses)"""
    try:
        from tableau_sync import TableauSync
        datos = request.json or {}
        hoy = datetime.now()
        meses = datos.get('meses')
        if not meses:
            # Por defecto: mes actual y los 2 anteriores
            meses = [((hoy.month - i - 1) % 12) + 1 for i in range(3)]
        meses = [int(m) for m in meses]
        ano = int(datos.get('ano', hoy.year))

        sync = TableauSync()
        resultado = sync.descargar_ipp_ultimos_meses(meses, ano)

        if not resultado.get('success'):
            return jsonify(resultado), 400

        ok, error = _recargar_generador()
        if not ok:
            return jsonify({'success': False, 'error': f'Sincronizado pero falló al recargar: {error}'}), 500

        return jsonify(resultado)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print("Iniciando servidor Flask en http://localhost:5000")
    app.run(debug=True, port=5000, use_reloader=False)

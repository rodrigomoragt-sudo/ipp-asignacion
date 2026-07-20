from flask import Flask, render_template, jsonify, request, send_file
from generar_plan import GeneradorPlanVisitas
import json
import os
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.dirname(__file__)

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
    return open('index.html', 'r', encoding='utf-8').read()

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
    """Retorna datos resumidos para el dashboard"""
    try:
        with open('datos_planificador.json', 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except:
        return jsonify({'error': 'No hay datos disponibles'}), 500

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
        num_dias_mes = 31
        dias_exclusion_raw = datos.get('dias_exclusion', [])

        if isinstance(dias_exclusion_raw, str):
            dias_exclusion = [int(d.strip()) for d in dias_exclusion_raw.split(',') if d.strip().isdigit()]
        else:
            dias_exclusion = [int(d) for d in dias_exclusion_raw if isinstance(d, (int, float)) and not (d != d)]  # Filtrar NaN

        # Agregar automáticamente días después del fin_visitas a la exclusión
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

@app.route('/api/actualizar-ipp', methods=['POST'])
def actualizar_clientes_ipp():
    """Actualiza dinámicamente la lista de clientes IPP del mes actual"""
    try:
        if not datos_cargados or not generador:
            return jsonify({'error': 'Sistema no inicializado'}), 500

        # Recargar datos IPP desde Excel
        import pandas as pd
        df_ipp_actual = pd.read_excel('datos/Clientes IPP Mes Actual.xlsx')
        generador.clientes_ipp_mes_actual = set(df_ipp_actual['Cod Cliente'].unique())

        total_ipp = len(generador.clientes_ipp_mes_actual)

        return jsonify({
            'success': True,
            'mensaje': f'Lista IPP actualizada: {total_ipp} clientes encuestados en el mes',
            'total_encuestados': total_ipp
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/subir-datos', methods=['POST'])
def subir_datos():
    """Recibe archivos Excel y los reemplaza en la carpeta datos/"""
    try:
        if 'files' not in request.files:
            return jsonify({'success': False, 'error': 'No se enviaron archivos'}), 400

        archivos_subidos = []
        for file in request.files.getlist('files'):
            if file and file.filename.endswith('.xlsx'):
                # Guardar en carpeta datos/
                archivo_path = os.path.join('datos', file.filename)
                file.save(archivo_path)
                archivos_subidos.append(file.filename)

        # Reiniciar el generador para cargar nuevos datos
        global generador, datos_cargados
        try:
            generador = GeneradorPlanVisitas()
            datos_cargados = True
        except Exception as e:
            return jsonify({'success': False, 'error': f'Error al cargar nuevos datos: {str(e)}'}), 500

        return jsonify({
            'success': True,
            'mensaje': f'{len(archivos_subidos)} archivo(s) actualizado(s): {", ".join(archivos_subidos)}',
            'archivos': archivos_subidos
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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

if __name__ == '__main__':
    print("Iniciando servidor Flask en http://localhost:5000")
    app.run(debug=True, port=5000, use_reloader=False)

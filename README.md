# 📅 Sistema de Planificador de Visitas - IPP

Un sistema inteligente para planificar visitas de supervisores de forma automática, considerando clientes con equipo de frío, segmentación y criterios operativos.

## 🚀 Características

✅ **Planificación Automática**
- 20 visitas por supervisor por día
- Priorización inteligente de clientes
- Distribución equilibrada de cargas de trabajo

✅ **Criterios de Planificación**
- **Prioridad 1**: Clientes con Equipo Frío (visita mínima 1 vez en el mes)
- **Prioridad 2**: Clientes Blindaje/BTL
- **Prioridad 3**: Clientes Desarrollar
- **Prioridad 4**: Clientes Optimizar
- **Prioridad 5**: Clientes Mantener

✅ **Reglas Operativas**
- No repetir frecuencia de visita (excepto última semana LU-JU)
- Validar regla de 3 meses móviles para encuestas IPP
- Excluir fechas específicas (fin de mes, días no laborables)
- Ajustable: días de inicio (1-5 del mes) y días sin visita

✅ **Exportación Flexible**
- Excel con cronograma detallado por supervisor
- JSON para integración con otros sistemas
- CSV para análisis adicional

✅ **Interfaz Web**
- Dashboard de estadísticas
- Configuración interactiva de parámetros
- Visualización de cronograma
- Exportación directa

## 📋 Requisitos Previos

- Python 3.7+
- Librerías Python:
  - pandas
  - openpyxl
  - (Los datos Excel deben estar en la misma carpeta)

### Instalar dependencias:
```bash
pip install pandas openpyxl
```

## 📂 Estructura de Archivos

### Datos de Entrada (Excel)
```
Clientes cedis (2).xlsx       - Base de datos de clientes CEDIS
Clientes IPP_.xlsx            - Clientes con encuestas IPP
Data EF - Julio 2026.xlsx     - Clientes con equipo de frío
```

### Archivos del Sistema
```
index.html                    - Interfaz web de la aplicación
server.py                     - Servidor local para la app web
generar_plan.py               - Motor de planificación
planificador.py               - Procesamiento de datos
analyze_data.py               - Análisis exploratorio de datos
```

### Salidas Generadas
```
plan_visitas_julio.json       - Plan en formato JSON
plan_visitas_julio.xlsx       - Plan en formato Excel con cronograma
datos_planificador.json       - Datos resumidos del dashboard
```

## 🔧 Cómo Usar

### Opción 1: Usar la Interfaz Web (Recomendado)

1. **Iniciar el servidor**:
```bash
py server.py
```

2. Se abrirá automáticamente el navegador en `http://localhost:8000`

3. **Usar el sistema**:
   - **Dashboard**: Ve resumen de datos y estadísticas
   - **Configurar Plan**: Ajusta parámetros de planificación
   - **Cronograma**: Visualiza el plan generado
   - **Exportar**: Descarga Excel o CSV

### Opción 2: Usar Script Python Directo

1. **Generar plan de Julio**:
```bash
py generar_plan.py
```

2. Esto genera automáticamente:
   - `plan_visitas_julio.json`
   - `plan_visitas_julio.xlsx`

3. **Personalizar plan** (editar `generar_plan.py` al final):
```python
plan = generador.generar_plan(
    mes=8,                              # Agosto
    ano=2026,
    inicio_visitas=3,                   # Inicio el 3 del mes
    visitas_por_dia=20,
    dias_exclusion=[28,29,30,31],       # Excluir fin de mes
    dias_sin_visita=[5, 6],             # Sábado y domingo
    supervisor=None                     # None = todos, o número de zona
)
```

## ⚙️ Parámetros Configurables

### Mes y Año
- Mes: 1-12
- Año: 2024 en adelante

### Inicio de Visitas
- Día del mes (1-5): Típicamente comienza el 5 para dejar margen administrativo

### Visitas por Día
- Cantidad de visitas asignadas por supervisor diariamente
- Valor recomendado: 20

### Días de Exclusión
- Días del mes sin programación de visitas
- Ejemplo: `[28, 29, 30, 31]` para excluir fin de mes

### Días sin Visita
- Días de la semana sin visitas
- `0=Lunes`, `1=Martes`, `2=Miércoles`, `3=Jueves`, `4=Viernes`, `5=Sábado`, `6=Domingo`
- Ejemplo: `[5, 6]` (no visitar sábados ni domingos)

## 📊 Interpretación de Resultados

### JSON Output
```json
{
  "mes": 7,
  "ano": 2026,
  "supervisores": {
    "1": {
      "zona": 1,
      "total_clientes": 2579,
      "clientes_planificados": 320,
      "cronograma": [
        {
          "fecha": "2026-07-06T00:00:00",
          "dia": 6,
          "día_semana": "Lun",
          "visitas": [...],
          "total_visitas": 20
        }
      ]
    }
  }
}
```

### Excel Output
- **Hoja Resumen**: Totales por supervisor
- **Hojas por Zona**: Detalle diario de visitas con:
  - Fecha y día de la semana
  - Código de cliente
  - Ruta asignada
  - Segmento del cliente
  - Clasificación (EF, Blindaje, etc.)

## 🎯 Ejemplo de Flujo Completo

1. Abrir terminal en la carpeta del proyecto
2. Ejecutar `py server.py`
3. El navegador abre automáticamente
4. En "Configurar Plan":
   - Mes: Julio 2026
   - Inicio: 5 del mes
   - Visitas/día: 20
   - Excluir días: 28,29,30,31
   - Clientes sin visita: 5,6
5. Hacer clic en "Generar Plan"
6. Ver cronograma en la pestaña "Cronograma"
7. Descargar Excel en "Exportar"

## 🔍 Criterios de Priorización Detallados

### Equipo Frío (EF)
- **Prioridad**: Máxima (1)
- **Regla**: Mínimo 1 visita en el mes
- **3 meses**: NO aplica (sin restricción)
- **Frecuencia**: Se puede repetir si es necesario

### Blindaje
- **Prioridad**: Alta (2)
- **Regla**: Se planifica después de EF
- **3 meses**: Sí aplica
- **Frecuencia**: No repetir excepto última semana

### Desarrollar/Optimizar/Mantener
- **Prioridad**: Media/Baja (3,4,5)
- **Regla**: Según disponibilidad
- **3 meses**: Sí aplica
- **Frecuencia**: No repetir excepto última semana

## 🐛 Troubleshooting

### Error: "ModuleNotFoundError: No module named 'pandas'"
```bash
pip install pandas openpyxl
```

### Error: "No se encuentra localhost:8000"
- Verificar que el servidor esté ejecutándose
- Intentar abrir manualmente `http://localhost:8000`
- Cambiar puerto en `server.py` si el 8000 está ocupado

### Error al cargar Excel
- Verificar que los excels estén en la misma carpeta
- Verificar nombres exactos de archivos
- Revisar que no haya archivos abiertos en Excel

### Plan vacío o pocos clientes asignados
- Verificar parámetros de "Días de Exclusión"
- Aumentar "Visitas por Día"
- Revisar datos en Excel (posibles registros vacíos)

## 📝 Notas Técnicas

### Estructura de Datos
- **CEDIS**: 58,105 registros
- **IPP**: 7,896 registros
- **EF**: 5,068 registros
- **Supervisores**: 27 zonas

### Lógica de Planificación
1. Agrupa clientes por Código Zona (supervisor)
2. Clasifica cada cliente por segmento/tipo
3. Ordena por prioridad
4. Asigna a días hábiles hasta llenar cuota (20 visitas/día)
5. Genera cronograma con trazabilidad completa

### Rendimiento
- Procesamiento de 58K clientes: ~2-3 segundos
- Generación de Excel: ~1 segundo
- Memoria requerida: ~200-300 MB

## 🤝 Contribuciones

Para mejoras o reportar bugs, contactar al equipo de desarrollo.

## 📄 Licencia

Uso interno - IPP Analytics

---

**Versión**: 1.0  
**Última actualización**: Julio 2026

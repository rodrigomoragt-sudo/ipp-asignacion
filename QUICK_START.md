# 🚀 QUICK START - Planificador de Visitas

## En 5 Minutos

### Opción 1: Windows (Más Fácil)
```
1. Haz doble clic en: install_y_ejecutar.bat
2. Espera a que se instale todo
3. Se abrirá automáticamente en http://localhost:5000
```

### Opción 2: Terminal (Cualquier SO)
```powershell
# Paso 1: Instalar dependencias
pip install pandas openpyxl flask

# Paso 2: Ejecutar servidor
py app.py

# Paso 3: Abre el navegador en http://localhost:5000
```

### Opción 3: Validar Primero
```powershell
py validar_sistema.py
```

---

## En la Aplicación Web

1. **Dashboard**: Ve los datos cargados (58K+ clientes)

2. **Configurar Plan**:
   - Mes: Julio 2026
   - Inicio: 5 del mes
   - Visitas/día: 20
   - Excluir días: 28,29,30,31
   - Sin visita: 5,6 (Sábado, Domingo)

3. **Generar Plan**: Click en "Generar Plan"

4. **Cronograma**: Ve el plan generado por supervisor

5. **Exportar**: Descarga como Excel o CSV

---

## Parámetros Clave

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| Mes | 7 | Julio 2026 |
| Inicio Visitas | 5 | Comienza el 5 del mes |
| Visitas/Día | 20 | Por supervisor |
| Excluir | 28,29,30,31 | Fin de mes |
| Sin Visita | 5,6 | Sáb, Dom |

---

## Prioridades Automáticas

```
1. Equipo Frío (EF)        → MAXIMA   (rojo)
2. Blindaje                → ALTA     (naranja)
3. Desarrollar             → MEDIA    (azul)
4. Optimizar               → BAJA     (verde)
5. Mantener                → MINIMA   (gris)
```

---

## Estructura del Plan Generado

El sistema planifica **320 clientes por supervisor** en 16 días hábiles:
- 20 clientes/día × 16 días = 320 clientes
- Prioriza EF hasta cubrir todos
- Luego blindaje, desarrollar, etc.

---

## Archivos Generados

```
plan_actual.json                    # Plan en JSON
plan_visitas_generado.xlsx          # Plan en Excel
plan_visitas.csv                    # Plan en CSV
```

---

## Troubleshooting

### "Module not found: flask"
```
pip install flask
```

### "Port 5000 already in use"
Edita `app.py` línea 70:
```python
app.run(debug=True, port=5001)  # Cambia 5001
```

### "No such file: Clientes cedis"
Verifica que los Excel estén en la misma carpeta

### La web no carga datos
Espera 10 segundos, recarga la página (F5)

---

## Siguiente Paso

Una vez generado el plan, **haz clic en "Descargar Excel"** para obtener:
- Hoja "Resumen" con totales
- Hojas por zona con cronograma detallado

---

**Problemas?** Ejecuta `py validar_sistema.py` para un diagnóstico completo.


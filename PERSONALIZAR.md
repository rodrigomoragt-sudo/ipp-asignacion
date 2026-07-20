# ⚙️ GUÍA DE PERSONALIZACIÓN - Planificador de Visitas

## Cómo Personalizar para Tu Caso

### 1. Cambiar Mes Predeterminado

**Archivo**: `config.json`

```json
{
  "parametros_defecto": {
    "mes": 8,                    // Cambiar a 8 para Agosto
    "ano": 2026,
    "inicio_visitas": 5,
    "visitas_por_dia": 20,
    "dias_exclusion": [28, 29, 30, 31],
    "dias_sin_visita": [5, 6]
  }
}
```

### 2. Cambiar Fechas de Exclusión

**Archivo**: `generar_plan.py` línea 326

```python
plan = generador.generar_plan(
    mes=7,
    ano=2026,
    dias_exclusion=[28, 29, 30, 31],  # Ej: [1,2,3] para primeros 3 días
    dias_sin_visita=[5, 6]             # 0=Lun, 6=Dom
)
```

### 3. Cambiar Visitas por Día

**Archivo**: `generar_plan.py` línea 320

```python
visitas_por_dia = 20  # Cambiar a 15, 25, etc.
```

### 4. Cambiar Definición de "Blindaje"

**Archivo**: `generar_plan.py` línea 56-58

```python
# Busca esta función:
def clasificar_cliente(self, codigo_cliente, segmento):
    # Modificar los keywords para blindaje
    if 'blind' in seg_lower or 'btl' in seg_lower or 'tu_palabra' in seg_lower:
        return 'Blindaje', 2
```

### 5. Cambiar Prioridades

**Archivo**: `generar_plan.py` línea 53-68

Modifica los números de prioridad (1=máxima, 5=mínima):

```python
if codigo_cliente in self.clientes_ef_ids:
    return 'Equipo Frío', 1  # Cambiar a 2 para bajar prioridad

if 'blind' in seg_lower:
    return 'Blindaje', 2      # Cambiar a 1 para subir prioridad
```

### 6. Agregar Nueva Clasificación

**Archivo**: `generar_plan.py` línea 53-68

```python
def clasificar_cliente(self, codigo_cliente, segmento):
    # Agregar antes del "return 'Mantener'"
    elif 'vip' in seg_lower:
        return 'VIP', 0  # Nueva clasificación con máxima prioridad
    
    elif 'nuevos' in seg_lower:
        return 'Nuevos', 2.5  # Entre Blindaje y Desarrollar
    
    return 'Mantener', 5
```

### 7. Cambiar Puerto del Servidor

**Archivo**: `app.py` línea 81

```python
app.run(debug=True, port=8080)  # Cambiar 5000 a otro puerto
```

### 8. Personalizar Interfaz Web

**Archivo**: `index.html`

```html
<!-- Cambiar título (línea 5) -->
<title>Planificador - Tu Empresa</title>

<!-- Cambiar header (línea 140) -->
<h1>📅 Sistema de Rutas - Tu Empresa</h1>
<p>Planificación automática personalizada</p>

<!-- Cambiar colores (línea 17-18) -->
<style>
    background: linear-gradient(135deg, #tu_color1 0%, #tu_color2 100%);
</style>
```

### 9. Usar Diferentes Bases de Datos

**Archivo**: `generar_plan.py` línea 17-19

```python
def __init__(self):
    self.df_cedis = pd.read_excel("Tu_archivo_CEDIS.xlsx")
    self.df_ipp = pd.read_excel("Tu_archivo_IPP.xlsx")
    self.df_ef = pd.read_excel("Tu_archivo_EF.xlsx")
```

### 10. Agregar Validaciones Adicionales

**Archivo**: `generar_plan.py` - Agregar nuevo método

```python
def validar_cliente(self, cliente):
    """Validar si el cliente debe incluirse en el plan"""
    
    # Ejemplo: Excluir clientes inactivos
    if cliente.get('estado') == 'inactivo':
        return False
    
    # Ejemplo: Excluir por rango de código
    codigo = cliente['codigo']
    if codigo < 10000 or codigo > 99999:
        return False
    
    return True
```

### 11. Modificar Formato de Exportación

**Archivo**: `generar_plan.py` - Método `exportar_excel()` línea 234

```python
# Agregar nueva columna
ws[f'G{row}'] = "Nuevo Campo"

# Cambiar estilos
ws[f'A{row}'].fill = PatternFill(start_color="FF0000", fill_type="solid")
```

### 12. Integrar con Base de Datos

**Crear archivo**: `db.py`

```python
import sqlite3
import pandas as pd

class BaseDatos:
    def __init__(self):
        self.conn = sqlite3.connect('planificador.db')
    
    def guardar_plan(self, plan):
        # Guardar plan en BD en lugar de JSON
        pass
    
    def obtener_plan(self, id_plan):
        pass
```

Luego modificar `generar_plan.py`:

```python
from db import BaseDatos
db = BaseDatos()
db.guardar_plan(plan)
```

---

## Ejemplos de Personalización Comunes

### Para Distribuidoras
```python
# Aumentar visitas por día
visitas_por_dia = 25

# Priorizar por tipo de cliente
if 'distribuidor' in seg_lower:
    return 'Distribuidor', 1  # Máxima prioridad
```

### Para Clínicas/Farmacia
```python
# Excluir domingos y lunes (cerrado)
dias_sin_visita = [0, 6]  # Lun, Dom

# Agregar clasificación de urgencia
elif 'urgente' in seg_lower:
    return 'Urgente', 0  # Máxima prioridad
```

### Para Manufactura
```python
# Iniciar más temprano
inicio_visitas = 2

# Excluir más días (mantenimiento)
dias_exclusion = [1, 15, 28, 29, 30, 31]

# Aumentar clientes por día
visitas_por_dia = 30
```

### Multi-mes
**Archivo**: `generar_plan.py` - Agregar al final

```python
# Generar planes para múltiples meses
meses = [7, 8, 9, 10]
for mes in meses:
    plan = generador.generar_plan(mes=mes)
    generador.exportar_excel(plan, f'plan_visitas_{mes}.xlsx')
```

---

## Testing de Cambios

Después de personalizar, ejecutar:

```powershell
py validar_sistema.py
```

Para probar un cambio sin ejecutar el servidor:

```python
from generar_plan import GeneradorPlanVisitas

gen = GeneradorPlanVisitas()
plan = gen.generar_plan(mes=7)

# Verificar resultados
for zona, datos in plan['supervisores'].items():
    print(f"Zona {zona}: {datos['clientes_planificados']} clientes")
```

---

## Checklist de Personalización

- [ ] Cambié el mes predeterminado
- [ ] Ajusté las fechas de exclusión
- [ ] Cambié prioridades según necesidad
- [ ] Personalicé la interfaz web
- [ ] Probé con `validar_sistema.py`
- [ ] Generé un plan de prueba
- [ ] Revisé el Excel generado
- [ ] Validé que las prioridades funcionen correctamente
- [ ] Personalicé la exportación (si necesaria)
- [ ] Documenté mis cambios

---

**¿Necesitas ayuda?** Revisa los comentarios en el código o contacta al equipo técnico.

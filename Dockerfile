FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Los .xlsx de datos/ no están en git (son datos, no código) y la carpeta
# puede llegar vacía al desplegar. La app arranca igual sin datos_cargados
# y espera a que se suban/sincronicen las tablas desde la UI.
RUN mkdir -p datos datos_history plantillas

ENV PORT=5050
EXPOSE 5050

# gunicorn en vez del servidor de desarrollo de Flask (recomendado para producción).
# 1 worker: cada worker carga el CEDIS completo (~58k filas) en memoria por su cuenta,
# más de uno multiplicaría el uso de RAM sin necesidad para el tráfico esperado.
# --timeout alto: subir/sincronizar una tabla obliga a recargar los 4 Excel completos.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 300 app:app"]

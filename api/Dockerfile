FROM python:3.12-slim

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requirements y luego instalar dependencias para aprovechar cache de Docker
COPY api/requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente de la aplicación
COPY api/app ./app

# Exponer el puerto en el que correrá la API
EXPOSE 8000

# Variable de entorno para que uvicorn no genere archivos pyc
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Comando para ejecutar la aplicación con uvicorn, con root_path /api
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
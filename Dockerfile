# Imagen base oficial de Python
FROM python:3.11-slim

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar archivo de dependencias primero (aprovecha la caché de capas)
COPY requirements.txt ./

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY app.py ./

# Exponer el puerto del servicio
EXPOSE 8082

# Comando de inicio
CMD ["python", "app.py"]

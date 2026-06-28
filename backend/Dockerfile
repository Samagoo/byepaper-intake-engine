#Usar la versión slim de Python 3.11 para reducir el tamaño de la imagen
FROM python:3.11-slim

#Evita que Python genere archivos complitados
ENV PYTHONDONTWRITEBYTECODE=1
#Obliga a Python a enviar la salida de consola directamente a la terminal sin buffering
ENV PYTHONUNBUFFERED=1

# Establece el directorio de trabajo principal dentro del contenedor
WORKDIR /app

#Actualizamos el sistema e instalamos curl para saber si la api esta viva
#rm -rf limpia la cache de apt para reducir el tamaño de la imagen
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copiamos el archivo de requerimientos al contenedor. 
# Si las dependencias no cambian, Docker usará la cache de la capa anterior y no volverá a instalar las dependencias    
COPY requirements.txt .

#Instalamos las dependencias de Python especificadas
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código de la aplicación al contenedor
COPY app ./app

# Creamos el directorio de almacenamiento de datos dentro del contenedor
RUN mkdir -p /data/storage

# Declaramos el puerto en el que escuchará el contenedor
EXPOSE 8000

# Comando por defecto para ejecutar la aplicación usando Uvicorn, especificando el host y el puerto
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
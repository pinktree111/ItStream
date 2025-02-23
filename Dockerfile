# Usa un'immagine base con Python
FROM python:3.10

# Imposta la directory di lavoro
WORKDIR /app

# Copia i file necessari
COPY . /app

# Installa le dipendenze
RUN pip install --no-cache-dir fastapi uvicorn requests

# Espone la porta 8000
EXPOSE 11000

# Comando di avvio del server
CMD ["uvicorn", "stremio_catalog:app", "--host", "0.0.0.0", "--port", "11000"]


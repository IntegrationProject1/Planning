# Gebruik een officiële Python runtime als parent image
FROM python:3.9-slim

# Zet de werkmap
WORKDIR /app

# Kopieer requirements file en installeer dependencies
COPY ../requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ../ ./

ENV PYTHONPATH=/app

# Start de app
CMD ["python", "event_producers/app.py"]
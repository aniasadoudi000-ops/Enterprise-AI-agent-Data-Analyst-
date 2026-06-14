FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# PyTorch CPU léger en premier (séparé pour le cache Docker)
RUN pip install --no-cache-dir torch \
    --extra-index-url https://download.pytorch.org/whl/cpu

# Reste des dépendances
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Le modèle sera téléchargé au premier démarrage, pas au build
ENV PORT=8080
EXPOSE 8080

CMD ["python", "-m", "uvicorn", "phase3_deployment.api:app", \
     "--host", "0.0.0.0", "--port", "8080"]
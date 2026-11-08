FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends g++ && rm -rf /var/lib/apt/lists/*
COPY backend/requirements-demo.txt backend/requirements-demo.txt
RUN pip install --no-cache-dir -r backend/requirements-demo.txt
COPY backend backend
COPY scripts scripts
COPY evaluation evaluation
RUN useradd --create-home autonomy && mkdir /app/artifacts && chown autonomy:autonomy /app/artifacts
USER autonomy
CMD ["python", "-m", "scripts.run_experiment", "--output", "artifacts/run"]

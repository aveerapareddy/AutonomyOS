FROM node:20-bookworm-slim AS dashboard
WORKDIR /frontend
COPY frontend/autonomy-dashboard/package*.json ./
RUN npm ci
COPY frontend/autonomy-dashboard/ ./
RUN npm run build -- --base-href /demo/

FROM python:3.11-slim-bookworm AS wheels
ARG TARGETARCH
WORKDIR /build
COPY backend/requirements-demo.txt ./requirements-demo.txt
RUN if [ "$TARGETARCH" = "arm64" ]; then apt-get update && apt-get install -y --no-install-recommends g++; fi \
    && pip wheel --no-cache-dir --wheel-dir=/wheels pip==26.3 setuptools==84.2.1 -r requirements-demo.txt

FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    AUTONOMY_PLANNER_MODE=rule_based AUTONOMY_DATABASE_PATH=/data/autonomy.sqlite3 \
    AUTONOMY_FRONTEND_DIRECTORY=/app/dashboard AUTONOMY_PUBLIC_DEMO=true
WORKDIR /app
COPY backend/requirements-demo.txt ./requirements-demo.txt
COPY --from=wheels /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels --upgrade pip==26.3 setuptools==84.2.1 \
    && pip install --no-cache-dir --no-index --find-links=/wheels -r requirements-demo.txt \
    && rm -rf /wheels \
    && useradd --uid 10001 --create-home autonomy \
    && mkdir /data && chown autonomy:autonomy /data
COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY evaluation/ ./evaluation/
COPY knowledge/ ./knowledge/
COPY --from=dashboard /frontend/dist/autonomy-dashboard/browser/ ./dashboard/
USER autonomy
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"
CMD ["python", "-m", "uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

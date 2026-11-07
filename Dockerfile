FROM node:20-bookworm-slim AS dashboard
WORKDIR /frontend
COPY frontend/autonomy-dashboard/package*.json ./
RUN npm ci
COPY frontend/autonomy-dashboard/ ./
RUN npm run build -- --base-href /demo/

FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    AUTONOMY_PLANNER_MODE=rule_based AUTONOMY_DATABASE_PATH=/data/autonomy.sqlite3 \
    AUTONOMY_FRONTEND_DIRECTORY=/app/dashboard AUTONOMY_PUBLIC_DEMO=true
WORKDIR /app
COPY backend/requirements-demo.txt ./requirements-demo.txt
RUN pip install --no-cache-dir -r requirements-demo.txt \
    && useradd --uid 10001 --create-home autonomy \
    && mkdir /data && chown autonomy:autonomy /data
COPY backend/ ./backend/
COPY --from=dashboard /frontend/dist/autonomy-dashboard/browser/ ./dashboard/
USER autonomy
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"
CMD ["python", "-m", "uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

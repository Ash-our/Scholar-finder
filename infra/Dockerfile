FROM node:24-bookworm-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci --ignore-scripts --no-fund --no-audit
COPY frontend/ ./
COPY data/countries.json /data/countries.json
RUN npm run build

FROM python:3.12-slim-bookworm AS api
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app/backend
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY pyproject.toml ./
COPY backend/ ./backend/
RUN pip install --no-deps -e .
COPY data/ ./data/
COPY --from=web /web/dist ./frontend/dist
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "scholarship_map.api:app", "--host", "0.0.0.0", "--port", "8000"]

FROM eclipse-temurin:21-jdk-jammy AS java

FROM api AS spark
COPY --from=java /opt/java/openjdk /opt/java/openjdk
ENV JAVA_HOME=/opt/java/openjdk PATH=/opt/java/openjdk/bin:$PATH
USER root
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 procps && rm -rf /var/lib/apt/lists/*
COPY requirements-spark.lock.txt ./
RUN pip install --no-cache-dir -r requirements-spark.lock.txt
CMD ["python", "-m", "scholarship_map.cli", "stream"]

FROM python:3.12-slim

WORKDIR /opt/app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/opt/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

# Воркеров ровно один: состояние circuit breaker в памяти процесса;
CMD ["gunicorn", "src.main:app", "--bind", "0.0.0.0:8000", "--worker-class", "aiohttp.worker.GunicornWebWorker", "--workers", "1", "--timeout", "120", "--graceful-timeout", "30"]

FROM python:3.12-slim

WORKDIR /opt/app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY shared/redis_rate_limit /tmp/redis_rate_limit
RUN pip install --no-cache-dir /tmp/redis_rate_limit

COPY auth-service/requirements.txt ./
RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove gcc \
    && rm -rf /var/lib/apt/lists/*

COPY auth-service/ .
RUN chmod +x ./prepare_service.sh

ENTRYPOINT ["./prepare_service.sh"]

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

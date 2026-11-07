FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir Flask==3.1.0

RUN useradd --create-home --uid 10001 app

WORKDIR /app

COPY src/ /app/
COPY files/ /app/files/

USER app

EXPOSE 8080

CMD ["python", "start.py"]

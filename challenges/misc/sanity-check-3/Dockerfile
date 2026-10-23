# container only serves the pointer page; the real artifact is the R2-hosted
# gifts.zip referenced in chall.yaml (already in the bucket at register time).
FROM python:3.13-alpine
WORKDIR /app
COPY src/main.py /app/main.py
CMD ["python3","-u","main.py"]

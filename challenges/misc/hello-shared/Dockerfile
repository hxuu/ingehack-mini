FROM python:3.13-alpine
WORKDIR /app
COPY src/main.py /app/main.py
ENV FLAG=clean-me-at-deploy
CMD ["python3","-u","main.py"]

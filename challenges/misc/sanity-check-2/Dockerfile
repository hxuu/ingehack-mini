# nothing to run in the container — the flag lives in the committed handout.
# A page is served so the static-challenge deploy has something to answer.
FROM python:3.13-alpine
WORKDIR /app
COPY src/main.py /app/main.py
CMD ["python3","-u","main.py"]

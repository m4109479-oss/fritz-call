FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY web ./web
COPY config.yaml .

ENV PYTHONUNBUFFERED=1

CMD ["python3", "-m", "app.main"]

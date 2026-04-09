
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    swig \
    python3-dev \
    liblgpio-dev \
    build-essential \
    i2c-tools \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir virtualenv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]

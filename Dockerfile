
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    swig \
    python3-dev \
    build-essential \
    i2c-tools \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://github.com/joan2937/lg/archive/master.zip \
    && unzip master.zip \
    && cd lg-master \
    && make install \
    && cd .. \
    && rm -rf lg-master master.zip

RUN pip install --no-cache-dir virtualenv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]

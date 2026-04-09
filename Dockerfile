
FROM python:3.11-slim AS builder
WORKDIR /app

RUN apt-get update && apt-get install -y \
    swig python3-dev build-essential wget unzip \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://github.com/joan2937/lg/archive/master.zip \
    && unzip master.zip && cd lg-master && make install \
    && cd .. && rm -rf lg-master master.zip

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt


FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app


RUN groupadd -g 1000 piuser && useradd -u 1000 -g piuser piuser


COPY --from=builder /usr/local/lib /usr/local/lib
COPY --from=builder /usr/local/include /usr/local/include
RUN ldconfig


RUN apt-get update && apt-get install -y i2c-tools curl && rm -rf /var/lib/apt/lists/*


COPY --from=builder /root/.local /home/piuser/.local
ENV PATH=/home/piuser/.local/bin:$PATH


RUN mkdir -p /app/data && chown -R piuser:piuser /app/data
COPY --chown=piuser:piuser . .

USER piuser
EXPOSE 8000


HEALTHCHECK --interval=30s --timeout=5s \
  CMD curl -f http://localhost:8000/sensor || exit 1

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]

# 158335 - Assignment 1 - Pi Sensor System

24003641 - Toby Cammock-Elliott

A fully functional temperature, humidity, air pressure implementation for the waveshare sense hat (C)

Can be accessed via port 8000 when running, via all interfaces including localhost

Dependencies: swig, virtualenv, python,liblgpio-dev

liblgpio-dev must be manually built.

To run this project, use the following docker one-liner

Please note that building and running this will take time. About 5 minutes at first run, the running shouldn't be as long from there!

Docker:
mkdir -p data && \
sudo chown -R 1000:1000 ./data && chmod -R 775 ./data && \
docker build -t smart_rpi_monitor . && \
docker run -d \
  --name smart_monitor \
  --group-add $(getent group i2c | cut -d: -f3) \
  --group-add $(getent group gpio | cut -d: -f3) \
  --device /dev/i2c-1:/dev/i2c-1 \
  --device /dev/gpiomem:/dev/gpiomem \
  --device /dev/gpiochip0:/dev/gpiochip0 \
  --device /dev/gpiochip4:/dev/gpiochip4 \
  --replace \
  -v $(pwd)/data:/app/data \
  -p 8000:8000 \
  smart_rpi_monitor

Podman:
mkdir -p data && \
sudo chown -R 1000:1000 ./data && chmod -R 775 ./data && \
podman build -t smart_rpi_monitor . && \
podman run -d \
  --name smart_monitor \
  --group-add keep-groups \
  --security-opt label=disable \
  --cap-add=SYS_RAWIO \
  --device /dev/i2c-1:/dev/i2c-1 \
  --device /dev/gpiomem:/dev/gpiomem \
  --device /dev/gpiochip0:/dev/gpiochip0 \
  --device /dev/gpiochip4:/dev/gpiochip4 \
  --replace \
  -v $(pwd)/data:/app/data \
  -p 8000:8000 \
  smart_rpi_monitor

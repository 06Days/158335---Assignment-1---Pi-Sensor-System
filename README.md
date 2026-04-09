# 158335 - Assignment 1 - Pi Sensor System

Dependencies: swig, virtualenv, python,liblgpio-dev

podman build -t smart_env_system . && podman run -d   --name smart_monitor   --privileged   --user root   --group-add keep-groups   --device /dev/i2c-1:/dev/i2c-1   --device /dev/gpiomem:/dev/gpiomem   --device /dev/gpiochip0:/dev/gpiochip0   -v $(pwd)/data:/app/data:Z   -p 8000:8000   --replace smart_env_system

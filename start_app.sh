#!/bin/bash

# Завершение всех процессов, использующих порт 5000
sudo fuser -k 5000/tcp

sudo systemctl restart bluetooth

# Активация виртуального окружения
# source venv/bin/activate

hciconfig

# Запуск Python-скрипта
sudo venv/bin/python3 main.py
#!/bin/bash

# Завершение всех процессов, использующих порт 5000
sudo fuser -k 5000/tcp

# Активация виртуального окружения
source venv/bin/activate

# Запуск Python-скрипта
python3 main.py

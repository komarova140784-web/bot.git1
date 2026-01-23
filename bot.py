#!/usr/bin/env python3
# monitor_bot.py

import subprocess
import time
import sys
import os
from datetime import datetime

# Настройки
SCRIPTS = [
    {"name": "bot2.py", "interval": 3, "log": "bot1.log"},
    {"name": "bot1.py", "interval": 5, "log": "bot2.log"},
]
RESTART_DELAY = 2  # секунд задержка перед перезапуском

def log(message, log_file="monitor.log"):
    """Запись в лог с таймстампом"""
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")

def is_process_running(pid):
    """Проверяет, существует ли процесс с данным PID"""
    try:
        os.kill(pid, 0)  # Проверка без отправки сигнала
        return True
    except OSError:
        return False

def get_script_pid(script_name):
    """Находит PID процесса по имени скрипта через pgrep (Linux/macOS)"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", script_name],
            capture_output=True,
            text=True
        )
        if result.stdout.strip():
            return int(result.stdout.strip())
        return None
    except Exception as e:
        log(f"Ошибка при поиске PID для {script_name}: {e}", "monitor.log")
        return None

def start_script(script_info):
    """Запускает скрипт и возвращает PID"""
    script_name = script_info["name"]
    log_file = script_info["log"]
    try:
        process = subprocess.Popen([sys.executable, script_name])
        log(f"Скрипт запущен: {script_name} (PID: {process.pid})", log_file)
        return process.pid
    except Exception as e:
        log(f"Ошибка запуска скрипта {script_name}: {e}", log_file)
        return None

def monitor_script(script_info):
    """Мониторинг одного скрипта"""
    script_name = script_info["name"]
    check_interval = script_info["interval"]
    log_file = script_info["log"]

    pid = get_script_pid(script_name)

    if pid is None:
        # Скрипт не найден — запускаем
        print(f"Скрипт не запущен: {script_name}. Запуск...")
        new_pid = start_script(script_info)  # Исправлено: было script_infos
        if new_pid:
            print(f"Скрипт запущен: {script_name} (PID: {new_pid})")
        else:
            print(f"Не удалось запустить {script_name}. Повторная попытка через {RESTART_DELAY} сек...")
            time.sleep(RESTART_DELAY)
    else:
        # Скрипт работает — логируем статус
        log(f"Скрипт работает: {script_name} (PID: {pid})", log_file)
        print(f"Скрипт работает: {script_name} (PID: {pid}). Проверка через {check_interval} сек...")

def main():
    log("Монитор запущен", "monitor.log")
    print("Монитор работает. Ожидание...")

    while True:
        for script_info in SCRIPTS:
            monitor_script(script_info)
            # Пауза между проверками разных скриптов (чтобы не перегружать систему)
            time.sleep(0.5)

        # Общая пауза перед следующим циклом мониторинга
        time.sleep(1)

if __name__ == "__main__":
    main()

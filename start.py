#!/usr/bin/env python3
"""
Скрипт для швидкого запуску системи моніторингу
"""

import subprocess
import time
import sys
import os

def run_command(command, description):
    """Виконання команди з описом"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - успішно")
            return True
        else:
            print(f"❌ {description} - помилка:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ {description} - помилка: {e}")
        return False

def check_docker():
    """Перевірка наявності Docker"""
    return run_command("docker --version", "Перевірка Docker")

def check_docker_compose():
    """Перевірка наявності Docker Compose"""
    return run_command("docker-compose --version", "Перевірка Docker Compose")

def stop_existing_containers():
    """Зупинка існуючих контейнерів"""
    return run_command("docker-compose down", "Зупинка існуючих контейнерів")

def start_system():
    """Запуск системи"""
    return run_command("docker-compose up -d", "Запуск системи моніторингу")

def wait_for_system():
    """Очікування ініціалізації системи"""
    print("⏳ Очікування ініціалізації системи...")
    
    for i in range(60):  # Максимум 60 секунд
        time.sleep(1)
        if i % 10 == 0:
            print(f"   Очікування: {i+1}/60 секунд")
    
    print("✅ Система має бути готова")

def show_status():
    """Показати статус контейнерів"""
    print("\n📊 Статус контейнерів:")
    subprocess.run("docker-compose ps", shell=True)

def show_urls():
    """Показати URL сервісів"""
    print("\n🌐 Доступні сервіси:")
    print("  • Grafana: http://localhost:3000 (admin/admin123)")
    print("  • Prometheus: http://localhost:9090")
    print("  • Auth Service: http://localhost:5000")
    print("  • Metrics: http://localhost:8000/metrics")
    print("  • MySQL: localhost:3306 (monitor_user/monitor_pass)")

def main():
    """Основна функція"""
    print("🚀 Швидкий запуск системи моніторингу MySQL")
    print("=" * 50)
    
    # Перевірка залежностей
    if not check_docker():
        print("❌ Docker не знайдено. Встановіть Docker та спробуйте знову.")
        return 1
    
    if not check_docker_compose():
        print("❌ Docker Compose не знайдено. Встановіть Docker Compose та спробуйте знову.")
        return 1
    
    # Зупинка існуючих контейнерів
    stop_existing_containers()
    
    # Запуск системи
    if not start_system():
        print("❌ Помилка запуску системи")
        return 1
    
    # Очікування ініціалізації
    wait_for_system()
    
    # Показати статус
    show_status()
    show_urls()
    
    print("\n🎉 Система запущена!")
    print("\n💡 Корисні команди:")
    print("  • Перегляд логів: docker-compose logs -f")
    print("  • Зупинка системи: docker-compose down")
    print("  • Тестування системи: python test_system.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

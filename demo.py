#!/usr/bin/env python3
"""
Повна демонстрація системи моніторингу MySQL
"""

import subprocess
import time
import webbrowser
import sys
import os

def print_header(title):
    """Красиво друкує заголовок"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_step(step_num, description):
    """Друкує номер кроку"""
    print(f"\n📋 Крок {step_num}: {description}")
    print("-" * 40)

def wait_for_user(message="Натисніть Enter для продовження..."):
    """Очікує натискання Enter"""
    input(f"\n{message}")

def open_browser_tabs():
    """Відкриває вкладки браузера"""
    urls = [
        ("Grafana Dashboard", "http://localhost:3000"),
        ("Prometheus", "http://localhost:9090"),
        ("Auth Service", "http://localhost:5000"),
        ("Metrics Endpoint", "http://localhost:8000/metrics")
    ]
    
    print("\n🌐 Відкриваю веб-інтерфейси...")
    
    for name, url in urls:
        try:
            webbrowser.open(url)
            print(f"  ✅ {name}: {url}")
            time.sleep(1)  # Невелика пауза між відкриттям вкладок
        except Exception as e:
            print(f"  ❌ Не вдалося відкрити {name}: {e}")

def show_demo_script():
    """Показує демонстраційний скрипт"""
    print("\n🎭 Демонстраційний сценарій:")
    print("""
1. 🔐 АВТОРИЗАЦІЯ
   • Відкрийте http://localhost:5000
   • Спробуйте вхід: admin/admin123
   • Створіть нового користувача

2. 📊 МЕТРИКИ
   • Відкрийте http://localhost:8000/metrics
   • Подивіться на генеровані метрики
   • Зверніть увагу на формат Prometheus

3. 🎯 PROMETHEUS  
   • Відкрийте http://localhost:9090
   • Перейдіть до Status → Targets
   • Спробуйте запити:
     - total_users_count
     - active_users_count
     - rate(orders_total[5m])

4. 📈 GRAFANA
   • Відкрийте http://localhost:3000
   • Увійдіть: admin/admin123
   • Відкрийте "MySQL Monitoring Dashboard"
   • Подивіться на графіки в реальному часі

5. 🔄 LIVE DEMO
   • Дані генеруються автоматично
   • Метрики оновлюються кожні 30 секунд  
   • Графіки показують зміни в реальному часі
""")

def run_comprehensive_demo():
    """Запускає повну демонстрацію"""
    
    print_header("🚀 ДЕМОНСТРАЦІЯ СИСТЕМИ МОНІТОРИНГУ MYSQL")
    
    print("""
Ця система демонструє:
✨ Моніторинг MySQL з Prometheus та Grafana
🔐 Сервіс авторизації з JWT токенами  
📊 Кастомні метрики та дашборди
🐳 Повну контейнеризацію з Docker
🔄 Генерацію даних в реальному часі
""")
    
    wait_for_user("Готові почати демонстрацію?")
    
    # Крок 1: Перевірка системи
    print_step(1, "Перевірка стану системи")
    
    result = subprocess.run("docker-compose ps", shell=True, capture_output=True, text=True)
    print(result.stdout)
    
    if "Up" not in result.stdout:
        print("❌ Система не запущена. Запускаю...")
        subprocess.run("docker-compose up -d", shell=True)
        print("⏳ Очікування ініціалізації (60 секунд)...")
        time.sleep(60)
    else:
        print("✅ Система запущена та готова")
    
    wait_for_user()
    
    # Крок 2: Відкриття інтерфейсів
    print_step(2, "Відкриття веб-інтерфейсів")
    open_browser_tabs()
    wait_for_user()
    
    # Крок 3: Демонстраційний сценарій
    print_step(3, "Демонстраційний сценарій")
    show_demo_script()
    wait_for_user("Готові розпочати інтерактивну демонстрацію?")
    
    # Крок 4: Запуск API демо
    print_step(4, "Тестування API")
    print("Запускаю демонстрацію API...")
    subprocess.run([sys.executable, "api_examples.py"])
    
    wait_for_user()
    
    # Крок 5: Системні тести
    print_step(5, "Системні тести")
    print("Запускаю повні системні тести...")
    subprocess.run([sys.executable, "test_system.py"])
    
    wait_for_user()
    
    # Фінал
    print_header("🎉 ДЕМОНСТРАЦІЯ ЗАВЕРШЕНА")
    
    print("""
Що ви побачили:
✅ Повністю функціональну систему моніторингу
✅ Інтеграцію між всіма компонентами
✅ Реальні метрики та дашборди
✅ Працюючу авторизацію та API
✅ Автоматичну генерацію даних

Файли проекту:
📁 auth/           - Сервіс авторизації
📁 data_generator/ - Генератор даних  
📁 metrics_exporter/ - Експортер метрик
📁 config/         - Конфігурації
📁 grafana/        - Дашборди Grafana
📁 prometheus/     - Конфігурація Prometheus
📄 docker-compose.yml - Опис всіх сервісів
📄 README.md       - Повна документація

Корисні команди:
🔧 docker-compose logs -f  - Логи всіх сервісів
🔧 docker-compose down     - Зупинка системи  
🔧 python test_system.py   - Тестування
🔧 python start.py         - Швидкий запуск
""")
    
    print("\n💡 Рекомендації для подальшого вивчення:")
    print("1. Змініть метрики в metrics_exporter/app.py")
    print("2. Створіть власні дашборди в Grafana") 
    print("3. Додайте нові таблиці в data_generator/app.py")
    print("4. Налаштуйте алерти в Grafana")
    print("5. Інтегруйте з реальною базою даних")

def main():
    """Головна функція"""
    try:
        run_comprehensive_demo()
    except KeyboardInterrupt:
        print("\n\n👋 Демонстрацію зупинено користувачем")
    except Exception as e:
        print(f"\n❌ Помилка під час демонстрації: {e}")

if __name__ == "__main__":
    main()

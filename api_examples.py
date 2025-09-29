#!/usr/bin/env python3
"""
Приклади використання API сервісів
"""

import requests
import json
import time

# Базові URL сервісів
AUTH_URL = "http://localhost:5000"
METRICS_URL = "http://localhost:8000"

def demo_auth_service():
    """Демонстрація роботи з сервісом авторизації"""
    print("🔐 Демонстрація сервісу авторизації")
    print("-" * 40)
    
    # 1. Вхід адміністратора
    print("\n1. Вхід адміністратора:")
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    response = requests.post(f"{AUTH_URL}/login", json=login_data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        auth_data = response.json()
        token = auth_data['token']
        print(f"Token отримано: {token[:50]}...")
        
        # 2. Перевірка токену
        print("\n2. Перевірка токену:")
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(f"{AUTH_URL}/verify", headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        # 3. Отримання профілю
        print("\n3. Отримання профілю:")
        response = requests.get(f"{AUTH_URL}/profile", headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        # 4. Реєстрація нового користувача
        print("\n4. Реєстрація нового користувача:")
        new_user = {
            "username": f"testuser_{int(time.time())}",
            "email": "test@example.com",
            "password": "password123"
        }
        
        response = requests.post(f"{AUTH_URL}/register", json=new_user)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        # 5. Список користувачів (тільки для адміна)
        print("\n5. Список всіх користувачів:")
        response = requests.get(f"{AUTH_URL}/admin/users", headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            users = response.json()['users']
            print(f"Знайдено {len(users)} користувачів:")
            for user in users[:3]:  # Показуємо перших 3
                print(f"  - {user['username']} ({user['role']}) - {user['email']}")
        
        return token
    else:
        print(f"Помилка входу: {response.text}")
        return None

def demo_metrics_service():
    """Демонстрація роботи з сервісом метрик"""
    print("\n\n📊 Демонстрація сервісу метрик")
    print("-" * 40)
    
    # 1. Головна сторінка
    print("\n1. Інформація про сервіс:")
    response = requests.get(METRICS_URL)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    # 2. Health check
    print("\n2. Health check:")
    response = requests.get(f"{METRICS_URL}/health")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    # 3. Метрики для Prometheus
    print("\n3. Prometheus метрики:")
    response = requests.get(f"{METRICS_URL}/metrics")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        metrics_text = response.text
        
        # Аналізуємо метрики
        lines = metrics_text.split('\n')
        metric_lines = [line for line in lines if line and not line.startswith('#')]
        
        print(f"Знайдено {len(metric_lines)} рядків метрик")
        
        # Показуємо кілька цікавих метрик
        interesting_metrics = [
            'total_users_count',
            'active_users_count',
            'total_products_count',
            'pending_orders_count',
            'total_revenue'
        ]
        
        print("\nОсновні метрики:")
        for metric in interesting_metrics:
            for line in metric_lines:
                if line.startswith(metric):
                    print(f"  {line}")
                    break

def demo_prometheus_queries():
    """Приклади запитів до Prometheus"""
    print("\n\n🎯 Приклади Prometheus запитів")
    print("-" * 40)
    
    prometheus_url = "http://localhost:9090"
    
    queries = [
        ("Активні користувачі", "active_users_count"),
        ("Загальна кількість користувачів", "total_users_count"),
        ("Швидкість створення замовлень", "rate(orders_total[5m])"),
        ("Середній час запитів", "rate(mysql_query_duration_seconds_sum[5m]) / rate(mysql_query_duration_seconds_count[5m])"),
        ("Загальний дохід", "total_revenue")
    ]
    
    for description, query in queries:
        print(f"\n{description}:")
        print(f"Query: {query}")
        
        try:
            response = requests.get(f"{prometheus_url}/api/v1/query", 
                                  params={'query': query}, 
                                  timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'success' and data['data']['result']:
                    result = data['data']['result'][0]
                    value = result['value'][1]
                    print(f"Поточне значення: {value}")
                else:
                    print("Немає даних")
            else:
                print(f"Помилка: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"Помилка підключення: {e}")

def demo_system_integration():
    """Демонстрація інтеграції між сервісами"""
    print("\n\n🔗 Демонстрація інтеграції системи")
    print("-" * 40)
    
    # Отримуємо токен авторизації
    token = demo_auth_service()
    
    if token:
        print("\n✅ Авторизація пройшла успішно")
        
        # Перевіряємо метрики
        demo_metrics_service()
        
        # Перевіряємо Prometheus
        demo_prometheus_queries()
        
        print("\n🎉 Всі сервіси працюють в інтеграції!")
        
        # Рекомендації для подальшого використання
        print("\n💡 Рекомендації:")
        print("1. Відкрийте Grafana: http://localhost:3000 (admin/admin123)")
        print("2. Перегляньте дашборд 'MySQL Monitoring Dashboard'")
        print("3. Експериментуйте з Prometheus: http://localhost:9090")
        print("4. Використовуйте Auth API для створення власних додатків")
    else:
        print("\n❌ Помилка авторизації. Перевірте, чи запущені сервіси")

def main():
    """Основна функція"""
    print("🚀 Демонстрація API системи моніторингу")
    print("=" * 50)
    
    try:
        demo_system_integration()
    except KeyboardInterrupt:
        print("\n\n👋 Демонстрацію зупинено користувачем")
    except Exception as e:
        print(f"\n❌ Помилка під час демонстрації: {e}")
        print("\n🔧 Переконайтеся, що система запущена:")
        print("   docker-compose up -d")

if __name__ == "__main__":
    main()

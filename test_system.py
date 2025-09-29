#!/usr/bin/env python3
"""
Скрипт для тестування системи моніторингу MySQL
"""

import requests
import time
import json
import sys

# Конфігурація сервісів
SERVICES = {
    'auth': 'http://localhost:5000',
    'metrics': 'http://localhost:8000',
    'prometheus': 'http://localhost:9090',
    'grafana': 'http://localhost:3000'
}

def test_service_health(service_name, url):
    """Тестування доступності сервісу"""
    try:
        if service_name == 'grafana':
            # Grafana має інший endpoint для перевірки
            response = requests.get(f"{url}/api/health", timeout=5)
        elif service_name == 'prometheus':
            # Prometheus має інший endpoint
            response = requests.get(f"{url}/-/healthy", timeout=5)
        else:
            # Інші сервіси мають /health
            response = requests.get(f"{url}/health", timeout=5)
        
        if response.status_code == 200:
            print(f"✅ {service_name.upper()}: Сервіс доступний")
            return True
        else:
            print(f"❌ {service_name.upper()}: Помилка {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ {service_name.upper()}: Недоступний ({e})")
        return False

def test_auth_service():
    """Тестування сервісу авторизації"""
    print("\n🔐 Тестування сервісу авторизації...")
    
    auth_url = SERVICES['auth']
    
    # Тест входу адміністратора
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(f"{auth_url}/login", json=login_data, timeout=10)
        
        if response.status_code == 200:
            token = response.json().get('token')
            print("✅ Успішний вхід адміністратора")
            
            # Тест перевірки токену
            headers = {'Authorization': f'Bearer {token}'}
            verify_response = requests.get(f"{auth_url}/verify", headers=headers, timeout=5)
            
            if verify_response.status_code == 200:
                print("✅ Токен валідний")
                return token
            else:
                print("❌ Токен невалідний")
                return None
        else:
            print(f"❌ Помилка входу: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Помилка підключення до сервісу авторизації: {e}")
        return None

def test_metrics_endpoint():
    """Тестування endpoint метрик"""
    print("\n📊 Тестування endpoint метрик...")
    
    try:
        response = requests.get(f"{SERVICES['metrics']}/metrics", timeout=10)
        
        if response.status_code == 200:
            metrics_data = response.text
            
            # Перевіряємо наявність основних метрик
            expected_metrics = [
                'total_users_count',
                'active_users_count',
                'total_products_count',
                'pending_orders_count',
                'total_revenue'
            ]
            
            found_metrics = []
            for metric in expected_metrics:
                if metric in metrics_data:
                    found_metrics.append(metric)
            
            print(f"✅ Знайдено {len(found_metrics)}/{len(expected_metrics)} метрик")
            
            if len(found_metrics) == len(expected_metrics):
                print("✅ Всі очікувані метрики присутні")
                return True
            else:
                missing = set(expected_metrics) - set(found_metrics)
                print(f"⚠️  Відсутні метрики: {missing}")
                return False
        else:
            print(f"❌ Помилка отримання метрик: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Помилка підключення до metrics endpoint: {e}")
        return False

def test_prometheus_targets():
    """Тестування цілей Prometheus"""
    print("\n🎯 Тестування цілей Prometheus...")
    
    try:
        response = requests.get(f"{SERVICES['prometheus']}/api/v1/targets", timeout=10)
        
        if response.status_code == 200:
            targets_data = response.json()
            
            if targets_data.get('status') == 'success':
                active_targets = targets_data['data']['activeTargets']
                
                target_status = {}
                for target in active_targets:
                    job = target['labels']['job']
                    health = target['health']
                    target_status[job] = health
                
                print("📋 Статус цілей:")
                for job, health in target_status.items():
                    status = "✅" if health == "up" else "❌"
                    print(f"  {status} {job}: {health}")
                
                up_targets = sum(1 for health in target_status.values() if health == "up")
                total_targets = len(target_status)
                
                print(f"\n📊 Загалом: {up_targets}/{total_targets} цілей активні")
                return up_targets == total_targets
            else:
                print("❌ Помилка отримання даних з Prometheus")
                return False
        else:
            print(f"❌ Помилка підключення до Prometheus: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Помилка підключення до Prometheus: {e}")
        return False

def test_grafana_datasources():
    """Тестування джерел даних Grafana"""
    print("\n📈 Тестування джерел даних Grafana...")
    
    try:
        # Спробуємо отримати інформацію про джерела даних
        # (це може потребувати аутентифікації в реальному середовищі)
        response = requests.get(f"{SERVICES['grafana']}/api/datasources", 
                              auth=('admin', 'admin123'), timeout=10)
        
        if response.status_code == 200:
            datasources = response.json()
            
            if datasources:
                print("✅ Знайдено джерела даних:")
                for ds in datasources:
                    print(f"  📊 {ds['name']} ({ds['type']})")
                return True
            else:
                print("⚠️  Джерела даних не знайдено")
                return False
        else:
            print(f"⚠️  Не вдалося отримати джерела даних: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"⚠️  Помилка підключення до Grafana: {e}")
        return False

def main():
    """Основна функція тестування"""
    print("🚀 Тестування системи моніторингу MySQL")
    print("=" * 50)
    
    # Тестування доступності сервісів
    print("\n🔍 Перевірка доступності сервісів...")
    
    service_results = {}
    for service_name, url in SERVICES.items():
        service_results[service_name] = test_service_health(service_name, url)
    
    # Детальне тестування
    auth_result = test_auth_service()
    metrics_result = test_metrics_endpoint()
    prometheus_result = test_prometheus_targets()
    grafana_result = test_grafana_datasources()
    
    # Підсумок
    print("\n" + "=" * 50)
    print("📋 ПІДСУМОК ТЕСТУВАННЯ")
    print("=" * 50)
    
    print("\n🔧 Доступність сервісів:")
    for service, result in service_results.items():
        status = "✅ ОК" if result else "❌ ПОМИЛКА"
        print(f"  {service.upper()}: {status}")
    
    print("\n🧪 Функціональні тести:")
    print(f"  Авторизація: {'✅ ОК' if auth_result else '❌ ПОМИЛКА'}")
    print(f"  Метрики: {'✅ ОК' if metrics_result else '❌ ПОМИЛКА'}")
    print(f"  Prometheus: {'✅ ОК' if prometheus_result else '❌ ПОМИЛКА'}")
    print(f"  Grafana: {'✅ ОК' if grafana_result else '⚠️  ЧАСТКОВА'}")
    
    # Загальний результат
    all_services_up = all(service_results.values())
    critical_tests_pass = auth_result and metrics_result and prometheus_result
    
    if all_services_up and critical_tests_pass:
        print("\n🎉 СИСТЕМА ПРАЦЮЄ КОРЕКТНО!")
        print("\n📖 Інструкції:")
        print("  • Grafana: http://localhost:3000 (admin/admin123)")
        print("  • Prometheus: http://localhost:9090")
        print("  • Auth API: http://localhost:5000")
        print("  • Metrics: http://localhost:8000/metrics")
        return 0
    else:
        print("\n⚠️  СИСТЕМА ПРАЦЮЄ З ПОМИЛКАМИ")
        print("\n🔧 Рекомендації:")
        if not all_services_up:
            print("  • Перевірте, що всі контейнери запущені: docker-compose ps")
            print("  • Перегляньте логи: docker-compose logs")
        if not critical_tests_pass:
            print("  • Зачекайте повної ініціалізації системи (2-3 хвилини)")
            print("  • Перезапустіть сервіси: docker-compose restart")
        return 1

if __name__ == "__main__":
    sys.exit(main())

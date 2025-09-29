# Швидкий старт

## 🚀 Запуск за 3 кроки

### 1. Встановіть Docker
- Завантажте та встановіть [Docker Desktop](https://www.docker.com/products/docker-desktop)

### 2. Запустіть систему
```bash
# Опція A: Автоматичний запуск
python start.py

# Опція B: Ручний запуск
docker-compose up -d
```

### 3. Отримайте доступ до сервісів
- **Grafana**: http://localhost:3000 (admin/admin123)
- **Prometheus**: http://localhost:9090
- **Auth API**: http://localhost:5000

## 🧪 Тестування системи
```bash
python test_system.py
```

## 📊 Що ви побачите

### У Grafana:
- Дашборд "MySQL Monitoring Dashboard"
- Графіки користувачів, продуктів, замовлень
- Метрики продуктивності MySQL

### У Prometheus:
- Збір метрик з MySQL
- Кастомні бізнес-метрики
- Метрики авторизації

## 🔧 Корисні команди

```bash
# Перегляд статусу
docker-compose ps

# Перегляд логів
docker-compose logs -f

# Зупинка системи
docker-compose down

# Перезапуск сервісу
docker-compose restart metrics_exporter
```

## ❓ Проблеми?

1. **Порти зайняті**: Змініть порти в `docker-compose.yml`
2. **Сервіси не запускаються**: Зачекайте 2-3 хвилини для ініціалізації
3. **Немає даних в Grafana**: Перевірте `http://localhost:9090/targets`

Детальна документація: `README.md`

# Система моніторингу MySQL з Prometheus та Grafana

Цей проект представляє собою повноцінну систему моніторингу MySQL бази даних з використанням Prometheus для збору метрик, Grafana для візуалізації та сервісу авторизації.

## Архітектура проекту

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Generator│    │ Metrics Exporter│    │ Auth Service    │
│   (Python)      │    │   (Python)      │    │   (Python)      │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     MySQL       │    │   Prometheus    │    │   SQLite        │
│   (Database)    │    │  (Metrics DB)   │    │  (Auth DB)      │
└─────────────────┘    └─────────┬───────┘    └─────────────────┘
                                 │
                                 ▼
                       ┌─────────────────┐
                       │    Grafana      │
                       │ (Visualization) │
                       └─────────────────┘
```

## Компоненти системи

### 1. MySQL Database
- **Призначення**: Основна база даних для зберігання бізнес-даних
- **Конфігурація**: Налаштована для максимального збору метрик
- **Порт**: 3306
- **Користувач**: monitor_user/monitor_pass

### 2. Data Generator (Python)
- **Призначення**: Генерація тестових даних та симуляція активності
- **Функції**:
  - Створення користувачів, продуктів, замовлень
  - Симуляція реальної активності
  - Безперервна генерація даних для моніторингу

### 3. Metrics Exporter (Python)
- **Призначення**: Збір кастомних метрик з MySQL та експорт до Prometheus
- **Порт**: 8000
- **Endpoint**: `/metrics`
- **Метрики**:
  - Кількість користувачів (загальна/активні)
  - Статистика продуктів
  - Статистика замовлень
  - Продуктивність запитів
  - Дохід

### 4. Prometheus
- **Призначення**: Збір, зберігання та обробка метрик
- **Порт**: 9090
- **Джерела метрик**:
  - MySQL Exporter (стандартні метрики MySQL)
  - Custom Metrics Exporter (бізнес-метрики)
  - Auth Service (метрики авторизації)

### 5. Grafana
- **Призначення**: Візуалізація метрик та створення дашбордів
- **Порт**: 3000
- **Користувач**: admin/admin123
- **Функції**:
  - Готові дашборди для MySQL моніторингу
  - Налаштовані джерела даних
  - Алерти та сповіщення

### 6. Auth Service (Python)
- **Призначення**: Авторизація та аутентифікація користувачів
- **Порт**: 5000
- **База даних**: SQLite
- **Функції**:
  - Реєстрація користувачів
  - JWT аутентифікація
  - Управління ролями
  - Логування спроб входу

## Швидкий запуск

### Передумови
- Docker та Docker Compose
- Мінімум 4GB RAM
- Порти 3000, 3306, 5000, 8000, 9090, 9104 мають бути вільними

### 1. Клонування та запуск

```bash
# Перейти до директорії проекту
cd D:\Uni\infosys\lab1

# Запустити всю систему
docker-compose up -d

# Перевірити статус сервісів
docker-compose ps
```

### 2. Перевірка запуску

```bash
# Перевірити логи всіх сервісів
docker-compose logs

# Перевірити конкретний сервіс
docker-compose logs mysql
docker-compose logs prometheus
docker-compose logs grafana
```

### 3. Доступ до сервісів

| Сервіс | URL | Користувач | Пароль |
|--------|-----|------------|--------|
| **Grafana** | http://localhost:3000 | admin | admin123 |
| **Prometheus** | http://localhost:9090 | - | - |
| **Auth Service** | http://localhost:5000 | admin | admin123 |
| **Metrics Exporter** | http://localhost:8000/metrics | - | - |
| **MySQL** | localhost:3306 | monitor_user | monitor_pass |

## Використання системи

### 1. Авторизація

#### Вхід до системи
```bash
curl -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

#### Реєстрація нового користувача
```bash
curl -X POST http://localhost:5000/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "user@example.com",
    "password": "password123"
  }'
```

#### Перевірка токену
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:5000/verify
```

### 2. Моніторинг в Grafana

1. Відкрийте http://localhost:3000
2. Увійдіть як admin/admin123
3. Перейдіть до Dashboards → Browse
4. Відкрийте "MySQL Monitoring Dashboard"

#### Основні метрики на дашборді:
- **Статистика користувачів**: Загальна кількість, активні користувачі
- **Статистика продуктів**: Кількість продуктів, товари з низьким запасом
- **Статистика замовлень**: Очікуючі замовлення, швидкість створення
- **Дохід**: Загальний дохід від продажів
- **Продуктивність**: Час виконання запитів, навантаження на БД

### 3. Prometheus Queries

Приклади корисних запитів:

```promql
# Кількість активних користувачів
active_users_count

# Швидкість створення замовлень за 5 хвилин
rate(orders_total[5m])

# Середній час виконання запитів
rate(mysql_query_duration_seconds_sum[5m]) / rate(mysql_query_duration_seconds_count[5m])

# Кількість запитів до БД за секунду
rate(mysql_queries_total[5m])
```

## Розширення та налаштування

### Додавання нових метрик

1. Відредагуйте `metrics_exporter/app.py`
2. Додайте нові Prometheus метрики
3. Реалізуйте збір даних в методах `collect_*_metrics`
4. Перезапустіть контейнер: `docker-compose restart metrics_exporter`

### Додавання нових дашбордів

1. Створіть новий JSON файл в `grafana/provisioning/dashboards/`
2. Перезапустіть Grafana: `docker-compose restart grafana`

### Налаштування алертів

1. В Grafana перейдіть до Alerting → Alert Rules
2. Створіть нові правила на базі наявних метрик
3. Налаштуйте канали сповіщень (email, Slack, тощо)

## Розробка та налагодження

### Локальна розробка

```bash
# Встановити залежності
pip install -r requirements.txt

# Запустити тільки MySQL та Prometheus
docker-compose up mysql prometheus -d

# Запустити сервіси локально для розробки
cd auth && python app.py
cd metrics_exporter && python app.py
cd data_generator && python app.py
```

### Перегляд логів

```bash
# Всі логи
docker-compose logs -f

# Конкретний сервіс
docker-compose logs -f mysql
docker-compose logs -f metrics_exporter
docker-compose logs -f auth_service
```

### Підключення до MySQL

```bash
# Через Docker
docker-compose exec mysql mysql -u monitor_user -p monitoring_db

# Або через будь-який MySQL клієнт
# Host: localhost:3306
# User: monitor_user
# Password: monitor_pass
# Database: monitoring_db
```

## Безпека

### Зміна паролів за замовчуванням

1. **MySQL**: Відредагуйте змінні середовища в `docker-compose.yml`
2. **Grafana**: Встановіть `GF_SECURITY_ADMIN_PASSWORD`
3. **Auth Service**: Змініть пароль адміністратора після першого входу

### JWT конфігурація

Встановіть змінну середовища `JWT_SECRET` для production:

```bash
export JWT_SECRET="your-super-secret-key"
```

## Troubleshooting

### Проблема: Сервіси не можуть підключитися до MySQL

**Рішення**: Зачекайте повної ініціалізації MySQL (1-2 хвилини) або перезапустіть:

```bash
docker-compose restart data_generator metrics_exporter
```

### Проблема: Grafana не показує дані

**Рішення**:
1. Перевірте, що Prometheus збирає метрики: http://localhost:9090/targets
2. Перевірте джерела даних в Grafana: Configuration → Data Sources
3. Перезапустіть сервіси: `docker-compose restart`

### Проблема: Порти зайняті

**Рішення**: Зупиніть конфліктуючі сервіси або змініть порти в `docker-compose.yml`

### Проблема: Недостатньо місця на диску

**Рішення**: Очистіть Docker:

```bash
docker system prune -a
docker volume prune
```

## Додаткові ресурси

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [MySQL Performance Schema](https://dev.mysql.com/doc/refman/8.0/en/performance-schema.html)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

## Ліцензія

Цей проект створено для навчальних цілей. Використовуйте на свій розсуд.

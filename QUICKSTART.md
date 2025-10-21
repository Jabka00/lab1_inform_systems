#  старт


###  Запустіть систему
```bash
docker-compose up -d
```

###  Отримайте доступ до сервісів
- ** Авторизація**: http://localhost:5001 (admin/admin123 або user/user123)
- **Grafana**: http://localhost:3000 (через авторизацію)
- **Prometheus**: http://localhost:9090 (через авторизацію)



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

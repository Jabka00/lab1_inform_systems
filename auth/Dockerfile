FROM python:3.9-slim

WORKDIR /app

# Копіюємо requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо код
COPY app.py .

# Створюємо директорію для SQLite
RUN mkdir -p /app/data

# Відкриваємо порт
EXPOSE 5000

# Запускаємо додаток
CMD ["python", "app.py"]

import os
import time
import logging
from datetime import datetime
import mysql.connector
from mysql.connector import Error
from flask import Flask, Response
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
import threading

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Prometheus метрики - простіші та зрозуміліші
# Основні гейджі
mysql_active_users = Gauge('mysql_active_users', 'Number of active users')
mysql_total_users = Gauge('mysql_total_users', 'Total number of users')
mysql_total_products = Gauge('mysql_total_products', 'Total number of products')
mysql_pending_orders = Gauge('mysql_pending_orders', 'Number of pending orders')
mysql_total_revenue = Gauge('mysql_total_revenue', 'Total revenue from completed orders')

# Лічильники активності
mysql_operations_total = Counter('mysql_operations_total', 'Total database operations')
mysql_orders_per_minute = Gauge('mysql_orders_per_minute', 'Orders created in last minute')

# Простий час запитів
mysql_avg_query_time = Gauge('mysql_avg_query_time', 'Average query execution time in seconds')

class MetricsExporter:
    def __init__(self):
        self.connection = None
        self.cursor = None
        self.connect_to_mysql()
        
    def connect_to_mysql(self):
        """Підключення до MySQL з перевіркою доступності"""
        max_retries = 30
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                self.connection = mysql.connector.connect(
                    host=os.getenv('MYSQL_HOST', 'localhost'),
                    port=int(os.getenv('MYSQL_PORT', 3306)),
                    user=os.getenv('MYSQL_USER', 'monitor_user'),
                    password=os.getenv('MYSQL_PASSWORD', 'monitor_pass'),
                    database=os.getenv('MYSQL_DATABASE', 'monitoring_db'),
                    autocommit=True
                )
                self.cursor = self.connection.cursor()
                logger.info("Успішно підключено до MySQL для експорту метрик")
                return
                
            except Error as e:
                retry_count += 1
                logger.warning(f"Спроба підключення {retry_count}/{max_retries} невдала: {e}")
                time.sleep(5)
                
        logger.error("Не вдалося підключитися до MySQL після всіх спроб")
        raise Exception("Не вдалося підключитися до MySQL")
    
    def execute_query(self, query):
        """Виконання запиту з підрахунком метрик"""
        start_time = time.time()
        
        try:
            self.cursor.execute(query)
            result = self.cursor.fetchall()
            
            # Збільшуємо лічильник операцій
            mysql_operations_total.inc()
            
            # Записуємо середній час виконання
            duration = time.time() - start_time
            mysql_avg_query_time.set(duration)
            
            return result
            
        except Error as e:
            logger.error(f"Помилка виконання запиту: {e}")
            return []
    
    def collect_all_metrics(self):
        """Збір всіх метрик"""
        try:
            logger.info("Збір метрик...")
            
            # Користувачі
            result = self.execute_query("SELECT COUNT(*) FROM users")
            if result:
                mysql_total_users.set(result[0][0])
            
            result = self.execute_query("SELECT COUNT(*) FROM users WHERE status = 'active'")
            if result:
                mysql_active_users.set(result[0][0])
            
            # Продукти
            result = self.execute_query("SELECT COUNT(*) FROM products")
            if result:
                mysql_total_products.set(result[0][0])
            
            # Замовлення
            result = self.execute_query("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
            if result:
                mysql_pending_orders.set(result[0][0])
            
            # Дохід
            result = self.execute_query("SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE status = 'completed'")
            if result:
                mysql_total_revenue.set(float(result[0][0]))
            
            # Замовлення за останню хвилину
            result = self.execute_query("SELECT COUNT(*) FROM orders WHERE order_date >= DATE_SUB(NOW(), INTERVAL 1 MINUTE)")
            if result:
                mysql_orders_per_minute.set(result[0][0])
            
            logger.info("Метрики зібрано")
            
        except Exception as e:
            logger.error(f"Помилка збору метрик: {e}")
    
    def run_metrics_collection(self):
        """Безперервний збір метрик"""
        while True:
            try:
                self.collect_all_metrics()
                time.sleep(30)  # Збираємо метрики кожні 30 секунд
            except Exception as e:
                logger.error(f"Помилка в циклі збору метрик: {e}")
                time.sleep(60)
    
    def close_connection(self):
        """Закриття підключення"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logger.info("Підключення до MySQL закрито")

# Глобальний екземпляр експортера
metrics_exporter = None

@app.route('/metrics')
def metrics():
    """Endpoint для Prometheus"""
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}

@app.route('/')
def index():
    """Головна сторінка"""
    return {
        'service': 'MySQL Metrics Exporter',
        'status': 'running',
        'endpoints': {
            'metrics': '/metrics',
            'health': '/health'
        }
    }

def start_metrics_collection():
    """Запуск збору метрик в окремому потоці"""
    global metrics_exporter
    metrics_exporter = MetricsExporter()
    metrics_thread = threading.Thread(target=metrics_exporter.run_metrics_collection)
    metrics_thread.daemon = True
    metrics_thread.start()
    logger.info("Збір метрик запущено в фоновому режимі")

if __name__ == '__main__':
    start_metrics_collection()
    
    try:
        app.run(host='0.0.0.0', port=8000, debug=False)
    except KeyboardInterrupt:
        logger.info("Отримано сигнал зупинки...")
    finally:
        if metrics_exporter:
            metrics_exporter.close_connection()
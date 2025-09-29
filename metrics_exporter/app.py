import os
import time
import logging
from datetime import datetime
import mysql.connector
from mysql.connector import Error
from flask import Flask, Response
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
import threading

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Prometheus метрики
# Лічильники
db_queries_total = Counter('mysql_queries_total', 'Total number of database queries', ['query_type'])
db_connections_total = Counter('mysql_connections_total', 'Total number of database connections')
user_registrations_total = Counter('user_registrations_total', 'Total number of user registrations')
orders_total = Counter('orders_total', 'Total number of orders', ['status'])

# Гейджи (поточні значення)
active_users = Gauge('active_users_count', 'Number of active users')
total_users = Gauge('total_users_count', 'Total number of users')
total_products = Gauge('total_products_count', 'Total number of products')
low_stock_products = Gauge('low_stock_products_count', 'Number of products with low stock')
pending_orders = Gauge('pending_orders_count', 'Number of pending orders')
total_revenue = Gauge('total_revenue', 'Total revenue from completed orders')

# Гістограми
query_duration = Histogram('mysql_query_duration_seconds', 'Time spent on database queries', ['query_type'])

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
    
    def execute_query(self, query, query_type="select"):
        """Виконання запиту з підрахунком метрик"""
        start_time = time.time()
        
        try:
            self.cursor.execute(query)
            result = self.cursor.fetchall()
            
            # Збільшуємо лічильник запитів
            db_queries_total.labels(query_type=query_type).inc()
            
            # Записуємо час виконання
            duration = time.time() - start_time
            query_duration.labels(query_type=query_type).observe(duration)
            
            return result
            
        except Error as e:
            logger.error(f"Помилка виконання запиту: {e}")
            return []
    
    def collect_user_metrics(self):
        """Збір метрик користувачів"""
        try:
            # Загальна кількість користувачів
            result = self.execute_query("SELECT COUNT(*) FROM users", "count_users")
            if result:
                total_users.set(result[0][0])
            
            # Активні користувачі
            result = self.execute_query("SELECT COUNT(*) FROM users WHERE status = 'active'", "count_active_users")
            if result:
                active_users.set(result[0][0])
            
            # Нові реєстрації за останню годину
            result = self.execute_query("""
                SELECT COUNT(*) FROM users 
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
            """, "new_registrations")
            
            if result:
                user_registrations_total.inc(result[0][0])
            
        except Exception as e:
            logger.error(f"Помилка збору метрик користувачів: {e}")
    
    def collect_product_metrics(self):
        """Збір метрик продуктів"""
        try:
            # Загальна кількість продуктів
            result = self.execute_query("SELECT COUNT(*) FROM products", "count_products")
            if result:
                total_products.set(result[0][0])
            
            # Продукти з низьким запасом (менше 10)
            result = self.execute_query("SELECT COUNT(*) FROM products WHERE stock_quantity < 10", "low_stock")
            if result:
                low_stock_products.set(result[0][0])
            
        except Exception as e:
            logger.error(f"Помилка збору метрик продуктів: {e}")
    
    def collect_order_metrics(self):
        """Збір метрик замовлень"""
        try:
            # Замовлення за статусом
            statuses = ['pending', 'processing', 'completed', 'cancelled']
            for status in statuses:
                result = self.execute_query(f"SELECT COUNT(*) FROM orders WHERE status = '{status}'", f"count_orders_{status}")
                if result:
                    if status == 'pending':
                        pending_orders.set(result[0][0])
                    orders_total.labels(status=status).inc(result[0][0])
            
            # Загальний дохід від завершених замовлень
            result = self.execute_query("SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE status = 'completed'", "revenue")
            if result:
                total_revenue.set(float(result[0][0]))
            
        except Exception as e:
            logger.error(f"Помилка збору метрик замовлень: {e}")
    
    def collect_database_metrics(self):
        """Збір загальних метрик бази даних"""
        try:
            # Кількість підключень
            result = self.execute_query("SHOW STATUS LIKE 'Threads_connected'", "connections")
            if result:
                db_connections_total.inc()
            
            # Додаткові метрики MySQL можна додати тут
            
        except Exception as e:
            logger.error(f"Помилка збору метрик БД: {e}")
    
    def collect_all_metrics(self):
        """Збір всіх метрик"""
        logger.info("Збір метрик...")
        self.collect_user_metrics()
        self.collect_product_metrics()
        self.collect_order_metrics()
        self.collect_database_metrics()
        logger.info("Метрики зібрано")
    
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

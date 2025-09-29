import os
import time
import random
import logging
from datetime import datetime, timedelta
import mysql.connector
from mysql.connector import Error
import threading

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataGenerator:
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
                logger.info("Успішно підключено до MySQL")
                self.setup_database()
                return
                
            except Error as e:
                retry_count += 1
                logger.warning(f"Спроба підключення {retry_count}/{max_retries} невдала: {e}")
                time.sleep(5)
                
        logger.error("Не вдалося підключитися до MySQL після всіх спроб")
        raise Exception("Не вдалося підключитися до MySQL")
    
    def setup_database(self):
        """Створення таблиць для моніторингу"""
        try:
            # Таблиця користувачів
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    status ENUM('active', 'inactive', 'suspended') DEFAULT 'active'
                )
            """)
            
            # Таблиця продуктів
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    category VARCHAR(50),
                    price DECIMAL(10,2),
                    stock_quantity INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            
            # Таблиця замовлень
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    product_id INT,
                    quantity INT,
                    total_amount DECIMAL(10,2),
                    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status ENUM('pending', 'processing', 'completed', 'cancelled') DEFAULT 'pending',
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (product_id) REFERENCES products(id)
                )
            """)
            
            # Таблиця логів активності
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    action VARCHAR(100),
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_address VARCHAR(45),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            logger.info("Структура бази даних створена успішно")
            
        except Error as e:
            logger.error(f"Помилка при створенні структури БД: {e}")
    
    def generate_users(self, count=10):
        """Генерація користувачів"""
        usernames = [
            'admin', 'user1', 'john_doe', 'jane_smith', 'alex_brown',
            'mike_jones', 'sarah_wilson', 'david_clark', 'lisa_taylor', 'tom_white'
        ]
        
        domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'company.com']
        statuses = ['active', 'inactive', 'suspended']
        
        for i in range(count):
            try:
                username = f"{random.choice(usernames)}_{random.randint(1, 1000)}"
                email = f"{username}@{random.choice(domains)}"
                status = random.choice(statuses)
                last_login = datetime.now() - timedelta(days=random.randint(0, 30))
                
                self.cursor.execute("""
                    INSERT IGNORE INTO users (username, email, status, last_login)
                    VALUES (%s, %s, %s, %s)
                """, (username, email, status, last_login))
                
            except Error as e:
                logger.warning(f"Помилка при додаванні користувача: {e}")
    
    def generate_products(self, count=50):
        """Генерація продуктів"""
        categories = ['Electronics', 'Clothing', 'Books', 'Home', 'Sports', 'Toys']
        product_names = [
            'Laptop', 'Smartphone', 'Headphones', 'T-Shirt', 'Jeans', 'Book',
            'Chair', 'Table', 'Ball', 'Toy Car', 'Camera', 'Watch'
        ]
        
        for i in range(count):
            try:
                name = f"{random.choice(product_names)} {random.randint(1, 100)}"
                category = random.choice(categories)
                price = round(random.uniform(10.00, 999.99), 2)
                stock = random.randint(0, 100)
                
                self.cursor.execute("""
                    INSERT INTO products (name, category, price, stock_quantity)
                    VALUES (%s, %s, %s, %s)
                """, (name, category, price, stock))
                
            except Error as e:
                logger.warning(f"Помилка при додаванні продукту: {e}")
    
    def simulate_activity(self):
        """Симуляція активності: замовлення, оновлення, логи"""
        try:
            # Отримуємо ID користувачів та продуктів
            self.cursor.execute("SELECT id FROM users WHERE status = 'active' LIMIT 10")
            user_ids = [row[0] for row in self.cursor.fetchall()]
            
            self.cursor.execute("SELECT id, price FROM products WHERE stock_quantity > 0 LIMIT 20")
            products = [(row[0], row[1]) for row in self.cursor.fetchall()]
            
            if not user_ids or not products:
                logger.warning("Недостатньо даних для симуляції активності")
                return
            
            # Створюємо кілька замовлень
            for _ in range(random.randint(1, 5)):
                user_id = random.choice(user_ids)
                product_id, price = random.choice(products)
                quantity = random.randint(1, 3)
                total = float(price) * quantity
                status = random.choice(['pending', 'processing', 'completed'])
                
                self.cursor.execute("""
                    INSERT INTO orders (user_id, product_id, quantity, total_amount, status)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, product_id, quantity, total, status))
                
                # Зменшуємо кількість на складі
                self.cursor.execute("""
                    UPDATE products SET stock_quantity = GREATEST(0, stock_quantity - %s)
                    WHERE id = %s
                """, (quantity, product_id))
            
            # Додаємо логи активності
            actions = ['login', 'logout', 'view_product', 'add_to_cart', 'checkout', 'profile_update']
            ips = ['192.168.1.100', '10.0.0.50', '172.16.0.25', '192.168.0.200']
            
            for _ in range(random.randint(3, 10)):
                user_id = random.choice(user_ids)
                action = random.choice(actions)
                details = f"User performed {action}"
                ip = random.choice(ips)
                
                self.cursor.execute("""
                    INSERT INTO activity_logs (user_id, action, details, ip_address)
                    VALUES (%s, %s, %s, %s)
                """, (user_id, action, details, ip))
            
            # Оновлюємо last_login для кількох користувачів
            for _ in range(random.randint(1, 3)):
                user_id = random.choice(user_ids)
                self.cursor.execute("""
                    UPDATE users SET last_login = NOW() WHERE id = %s
                """, (user_id,))
            
            logger.info(f"Симуляція активності виконана: користувачі={len(user_ids)}, продукти={len(products)}")
            
        except Error as e:
            logger.error(f"Помилка при симуляції активності: {e}")
    
    def run_continuous_generation(self):
        """Безперервна генерація даних"""
        logger.info("Початок безперервної генерації даних...")
        
        # Початкова генерація даних
        self.generate_users(20)
        self.generate_products(100)
        
        # Цикл симуляції активності
        while True:
            try:
                self.simulate_activity()
                
                # Іноді додаємо нових користувачів та продукти
                if random.random() < 0.1:  # 10% шансу
                    self.generate_users(random.randint(1, 3))
                    
                if random.random() < 0.05:  # 5% шансу
                    self.generate_products(random.randint(1, 5))
                
                # Пауза між циклами
                time.sleep(random.randint(10, 30))
                
            except Exception as e:
                logger.error(f"Помилка в циклі генерації: {e}")
                time.sleep(60)  # Довша пауза при помилці
    
    def close_connection(self):
        """Закриття підключення"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logger.info("Підключення до MySQL закрито")

def main():
    generator = DataGenerator()
    
    try:
        generator.run_continuous_generation()
    except KeyboardInterrupt:
        logger.info("Отримано сигнал зупинки...")
    except Exception as e:
        logger.error(f"Критична помилка: {e}")
    finally:
        generator.close_connection()

if __name__ == "__main__":
    main()

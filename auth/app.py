import os
import sqlite3
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, session
from functools import wraps
import jwt

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))

# Конфігурація JWT
JWT_SECRET = os.getenv('JWT_SECRET', secrets.token_hex(32))
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

class AuthService:
    def __init__(self, db_path='/app/auth.db'):
        self.db_path = db_path
        self.init_database()
        
    def init_database(self):
        """Ініціалізація бази даних SQLite"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Таблиця користувачів
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            ''')
            
            # Таблиця сесій
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    token TEXT UNIQUE NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Таблиця логів авторизації
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS auth_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    action TEXT,
                    success BOOLEAN,
                    ip_address TEXT,
                    user_agent TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            
            # Створюємо адміністратора за замовчуванням
            self.create_default_admin()
            
            logger.info("База даних авторизації ініціалізована")
            
        except Exception as e:
            logger.error(f"Помилка ініціалізації БД: {e}")
    
    def create_default_admin(self):
        """Створення адміністратора за замовчуванням"""
        try:
            if not self.user_exists('admin'):
                self.register_user('admin', 'admin@system.com', 'admin123', 'admin')
                logger.info("Створено адміністратора за замовчуванням (admin/admin123)")
        except Exception as e:
            logger.error(f"Помилка створення адміністратора: {e}")
    
    def hash_password(self, password, salt=None):
        """Хешування паролю з сіллю"""
        if salt is None:
            salt = secrets.token_hex(32)
        
        password_hash = hashlib.pbkdf2_hmac('sha256', 
                                           password.encode('utf-8'), 
                                           salt.encode('utf-8'), 
                                           100000)
        return password_hash.hex(), salt
    
    def verify_password(self, password, password_hash, salt):
        """Перевірка паролю"""
        hash_to_check, _ = self.hash_password(password, salt)
        return hash_to_check == password_hash
    
    def user_exists(self, username):
        """Перевірка існування користувача"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()
        
        conn.close()
        return result is not None
    
    def register_user(self, username, email, password, role='user'):
        """Реєстрація нового користувача"""
        try:
            if self.user_exists(username):
                return False, "Користувач вже існує"
            
            password_hash, salt = self.hash_password(password)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, salt, role)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, email, password_hash, salt, role))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Користувач {username} зареєстрований успішно")
            return True, "Користувач зареєстрований успішно"
            
        except Exception as e:
            logger.error(f"Помилка реєстрації користувача: {e}")
            return False, str(e)
    
    def authenticate_user(self, username, password, ip_address=None, user_agent=None):
        """Аутентифікація користувача"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, password_hash, salt, role, is_active 
                FROM users WHERE username = ?
            ''', (username,))
            
            result = cursor.fetchone()
            
            if not result:
                self.log_auth_attempt(username, 'login', False, ip_address, user_agent)
                return False, None, "Невірний логін або пароль"
            
            user_id, password_hash, salt, role, is_active = result
            
            if not is_active:
                self.log_auth_attempt(username, 'login', False, ip_address, user_agent)
                return False, None, "Обліковий запис деактивований"
            
            if self.verify_password(password, password_hash, salt):
                # Оновлюємо час останнього входу
                cursor.execute('UPDATE users SET last_login = ? WHERE id = ?', 
                             (datetime.now(), user_id))
                conn.commit()
                
                self.log_auth_attempt(username, 'login', True, ip_address, user_agent)
                logger.info(f"Успішна аутентифікація користувача {username}")
                
                conn.close()
                return True, {'id': user_id, 'username': username, 'role': role}, None
            else:
                self.log_auth_attempt(username, 'login', False, ip_address, user_agent)
                conn.close()
                return False, None, "Невірний логін або пароль"
                
        except Exception as e:
            logger.error(f"Помилка аутентифікації: {e}")
            return False, None, str(e)
    
    def log_auth_attempt(self, username, action, success, ip_address, user_agent):
        """Логування спроб авторизації"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO auth_logs (username, action, success, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, action, success, ip_address, user_agent))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Помилка логування: {e}")
    
    def generate_jwt_token(self, user_data):
        """Генерація JWT токену"""
        payload = {
            'user_id': user_data['id'],
            'username': user_data['username'],
            'role': user_data['role'],
            'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
            'iat': datetime.utcnow()
        }
        
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return token
    
    def verify_jwt_token(self, token):
        """Перевірка JWT токену"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return True, payload
        except jwt.ExpiredSignatureError:
            return False, "Токен прострочений"
        except jwt.InvalidTokenError:
            return False, "Невірний токен"

# Глобальний екземпляр сервісу авторизації
auth_service = AuthService()

def token_required(f):
    """Декоратор для перевірки токену"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'Токен відсутній'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            
            valid, payload = auth_service.verify_jwt_token(token)
            
            if not valid:
                return jsonify({'error': payload}), 401
            
            request.current_user = payload
            
        except Exception as e:
            return jsonify({'error': 'Невірний токен'}), 401
        
        return f(*args, **kwargs)
    
    return decorated

def admin_required(f):
    """Декоратор для перевірки прав адміністратора"""
    @wraps(f)
    @token_required
    def decorated(*args, **kwargs):
        if request.current_user.get('role') != 'admin':
            return jsonify({'error': 'Потрібні права адміністратора'}), 403
        return f(*args, **kwargs)
    
    return decorated

@app.route('/register', methods=['POST'])
def register():
    """Реєстрація нового користувача"""
    try:
        data = request.get_json()
        
        if not data or not all(k in data for k in ('username', 'email', 'password')):
            return jsonify({'error': 'Потрібні поля: username, email, password'}), 400
        
        success, message = auth_service.register_user(
            data['username'], 
            data['email'], 
            data['password'],
            data.get('role', 'user')
        )
        
        if success:
            return jsonify({'message': message}), 201
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        logger.error(f"Помилка реєстрації: {e}")
        return jsonify({'error': 'Внутрішня помилка сервера'}), 500

@app.route('/login', methods=['POST'])
def login():
    """Вхід користувача"""
    try:
        data = request.get_json()
        
        if not data or not all(k in data for k in ('username', 'password')):
            return jsonify({'error': 'Потрібні поля: username, password'}), 400
        
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent')
        
        success, user_data, error = auth_service.authenticate_user(
            data['username'], 
            data['password'],
            ip_address,
            user_agent
        )
        
        if success:
            token = auth_service.generate_jwt_token(user_data)
            
            return jsonify({
                'message': 'Успішний вхід',
                'token': token,
                'user': {
                    'id': user_data['id'],
                    'username': user_data['username'],
                    'role': user_data['role']
                }
            })
        else:
            return jsonify({'error': error}), 401
            
    except Exception as e:
        logger.error(f"Помилка входу: {e}")
        return jsonify({'error': 'Внутрішня помилка сервера'}), 500

@app.route('/verify', methods=['GET'])
@token_required
def verify_token():
    """Перевірка токену"""
    return jsonify({
        'valid': True,
        'user': request.current_user
    })

@app.route('/profile', methods=['GET'])
@token_required
def get_profile():
    """Отримання профілю користувача"""
    return jsonify({
        'user': request.current_user
    })

@app.route('/admin/users', methods=['GET'])
@admin_required
def get_users():
    """Отримання списку користувачів (тільки для адміністраторів)"""
    try:
        conn = sqlite3.connect(auth_service.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, email, role, is_active, created_at, last_login
            FROM users ORDER BY created_at DESC
        ''')
        
        users = []
        for row in cursor.fetchall():
            users.append({
                'id': row[0],
                'username': row[1],
                'email': row[2],
                'role': row[3],
                'is_active': bool(row[4]),
                'created_at': row[5],
                'last_login': row[6]
            })
        
        conn.close()
        return jsonify({'users': users})
        
    except Exception as e:
        logger.error(f"Помилка отримання користувачів: {e}")
        return jsonify({'error': 'Внутрішня помилка сервера'}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'service': 'auth-service',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/', methods=['GET'])
def index():
    """Головна сторінка"""
    return jsonify({
        'service': 'Authentication Service',
        'version': '1.0.0',
        'endpoints': {
            'register': '/register (POST)',
            'login': '/login (POST)',
            'verify': '/verify (GET)',
            'profile': '/profile (GET)',
            'admin_users': '/admin/users (GET)',
            'health': '/health (GET)'
        }
    })

if __name__ == '__main__':
    logger.info("Запуск сервісу авторизації...")
    app.run(host='0.0.0.0', port=5000, debug=False)

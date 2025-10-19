import os
import sqlite3
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, redirect, session, render_template_string
from functools import wraps
import jwt
import requests
from werkzeug.security import generate_password_hash, check_password_hash

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))

JWT_SECRET = os.getenv('JWT_SECRET', secrets.token_hex(32))
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

GRAFANA_URL = os.getenv('GRAFANA_URL', 'http://localhost:3000')
PROMETHEUS_URL = os.getenv('PROMETHEUS_URL', 'http://localhost:9090')

class AuthDatabase:
    def __init__(self, db_path='auth.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Ініціалізація бази даних SQLite"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    session_token TEXT UNIQUE NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS auth_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    success BOOLEAN,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            conn.commit()
            conn.close()
            
            self.create_default_admin()
            
            logger.info("База даних авторизації ініціалізована")
            
        except Exception as e:
            logger.error(f"Помилка ініціалізації БД: {e}")
    
    def create_default_admin(self):
        """Створення адміністратора за замовчуванням"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM users WHERE username = 'admin'")
            if cursor.fetchone():
                conn.close()
                return
            
            admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
            password_hash = generate_password_hash(admin_password)
            
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, role, is_active)
                VALUES (?, ?, ?, ?, ?)
            ''', ('admin', 'admin@monitoring.local', password_hash, 'admin', 1))
            
            conn.commit()
            conn.close()
            
            logger.info("Створено адміністратора за замовчуванням: admin/admin123")
            
        except Exception as e:
            logger.error(f"Помилка створення адміністратора: {e}")
    
    def authenticate_user(self, username, password):
        """Автентифікація користувача"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, username, email, password_hash, role, is_active
                FROM users WHERE username = ? AND is_active = 1
            ''', (username,))
            
            user = cursor.fetchone()
            conn.close()
            
            if user and check_password_hash(user[3], password):
                self.update_last_login(user[0])
                return {
                    'id': user[0],
                    'username': user[1],
                    'email': user[2],
                    'role': user[4]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Помилка автентифікації: {e}")
            return None
    
    def update_last_login(self, user_id):
        """Оновлення часу останнього входу"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
            ''', (user_id,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Помилка оновлення часу входу: {e}")
    
    def log_auth_action(self, user_id, action, ip_address, user_agent, success):
        """Логування дій авторизації"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO auth_logs (user_id, action, ip_address, user_agent, success)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, action, ip_address, user_agent, success))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Помилка логування: {e}")

auth_db = AuthDatabase()

def generate_jwt_token(user_data):
    """Генерація JWT токена"""
    payload = {
        'user_id': user_data['id'],
        'username': user_data['username'],
        'role': user_data['role'],
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token):
    """Перевірка JWT токена"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def require_auth(f):
    """Декоратор для захисту маршрутів"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Токен авторизації відсутній'}), 401
        
        if token.startswith('Bearer '):
            token = token[7:]
        
        payload = verify_jwt_token(token)
        if not payload:
            return jsonify({'error': 'Недійсний токен'}), 401
        
        request.user = payload
        return f(*args, **kwargs)
    
    return decorated_function

def require_admin(f):
    """Декоратор для захисту адміністративних маршрутів"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(request, 'user') or request.user.get('role') != 'admin':
            return jsonify({'error': 'Недостатньо прав доступу'}), 403
        return f(*args, **kwargs)
    
    return decorated_function

LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Авторизація - Система моніторингу</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }
        .container { max-width: 400px; margin: 100px auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #333; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; color: #555; }
        input[type="text"], input[type="password"] { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        button:hover { background: #0056b3; }
        .error { color: #dc3545; margin-top: 10px; }
        .info { background: #e7f3ff; padding: 15px; border-radius: 4px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔐 Авторизація</h1>
        <div class="info">
            <strong>Тестові облікові записи:</strong><br>
            Адміністратор: <code>admin</code> / <code>admin123</code><br>
            Користувач: <code>user</code> / <code>user123</code>
        </div>
        <form method="POST">
            <div class="form-group">
                <label for="username">Ім'я користувача:</label>
                <input type="text" id="username" name="username" required>
            </div>
            <div class="form-group">
                <label for="password">Пароль:</label>
                <input type="password" id="password" name="password" required>
            </div>
            <button type="submit">Увійти</button>
        </form>
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
    </div>
</body>
</html>
'''

DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Панель управління - Система моніторингу</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .services { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .service-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .service-card h3 { margin-top: 0; color: #333; }
        .btn { display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; margin: 5px 5px 5px 0; }
        .btn:hover { background: #0056b3; }
        .btn-success { background: #28a745; }
        .btn-success:hover { background: #1e7e34; }
        .logout { float: right; }
        .user-info { color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Панель управління системою моніторингу</h1>
            <div class="user-info">
                Привіт, <strong>{{ user.username }}</strong>! 
                <span class="logout">
                    <a href="/logout" class="btn">Вийти</a>
                </span>
            </div>
        </div>
        
        <div class="services">
            <div class="service-card">
                <h3>📈 Grafana</h3>
                <p>Візуалізація метрик та дашборди</p>
                <p><small>Логін: admin/admin123</small></p>
                <a href="/proxy/grafana" class="btn btn-success" target="_blank">Відкрити Grafana</a>
                <a href="http://localhost:3000" class="btn" target="_blank">Прямий доступ</a>
            </div>
            
            <div class="service-card">
                <h3>🔍 Prometheus</h3>
                <p>Збір та зберігання метрик</p>
                <a href="/proxy/prometheus" class="btn btn-success" target="_blank">Відкрити Prometheus</a>
                <a href="http://localhost:9090" class="btn" target="_blank">Прямий доступ</a>
            </div>
            
            <div class="service-card">
                <h3>📊 Метрики</h3>
                <p>Прямий доступ до метрик</p>
                <a href="/proxy/metrics" class="btn" target="_blank">Переглянути метрики</a>
                <a href="http://localhost:8000/metrics" class="btn" target="_blank">Прямий доступ</a>
            </div>
        </div>
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    """Головна сторінка - перенаправлення на логін або панель"""
    if 'user' in session:
        return render_template_string(DASHBOARD_TEMPLATE, user=session['user'])
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Сторінка авторизації"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return render_template_string(LOGIN_TEMPLATE, error='Введіть ім\'я користувача та пароль')
        
        user = auth_db.authenticate_user(username, password)
        
        if user:
            auth_db.log_auth_action(
                user['id'], 'login', 
                request.remote_addr, 
                request.headers.get('User-Agent', ''), 
                True
            )
            
            session['user'] = user
            session['token'] = generate_jwt_token(user)
            
            logger.info(f"Успішний вхід користувача: {username}")
            return redirect('/')
        else:
            auth_db.log_auth_action(
                None, 'login_failed', 
                request.remote_addr, 
                request.headers.get('User-Agent', ''), 
                False
            )
            
            logger.warning(f"Невдала спроба входу: {username}")
            return render_template_string(LOGIN_TEMPLATE, error='Невірне ім\'я користувача або пароль')
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    """Вихід з системи"""
    if 'user' in session:
        auth_db.log_auth_action(
            session['user']['id'], 'logout', 
            request.remote_addr, 
            request.headers.get('User-Agent', ''), 
            True
        )
        logger.info(f"Вихід користувача: {session['user']['username']}")
    
    session.clear()
    return redirect('/login')

@app.route('/api/auth', methods=['POST'])
def api_auth():
    """API для авторизації"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Введіть ім\'я користувача та пароль'}), 400
    
    user = auth_db.authenticate_user(username, password)
    
    if user:
        token = generate_jwt_token(user)
        auth_db.log_auth_action(
            user['id'], 'api_login', 
            request.remote_addr, 
            request.headers.get('User-Agent', ''), 
            True
        )
        
        return jsonify({
            'success': True,
            'token': token,
            'user': user
        })
    else:
        auth_db.log_auth_action(
            None, 'api_login_failed', 
            request.remote_addr, 
            request.headers.get('User-Agent', ''), 
            False
        )
        
        return jsonify({'error': 'Невірні облікові дані'}), 401

@app.route('/api/verify', methods=['GET'])
@require_auth
def api_verify():
    """API для перевірки токена"""
    return jsonify({
        'valid': True,
        'user': request.user
    })

@app.route('/proxy/grafana')
def proxy_grafana():
    """Проксі для Grafana"""
    if 'user' not in session:
        return redirect('/login')
    
    return redirect(GRAFANA_URL)

@app.route('/proxy/prometheus')
def proxy_prometheus():
    """Проксі для Prometheus"""
    if 'user' not in session:
        return redirect('/login')
    
    return redirect(PROMETHEUS_URL)

@app.route('/proxy/metrics')
def proxy_metrics():
    """Проксі для метрик"""
    if 'user' not in session:
        return redirect('/login')
    
    try:
        response = requests.get('http://metrics_exporter:8000/metrics', timeout=10)
        return response.text, 200, {'Content-Type': 'text/plain'}
    except Exception as e:
        logger.error(f"Помилка отримання метрик: {e}")
        return "Помилка отримання метрик", 500

@app.route('/api/users', methods=['GET'])
@require_auth
@require_admin
def api_users():
    """API для отримання списку користувачів (тільки для адміністраторів)"""
    try:
        conn = sqlite3.connect(auth_db.db_path)
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
        return jsonify({'error': 'Помилка сервера'}), 500

@app.route('/api/logs', methods=['GET'])
@require_auth
@require_admin
def api_logs():
    """API для отримання логів авторизації (тільки для адміністраторів)"""
    try:
        conn = sqlite3.connect(auth_db.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT al.action, al.ip_address, al.success, al.timestamp, u.username
            FROM auth_logs al
            LEFT JOIN users u ON al.user_id = u.id
            ORDER BY al.timestamp DESC
            LIMIT 100
        ''')
        
        logs = []
        for row in cursor.fetchall():
            logs.append({
                'action': row[0],
                'ip_address': row[1],
                'success': bool(row[2]),
                'timestamp': row[3],
                'username': row[4] or 'Unknown'
            })
        
        conn.close()
        return jsonify({'logs': logs})
        
    except Exception as e:
        logger.error(f"Помилка отримання логів: {e}")
        return jsonify({'error': 'Помилка сервера'}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'auth_server',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    try:
        conn = sqlite3.connect(auth_db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE username = 'user'")
        if not cursor.fetchone():
            password_hash = generate_password_hash('user123')
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, role, is_active)
                VALUES (?, ?, ?, ?, ?)
            ''', ('user', 'user@monitoring.local', password_hash, 'user', 1))
            
            conn.commit()
            logger.info("Створено тестового користувача: user/user123")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Помилка створення тестового користувача: {e}")
    
    logger.info("Сервер авторизації запущено")
    app.run(host='0.0.0.0', port=5000, debug=False)

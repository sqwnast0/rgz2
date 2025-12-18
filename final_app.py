from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import random
import string

# Создание приложения
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key-123-final'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///final_warehouse.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Модели
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CartItem(db.Model):
    __tablename__ = 'cart_items'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True)
    user_id = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Float, default=0)
    is_paid = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Вспомогательные функции
def generate_order_number():
    return f'ORD-{datetime.now().strftime("%Y%m%d")}-{"".join(random.choices(string.digits, k=6))}'

# Инициализация базы данных
def init_database():
    with app.app_context():
        db.create_all()
        
        if not User.query.filter_by(username='admin').first():
            # Создаем пользователей
            admin = User(username='admin', is_active=True)
            admin.set_password('admin123')
            db.session.add(admin)
            
            warehouse = User(username='warehouse', is_active=True)
            warehouse.set_password('warehouse123')
            db.session.add(warehouse)
            
            # Создаем тестовые товары (бытовая техника)
            products_data = [
                {'sku': 'FR001', 'name': 'Холодильник Samsung RB33J3000SA', 'quantity': 15, 'price': 34999},
                {'sku': 'WM001', 'name': 'Стиральная машина LG F2V5HS0W', 'quantity': 20, 'price': 32999},
                {'sku': 'TV001', 'name': 'Телевизор Sony KD-55X75WL', 'quantity': 8, 'price': 64999},
                {'sku': 'AC001', 'name': 'Кондиционер Ballu BSWI-09HN1', 'quantity': 12, 'price': 28999},
                {'sku': 'VC001', 'name': 'Пылесос Samsung VCC4520S36', 'quantity': 25, 'price': 12999},
                {'sku': 'KT001', 'name': 'Микроволновка Samsung MS23K3515AW', 'quantity': 18, 'price': 8999},
                {'sku': 'WH001', 'name': 'Водонагреватель Ariston 80L', 'quantity': 10, 'price': 15999},
                {'sku': 'ST001', 'name': 'Варочная панель Bosch PKE645B17E', 'quantity': 7, 'price': 23999},
                {'sku': 'OV001', 'name': 'Духовой шкаф Electrolux EOB 53434', 'quantity': 5, 'price': 31999},
                {'sku': 'KT002', 'name': 'Электрочайник Bosch TWK 3A013', 'quantity': 30, 'price': 3499},
            ]
            
            for data in products_data:
                product = Product(**data)
                db.session.add(product)
            
            db.session.commit()
            print("✅ База данных создана с тестовыми данными")
            print("👤 Пользователи: admin/admin123, warehouse/warehouse123")
        else:
            print("✅ База данных уже существует")

# Маршруты
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(username=username, is_active=True).first()
        if user and user.check_password(password):
            login_user(user)
            flash(f'Добро пожаловать, {username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Неверный логин или пароль', 'error')
    
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Вход в систему</title>
        <style>
            body { font-family: Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .login-box { background: white; padding: 40px; border-radius: 15px; box-shadow: 0 20px 40px rgba(0,0,0,0.1); width: 100%; max-width: 400px; }
            h1 { text-align: center; color: #333; margin-bottom: 30px; font-size: 28px; }
            input { width: 100%; padding: 12px 15px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 16px; margin: 10px 0; box-sizing: border-box; }
            input:focus { outline: none; border-color: #667eea; }
            button { width: 100%; padding: 12px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; margin-top: 10px; }
            button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4); }
            .alert { padding: 12px; border-radius: 8px; margin-bottom: 20px; font-size: 14px; }
            .alert-error { background: #fee; color: #c33; border: 1px solid #fcc; }
            .alert-success { background: #efe; color: #3a3; border: 1px solid #cfc; }
            .user-list { margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px; text-align: center; }
        </style>
    </head>
    <body>
        <div class="login-box">
            <h1>Склад бытовой техники</h1>
            
            <div id="flash-messages">
                <!-- Сообщения будут здесь -->
            </div>
            
            <form method="POST" id="login-form">
                <input type="text" name="username" placeholder="Логин" required>
                <input type="password" name="password" placeholder="Пароль" required>
                <button type="submit">Войти в систему</button>
            </form>
            
            <div class="user-list">
                <p><strong>Тестовые пользователи:</strong></p>
                <p>👑 admin / admin123</p>
                <p>👷 warehouse / warehouse123</p>
            </div>
        </div>
        
        <script>
            // Показываем flash сообщения
            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.has('error')) {
                const errorDiv = document.createElement('div');
                errorDiv.className = 'alert alert-error';
                errorDiv.textContent = 'Неверный логин или пароль';
                document.getElementById('flash-messages').appendChild(errorDiv);
            }
        </script>
    </body>
    </html>
    '''

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Статистика
    total_products = Product.query.count()
    total_quantity = sum(p.quantity for p in Product.query.all())
    total_orders = Order.query.filter_by(user_id=current_user.id).count()
    
    # Товары
    products = Product.query.order_by(Product.created_at.desc()).limit(10).all()
    
    # Товары с низким запасом
    low_stock = [p for p in Product.query.all() if p.quantity <= 5]
    
    # Заказы
    recent_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).limit(5).all()
    
    # Корзина
    cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Панель управления</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f7fa; color: #333; }}
            .dashboard-container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
            
            /* Навигация */
            .navbar {{ background: white; border-radius: 10px; padding: 15px 25px; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: flex; justify-content: space-between; align-items: center; }}
            .nav-brand h2 {{ color: #2c3e50; margin-bottom: 5px; }}
            .nav-brand p {{ color: #7f8c8d; font-size: 14px; }}
            .nav-links {{ display: flex; gap: 15px; flex-wrap: wrap; }}
            .nav-link {{ color: #3498db; text-decoration: none; padding: 8px 16px; border-radius: 6px; transition: all 0.3s; font-weight: 500; }}
            .nav-link:hover {{ background: #f8f9fa; color: #2980b9; }}
            .nav-link.active {{ background: #3498db; color: white; }}
            
            /* Статистика */
            .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }}
            .stat-card {{ background: white; border-radius: 10px; padding: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; transition: transform 0.3s; }}
            .stat-card:hover {{ transform: translateY(-5px); box-shadow: 0 6px 12px rgba(0,0,0,0.15); }}
            .stat-value {{ font-size: 36px; font-weight: bold; color: #3498db; margin: 10px 0; }}
            .stat-label {{ color: #7f8c8d; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; }}
            
            /* Секции */
            .section {{ background: white; border-radius: 10px; padding: 25px; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .section-title {{ color: #2c3e50; margin-bottom: 20px; font-size: 20px; font-weight: 600; display: flex; align-items: center; gap: 10px; }}
            .section-title::before {{ content: "📦"; font-size: 24px; }}
            
            /* Таблицы */
            .table-container {{ overflow-x: auto; margin-top: 15px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }}
            th {{ background: #f8f9fa; font-weight: 600; color: #555; }}
            tr:hover {{ background: #f9f9f9; }}
            
            /* Кнопки */
            .btn {{ padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.3s; }}
            .btn-primary {{ background: #3498db; color: white; }}
            .btn-primary:hover {{ background: #2980b9; }}
            .btn-success {{ background: #2ecc71; color: white; }}
            .btn-success:hover {{ background: #27ae60; }}
            .btn-danger {{ background: #e74c3c; color: white; }}
            .btn-danger:hover {{ background: #c0392b; }}
            .btn-sm {{ padding: 5px 10px; font-size: 12px; }}
            
            /* Состояния товаров */
            .quantity-low {{ color: #e74c3c; font-weight: bold; background: #ffeaea; padding: 3px 8px; border-radius: 4px; }}
            .quantity-ok {{ color: #27ae60; font-weight: bold; }}
            
            /* Заказы */
            .order-status {{ display: inline-block; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
            .status-paid {{ background: #d4edda; color: #155724; }}
            .status-unpaid {{ background: #f8d7da; color: #721c24; }}
            
            /* Адаптивность */
            @media (max-width: 768px) {{
                .navbar {{ flex-direction: column; gap: 15px; }}
                .nav-links {{ justify-content: center; }}
                .stats-grid {{ grid-template-columns: 1fr; }}
            }}
        </style>
    </head>
    <body>
        <div class="dashboard-container">
            <!-- Навигация -->
            <nav class="navbar">
                <div class="nav-brand">
                    <h2>📦 Склад бытовой техники</h2>
                    <p>Добро пожаловать, {current_user.username}!</p>
                </div>
                <div class="nav-links">
                    <a href="/dashboard" class="nav-link active">Главная</a>
                    <a href="/products" class="nav-link">Товары</a>
                    <a href="/cart" class="nav-link">Корзина ({cart_count})</a>
                    <a href="/orders" class="nav-link">Заказы ({total_orders})</a>
                    <a href="/logout" class="nav-link">Выйти</a>
                </div>
            </nav>
            
            <!-- Статистика -->
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">Всего товаров</div>
                    <div class="stat-value">{total_products}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Общее количество</div>
                    <div class="stat-value">{total_quantity}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Мои заказы</div>
                    <div class="stat-value">{total_orders}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Товаров в корзине</div>
                    <div class="stat-value">{cart_count}</div>
                </div>
            </div>
            
            <!-- Последние товары -->
            <div class="section">
                <h3 class="section-title">Последние товары на складе</h3>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Артикул</th>
                                <th>Название</th>
                                <th>Количество</th>
                                <th>Цена</th>
                                <th>Действия</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join(f'''
                            <tr>
                                <td>{p.sku}</td>
                                <td>{p.name}</td>
                                <td><span class="{'quantity-low' if p.quantity <= 5 else 'quantity-ok'}">{p.quantity} шт.</span></td>
                                <td>{p.price:.2f} ₽</td>
                                <td>
                                    <button class="btn btn-primary btn-sm" onclick="addToCart({p.id})">
                                        В корзину
                                    </button>
                                </td>
                            </tr>
                            ''' for p in products)}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <!-- Товары с низким запасом -->
            {f'''
            <div class="section">
                <h3 class="section-title" style="color: #e74c3c;">⚠️ Товары с низким запасом</h3>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Артикул</th>
                                <th>Название</th>
                                <th>Остаток</th>
                                <th>Действия</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join(f'''
                            <tr>
                                <td>{p.sku}</td>
                                <td>{p.name}</td>
                                <td class="quantity-low">{p.quantity} шт.</td>
                                <td>
                                    <button class="btn btn-danger btn-sm" onclick="addToCart({p.id})">
                                        Заказать
                                    </button>
                                </td>
                            </tr>
                            ''' for p in low_stock)}
                        </tbody>
                    </table>
                </div>
            </div>
            ''' if low_stock else ''}
            
            <!-- Последние заказы -->
            {f'''
            <div class="section">
                <h3 class="section-title">📋 Последние заказы</h3>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Номер заказа</th>
                                <th>Дата</th>
                                <th>Сумма</th>
                                <th>Статус</th>
                                <th>Действия</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join(f'''
                            <tr>
                                <td>{order.order_number}</td>
                                <td>{order.created_at.strftime('%d.%m.%Y')}</td>
                                <td>{order.total:.2f} ₽</td>
                                <td>
                                    <span class="order-status {'status-paid' if order.is_paid else 'status-unpaid'}">
                                        {'Оплачен' if order.is_paid else 'Не оплачен'}
                                    </span>
                                </td>
                                <td>
                                    {f'''
                                    <button class="btn btn-success btn-sm" onclick="markOrderPaid({order.id})">
                                        Отметить оплату
                                    </button>
                                    ''' if not order.is_paid else ''}
                                </td>
                            </tr>
                            ''' for order in recent_orders)}
                        </tbody>
                    </table>
                </div>
            </div>
            ''' if recent_orders else ''}
        </div>
        
        <script>
            // Функция добавления в корзину
            async function addToCart(productId) {{
                try {{
                    const response = await fetch('/api/add_to_cart', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{product_id: productId}})
                    }});
                    
                    const result = await response.json();
                    if (result.success) {{
                        alert('✅ ' + result.message);
                        setTimeout(() => location.reload(), 1000);
                    }} else {{
                        alert('❌ ' + result.error);
                    }}
                }} catch (error) {{
                    alert('❌ Ошибка сети: ' + error.message);
                }}
            }}
            
            // Функция отметки оплаты заказа
            async function markOrderPaid(orderId) {{
                if (!confirm('Отметить заказ как оплаченный?')) return;
                
                try {{
                    const response = await fetch('/api/mark_order_paid', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{order_id: orderId}})
                    }});
                    
                    const result = await response.json();
                    if (result.success) {{
                        alert('✅ ' + result.message);
                        location.reload();
                    }} else {{
                        alert('❌ ' + result.error);
                    }}
                }} catch (error) {{
                    alert('❌ Ошибка сети: ' + error.message);
                }}
            }}
            
            // Автоматическое обновление каждые 30 секунд
            setTimeout(() => {{
                console.log('Автообновление данных...');
                location.reload();
            }}, 30000);
        </script>
    </body>
    </html>
    '''

@app.route('/products')
@login_required
def products():
    all_products = Product.query.order_by(Product.name).all()
    cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Каталог товаров</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f7fa; }}
            .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
            
            .navbar {{ background: white; border-radius: 10px; padding: 15px 25px; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: flex; justify-content: space-between; align-items: center; }}
            .nav-links {{ display: flex; gap: 15px; }}
            .nav-link {{ color: #3498db; text-decoration: none; padding: 8px 16px; border-radius: 6px; }}
            .nav-link:hover {{ background: #f8f9fa; }}
            
            .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }}
            .search-box {{ display: flex; gap: 10px; }}
            .search-input {{ padding: 10px 15px; border: 2px solid #e0e0e0; border-radius: 8px; width: 300px; }}
            .search-btn {{ background: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; }}
            
            .products-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 25px; }}
            .product-card {{ background: white; border-radius: 10px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: transform 0.3s; }}
            .product-card:hover {{ transform: translateY(-5px); box-shadow: 0 6px 12px rgba(0,0,0,0.15); }}
            .product-sku {{ color: #7f8c8d; font-size: 14px; margin-bottom: 5px; }}
            .product-name {{ font-size: 18px; font-weight: 600; color: #2c3e50; margin-bottom: 15px; }}
            .product-price {{ font-size: 24px; font-weight: bold; color: #3498db; margin: 15px 0; }}
            .product-quantity {{ display: inline-block; padding: 5px 10px; border-radius: 4px; font-size: 14px; }}
            .quantity-low {{ background: #ffeaea; color: #e74c3c; }}
            .quantity-ok {{ background: #e8f6ef; color: #27ae60; }}
            .product-actions {{ display: flex; gap: 10px; margin-top: 20px; }}
            .btn {{ padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; }}
            .btn-primary {{ background: #3498db; color: white; flex: 1; }}
            .btn-primary:hover {{ background: #2980b9; }}
            
            @media (max-width: 768px) {{
                .navbar {{ flex-direction: column; gap: 15px; }}
                .search-box {{ flex-direction: column; }}
                .search-input {{ width: 100%; }}
                .products-grid {{ grid-template-columns: 1fr; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Навигация -->
            <nav class="navbar">
                <div>
                    <h2>🛍️ Каталог товаров</h2>
                </div>
                <div class="nav-links">
                    <a href="/dashboard" class="nav-link">Главная</a>
                    <a href="/products" class="nav-link">Товары</a>
                    <a href="/cart" class="nav-link">Корзина ({cart_count})</a>
                    <a href="/orders" class="nav-link">Заказы</a>
                    <a href="/logout" class="nav-link">Выйти</a>
                </div>
            </nav>
            
            <!-- Поиск -->
            <div class="header">
                <h1>Бытовая техника ({len(all_products)} товаров)</h1>
                <div class="search-box">
                    <input type="text" class="search-input" placeholder="Поиск товаров..." id="search-input">
                    <button class="search-btn" onclick="searchProducts()">Найти</button>
                </div>
            </div>
            
            <!-- Сетка товаров -->
            <div class="products-grid">
                {"".join(f'''
                <div class="product-card">
                    <div class="product-sku">Артикул: {p.sku}</div>
                    <div class="product-name">{p.name}</div>
                    <div class="product-price">{p.price:.2f} ₽</div>
                    <div class="product-quantity {'quantity-low' if p.quantity <= 5 else 'quantity-ok'}">
                        {p.quantity} шт. в наличии
                    </div>
                    <div class="product-actions">
                        <button class="btn btn-primary" onclick="addToCart({p.id})">
                            Добавить в корзину
                        </button>
                    </div>
                </div>
                ''' for p in all_products)}
            </div>
        </div>
        
        <script>
            // Функция поиска
            function searchProducts() {{
                const searchTerm = document.getElementById('search-input').value.toLowerCase();
                const cards = document.querySelectorAll('.product-card');
                
                cards.forEach(card => {{
                    const name = card.querySelector('.product-name').textContent.toLowerCase();
                    const sku = card.querySelector('.product-sku').textContent.toLowerCase();
                    
                    if (name.includes(searchTerm) || sku.includes(searchTerm)) {{
                        card.style.display = 'block';
                    }} else {{
                        card.style.display = 'none';
                    }}
                }});
            }}
            
            // Функция добавления в корзину
            async function addToCart(productId) {{
                try {{
                    const response = await fetch('/api/add_to_cart', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{product_id: productId}})
                    }});
                    
                    const result = await response.json();
                    if (result.success) {{
                        alert('✅ ' + result.message);
                    }} else {{
                        alert('❌ ' + result.error);
                    }}
                }} catch (error) {{
                    alert('❌ Ошибка сети: ' + error.message);
                }}
            }}
            
            // Поиск при нажатии Enter
            document.getElementById('search-input').addEventListener('keypress', function(e) {{
                if (e.key === 'Enter') {{
                    searchProducts();
                }}
            }});
        </script>
    </body>
    </html>
    '''

@app.route('/cart')
@login_required
def cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    items_with_details = []
    total = 0
    
    for item in cart_items:
        product = Product.query.get(item.product_id)
        if product:
            item_total = product.price * item.quantity
            items_with_details.append({
                'product': product,
                'quantity': item.quantity,
                'total': item_total
            })
            total += item_total
    
    cart_count = len(items_with_details)
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Корзина</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f7fa; }}
            .container {{ max-width: 1000px; margin: 0 auto; padding: 20px; }}
            
            .navbar {{ background: white; border-radius: 10px; padding: 15px 25px; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: flex; justify-content: space-between; align-items: center; }}
            .nav-links {{ display: flex; gap: 15px; }}
            .nav-link {{ color: #3498db; text-decoration: none; padding: 8px 16px; border-radius: 6px; }}
            .nav-link:hover {{ background: #f8f9fa; }}
            
            .cart-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }}
            
            .cart-items {{ display: flex; flex-direction: column; gap: 15px; }}
            .cart-item {{ background: white; border-radius: 10px; padding: 20px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .cart-item-info {{ flex: 1; }}
            .cart-item-name {{ font-size: 18px; font-weight: 600; color: #2c3e50; }}
            .cart-item-details {{ color: #7f8c8d; margin-top: 5px; }}
            .cart-item-price {{ font-size: 20px; font-weight: bold; color: #3498db; }}
            .cart-item-quantity {{ display: flex; align-items: center; gap: 10px; }}
            .quantity-btn {{ width: 30px; height: 30px; border-radius: 50%; border: 2px solid #3498db; background: white; color: #3498db; font-size: 18px; cursor: pointer; }}
            .quantity-btn:hover {{ background: #3498db; color: white; }}
            
            .cart-total {{ background: white; border-radius: 10px; padding: 25px; margin-top: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .total-row {{ display: flex; justify-content: space-between; margin-bottom: 15px; font-size: 18px; }}
            .total-amount {{ font-size: 28px; font-weight: bold; color: #2c3e50; }}
            
            .cart-actions {{ display: flex; gap: 15px; margin-top: 25px; }}
            .btn {{ padding: 12px 30px; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: 600; }}
            .btn-primary {{ background: #3498db; color: white; }}
            .btn-primary:hover {{ background: #2980b9; }}
            .btn-success {{ background: #2ecc71; color: white; }}
            .btn-success:hover {{ background: #27ae60; }}
            .btn-danger {{ background: #e74c3c; color: white; }}
            .btn-danger:hover {{ background: #c0392b; }}
            
            .empty-cart {{ text-align: center; padding: 60px 20px; }}
            .empty-icon {{ font-size: 64px; margin-bottom: 20px; }}
            .empty-title {{ font-size: 24px; color: #7f8c8d; margin-bottom: 10px; }}
            
            @media (max-width: 768px) {{
                .cart-item {{ flex-direction: column; align-items: flex-start; gap: 15px; }}
                .cart-actions {{ flex-direction: column; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Навигация -->
            <nav class="navbar">
                <div>
                    <h2>🛒 Корзина покупок</h2>
                </div>
                <div class="nav-links">
                    <a href="/dashboard" class="nav-link">Главная</a>
                    <a href="/products" class="nav-link">Товары</a>
                    <a href="/cart" class="nav-link">Корзина ({cart_count})</a>
                    <a href="/orders" class="nav-link">Заказы</a>
                    <a href="/logout" class="nav-link">Выйти</a>
                </div>
            </nav>
            
            {"".join(f'''
            <!-- Заполненная корзина -->
            <div class="cart-header">
                <h1>Ваша корзина ({cart_count} товаров)</h1>
                <button class="btn btn-danger" onclick="clearCart()">Очистить корзину</button>
            </div>
            
            <div class="cart-items">
                {"".join(f'''
                <div class="cart-item" id="cart-item-{item['product'].id}">
                    <div class="cart-item-info">
                        <div class="cart-item-name">{item['product'].name}</div>
                        <div class="cart-item-details">
                            Артикул: {item['product'].sku} | Цена: {item['product'].price:.2f} ₽
                        </div>
                    </div>
                    
                    <div class="cart-item-quantity">
                        <button class="quantity-btn" onclick="updateQuantity({item['product'].id}, {item['quantity'] - 1})">-</button>
                        <span style="font-size: 18px; font-weight: bold;">{item['quantity']} шт.</span>
                        <button class="quantity-btn" onclick="updateQuantity({item['product'].id}, {item['quantity'] + 1})">+</button>
                    </div>
                    
                    <div class="cart-item-price">{item['total']:.2f} ₽</div>
                    
                    <button class="btn btn-danger" onclick="removeFromCart({item['product'].id})">Удалить</button>
                </div>
                ''' for item in items_with_details)}
            </div>
            
            <!-- Итого -->
            <div class="cart-total">
                <div class="total-row">
                    <span>Сумма:</span>
                    <span>{total:.2f} ₽</span>
                </div>
                <div class="total-row" style="border-top: 2px solid #eee; padding-top: 15px;">
                    <span class="total-amount">Итого:</span>
                    <span class="total-amount">{total:.2f} ₽</span>
                </div>
                
                <div class="cart-actions">
                    <button class="btn btn-primary" onclick="window.location.href='/products'">
                        ← Продолжить покупки
                    </button>
                    <button class="btn btn-success" onclick="createOrder()">
                        Оформить заказ →
                    </button>
                </div>
            </div>
            ''') if items_with_details else f'''
            <!-- Пустая корзина -->
            <div class="empty-cart">
                <div class="empty-icon">🛒</div>
                <div class="empty-title">Ваша корзина пуста</div>
                <p style="color: #95a5a6; margin-bottom: 30px;">Добавьте товары из каталога</p>
                <button class="btn btn-primary" onclick="window.location.href='/products'">
                    Перейти к товарам
                </button>
            </div>
            '''}
        </div>
        
        <script>
            // Обновление количества товара
            async function updateQuantity(productId, newQuantity) {{
                if (newQuantity < 1) {{
                    removeFromCart(productId);
                    return;
                }}
                
                try {{
                    // Сначала удаляем, потом добавляем с новым количеством
                    await removeFromCart(productId);
                    
                    const response = await fetch('/api/add_to_cart', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{product_id: productId, quantity: newQuantity}})
                    }});
                    
                    const result = await response.json();
                    if (result.success) {{
                        location.reload();
                    }} else {{
                        alert('❌ ' + result.error);
                    }}
                }} catch (error) {{
                    alert('❌ Ошибка сети: ' + error.message);
                }}
            }}
            
            // Удаление товара из корзины
            async function removeFromCart(productId) {{
                try {{
                    const response = await fetch('/api/remove_from_cart', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{product_id: productId}})
                    }});
                    
                    const result = await response.json();
                    if (!result.success) {{
                        console.error('Ошибка удаления:', result.error);
                    }}
                }} catch (error) {{
                    console.error('Ошибка сети:', error);
                }}
            }}
            
            // Очистка корзины
            async function clearCart() {{
                if (!confirm('Очистить всю корзину?')) return;
                
                {"".join(f'''
                await removeFromCart({item['product'].id});
                ''' for item in items_with_details) if items_with_details else ''}
                
                alert('✅ Корзина очищена');
                location.reload();
            }}
            
            // Создание заказа
            async function createOrder() {{
                if (!confirm('Оформить заказ?')) return;
                
                try {{
                    const response = await fetch('/api/create_order', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}}
                    }});
                    
                    const result = await response.json();
                    if (result.success) {{
                        alert('✅ ' + result.message);
                        window.location.href = '/orders';
                    }} else {{
                        alert('❌ ' + result.error);
                    }}
                }} catch (error) {{
                    alert('❌ Ошибка сети: ' + error.message);
                }}
            }}
        </script>
    </body>
    </html>
    '''

@app.route('/orders')
@login_required
def orders():
    orders_list = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Мои заказы</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f7fa; }}
            .container {{ max-width: 1000px; margin: 0 auto; padding: 20px; }}
            
            .navbar {{ background: white; border-radius: 10px; padding: 15px 25px; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: flex; justify-content: space-between; align-items: center; }}
            .nav-links {{ display: flex; gap: 15px; }}
            .nav-link {{ color: #3498db; text-decoration: none; padding: 8px 16px; border-radius: 6px; }}
            .nav-link:hover {{ background: #f8f9fa; }}
            
            .orders-list {{ display: flex; flex-direction: column; gap: 20px; }}
            .order-card {{ background: white; border-radius: 10px; padding: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .order-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }}
            .order-number {{ font-size: 20px; font-weight: bold; color: #2c3e50; }}
            .order-date {{ color: #7f8c8d; }}
            .order-status {{ display: inline-block; padding: 6px 15px; border-radius: 20px; font-size: 14px; font-weight: bold; }}
            .status-paid {{ background: #d4edda; color: #155724; }}
            .status-unpaid {{ background: #f8d7da; color: #721c24; }}
            .order-total {{ font-size: 24px; font-weight: bold; color: #3498db; text-align: right; margin-top: 15px; }}
            .order-actions {{ margin-top: 20px; display: flex; gap: 10px; }}
            
            .btn {{ padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; }}
            .btn-success {{ background: #2ecc71; color: white; }}
            .btn-success:hover {{ background: #27ae60; }}
            
            .empty-orders {{ text-align: center; padding: 60px 20px; }}
            .empty-icon {{ font-size: 64px; margin-bottom: 20px; }}
            .empty-title {{ font-size: 24px; color: #7f8c8d; margin-bottom: 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Навигация -->
            <nav class="navbar">
                <div>
                    <h2>📋 Мои заказы</h2>
                </div>
                <div class="nav-links">
                    <a href="/dashboard" class="nav-link">Главная</a>
                    <a href="/products" class="nav-link">Товары</a>
                    <a href="/cart" class="nav-link">Корзина ({cart_count})</a>
                    <a href="/orders" class="nav-link">Заказы</a>
                    <a href="/logout" class="nav-link">Выйти</a>
                </div>
            </nav>
            
            {"".join(f'''
            <!-- Список заказов -->
            <div class="orders-list">
                {"".join(f'''
                <div class="order-card">
                    <div class="order-header">
                        <div>
                            <div class="order-number">{order.order_number}</div>
                            <div class="order-date">{order.created_at.strftime('%d.%m.%Y %H:%M')}</div>
                        </div>
                        <span class="order-status {'status-paid' if order.is_paid else 'status-unpaid'}">
                            {'✅ Оплачен' if order.is_paid else '❌ Не оплачен'}
                        </span>
                    </div>
                    
                    <div class="order-total">{order.total:.2f} ₽</div>
                    
                    {f'''
                    <div class="order-actions">
                        <button class="btn btn-success" onclick="markAsPaid({order.id})">
                            Отметить как оплаченный
                        </button>
                    </div>
                    ''' if not order.is_paid else ''}
                </div>
                ''' for order in orders_list)}
            </div>
            ''') if orders_list else f'''
            <!-- Нет заказов -->
            <div class="empty-orders">
                <div class="empty-icon">📭</div>
                <div class="empty-title">Заказов пока нет</div>
                <p style="color: #95a5a6; margin-bottom: 30px;">Создайте первый заказ из корзины</p>
                <button class="btn btn-success" onclick="window.location.href='/cart'">
                    Перейти в корзину
                </button>
            </div>
            '''}
        </div>
        
        <script>
            // Отметка заказа как оплаченного
            async function markAsPaid(orderId) {{
                if (!confirm('Отметить заказ как оплаченный?')) return;
                
                try {{
                    const response = await fetch('/api/mark_order_paid', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{order_id: orderId}})
                    }});
                    
                    const result = await response.json();
                    if (result.success) {{
                        alert('✅ ' + result.message);
                        location.reload();
                    }} else {{
                        alert('❌ ' + result.error);
                    }}
                }} catch (error) {{
                    alert('❌ Ошибка сети: ' + error.message);
                }}
            }}
        </script>
    </body>
    </html>
    '''

# API маршруты
@app.route('/api/add_to_cart', methods=['POST'])
@login_required
def api_add_to_cart():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Нет данных'})
        
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)
        
        if not product_id:
            return jsonify({'success': False, 'error': 'Не указан ID товара'})
        
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'success': False, 'error': 'Товар не найден'})
        
        if product.quantity < quantity:
            return jsonify({'success': False, 'error': f'Недостаточно товара. В наличии: {product.quantity}'})
        
        # Проверяем, есть ли товар уже в корзине
        cart_item = CartItem.query.filter_by(
            user_id=current_user.id,
            product_id=product_id
        ).first()
        
        if cart_item:
            new_quantity = cart_item.quantity + quantity
            if product.quantity < new_quantity:
                return jsonify({'success': False, 'error': f'Недостаточно товара. В наличии: {product.quantity}'})
            cart_item.quantity = new_quantity
        else:
            cart_item = CartItem(
                user_id=current_user.id,
                product_id=product_id,
                quantity=quantity
            )
            db.session.add(cart_item)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Товар "{product.name}" добавлен в корзину',
            'cart_count': CartItem.query.filter_by(user_id=current_user.id).count()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/remove_from_cart', methods=['POST'])
@login_required
def api_remove_from_cart():
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        
        if not product_id:
            return jsonify({'success': False, 'error': 'Не указан ID товара'})
        
        cart_item = CartItem.query.filter_by(
            user_id=current_user.id,
            product_id=product_id
        ).first()
        
        if cart_item:
            db.session.delete(cart_item)
            db.session.commit()
            return jsonify({'success': True})
        
        return jsonify({'success': True, 'message': 'Товар не найден в корзине'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/create_order', methods=['POST'])
@login_required
def api_create_order():
    try:
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        
        if not cart_items:
            return jsonify({'success': False, 'error': 'Корзина пуста'})
        
        # Проверяем наличие товаров
        for item in cart_items:
            product = Product.query.get(item.product_id)
            if not product:
                return jsonify({'success': False, 'error': f'Товар не найден (ID: {item.product_id})'})
            
            if product.quantity < item.quantity:
                return jsonify({
                    'success': False, 
                    'error': f'Недостаточно товара "{product.name}". В наличии: {product.quantity}, требуется: {item.quantity}'
                })
        
        # Создаем заказ
        order_number = generate_order_number()
        order = Order(
            order_number=order_number,
            user_id=current_user.id,
            total=0,
            is_paid=False
        )
        db.session.add(order)
        
        total = 0
        
        # Уменьшаем количество товаров и считаем сумму
        for item in cart_items:
            product = Product.query.get(item.product_id)
            product.quantity -= item.quantity
            total += product.price * item.quantity
        
        order.total = total
        
        # Очищаем корзину
        CartItem.query.filter_by(user_id=current_user.id).delete()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Заказ {order_number} успешно создан',
            'order_number': order_number,
            'total': total
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/mark_order_paid', methods=['POST'])
@login_required
def api_mark_order_paid():
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        
        if not order_id:
            return jsonify({'success': False, 'error': 'Не указан ID заказа'})
        
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'success': False, 'error': 'Заказ не найден'})
        
        if order.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Доступ запрещен'})
        
        if order.is_paid:
            return jsonify({'success': False, 'error': 'Заказ уже оплачен'})
        
        order.is_paid = True
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Заказ {order.order_number} отмечен как оплаченный'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/health', methods=['GET'])
def api_health():
    return jsonify({
        'status': 'ok',
        'service': 'Warehouse Management System',
        'version': '2.0',
        'authenticated': current_user.is_authenticated,
        'user': current_user.username if current_user.is_authenticated else None
    })

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 СИСТЕМА УПРАВЛЕНИЯ СКЛАДОМ БЫТОВОЙ ТЕХНИКИ")
    print("=" * 60)
    
    # Инициализация базы данных
    init_database()
    
    print("\n✅ Система готова к работе!")
    print("🌐 Доступно по адресу: http://127.0.0.1:5000")
    print("👤 Тестовые пользователи:")
    print("   - admin / admin123 (администратор)")
    print("   - warehouse / warehouse123 (кладовщик)")
    print("=" * 60)
    print("\n🔄 Запуск сервера...\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
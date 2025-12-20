from flask import Flask, request, jsonify, redirect, url_for, flash, send_from_directory, send_file
from config import Config
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import random
import string
from PIL import Image, ImageDraw
import io

basedir = os.path.abspath(os.path.dirname(__file__))

# Создание приложения
app = Flask(__name__, static_folder='static')
app.config.from_object(Config)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(basedir, "warehouse.db")


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
            # Создаем пользователи
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

# Функция для генерации HTML head с иконками
def get_head(title):
    return f'''
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🏭 {title} - Склад бытовой техники</title>

        <!-- Favicon (иконка для вкладки) -->
        <link rel="shortcut icon" href="/static/favicon/favicon.png" type="image/png">
        <link rel="icon" href="/static/favicon/favicon.png" type="image/png">

        <!-- Font Awesome иконки -->
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

        <!-- Google Fonts -->
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">

        <style>
            :root {{
                --primary-color: #3498db;
                --secondary-color: #2c3e50;
                --success-color: #2ecc71;
                --danger-color: #e74c3c;
                --warning-color: #f39c12;
                --light-bg: #f5f7fa;
                --card-shadow: 0 4px 6px rgba(0,0,0,0.1);
                --hover-shadow: 0 6px 12px rgba(0,0,0,0.15);
            }}

            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: 'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: var(--light-bg);
                color: #333;
                line-height: 1.6;
            }}

            .dashboard-container {{
                max-width: 1400px;
                margin: 0 auto;
                padding: 20px;
            }}

            /* Навигация */
            .navbar {{
                background: white;
                border-radius: 12px;
                padding: 15px 25px;
                margin-bottom: 25px;
                box-shadow: var(--card-shadow);
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-left: 5px solid var(--primary-color);
            }}

            .nav-brand h2 {{
                color: var(--secondary-color);
                margin-bottom: 5px;
                display: flex;
                align-items: center;
                gap: 10px;
            }}

            .nav-brand p {{
                color: #7f8c8d;
                font-size: 14px;
                display: flex;
                align-items: center;
                gap: 8px;
            }}

            .nav-links {{
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
            }}

            .nav-link {{
                color: var(--primary-color);
                text-decoration: none;
                padding: 8px 16px;
                border-radius: 8px;
                transition: all 0.3s;
                font-weight: 500;
                display: flex;
                align-items: center;
                gap: 8px;
                border: 1px solid transparent;
            }}

            .nav-link:hover {{
                background: #f8f9fa;
                color: #2980b9;
                border-color: #e0e0e0;
            }}

            .nav-link.active {{
                background: var(--primary-color);
                color: white;
            }}

            .nav-link i {{
                font-size: 16px;
            }}

            /* Футер с информацией о студенте */
            .student-footer {{
                text-align: center;
                margin-top: 30px;
                padding: 20px;
                color: #7f8c8d;
                font-size: 14px;
                border-top: 1px solid #eee;
            }}

            .student-info {{
                background: white;
                padding: 15px;
                border-radius: 8px;
                display: inline-block;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                border-left: 4px solid var(--primary-color);
            }}

            /* Статистика */
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}

            .stat-card {{
                background: white;
                border-radius: 12px;
                padding: 25px;
                box-shadow: var(--card-shadow);
                text-align: center;
                transition: transform 0.3s, box-shadow 0.3s;
                border-top: 4px solid var(--primary-color);
            }}

            .stat-card:hover {{
                transform: translateY(-5px);
                box-shadow: var(--hover-shadow);
            }}

            .stat-icon {{
                font-size: 32px;
                color: var(--primary-color);
                margin-bottom: 15px;
            }}

            .stat-value {{
                font-size: 36px;
                font-weight: bold;
                color: var(--primary-color);
                margin: 10px 0;
            }}

            .stat-label {{
                color: #7f8c8d;
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}

            /* Секции */
            .section {{
                background: white;
                border-radius: 12px;
                padding: 25px;
                margin-bottom: 25px;
                box-shadow: var(--card-shadow);
            }}

            .section-title {{
                color: var(--secondary-color);
                margin-bottom: 20px;
                font-size: 20px;
                font-weight: 600;
                display: flex;
                align-items: center;
                gap: 10px;
                padding-bottom: 10px;
                border-bottom: 2px solid #f0f0f0;
            }}

            .section-title i {{
                color: var(--primary-color);
                font-size: 20px;
            }}

            /* Таблицы */
            .table-container {{
                overflow-x: auto;
                margin-top: 15px;
                border-radius: 8px;
                border: 1px solid #eee;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
            }}

            th, td {{
                padding: 12px 15px;
                text-align: left;
                border-bottom: 1px solid #eee;
            }}

            th {{
                background: #f8f9fa;
                font-weight: 600;
                color: #555;
                position: sticky;
                top: 0;
            }}

            tr:hover {{
                background: #f9f9f9;
            }}

            /* Кнопки */
            .btn {{
                padding: 8px 16px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 500;
                transition: all 0.3s;
                display: inline-flex;
                align-items: center;
                gap: 8px;
            }}

            .btn-primary {{
                background: var(--primary-color);
                color: white;
            }}

            .btn-primary:hover {{
                background: #2980b9;
                transform: translateY(-2px);
            }}

            .btn-success {{
                background: var(--success-color);
                color: white;
            }}

            .btn-success:hover {{
                background: #27ae60;
                transform: translateY(-2px);
            }}

            .btn-danger {{
                background: var(--danger-color);
                color: white;
            }}

            .btn-danger:hover {{
                background: #c0392b;
                transform: translateY(-2px);
            }}

            .btn-warning {{
                background: var(--warning-color);
                color: white;
            }}

            .btn-warning:hover {{
                background: #e67e22;
                transform: translateY(-2px);
            }}

            .btn-sm {{
                padding: 5px 10px;
                font-size: 12px;
            }}

            /* Состояния товаров */
            .quantity-low {{
                color: var(--danger-color);
                font-weight: bold;
                background: #ffeaea;
                padding: 4px 10px;
                border-radius: 6px;
                display: inline-flex;
                align-items: center;
                gap: 5px;
            }}

            .quantity-ok {{
                color: var(--success-color);
                font-weight: bold;
                background: #e8f6ef;
                padding: 4px 10px;
                border-radius: 6px;
                display: inline-flex;
                align-items: center;
                gap: 5px;
            }}

            /* Заказы */
            .order-status {{
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 5px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
            }}

            .status-paid {{
                background: #d4edda;
                color: #155724;
            }}

            .status-unpaid {{
                background: #f8d7da;
                color: #721c24;
            }}

            /* Анимации */
            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(20px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}

            .fade-in {{
                animation: fadeIn 0.5s ease-out;
            }}

            /* Адаптивность */
            @media (max-width: 768px) {{
                .navbar {{
                    flex-direction: column;
                    gap: 15px;
                }}

                .nav-links {{
                    justify-content: center;
                    width: 100%;
                }}

                .stats-grid {{
                    grid-template-columns: 1fr;
                }}

                .table-container {{
                    font-size: 14px;
                }}

                th, td {{
                    padding: 8px 10px;
                }}
            }}

            /* Уведомления */
            .alert {{
                padding: 15px;
                border-radius: 8px;
                margin: 15px 0;
                display: flex;
                align-items: center;
                gap: 10px;
                animation: fadeIn 0.3s ease-out;
            }}

            .alert-success {{
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }}

            .alert-error {{
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }}

            .alert-warning {{
                background: #fff3cd;
                color: #856404;
                border: 1px solid #ffeaa7;
            }}

            /* Карточки товаров */
            .product-card {{
                background: white;
                border-radius: 12px;
                padding: 20px;
                box-shadow: var(--card-shadow);
                transition: all 0.3s;
                border: 1px solid transparent;
            }}

            .product-card:hover {{
                transform: translateY(-5px);
                box-shadow: var(--hover-shadow);
                border-color: var(--primary-color);
            }}
        </style>
    </head>
    '''

# Маршрут для favicon.ico
@app.route('/favicon.ico')
def favicon():
    favicon_path = os.path.join(app.root_path, 'static', 'favicon', 'favicon.ico')
    if os.path.exists(favicon_path):
        return send_from_directory(os.path.join(app.root_path, 'static', 'favicon'), 'favicon.ico')
    else:
        # Возвращаем дефолтную иконку если файла нет
        return '', 204

# Маршрут для favicon.png
@app.route('/static/favicon/favicon.png')
def favicon_png():
    png_path = os.path.join(app.root_path, 'static', 'favicon', 'favicon.png')
    if os.path.exists(png_path):
        return send_from_directory(os.path.join(app.root_path, 'static', 'favicon'), 'favicon.png')
    else:
        # Создаем простую иконку на лету
        img = Image.new('RGB', (64, 64), color='#3498db')
        draw = ImageDraw.Draw(img)

        # Рисуем склад/дом
        draw.rectangle([15, 20, 49, 45], fill='#2c3e50', outline='white')  # Здание
        draw.rectangle([25, 25, 39, 35], fill='#ffffff')  # Дверь
        draw.polygon([15, 20, 32, 10, 49, 20], fill='#e74c3c')  # Крыша
        draw.rectangle([40, 10, 44, 15], fill='#f1c40f')  # Фонарь

        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)

        return send_file(img_io, mimetype='image/png')

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

    return f'''
    <!DOCTYPE html>
    <html>
    {get_head('Вход в систему')}
    <body>
        <div class="dashboard-container">
            <div class="section" style="max-width: 400px; margin: 50px auto;">
                <div style="text-align: center; margin-bottom: 30px;">
                    <div style="font-size: 48px; color: #3498db; margin-bottom: 10px;">
                        <i class="fas fa-warehouse"></i>
                    </div>
                    <h1 style="color: #2c3e50;">Склад бытовой техники</h1>
                    <p style="color: #7f8c8d; margin-top: 5px;">Система управления запасами</p>
                </div>

                <div id="flash-messages">
                    <!-- Сообщения будут здесь -->
                </div>

                <form method="POST" id="login-form">
                    <div style="margin-bottom: 20px;">
                        <label style="display: block; margin-bottom: 8px; color: #555; font-weight: 500;">
                            <i class="fas fa-user"></i> Логин
                        </label>
                        <input type="text" name="username"
                               style="width: 100%; padding: 12px 15px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 16px;"
                               placeholder="Введите логин" required>
                    </div>

                    <div style="margin-bottom: 25px;">
                        <label style="display: block; margin-bottom: 8px; color: #555; font-weight: 500;">
                            <i class="fas fa-lock"></i> Пароль
                        </label>
                        <input type="password" name="password"
                               style="width: 100%; padding: 12px 15px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 16px;"
                               placeholder="Введите пароль" required>
                    </div>

                    <button type="submit"
                            style="width: 100%; padding: 14px; background: linear-gradient(135deg, #3498db 0%, #2c3e50 100%);
                                   color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer;
                                   display: flex; align-items: center; justify-content: center; gap: 10px;">
                        <i class="fas fa-sign-in-alt"></i> Войти в систему
                    </button>
                </form>

                <div class="section" style="margin-top: 25px; text-align: center; background: #f8f9fa;">
                    <h3 style="margin-bottom: 15px; color: #555;">
                        <i class="fas fa-users"></i> Тестовые пользователи
                    </h3>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div style="text-align: left; padding: 12px; background: white; border-radius: 8px;">
                            <div style="font-weight: bold; color: #3498db;">
                                <i class="fas fa-crown"></i> Администратор
                            </div>
                            <div style="margin-top: 5px;">
                                <strong>Логин:</strong> admin<br>
                                <strong>Пароль:</strong> admin123
                            </div>
                        </div>
                        <div style="text-align: left; padding: 12px; background: white; border-radius: 8px;">
                            <div style="font-weight: bold; color: #3498db;">
                                <i class="fas fa-user-tie"></i> Кладовщик
                            </div>
                            <div style="margin-top: 5px;">
                                <strong>Логин:</strong> warehouse<br>
                                <strong>Пароль:</strong> warehouse123
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Футер с информацией о студенте -->
            <div class="student-footer">
                <div class="student-info">
                    <i class="fas fa-user-graduate"></i> Чикирисова Анастасия Вячеславовна ФБИ-33
                </div>
            </div>
        </div>

        <script>
            // Показываем flash сообщения
            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.has('error')) {{
                const errorDiv = document.createElement('div');
                errorDiv.className = 'alert alert-error';
                errorDiv.innerHTML = '<i class="fas fa-exclamation-circle"></i> Неверный логин или пароль';
                document.getElementById('flash-messages').appendChild(errorDiv);
            }}

            // Анимация появления
            document.addEventListener('DOMContentLoaded', function() {{
                const form = document.querySelector('.section');
                form.style.opacity = '0';
                form.style.transform = 'translateY(20px)';

                setTimeout(() => {{
                    form.style.transition = 'all 0.5s ease-out';
                    form.style.opacity = '1';
                    form.style.transform = 'translateY(0)';
                }}, 100);
            }});
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

    # Генерация HTML для таблицы товаров
    products_html = ""
    for p in products:
        quantity_class = "quantity-low" if p.quantity <= 5 else "quantity-ok"
        icon_class = "fa-exclamation-triangle" if p.quantity <= 5 else "fa-check-circle"

        products_html += f'''
        <tr>
            <td><strong>{p.sku}</strong></td>
            <td>{p.name}</td>
            <td>
                <span class="{quantity_class}">
                    <i class="fas {icon_class}"></i>
                    {p.quantity} шт.
                </span>
            </td>
            <td><strong>{p.price:.2f} ₽</strong></td>
            <td>
                <button class="btn btn-primary btn-sm" onclick="addToCart({p.id})">
                    <i class="fas fa-cart-plus"></i> В корзину
                </button>
            </td>
        </tr>
        '''

    # Генерация HTML для товаров с низким запасом
    low_stock_html = ""
    if low_stock:
        low_stock_rows = ""
        for p in low_stock:
            low_stock_rows += f'''
            <tr>
                <td><strong>{p.sku}</strong></td>
                <td>{p.name}</td>
                <td class="quantity-low">
                    <i class="fas fa-exclamation-triangle"></i> {p.quantity} шт.
                </td>
                <td>
                    <button class="btn btn-danger btn-sm" onclick="addToCart({p.id})">
                        <i class="fas fa-shopping-cart"></i> Заказать
                    </button>
                </td>
            </tr>
            '''

        low_stock_html = f'''
        <div class="section">
            <h3 class="section-title" style="color: #e74c3c;">
                <i class="fas fa-exclamation-triangle"></i> Товары с низким запасом
            </h3>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th><i class="fas fa-barcode"></i> Артикул</th>
                            <th><i class="fas fa-tag"></i> Название</th>
                            <th><i class="fas fa-boxes"></i> Остаток</th>
                            <th><i class="fas fa-cogs"></i> Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        {low_stock_rows}
                    </tbody>
                </table>
            </div>
        </div>
        '''

    # Генерация HTML для последних заказов
    orders_html = ""
    if recent_orders:
        orders_rows = ""
        for order in recent_orders:
            status_class = "status-paid" if order.is_paid else "status-unpaid"
            status_icon = "fa-check-circle" if order.is_paid else "fa-times-circle"
            status_text = "Оплачен" if order.is_paid else "Не оплачен"

            action_button = ""
            if not order.is_paid:
                action_button = f'''
                <button class="btn btn-success btn-sm" onclick="markOrderPaid({order.id})">
                    <i class="fas fa-check"></i> Отметить оплату
                </button>
                '''

            orders_rows += f'''
            <tr>
                <td><strong>{order.order_number}</strong></td>
                <td>{order.created_at.strftime('%d.%m.%Y')}</td>
                <td><strong>{order.total:.2f} ₽</strong></td>
                <td>
                    <span class="order-status {status_class}">
                        <i class="fas {status_icon}"></i>
                        {status_text}
                    </span>
                </td>
                <td>
                    {action_button}
                </td>
            </tr>
            '''

        orders_html = f'''
        <div class="section">
            <h3 class="section-title">
                <i class="fas fa-receipt"></i> Последние заказы
            </h3>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th><i class="fas fa-hashtag"></i> Номер заказа</th>
                            <th><i class="fas fa-calendar"></i> Дата</th>
                            <th><i class="fas fa-money-bill-wave"></i> Сумма</th>
                            <th><i class="fas fa-info-circle"></i> Статус</th>
                            <th><i class="fas fa-cogs"></i> Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        {orders_rows}
                    </tbody>
                </table>
            </div>
        </div>
        '''

    return f'''
    <!DOCTYPE html>
    <html>
    {get_head('Панель управления')}
    <body>
        <div class="dashboard-container fade-in">
            <!-- Навигация -->
            <nav class="navbar">
                <div class="nav-brand">
                    <h2><i class="fas fa-warehouse"></i> Склад бытовой техники</h2>
                    <p><i class="fas fa-user"></i> Добро пожаловать, {current_user.username}!</p>
                </div>
                <div class="nav-links">
                    <a href="/dashboard" class="nav-link active">
                        <i class="fas fa-tachometer-alt"></i> Главная
                    </a>
                    <a href="/products" class="nav-link">
                        <i class="fas fa-boxes"></i> Товары
                    </a>
                    <a href="/cart" class="nav-link">
                        <i class="fas fa-shopping-cart"></i> Корзина
                        {f'<span style="background: #e74c3c; color: white; padding: 2px 6px; border-radius: 10px; font-size: 12px;">{cart_count}</span>' if cart_count > 0 else ''}
                    </a>
                    <a href="/orders" class="nav-link">
                        <i class="fas fa-receipt"></i> Заказы
                        {f'<span style="background: #3498db; color: white; padding: 2px 6px; border-radius: 10px; font-size: 12px;">{total_orders}</span>' if total_orders > 0 else ''}
                    </a>
                    <a href="/logout" class="nav-link" style="color: #e74c3c;">
                        <i class="fas fa-sign-out-alt"></i> Выйти
                    </a>
                </div>
            </nav>

            <!-- Статистика -->
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon"><i class="fas fa-box"></i></div>
                    <div class="stat-label">Всего товаров</div>
                    <div class="stat-value">{total_products}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon"><i class="fas fa-layer-group"></i></div>
                    <div class="stat-label">Общее количество</div>
                    <div class="stat-value">{total_quantity}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon"><i class="fas fa-clipboard-list"></i></div>
                    <div class="stat-label">Мои заказы</div>
                    <div class="stat-value">{total_orders}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon"><i class="fas fa-shopping-cart"></i></div>
                    <div class="stat-label">Товаров в корзине</div>
                    <div class="stat-value">{cart_count}</div>
                </div>
            </div>

            <!-- Последние товары -->
            <div class="section">
                <h3 class="section-title">
                    <i class="fas fa-history"></i> Последние товары на складе
                </h3>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th><i class="fas fa-barcode"></i> Артикул</th>
                                <th><i class="fas fa-tag"></i> Название</th>
                                <th><i class="fas fa-boxes"></i> Количество</th>
                                <th><i class="fas fa-money-bill-wave"></i> Цена</th>
                                <th><i class="fas fa-cogs"></i> Действия</th>
                            </tr>
                        </thead>
                        <tbody>
                            {products_html}
                        </tbody>
                    </table>
                </div>
            </div>

            {low_stock_html}

            {orders_html}

            <!-- Быстрые действия -->
            <div class="section">
                <h3 class="section-title">
                    <i class="fas fa-bolt"></i> Быстрые действия
                </h3>
                <div style="display: flex; gap: 15px; flex-wrap: wrap;">
                    <button class="btn btn-primary" onclick="window.location.href='/products'">
                        <i class="fas fa-search"></i> Просмотреть все товары
                    </button>
                    <button class="btn btn-success" onclick="window.location.href='/cart'">
                        <i class="fas fa-shopping-cart"></i> Перейти в корзину
                    </button>
                    <button class="btn btn-warning" onclick="window.print()">
                        <i class="fas fa-print"></i> Распечатать отчет
                    </button>
                </div>
            </div>

            <!-- Футер с информацией о студенте -->
            <div class="student-footer">
                <div class="student-info">
                    <i class="fas fa-user-graduate"></i> Чикирисова Анастасия Вячеславовна ФБИ-33
                </div>
            </div>
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
                        showAlert('success', '✅ ' + result.message);
                        setTimeout(() => location.reload(), 1000);
                    }} else {{
                        showAlert('error', '❌ ' + result.error);
                    }}
                }} catch (error) {{
                    showAlert('error', '❌ Ошибка сети: ' + error.message);
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
                        showAlert('success', '✅ ' + result.message);
                        setTimeout(() => location.reload(), 1500);
                    }} else {{
                        showAlert('error', '❌ ' + result.error);
                    }}
                }} catch (error) {{
                    showAlert('error', '❌ Ошибка сети: ' + error.message);
                }}
            }}

            // Показать уведомление
            function showAlert(type, message) {{
                const alertDiv = document.createElement('div');
                alertDiv.className = `alert alert-${{type}}`;
                alertDiv.innerHTML = message;
                alertDiv.style.position = 'fixed';
                alertDiv.style.top = '20px';
                alertDiv.style.right = '20px';
                alertDiv.style.zIndex = '1000';
                alertDiv.style.minWidth = '300px';
                alertDiv.style.maxWidth = '500px';

                document.body.appendChild(alertDiv);

                setTimeout(() => {{
                    alertDiv.remove();
                }}, 3000);
            }}

            // Автоматическое обновление каждые 30 секунд
            setTimeout(() => {{
                console.log('🔄 Автообновление данных...');
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
    total_orders = Order.query.filter_by(user_id=current_user.id).count()

    # Генерация HTML для карточек товаров
    product_cards = ""
    for p in all_products:
        quantity_class = "quantity-low" if p.quantity <= 5 else "quantity-ok"
        quantity_icon = "fa-exclamation-triangle" if p.quantity <= 5 else "fa-box"

        product_cards += f'''
        <div class="product-card" onclick="addToCart({p.id})" style="cursor: pointer;">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 15px;">
                <div>
                    <div style="font-size: 14px; color: #7f8c8d; margin-bottom: 5px;">
                        <i class="fas fa-barcode"></i> {p.sku}
                    </div>
                    <div style="font-size: 18px; font-weight: 600; color: #2c3e50; margin-bottom: 10px;">
                        {p.name}
                    </div>
                </div>
                <div class="{quantity_class}" style="font-size: 14px;">
                    <i class="fas {quantity_icon}"></i> {p.quantity} шт.
                </div>
            </div>

            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 20px; padding-top: 15px; border-top: 1px solid #eee;">
                <div style="font-size: 24px; font-weight: bold; color: #3498db;">
                    {p.price:.2f} ₽
                </div>
                <div>
                    <button class="btn btn-primary" onclick="event.stopPropagation(); addToCart({p.id})">
                        <i class="fas fa-cart-plus"></i> Добавить
                    </button>
                </div>
            </div>
        </div>
        '''

    return f'''
    <!DOCTYPE html>
    <html>
    {get_head('Каталог товаров')}
    <body>
        <div class="dashboard-container fade-in">
            <!-- Навигация -->
            <nav class="navbar">
                <div class="nav-brand">
                    <h2><i class="fas fa-boxes"></i> Каталог товаров</h2>
                    <p><i class="fas fa-user"></i> {current_user.username} | <i class="fas fa-box"></i> {len(all_products)} товаров</p>
                </div>
                <div class="nav-links">
                    <a href="/dashboard" class="nav-link">
                        <i class="fas fa-tachometer-alt"></i> Главная
                    </a>
                    <a href="/products" class="nav-link active">
                        <i class="fas fa-boxes"></i> Товары
                    </a>
                    <a href="/cart" class="nav-link">
                        <i class="fas fa-shopping-cart"></i> Корзина
                        {f'<span style="background: #e74c3c; color: white; padding: 2px 6px; border-radius: 10px; font-size: 12px;">{cart_count}</span>' if cart_count > 0 else ''}
                    </a>
                    <a href="/orders" class="nav-link">
                        <i class="fas fa-receipt"></i> Заказы
                        {f'<span style="background: #3498db; color: white; padding: 2px 6px; border-radius: 10px; font-size: 12px;">{total_orders}</span>' if total_orders > 0 else ''}
                    </a>
                    <a href="/logout" class="nav-link" style="color: #e74c3c;">
                        <i class="fas fa-sign-out-alt"></i> Выйти
                    </a>
                </div>
            </nav>

            <!-- Поиск и фильтры -->
            <div class="section">
                <h3 class="section-title">
                    <i class="fas fa-search"></i> Поиск товаров
                </h3>
                <div style="display: flex; gap: 15px; align-items: center; flex-wrap: wrap;">
                    <div style="flex: 1; min-width: 300px;">
                        <div style="position: relative;">
                            <input type="text" id="search-input"
                                   style="width: 100%; padding: 12px 15px 12px 45px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 16px;"
                                   placeholder="Поиск по названию или артикулу...">
                            <i class="fas fa-search" style="position: absolute; left: 15px; top: 50%; transform: translateY(-50%); color: #7f8c8d;"></i>
                        </div>
                    </div>
                    <button class="btn btn-primary" onclick="searchProducts()">
                        <i class="fas fa-search"></i> Найти
                    </button>
                    <button class="btn btn-success" onclick="showLowStock()">
                        <i class="fas fa-exclamation-triangle"></i> Низкий запас
                    </button>
                    <button class="btn btn-warning" onclick="resetSearch()">
                        <i class="fas fa-redo"></i> Сбросить
                    </button>
                </div>
            </div>

            <!-- Сетка товаров -->
            <div class="section">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h3 class="section-title" style="margin: 0;">
                        <i class="fas fa-list"></i> Все товары ({len(all_products)})
                    </h3>
                    <div style="color: #7f8c8d; font-size: 14px;">
                        <i class="fas fa-info-circle"></i> Нажмите на товар для добавления в корзину
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px;">
                    {product_cards}
                </div>
            </div>

            <!-- Футер с информацией о студенте -->
            <div class="student-footer">
                <div class="student-info">
                    <i class="fas fa-user-graduate"></i> Чикирисова Анастасия Вячеславовна ФБИ-33
                </div>
            </div>
        </div>

        <script>
            // Функция поиска
            function searchProducts() {{
                const searchTerm = document.getElementById('search-input').value.toLowerCase().trim();
                const cards = document.querySelectorAll('.product-card');

                if (!searchTerm) {{
                    cards.forEach(card => card.style.display = 'block');
                    return;
                }}

                cards.forEach(card => {{
                    const name = card.querySelector('div:nth-child(1) > div:nth-child(2)').textContent.toLowerCase();
                    const sku = card.querySelector('div:nth-child(1) > div:nth-child(1)').textContent.toLowerCase();

                    if (name.includes(searchTerm) || sku.includes(searchTerm)) {{
                        card.style.display = 'block';
                    }} else {{
                        card.style.display = 'none';
                    }}
                }});
            }}

            // Показать только товары с низким запасом
            function showLowStock() {{
                const cards = document.querySelectorAll('.product-card');
                cards.forEach(card => {{
                    const quantityClass = card.querySelector('div:nth-child(1) > div:nth-child(2)').className;
                    if (quantityClass.includes('quantity-low')) {{
                        card.style.display = 'block';
                    }} else {{
                        card.style.display = 'none';
                    }}
                }});
            }}

            // Сбросить поиск
            function resetSearch() {{
                document.getElementById('search-input').value = '';
                const cards = document.querySelectorAll('.product-card');
                cards.forEach(card => card.style.display = 'block');
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
                        showAlert('success', '✅ ' + result.message);
                    }} else {{
                        showAlert('error', '❌ ' + result.error);
                    }}
                }} catch (error) {{
                    showAlert('error', '❌ Ошибка сети: ' + error.message);
                }}
            }}

            // Поиск при нажатии Enter
            document.getElementById('search-input').addEventListener('keypress', function(e) {{
                if (e.key === 'Enter') {{
                    searchProducts();
                }}
            }});

            // Показать уведомление
            function showAlert(type, message) {{
                const alertDiv = document.createElement('div');
                alertDiv.className = `alert alert-${{type}}`;
                alertDiv.innerHTML = message;
                alertDiv.style.position = 'fixed';
                alertDiv.style.top = '20px';
                alertDiv.style.right = '20px';
                alertDiv.style.zIndex = '1000';
                alertDiv.style.minWidth = '300px';
                alertDiv.style.maxWidth = '500px';

                document.body.appendChild(alertDiv);

                setTimeout(() => {{
                    alertDiv.remove();
                }}, 3000);
            }}
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
    total_orders = Order.query.filter_by(user_id=current_user.id).count()

    # Генерация HTML для корзины
    cart_content = ""
    if items_with_details:
        # Генерация строк корзины
        cart_rows = ""
        for item in items_with_details:
            cart_rows += f'''
            <div class="product-card" id="cart-item-{item['product'].id}">
                <div style="display: flex; justify-content: space-between; align-items: center; gap: 20px;">
                    <div style="flex: 1;">
                        <div style="font-size: 14px; color: #7f8c8d; margin-bottom: 5px;">
                            <i class="fas fa-barcode"></i> {item['product'].sku}
                        </div>
                        <div style="font-size: 18px; font-weight: 600; color: #2c3e50; margin-bottom: 10px;">
                            {item['product'].name}
                        </div>
                        <div style="color: #7f8c8d;">
                            <i class="fas fa-money-bill-wave"></i> Цена: {item['product'].price:.2f} ₽
                        </div>
                    </div>

                    <div style="display: flex; align-items: center; gap: 15px;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <button class="btn btn-warning btn-sm" onclick="updateQuantity({item['product'].id}, {item['quantity'] - 1})">
                                <i class="fas fa-minus"></i>
                            </button>
                            <div style="font-size: 18px; font-weight: bold; min-width: 40px; text-align: center;">
                                {item['quantity']}
                            </div>
                            <button class="btn btn-success btn-sm" onclick="updateQuantity({item['product'].id}, {item['quantity'] + 1})">
                                <i class="fas fa-plus"></i>
                            </button>
                        </div>

                        <div style="font-size: 20px; font-weight: bold; color: #3498db; min-width: 120px; text-align: right;">
                            {item['total']:.2f} ₽
                        </div>

                        <button class="btn btn-danger" onclick="removeFromCart({item['product'].id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
            '''

        cart_content = f'''
        <!-- Заполненная корзина -->
        <div class="section">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h3 class="section-title" style="margin: 0;">
                    <i class="fas fa-shopping-cart"></i> Ваша корзина ({cart_count} товаров)
                </h3>
                <button class="btn btn-danger" onclick="clearCart()">
                    <i class="fas fa-trash-alt"></i> Очистить корзину
                </button>
            </div>

            <div style="display: flex; flex-direction: column; gap: 15px;">
                {cart_rows}
            </div>
        </div>

        <!-- Итого и оформление -->
        <div class="section">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px;">
                <div>
                    <div style="font-size: 14px; color: #7f8c8d;">Общая сумма</div>
                    <div style="font-size: 36px; font-weight: bold; color: #2c3e50;">
                        {total:.2f} ₽
                    </div>
                </div>

                <div style="display: flex; gap: 15px;">
                    <button class="btn btn-primary" onclick="window.location.href='/products'">
                        <i class="fas fa-arrow-left"></i> Продолжить покупки
                    </button>
                    <button class="btn btn-success" style="font-size: 18px; padding: 15px 30px;" onclick="createOrder()">
                        <i class="fas fa-check-circle"></i> Оформить заказ
                    </button>
                </div>
            </div>
        </div>
        '''
    else:
        cart_content = f'''
        <!-- Пустая корзина -->
        <div class="section" style="text-align: center; padding: 60px 20px;">
            <div style="font-size: 80px; color: #ddd; margin-bottom: 20px;">
                <i class="fas fa-shopping-cart"></i>
            </div>
            <h2 style="color: #7f8c8d; margin-bottom: 15px;">Ваша корзина пуста</h2>
            <p style="color: #95a5a6; margin-bottom: 30px; max-width: 500px; margin: 0 auto 30px;">
                Добавьте товары из каталога, чтобы создать заказ
            </p>
            <button class="btn btn-primary" onclick="window.location.href='/products'" style="font-size: 16px; padding: 12px 30px;">
                <i class="fas fa-boxes"></i> Перейти к товарам
            </button>
        </div>
        '''

    clear_cart_js = "\n".join(
            f"await removeFromCartNoConfirm({item['product'].id});"
            for item in items_with_details
        ) if items_with_details else ""

    return f'''
    <!DOCTYPE html>
    <html>
    {get_head('Корзина покупок')}
    <body>
        <div class="dashboard-container fade-in">
            <!-- Навигация -->
            <nav class="navbar">
                <div class="nav-brand">
                    <h2><i class="fas fa-shopping-cart"></i> Корзина покупок</h2>
                    <p><i class="fas fa-user"></i> {current_user.username} | <i class="fas fa-box"></i> {cart_count} товаров</p>
                </div>
                <div class="nav-links">
                    <a href="/dashboard" class="nav-link">
                        <i class="fas fa-tachometer-alt"></i> Главная
                    </a>
                    <a href="/products" class="nav-link">
                        <i class="fas fa-boxes"></i> Товары
                    </a>
                    <a href="/cart" class="nav-link active">
                        <i class="fas fa-shopping-cart"></i> Корзина
                        {f'<span style="background: #e74c3c; color: white; padding: 2px 6px; border-radius: 10px; font-size: 12px;">{cart_count}</span>' if cart_count > 0 else ''}
                    </a>
                    <a href="/orders" class="nav-link">
                        <i class="fas fa-receipt"></i> Заказы
                        {f'<span style="background: #3498db; color: white; padding: 2px 6px; border-radius: 10px; font-size: 12px;">{total_orders}</span>' if total_orders > 0 else ''}
                    </a>
                    <a href="/logout" class="nav-link" style="color: #e74c3c;">
                        <i class="fas fa-sign-out-alt"></i> Выйти
                    </a>
                </div>
            </nav>

            {cart_content}

            <!-- Футер с информацией о студенте -->
            <div class="student-footer">
                <div class="student-info">
                    <i class="fas fa-user-graduate"></i> Чикирисова Анастасия Вячеславовна ФБИ-33
                </div>
            </div>
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
                        showAlert('error', '❌ ' + result.error);
                    }}
                }} catch (error) {{
                    showAlert('error', '❌ Ошибка сети: ' + error.message);
                }}
            }}

            // Удаление товара из корзины (с confirm)
            async function removeFromCart(productId) {{
              if (!confirm('Удалить товар из корзины?')) return;
              return removeFromCartNoConfirm(productId);
            }}

            // Удаление товара без confirm (для clearCart)
            async function removeFromCartNoConfirm(productId) {{
              try {{
                const response = await fetch('/api/remove_from_cart', {{
                  method: 'POST',
                  headers: {{'Content-Type': 'application/json'}},
                  body: JSON.stringify({{product_id: productId}})
                }});
                const result = await response.json();
                if (!result.success) {{
                  showAlert('error', '❌ ' + (result.error || 'Ошибка'));
                  throw new Error(result.error || 'remove_from_cart failed');
                }}
                return true;
              }} catch (error) {{
                showAlert('error', '❌ Ошибка сети: ' + error.message);
                throw error;
              }}
            }}

            // Очистка корзины
            async function clearCart() {{
              if (!confirm('Очистить всю корзину?')) return;

              try {{

                {clear_cart_js}

                showAlert('success', '✅ Корзина очищена');
                setTimeout(() => location.reload(), 300);
              }} catch (e) {{
                // уже показали alert внутри
              }}
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
                        showAlert('success', '✅ ' + result.message);
                        setTimeout(() => window.location.href = '/orders', 1500);
                    }} else {{
                        showAlert('error', '❌ ' + result.error);
                    }}
                }} catch (error) {{
                    showAlert('error', '❌ Ошибка сети: ' + error.message);
                }}
            }}

            // Показать уведомление
            function showAlert(type, message) {{
                const alertDiv = document.createElement('div');
                alertDiv.className = `alert alert-${{type}}`;
                alertDiv.innerHTML = message;
                alertDiv.style.position = 'fixed';
                alertDiv.style.top = '20px';
                alertDiv.style.right = '20px';
                alertDiv.style.zIndex = '1000';
                alertDiv.style.minWidth = '300px';
                alertDiv.style.maxWidth = '500px';

                document.body.appendChild(alertDiv);

                setTimeout(() => {{
                    alertDiv.remove();
                }}, 3000);
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
    total_orders = len(orders_list)

    # Генерация HTML для заказов
    orders_content = ""
    if orders_list:
        # Генерация карточек заказов
        orders_cards = ""
        for order in orders_list:
            status_class = "status-paid" if order.is_paid else "status-unpaid"
            status_icon = "fa-check-circle" if order.is_paid else "fa-times-circle"
            status_text = "Оплачен" if order.is_paid else "Не оплачен"

            action_button = ""
            if not order.is_paid:
                action_button = f'''
                <button class="btn btn-success btn-sm" onclick="markAsPaid({order.id})" style="margin-top: 10px;">
                    <i class="fas fa-check"></i> Отметить оплату
                </button>
                '''
            else:
                action_button = '''
                <div style="font-size: 12px; color: #2ecc71; margin-top: 5px;">
                    <i class="fas fa-check-circle"></i> Оплачен
                </div>
                '''

            orders_cards += f'''
            <div class="product-card" style="border-left: 5px solid {'#2ecc71' if order.is_paid else '#e74c3c'};">
                <div style="display: flex; justify-content: space-between; align-items: center; gap: 20px;">
                    <div style="flex: 1;">
                        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                            <div style="font-size: 18px; font-weight: bold; color: #2c3e50;">
                                {order.order_number}
                            </div>
                            <span class="order-status {status_class}" style="font-size: 12px;">
                                <i class="fas {status_icon}"></i>
                                {status_text}
                            </span>
                        </div>
                        <div style="font-size: 14px; color: #7f8c8d;">
                            <i class="fas fa-calendar"></i> {order.created_at.strftime('%d.%m.%Y %H:%M')}
                        </div>
                    </div>

                    <div style="text-align: right;">
                        <div style="font-size: 24px; font-weight: bold; color: #3498db;">
                            {order.total:.2f} ₽
                        </div>
                        {action_button}
                    </div>
                </div>
            </div>
            '''

        orders_content = f'''
        <!-- Список заказов -->
        <div class="section">
            <h3 class="section-title">
                <i class="fas fa-history"></i> История заказов
            </h3>

            <div style="display: flex; flex-direction: column; gap: 20px;">
                {orders_cards}
            </div>
        </div>

        <!-- Статистика заказов -->
        <div class="section">
            <h3 class="section-title">
                <i class="fas fa-chart-bar"></i> Статистика заказов
            </h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px;">
                <div style="text-align: center;">
                    <div style="font-size: 32px; font-weight: bold; color: #3498db;">{total_orders}</div>
                    <div style="color: #7f8c8d; font-size: 14px;">Всего заказов</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 32px; font-weight: bold; color: #2ecc71;">{sum(1 for o in orders_list if o.is_paid)}</div>
                    <div style="color: #7f8c8d; font-size: 14px;">Оплаченные</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 32px; font-weight: bold; color: #e74c3c;">{sum(1 for o in orders_list if not o.is_paid)}</div>
                    <div style="color: #7f8c8d; font-size: 14px;">Не оплаченные</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 32px; font-weight: bold; color: #2c3e50;">{sum(o.total for o in orders_list):.2f} ₽</div>
                    <div style="color: #7f8c8d; font-size: 14px;">Общая сумма</div>
                </div>
            </div>
        </div>
        '''
    else:
        orders_content = f'''
        <!-- Нет заказов -->
        <div class="section" style="text-align: center; padding: 60px 20px;">
            <div style="font-size: 80px; color: #ddd; margin-bottom: 20px;">
                <i class="fas fa-clipboard-list"></i>
            </div>
            <h2 style="color: #7f8c8d; margin-bottom: 15px;">Заказов пока нет</h2>
            <p style="color: #95a5a6; margin-bottom: 30px; max-width: 500px; margin: 0 auto 30px;">
                Создайте первый заказ из корзины, чтобы увидеть его здесь
            </p>
            <button class="btn btn-success" onclick="window.location.href='/cart'" style="font-size: 16px; padding: 12px 30px;">
                <i class="fas fa-shopping-cart"></i> Перейти в корзину
            </button>
        </div>
        '''

    return f'''
    <!DOCTYPE html>
    <html>
    {get_head('Мои заказы')}
    <body>
        <div class="dashboard-container fade-in">
            <!-- Навигация -->
            <nav class="navbar">
                <div class="nav-brand">
                    <h2><i class="fas fa-receipt"></i> Мои заказы</h2>
                    <p><i class="fas fa-user"></i> {current_user.username} | <i class="fas fa-clipboard-list"></i> {total_orders} заказов</p>
                </div>
                <div class="nav-links">
                    <a href="/dashboard" class="nav-link">
                        <i class="fas fa-tachometer-alt"></i> Главная
                    </a>
                    <a href="/products" class="nav-link">
                        <i class="fas fa-boxes"></i> Товары
                    </a>
                    <a href="/cart" class="nav-link">
                        <i class="fas fa-shopping-cart"></i> Корзина
                        {f'<span style="background: #e74c3c; color: white; padding: 2px 6px; border-radius: 10px; font-size: 12px;">{cart_count}</span>' if cart_count > 0 else ''}
                    </a>
                    <a href="/orders" class="nav-link active">
                        <i class="fas fa-receipt"></i> Заказы
                        {f'<span style="background: #3498db; color: white; padding: 2px 6px; border-radius: 10px; font-size: 12px;">{total_orders}</span>' if total_orders > 0 else ''}
                    </a>
                    <a href="/logout" class="nav-link" style="color: #e74c3c;">
                        <i class="fas fa-sign-out-alt"></i> Выйти
                    </a>
                </div>
            </nav>

            {orders_content}

            <!-- Футер с информацией о студенте -->
            <div class="student-footer">
                <div class="student-info">
                    <i class="fas fa-user-graduate"></i> Чикирисова Анастасия Вячеславовна ФБИ-33
                </div>
            </div>
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
                        showAlert('success', '✅ ' + result.message);
                        setTimeout(() => location.reload(), 1500);
                    }} else {{
                        showAlert('error', '❌ ' + result.error);
                    }}
                }} catch (error) {{
                    showAlert('error', '❌ Ошибка сети: ' + error.message);
                }}
            }}

            // Показать уведомление
            function showAlert(type, message) {{
                const alertDiv = document.createElement('div');
                alertDiv.className = `alert alert-${{type}}`;
                alertDiv.innerHTML = message;
                alertDiv.style.position = 'fixed';
                alertDiv.style.top = '20px';
                alertDiv.style.right = '20px';
                alertDiv.style.zIndex = '1000';
                alertDiv.style.minWidth = '300px';
                alertDiv.style.maxWidth = '500px';

                document.body.appendChild(alertDiv);

                setTimeout(() => {{
                    alertDiv.remove();
                }}, 3000);
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
        'version': '3.0',
        'authenticated': current_user.is_authenticated,
        'user': current_user.username if current_user.is_authenticated else None
    })

@app.route('/api')
@login_required
def api_default():
    return jsonify({
        'status': 'ok',
        'message': 'API работает',
        'user': current_user.username
    })

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 СИСТЕМА УПРАВЛЕНИЯ СКЛАДОМ БЫТОВОЙ ТЕХНИКИ")
    print("=" * 60)

    # Создаем папку для статики и favicon
    os.makedirs('static', exist_ok=True)
    os.makedirs('static/favicon', exist_ok=True)

    # Инициализация базы данных
    init_database()

    print("\n✅ Система готова к работе!")
    print("🌐 Доступно по адресу: http://127.0.0.1:5000")
    print("👤 Тестовые пользователи:")
    print("   - admin / admin123 (администратор)")
    print("   - warehouse / warehouse123 (кладовщик)")
    print("=" * 60)
    print("🎨 В этой версии:")
    print("   ✅ Фавиконка склада (автоматически генерируется)")
    print("   ✅ Иконка 🏭 в заголовке страницы")
    print("   ✅ Font Awesome иконки")
    print("   ✅ Современный дизайн")
    print("   ✅ Информация о студенте: Чикирисова Анастасия Вячеславовна ФБИ-33")
    print("=" * 60)
    print("\n🔄 Запуск сервера...\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
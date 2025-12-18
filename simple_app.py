from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

# Создание приложения
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///simple_warehouse.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Модели - User должен наследовать UserMixin
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, default=True)  # Добавляем это поле
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    price = db.Column(db.Float, nullable=False)

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, default=1)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True)
    user_id = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Float, default=0)
    is_paid = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Создание базы данных
with app.app_context():
    db.create_all()
    
    # Создаем пользователя если его нет
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', is_active=True)
        admin.set_password('admin123')
        db.session.add(admin)
        
        # Создаем тестовые товары
        products = [
            Product(sku='FR001', name='Холодильник Samsung', quantity=10, price=34999),
            Product(sku='WM001', name='Стиральная машина LG', quantity=15, price=32999),
            Product(sku='TV001', name='Телевизор Sony', quantity=8, price=64999),
            Product(sku='AC001', name='Кондиционер', quantity=5, price=28999),
            Product(sku='VC001', name='Пылесос', quantity=20, price=12999),
        ]
        for p in products:
            db.session.add(p)
        
        db.session.commit()
        print("База данных создана с тестовыми данными")

# Маршруты
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username, is_active=True).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Неверный логин или пароль')
    
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Вход</title>
        <style>
            body { font-family: Arial; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #f0f2f5; }
            .login-box { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); width: 300px; }
            h1 { text-align: center; color: #333; margin-bottom: 30px; }
            input { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
            button { width: 100%; padding: 12px; background: #1890ff; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            button:hover { background: #40a9ff; }
            .error { background: #ffebee; color: #c62828; padding: 10px; border-radius: 5px; margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <div class="login-box">
            <h1>Склад бытовой техники</h1>
            
            <form method="POST">
                <input type="text" name="username" placeholder="Логин" required>
                <input type="password" name="password" placeholder="Пароль" required>
                <button type="submit">Войти</button>
            </form>
            
            <div style="margin-top: 20px; text-align: center; color: #666;">
                <p>Используйте: <strong>admin</strong> / <strong>admin123</strong></p>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    total_products = Product.query.count()
    total_quantity = sum(p.quantity for p in Product.query.all())
    products = Product.query.limit(10).all()
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Панель управления</title>
        <style>
            body {{ font-family: Arial; margin: 0; background: #f5f5f5; }}
            nav {{ background: #1890ff; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }}
            nav a {{ color: white; text-decoration: none; margin: 0 15px; }}
            nav a:hover {{ text-decoration: underline; }}
            .stats {{ display: flex; gap: 20px; padding: 20px; }}
            .stat-card {{ background: white; padding: 20px; border-radius: 8px; flex: 1; box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center; }}
            .stat-value {{ font-size: 32px; font-weight: bold; color: #1890ff; margin: 10px 0; }}
            .stat-label {{ color: #666; }}
            table {{ width: calc(100% - 40px); background: white; border-collapse: collapse; margin: 20px; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
            th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }}
            th {{ background: #fafafa; font-weight: bold; color: #333; }}
            .btn {{ background: #1890ff; color: white; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer; font-size: 14px; }}
            .btn:hover {{ background: #40a9ff; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .quantity-low {{ color: #ff4d4f; font-weight: bold; }}
            .quantity-ok {{ color: #52c41a; }}
        </style>
    </head>
    <body>
        <nav>
            <div><strong>Склад бытовой техники</strong></div>
            <div>
                <a href="/dashboard">Главная</a>
                <a href="/products">Товары</a>
                <a href="/cart">Корзина</a>
                <a href="/orders">Заказы</a>
                <a href="/logout">Выйти ({current_user.username})</a>
            </div>
        </nav>
        
        <div class="container">
            <h1 style="padding: 20px;">Панель управления</h1>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-label">Всего товаров</div>
                    <div class="stat-value">{total_products}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Общее количество</div>
                    <div class="stat-value">{total_quantity}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Товаров в наличии</div>
                    <div class="stat-value">{sum(1 for p in products if p.quantity > 0)}</div>
                </div>
            </div>
            
            <h2 style="padding: 0 20px;">Последние товары</h2>
            <table>
                <tr>
                    <th>Артикул</th>
                    <th>Название</th>
                    <th>Количество</th>
                    <th>Цена</th>
                    <th>Действия</th>
                </tr>
                {"".join(f'''
                <tr>
                    <td>{p.sku}</td>
                    <td>{p.name}</td>
                    <td class="{'quantity-low' if p.quantity <= 5 else 'quantity-ok'}">{p.quantity}</td>
                    <td>{p.price:.2f} ₽</td>
                    <td>
                        <button class="btn" onclick="addToCart({p.id})">В корзину</button>
                    </td>
                </tr>
                ''' for p in products)}
            </table>
        </div>
        
        <script>
            async function addToCart(productId) {{
                try {{
                    const response = await fetch('/api/add_to_cart', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{product_id: productId}})
                    }});
                    
                    const result = await response.json();
                    if (result.success) {{
                        alert('✓ Товар добавлен в корзину!');
                    }} else {{
                        alert('✗ Ошибка: ' + result.error);
                    }}
                }} catch (error) {{
                    alert('✗ Ошибка сети: ' + error.message);
                }}
            }}
        </script>
    </body>
    </html>
    '''

@app.route('/products')
@login_required
def products():
    products = Product.query.all()
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Товары</title>
        <style>
            body {{ font-family: Arial; margin: 0; background: #f5f5f5; }}
            nav {{ background: #1890ff; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }}
            nav a {{ color: white; text-decoration: none; margin: 0 15px; }}
            nav a:hover {{ text-decoration: underline; }}
            table {{ width: calc(100% - 40px); background: white; border-collapse: collapse; margin: 20px; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
            th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }}
            th {{ background: #fafafa; font-weight: bold; color: #333; }}
            .btn {{ background: #1890ff; color: white; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer; font-size: 14px; }}
            .btn:hover {{ background: #40a9ff; }}
            .quantity-low {{ color: #ff4d4f; font-weight: bold; }}
            .quantity-ok {{ color: #52c41a; }}
        </style>
    </head>
    <body>
        <nav>
            <div><strong>Склад бытовой техники</strong></div>
            <div>
                <a href="/dashboard">Главная</a>
                <a href="/products">Товары</a>
                <a href="/cart">Корзина</a>
                <a href="/orders">Заказы</a>
                <a href="/logout">Выйти ({current_user.username})</a>
            </div>
        </nav>
        
        <h1 style="padding: 20px;">Список товаров</h1>
        
        <table>
            <tr>
                <th>Артикул</th>
                <th>Название</th>
                <th>Количество</th>
                <th>Цена</th>
                <th>Действия</th>
            </tr>
            {"".join(f'''
            <tr>
                <td>{p.sku}</td>
                <td>{p.name}</td>
                <td class="{'quantity-low' if p.quantity <= 5 else 'quantity-ok'}">{p.quantity}</td>
                <td>{p.price:.2f} ₽</td>
                <td>
                    <button class="btn" onclick="addToCart({p.id})">В корзину</button>
                </td>
            </tr>
            ''' for p in products)}
        </table>
        
        <script>
            async function addToCart(productId) {{
                try {{
                    const response = await fetch('/api/add_to_cart', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{product_id: productId}})
                    }});
                    
                    const result = await response.json();
                    if (result.success) {{
                        alert('✓ Товар добавлен в корзину!');
                    }} else {{
                        alert('✗ Ошибка: ' + result.error);
                    }}
                }} catch (error) {{
                    alert('✗ Ошибка сети: ' + error.message);
                }}
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
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Корзина</title>
        <style>
            body {{ font-family: Arial; margin: 0; background: #f5f5f5; }}
            nav {{ background: #1890ff; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }}
            nav a {{ color: white; text-decoration: none; margin: 0 15px; }}
            nav a:hover {{ text-decoration: underline; }}
            .container {{ max-width: 800px; margin: 20px auto; padding: 20px; }}
            .cart-item {{ background: white; padding: 20px; margin-bottom: 15px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
            .cart-total {{ background: white; padding: 20px; margin-top: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: right; font-size: 20px; }}
            .btn {{ background: #1890ff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-size: 16px; margin: 5px; }}
            .btn:hover {{ background: #40a9ff; }}
            .btn-danger {{ background: #ff4d4f; }}
            .btn-danger:hover {{ background: #ff7875; }}
            .btn-success {{ background: #52c41a; }}
            .btn-success:hover {{ background: #73d13d; }}
            .empty-cart {{ text-align: center; padding: 50px; color: #999; }}
        </style>
    </head>
    <body>
        <nav>
            <div><strong>Склад бытовой техники</strong></div>
            <div>
                <a href="/dashboard">Главная</a>
                <a href="/products">Товары</a>
                <a href="/cart">Корзина ({cart_count})</a>
                <a href="/orders">Заказы</a>
                <a href="/logout">Выйти ({current_user.username})</a>
            </div>
        </nav>
        
        <div class="container">
            <h1>Корзина</h1>
            
            {f'''
            <div class="empty-cart">
                <h2>😔 Корзина пуста</h2>
                <p>Добавьте товары из каталога</p>
                <button class="btn" onclick="window.location.href='/products'">Перейти к товарам</button>
            </div>
            ''' if not items_with_details else ""}
            
            {"".join(f'''
            <div class="cart-item" id="item-{item['product'].id}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h3 style="margin: 0;">{item['product'].name}</h3>
                        <p style="margin: 5px 0; color: #666;">Артикул: {item['product'].sku}</p>
                        <p style="margin: 5px 0;">Количество: {item['quantity']}</p>
                        <p style="margin: 5px 0;">Цена за единицу: {item['product'].price:.2f} ₽</p>
                    </div>
                    <div style="text-align: right;">
                        <h3 style="margin: 0; color: #1890ff;">{item['total']:.2f} ₽</h3>
                        <button class="btn btn-danger" onclick="removeFromCart({item['product'].id})">Удалить</button>
                    </div>
                </div>
            </div>
            ''' for item in items_with_details)}
            
            {f'''
            <div class="cart-total">
                <h2>Итого: {total:.2f} ₽</h2>
                <button class="btn btn-success" onclick="createOrder()">Оформить заказ</button>
                <button class="btn btn-danger" onclick="clearCart()">Очистить корзину</button>
            </div>
            ''' if items_with_details else ""}
        </div>
        
        <script>
            async function removeFromCart(productId) {{
                if (!confirm('Удалить товар из корзины?')) return;
                
                try {{
                    const response = await fetch('/api/remove_from_cart', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{product_id: productId}})
                    }});
                    
                    const result = await response.json();
                    if (result.success) {{
                        alert('✓ Товар удален из корзины');
                        location.reload();
                    }} else {{
                        alert('✗ Ошибка: ' + result.error);
                    }}
                }} catch (error) {{
                    alert('✗ Ошибка сети: ' + error.message);
                }}
            }}
            
            async function clearCart() {{
                if (!confirm('Очистить всю корзину?')) return;
                
                // Удаляем все товары из корзины
                {f'''
                {"".join(f'''
                await fetch('/api/remove_from_cart', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{product_id: {item['product'].id}}})
                }});
                ''' for item in items_with_details)}
                ''' if items_with_details else ""}
                
                alert('✓ Корзина очищена');
                location.reload();
            }}
            
            async function createOrder() {{
                if (!confirm('Оформить заказ из корзины?')) return;
                
                try {{
                    const response = await fetch('/api/create_order', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}}
                    }});
                    
                    const result = await response.json();
                    if (result.success) {{
                        alert('✓ Заказ создан! Номер: ' + result.order_number);
                        location.href = '/orders';
                    }} else {{
                        alert('✗ Ошибка: ' + result.error);
                    }}
                }} catch (error) {{
                    alert('✗ Ошибка сети: ' + error.message);
                }}
            }}
        </script>
    </body>
    </html>
    '''

@app.route('/orders')
@login_required
def orders():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Заказы</title>
        <style>
            body {{ font-family: Arial; margin: 0; background: #f5f5f5; }}
            nav {{ background: #1890ff; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }}
            nav a {{ color: white; text-decoration: none; margin: 0 15px; }}
            nav a:hover {{ text-decoration: underline; }}
            .container {{ max-width: 800px; margin: 20px auto; padding: 20px; }}
            .order-card {{ background: white; padding: 20px; margin-bottom: 15px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
            .order-paid {{ border-left: 5px solid #52c41a; }}
            .order-unpaid {{ border-left: 5px solid #ff4d4f; }}
            .btn {{ background: #1890ff; color: white; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer; font-size: 14px; }}
            .btn:hover {{ background: #40a9ff; }}
            .btn-success {{ background: #52c41a; }}
            .btn-success:hover {{ background: #73d13d; }}
            .status-paid {{ color: #52c41a; font-weight: bold; }}
            .status-unpaid {{ color: #ff4d4f; font-weight: bold; }}
            .empty-orders {{ text-align: center; padding: 50px; color: #999; }}
        </style>
    </head>
    <body>
        <nav>
            <div><strong>Склад бытовой техники</strong></div>
            <div>
                <a href="/dashboard">Главная</a>
                <a href="/products">Товары</a>
                <a href="/cart">Корзина</a>
                <a href="/orders">Заказы</a>
                <a href="/logout">Выйти ({current_user.username})</a>
            </div>
        </nav>
        
        <div class="container">
            <h1>Мои заказы</h1>
            
            {f'''
            <div class="empty-orders">
                <h2>📦 Заказов пока нет</h2>
                <p>Создайте первый заказ из корзины</p>
                <button class="btn" onclick="window.location.href='/cart'">Перейти в корзину</button>
            </div>
            ''' if not orders else ""}
            
            {"".join(f'''
            <div class="order-card {'order-paid' if order.is_paid else 'order-unpaid'}">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <div>
                        <h3 style="margin: 0;">Заказ №{order.order_number}</h3>
                        <p style="margin: 5px 0; color: #666;">Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}</p>
                    </div>
                    <div style="text-align: right;">
                        <h3 style="margin: 0; color: #1890ff;">{order.total:.2f} ₽</h3>
                        <p class="{'status-paid' if order.is_paid else 'status-unpaid'}" style="margin: 5px 0;">
                            {("✅ Оплачен" if order.is_paid else "❌ Не оплачен")}
                        </p>
                    </div>
                </div>
                
                {f'''
                <button class="btn btn-success" onclick="markAsPaid({order.id})">Отметить как оплаченный</button>
                ''' if not order.is_paid else ""}
            </div>
            ''' for order in orders)}
        </div>
        
        <script>
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
                        alert('✓ Заказ отмечен как оплаченный!');
                        location.reload();
                    }} else {{
                        alert('✗ Ошибка: ' + result.error);
                    }}
                }} catch (error) {{
                    alert('✗ Ошибка сети: ' + error.message);
                }}
            }}
        </script>
    </body>
    </html>
    '''

# Простое API (не JSON-RPC)
@app.route('/api/add_to_cart', methods=['POST'])
@login_required
def api_add_to_cart():
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'success': False, 'error': 'Товар не найден'})
        
        if product.quantity < 1:
            return jsonify({'success': False, 'error': 'Товара нет в наличии'})
        
        # Ищем товар в корзине
        cart_item = CartItem.query.filter_by(
            user_id=current_user.id,
            product_id=product_id
        ).first()
        
        if cart_item:
            cart_item.quantity += 1
        else:
            cart_item = CartItem(
                user_id=current_user.id,
                product_id=product_id,
                quantity=1
            )
            db.session.add(cart_item)
        
        db.session.commit()
        return jsonify({'success': True, 'message': f'Товар "{product.name}" добавлен в корзину'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/remove_from_cart', methods=['POST'])
@login_required
def api_remove_from_cart():
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        
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
        
        total = 0
        
        # Проверяем наличие товаров
        for item in cart_items:
            product = Product.query.get(item.product_id)
            if not product:
                return jsonify({'success': False, 'error': f'Товар ID:{item.product_id} не найден'})
            
            if product.quantity < item.quantity:
                return jsonify({
                    'success': False, 
                    'error': f'Недостаточно товара "{product.name}". В наличии: {product.quantity}, требуется: {item.quantity}'
                })
        
        # Создаем номер заказа
        import random
        import string
        order_number = f'ORD-{datetime.now().strftime("%Y%m%d")}-{"".join(random.choices(string.digits, k=6))}'
        
        # Создаем заказ
        order = Order(
            order_number=order_number,
            user_id=current_user.id,
            total=0,
            is_paid=False
        )
        db.session.add(order)
        
        # Уменьшаем количество товаров
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
            'order_number': order_number,
            'total': total,
            'message': f'Заказ {order_number} создан успешно'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/mark_order_paid', methods=['POST'])
@login_required
def api_mark_order_paid():
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'success': False, 'error': 'Заказ не найден'})
        
        if order.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Доступ запрещен'})
        
        order.is_paid = True
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Заказ {order.order_number} отмечен как оплаченный'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/health', methods=['GET'])
def api_health():
    return jsonify({
        'status': 'ok',
        'service': 'Warehouse System',
        'authenticated': current_user.is_authenticated,
        'user': current_user.username if current_user.is_authenticated else None
    })

if __name__ == '__main__':
    print("=" * 50)
    print("Склад бытовой техники - Запущен!")
    print("=" * 50)
    print("Доступно по адресу: http://127.0.0.1:5000")
    print("Логин: admin / admin123")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)
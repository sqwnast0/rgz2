from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
import json
import logging
import os
from datetime import datetime
from config import config
from models import db, Product, Category, User, Order, Cart, OrderItem, CartItem
from auth import login_manager, authenticate

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Инициализация расширений
    db.init_app(app)
    login_manager.init_app(app)
    
    # Создание папок
    os.makedirs('static/uploads', exist_ok=True)
    
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
            
            if not username or not password:
                flash('Введите логин и пароль', 'error')
                return render_template('login.html')
            
            auth_user = authenticate(username, password)
            if auth_user:
                login_user(auth_user)
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard'))
            else:
                flash('Неверный логин или пароль', 'error')
        
        return render_template('login.html')
    
    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('Вы вышли из системы', 'info')
        return redirect(url_for('login'))
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        # Получаем статистику для дашборда
        total_products = Product.query.count()
        total_quantity = db.session.query(db.func.sum(Product.quantity)).scalar() or 0
        total_orders = Order.query.filter_by(user_id=current_user.id).count()
        
        # Последние 10 товаров
        recent_products = Product.query.order_by(Product.created_at.desc()).limit(10).all()
        
        # Товары с низким запасом
        low_stock = Product.query.filter(Product.quantity > 0, Product.quantity <= 5).limit(10).all()
        
        # Последние 5 заказов
        recent_orders = Order.query.filter_by(user_id=current_user.id)\
            .order_by(Order.created_at.desc()).limit(5).all()
        
        # Корзина пользователя
        cart = Cart.query.filter_by(user_id=current_user.id).first()
        cart_items = len(cart.items) if cart else 0
        
        return render_template('index.html',
                             username=current_user.username,
                             total_products=total_products,
                             total_quantity=total_quantity,
                             total_orders=total_orders,
                             recent_products=recent_products,
                             low_stock=low_stock,
                             recent_orders=recent_orders,
                             cart_items=cart_items)
    
    @app.route('/products')
    @login_required
    def products_page():
        categories = Category.query.order_by(Category.name).all()
        return render_template('products.html', categories=categories)
    
    @app.route('/add-product')
    @login_required
    def add_product_page():
        categories = Category.query.order_by(Category.name).all()
        return render_template('add_product.html', categories=categories)
    
    @app.route('/cart')
    @login_required
    def cart_page():
        return render_template('cart.html')
    
    @app.route('/orders')
    @login_required
    def orders_page():
        return render_template('orders.html')
    
    @app.route('/api', methods=['POST'])
    @login_required
    def api():
        """JSON-RPC endpoint"""
        logger.info(f"API request from {request.remote_addr}")
        
        if not request.is_json:
            logger.error("Request is not JSON")
            return jsonify({
                'jsonrpc': '2.0',
                'error': {
                    'code': -32700,
                    'message': 'Invalid JSON: Content-Type must be application/json'
                },
                'id': None
            }), 400
        
        try:
            data = request.get_json()
            
            if not data:
                logger.error("Empty JSON data")
                return jsonify({
                    'jsonrpc': '2.0',
                    'error': {
                        'code': -32600,
                        'message': 'Invalid Request: Empty JSON'
                    },
                    'id': None
                }), 400
            
            # Определяем формат запроса
            if 'jsonrpc' in data and 'method' in data:
                # JSON-RPC 2.0 формат
                method = data.get('method')
                params = data.get('params', {})
                request_id = data.get('id')
                
            elif 'action' in data:
                # Старый формат
                method = data.get('action')
                params = {k: v for k, v in data.items() if k != 'action'}
                request_id = data.get('id', None)
                
            else:
                logger.error("Invalid request format. Keys: " + str(list(data.keys())))
                return jsonify({
                    'jsonrpc': '2.0',
                    'error': {
                        'code': -32600,
                        'message': 'Invalid Request: Missing method/action field'
                    },
                    'id': None
                }), 400
            
            # Обработка запроса
            from api import handle_json_rpc
            result = handle_json_rpc(method=method, params=params, id=request_id)
            
            if isinstance(result, tuple) and len(result) == 2:
                # Ошибка была обработана в декораторе
                return result
            
            return jsonify({
                'jsonrpc': '2.0',
                'result': result,
                'id': request_id
            })
            
        except Exception as e:
            logger.error(f"API error: {str(e)}", exc_info=True)
            return jsonify({
                'jsonrpc': '2.0',
                'error': {
                    'code': -32603,
                    'message': 'Internal error',
                    'data': str(e)
                },
                'id': None
            }), 500
    
    @app.route('/api/health', methods=['GET'])
    def api_health():
        """Проверка работоспособности API"""
        return jsonify({
            'status': 'ok',
            'service': 'Warehouse Management System',
            'version': '1.0',
            'user_authenticated': current_user.is_authenticated,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        logger.error(f"Server error: {error}", exc_info=True)
        return render_template('500.html'), 500
    
    return app

# Создание приложения
app = create_app()

# Инициализация базы данных при запуске
with app.app_context():
    db.create_all()
    
    # Создаем пользователей по умолчанию
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', full_name='Администратор')
        admin.set_password('admin123')
        db.session.add(admin)
    
    if not User.query.filter_by(username='warehouse').first():
        warehouse = User(username='warehouse', full_name='Кладовщик')
        warehouse.set_password('warehouse123')
        db.session.add(warehouse)
    
    # Создаем категории по умолчанию
    if Category.query.count() == 0:
        categories = [
            Category(name='Холодильники', description='Холодильники и морозильники'),
            Category(name='Стиральные машины', description='Стиральные машины и сушилки'),
            Category(name='Телевизоры', description='Телевизоры и мониторы'),
            Category(name='Плиты и духовки', description='Варочные панели и духовые шкафы'),
            Category(name='Кондиционеры', description='Климатическая техника'),
            Category(name='Мелкая техника', description='Чайники, микроволновки, тостеры'),
            Category(name='Пылесосы', description='Пылесосы и моющие пылесосы'),
            Category(name='Водонагреватели', description='Бойлеры и водонагреватели'),
        ]
        for category in categories:
            db.session.add(category)
    
    # Создаем тестовые товары
    if Product.query.count() == 0:
        products_data = [
            # Холодильники
            {'sku': 'FR001', 'name': 'Холодильник Samsung RB33J3000SA', 'price': 34999, 'quantity': 15, 'category_id': 1, 'brand': 'Samsung', 'model': 'RB33J3000SA'},
            {'sku': 'FR002', 'name': 'Холодильник LG GA-B459SLWL', 'price': 42999, 'quantity': 8, 'category_id': 1, 'brand': 'LG', 'model': 'GA-B459SLWL'},
            {'sku': 'FR003', 'name': 'Холодильник Bosch KGN39VW22R', 'price': 51999, 'quantity': 5, 'category_id': 1, 'brand': 'Bosch', 'model': 'KGN39VW22R'},
            {'sku': 'FR004', 'name': 'Морозильник Indesit TZ 8', 'price': 18999, 'quantity': 12, 'category_id': 1, 'brand': 'Indesit', 'model': 'TZ 8'},
            
            # Стиральные машины
            {'sku': 'WM001', 'name': 'Стиральная машина Bosch WAU28PH8BR', 'price': 41999, 'quantity': 10, 'category_id': 2, 'brand': 'Bosch', 'model': 'WAU28PH8BR'},
            {'sku': 'WM002', 'name': 'Стиральная машина LG F2V5HS0W', 'price': 32999, 'quantity': 18, 'category_id': 2, 'brand': 'LG', 'model': 'F2V5HS0W'},
            {'sku': 'WM003', 'name': 'Стиральная машина Samsung WW65J42E0HW', 'price': 27999, 'quantity': 22, 'category_id': 2, 'brand': 'Samsung', 'model': 'WW65J42E0HW'},
            {'sku': 'WM004', 'name': 'Сушильная машина Miele TDB130WP', 'price': 68999, 'quantity': 3, 'category_id': 2, 'brand': 'Miele', 'model': 'TDB130WP'},
            
            # Телевизоры
            {'sku': 'TV001', 'name': 'Телевизор Samsung QE55Q60BAU', 'price': 64999, 'quantity': 7, 'category_id': 3, 'brand': 'Samsung', 'model': 'QE55Q60BAU'},
            {'sku': 'TV002', 'name': 'Телевизор LG 55NANO766QA', 'price': 52999, 'quantity': 9, 'category_id': 3, 'brand': 'LG', 'model': '55NANO766QA'},
            {'sku': 'TV003', 'name': 'Телевизор Sony KD-55X75WL', 'price': 71999, 'quantity': 4, 'category_id': 3, 'brand': 'Sony', 'model': 'KD-55X75WL'},
            {'sku': 'TV004', 'name': 'Телевизор Philips 50PUS8507', 'price': 45999, 'quantity': 11, 'category_id': 3, 'brand': 'Philips', 'model': '50PUS8507'},
            
            # Плиты и духовки
            {'sku': 'ST001', 'name': 'Варочная панель Bosch PKE645B17E', 'price': 23999, 'quantity': 14, 'category_id': 4, 'brand': 'Bosch', 'model': 'PKE645B17E'},
            {'sku': 'ST002', 'name': 'Духовой шкаф Electrolux EOB 53434 AX', 'price': 31999, 'quantity': 8, 'category_id': 4, 'brand': 'Electrolux', 'model': 'EOB 53434 AX'},
            {'sku': 'ST003', 'name': 'Газовая плита Gorenje K 521 CLI', 'price': 18999, 'quantity': 16, 'category_id': 4, 'brand': 'Gorenje', 'model': 'K 521 CLI'},
            {'sku': 'ST004', 'name': 'Индукционная панель Samsung NZ64R3747BK', 'price': 27999, 'quantity': 6, 'category_id': 4, 'brand': 'Samsung', 'model': 'NZ64R3747BK'},
            
            # Кондиционеры
            {'sku': 'AC001', 'name': 'Кондиционер Ballu BSWI-09HN1', 'price': 28999, 'quantity': 13, 'category_id': 5, 'brand': 'Ballu', 'model': 'BSWI-09HN1'},
            {'sku': 'AC002', 'name': 'Кондиционер Mitsubishi Electric MSZ-LN35VG', 'price': 64999, 'quantity': 5, 'category_id': 5, 'brand': 'Mitsubishi', 'model': 'MSZ-LN35VG'},
            {'sku': 'AC003', 'name': 'Мобильный кондиционер Zanussi ZACM-09 MP-III/N1', 'price': 32999, 'quantity': 7, 'category_id': 5, 'brand': 'Zanussi', 'model': 'ZACM-09 MP-III/N1'},
            
            # Мелкая техника
            {'sku': 'KT001', 'name': 'Микроволновая печь Samsung MS23K3515AW', 'price': 8999, 'quantity': 25, 'category_id': 6, 'brand': 'Samsung', 'model': 'MS23K3515AW'},
            {'sku': 'KT002', 'name': 'Электрочайник Bosch TWK 3A013', 'price': 3499, 'quantity': 30, 'category_id': 6, 'brand': 'Bosch', 'model': 'TWK 3A013'},
            {'sku': 'KT003', 'name': 'Тостер Tefal TT1D10', 'price': 2999, 'quantity': 28, 'category_id': 6, 'brand': 'Tefal', 'model': 'TT1D10'},
            {'sku': 'KT004', 'name': 'Кофемашина DeLonghi ECAM 22.110.B', 'price': 38999, 'quantity': 4, 'category_id': 6, 'brand': 'DeLonghi', 'model': 'ECAM 22.110.B'},
            {'sku': 'KT005', 'name': 'Блендер Philips HR3655/00', 'price': 8999, 'quantity': 17, 'category_id': 6, 'brand': 'Philips', 'model': 'HR3655/00'},
            
            # Пылесосы
            {'sku': 'VC001', 'name': 'Пылесос Samsung VCC4520S36', 'price': 12999, 'quantity': 15, 'category_id': 7, 'brand': 'Samsung', 'model': 'VCC4520S36'},
            {'sku': 'VC002', 'name': 'Робот-пылесос Xiaomi Robot Vacuum S10+', 'price': 29999, 'quantity': 6, 'category_id': 7, 'brand': 'Xiaomi', 'model': 'S10+'},
            {'sku': 'VC003', 'name': 'Вертикальный пылесос Dyson V12 Detect Slim', 'price': 54999, 'quantity': 3, 'category_id': 7, 'brand': 'Dyson', 'model': 'V12 Detect Slim'},
            
            # Водонагреватели
            {'sku': 'WH001', 'name': 'Водонагреватель Ariston ABS PRO ECO 80 V', 'price': 15999, 'quantity': 9, 'category_id': 8, 'brand': 'Ariston', 'model': 'ABS PRO ECO 80 V'},
            {'sku': 'WH002', 'name': 'Бойлер Thermex Ultra Slim 100', 'price': 17999, 'quantity': 11, 'category_id': 8, 'brand': 'Thermex', 'model': 'Ultra Slim 100'},
            {'sku': 'WH003', 'name': 'Водонагреватель Electrolux EWH 100 Centurio IQ 2.0', 'price': 22999, 'quantity': 7, 'category_id': 8, 'brand': 'Electrolux', 'model': 'EWH 100 Centurio IQ 2.0'},
        ]
        
        for prod_data in products_data:
            product = Product(
                sku=prod_data['sku'],
                name=prod_data['name'],
                price=prod_data['price'],
                quantity=prod_data['quantity'],
                category_id=prod_data['category_id'],
                brand=prod_data['brand'],
                model=prod_data['model'],
                description=f'{prod_data["brand"]} {prod_data["model"]}. Гарантия 24 месяца.'
            )
            db.session.add(product)
    
    db.session.commit()
    print('База данных инициализирована')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
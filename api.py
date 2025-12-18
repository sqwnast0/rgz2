from functools import wraps
from flask import jsonify
from models import db, Product, Category, Order, OrderItem, Cart, CartItem
from flask_login import current_user
import random
import string
from datetime import datetime

def jsonrpc_error(code, message, data=None):
    error = {
        'code': code,
        'message': message
    }
    if data:
        error['data'] = data
    
    return jsonify({
        'jsonrpc': '2.0',
        'error': error,
        'id': None
    }), 200

def require_params(*required_params):
    def decorator(func):
        @wraps(func)
        def wrapper(params, *args, **kwargs):
            missing = [param for param in required_params if param not in params]
            if missing:
                return jsonrpc_error(-32602, f'Missing required parameters: {", ".join(missing)}')
            return func(params, *args, **kwargs)
        return wrapper
    return decorator

def generate_order_number():
    date_str = datetime.now().strftime('%Y%m%d')
    random_str = ''.join(random.choices(string.digits, k=6))
    return f'ORD-{date_str}-{random_str}'

def handle_json_rpc(method, params, id):
    methods = {
        'get_products': get_products,
        'get_product': get_product,
        'add_product': add_product,
        'get_categories': get_categories,
        'add_to_cart': add_to_cart,
        'remove_from_cart': remove_from_cart,
        'get_cart': get_cart,
        'create_order': create_order,
        'get_orders': get_orders,
        'mark_order_paid': mark_order_paid,
        'get_statistics': get_statistics,
    }
    
    if method in methods:
        return methods[method](params)
    else:
        return jsonrpc_error(-32601, f'Method {method} not found')

# Реализация методов
def get_products(params):
    page = int(params.get('page', 1))
    per_page = int(params.get('per_page', 20))
    category_id = params.get('category_id')
    
    query = Product.query
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    products = query.order_by(Product.name).all()
    
    total = len(products)
    pages = (total + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    paginated_products = products[start:end]
    
    return {
        'products': [p.to_dict() for p in paginated_products],
        'total': total,
        'pages': pages,
        'current_page': page,
        'per_page': per_page,
        'has_next': page < pages,
        'has_prev': page > 1
    }

def get_categories(params):
    categories = Category.query.order_by(Category.name).all()
    return [{
        'id': c.id,
        'name': c.name,
        'description': c.description,
        'product_count': len(c.products)
    } for c in categories]

@require_params('product_id')
def add_to_cart(params):
    product_id = params['product_id']
    quantity = int(params.get('quantity', 1))
    
    product = Product.query.get(product_id)
    if not product:
        return jsonrpc_error(-32001, 'Product not found')
    
    if product.quantity < quantity:
        return jsonrpc_error(-32003, f'Not enough stock. Available: {product.quantity}')
    
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart:
        cart = Cart(user_id=current_user.id)
        db.session.add(cart)
        db.session.commit()
    
    cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
    
    if cart_item:
        new_quantity = cart_item.quantity + quantity
        if product.quantity < new_quantity:
            return jsonrpc_error(-32003, f'Not enough stock. Available: {product.quantity}')
        cart_item.quantity = new_quantity
    else:
        cart_item = CartItem(cart_id=cart.id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)
    
    cart.updated_at = datetime.utcnow()
    db.session.commit()
    
    return {
        'success': True,
        'cart_item': {
            'id': cart_item.id,
            'product_id': cart_item.product_id,
            'product_name': product.name,
            'product_sku': product.sku,
            'quantity': cart_item.quantity,
            'price': float(product.price) if product.price else 0
        }
    }

def get_cart(params):
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart:
        return {'items': [], 'total_items': 0, 'total_amount': 0}
    
    items = []
    total_amount = 0
    total_items = 0
    
    for item in cart.items:
        if item.product:
            item_total = float(item.product.price) * item.quantity if item.product.price else 0
            items.append({
                'id': item.id,
                'product_id': item.product_id,
                'product_name': item.product.name,
                'product_sku': item.product.sku,
                'quantity': item.quantity,
                'price': float(item.product.price) if item.product.price else 0,
                'total': item_total,
                'available_quantity': item.product.quantity
            })
            total_amount += item_total
            total_items += item.quantity
    
    return {
        'items': items,
        'total_items': total_items,
        'total_amount': total_amount,
        'cart_id': cart.id
    }

@require_params('product_id')
def remove_from_cart(params):
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart:
        return {'success': True, 'message': 'Cart is empty'}
    
    cart_item = CartItem.query.filter_by(
        cart_id=cart.id, 
        product_id=params['product_id']
    ).first()
    
    if cart_item:
        db.session.delete(cart_item)
        cart.updated_at = datetime.utcnow()
        db.session.commit()
    
    return {'success': True}

def create_order(params):
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart or not cart.items:
        return jsonrpc_error(-32004, 'Cart is empty')
    
    for item in cart.items:
        if item.product.quantity < item.quantity:
            return jsonrpc_error(-32003, 
                f'Not enough stock for {item.product.name}. Available: {item.product.quantity}')
    
    order = Order(
        order_number=generate_order_number(),
        user_id=current_user.id,
        status='pending',
        is_paid=False,
        notes=params.get('notes', '')
    )
    db.session.add(order)
    
    total_amount = 0
    
    for cart_item in cart.items:
        product = cart_item.product
        
        order_item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=cart_item.quantity,
            price=product.price
        )
        db.session.add(order_item)
        
        product.quantity -= cart_item.quantity
        total_amount += float(product.price) * cart_item.quantity if product.price else 0
    
    order.total_amount = total_amount
    
    CartItem.query.filter_by(cart_id=cart.id).delete()
    cart.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    return {
        'success': True,
        'order': order.to_dict(),
        'message': f'Order {order.order_number} created successfully'
    }

def get_orders(params):
    page = int(params.get('page', 1))
    per_page = int(params.get('per_page', 20))
    
    orders = Order.query.filter_by(user_id=current_user.id)\
        .order_by(Order.created_at.desc()).all()
    
    total = len(orders)
    pages = (total + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    paginated_orders = orders[start:end]
    
    return {
        'orders': [o.to_dict() for o in paginated_orders],
        'total': total,
        'pages': pages,
        'current_page': page,
        'per_page': per_page
    }

@require_params('order_id')
def mark_order_paid(params):
    order = Order.query.get(params['order_id'])
    if not order:
        return jsonrpc_error(-32005, 'Order not found')
    
    if order.is_paid:
        return {'success': True, 'message': 'Order already paid'}
    
    order.is_paid = True
    order.status = 'completed'
    order.updated_at = datetime.utcnow()
    db.session.commit()
    
    return {'success': True, 'order': order.to_dict()}

def get_statistics(params):
    total_products = Product.query.count()
    total_quantity = db.session.query(db.func.sum(Product.quantity)).scalar() or 0
    total_orders = Order.query.filter_by(user_id=current_user.id).count()
    
    low_stock_products = Product.query.filter(
        Product.quantity > 0, 
        Product.quantity <= 5
    ).count()
    
    unpaid_amount = db.session.query(db.func.sum(Order.total_amount)).filter(
        Order.user_id == current_user.id,
        Order.is_paid == False
    ).scalar() or 0
    
    recent_orders = Order.query.filter_by(user_id=current_user.id)\
        .order_by(Order.created_at.desc()).limit(5).all()
    
    return {
        'total_products': total_products,
        'total_quantity': int(total_quantity),
        'total_orders': total_orders,
        'low_stock_products': low_stock_products,
        'unpaid_amount': float(unpaid_amount) if unpaid_amount else 0,
        'recent_orders': [o.to_dict() for o in recent_orders]
    }

@require_params('sku', 'name', 'price', 'category_id', 'quantity')
def add_product(params):
    sku = params['sku'].strip().upper()
    
    product = Product.query.filter_by(sku=sku).first()
    
    if product:
        product.quantity += int(params['quantity'])
        product.updated_at = datetime.utcnow()
        action = 'updated'
    else:
        product = Product(
            sku=sku,
            name=params['name'],
            description=params.get('description', ''),
            price=params['price'],
            category_id=params['category_id'],
            quantity=params['quantity'],
            brand=params.get('brand', ''),
            model=params.get('model', ''),
            warranty_months=params.get('warranty_months', 12)
        )
        db.session.add(product)
        action = 'created'
    
    db.session.commit()
    
    return {
        'success': True,
        'action': action,
        'product': product.to_dict()
    }

@require_params('product_id')
def get_product(params):
    product = Product.query.get(params['product_id'])
    if not product:
        return jsonrpc_error(-32001, 'Product not found')
    
    return product.to_dict()
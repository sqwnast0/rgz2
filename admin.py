"""
Модуль для административных функций
"""

from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, User, Product, Order, Category
from auth import admin_required
import csv
from io import StringIO
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@login_required
@admin_required
def admin_dashboard():
    """Панель администратора"""
    # Статистика
    total_users = User.query.count()
    total_products = Product.query.count()
    total_orders = Order.query.count()
    
    # Активные пользователи
    active_users = User.query.filter_by(is_active=True).count()
    
    # Последние регистрации
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    
    # Товары с нулевым запасом
    out_of_stock = Product.query.filter_by(quantity=0).count()
    
    # Заказы за последние 7 дней
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_orders = Order.query.filter(Order.created_at >= week_ago).count()
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_products=total_products,
                         total_orders=total_orders,
                         active_users=active_users,
                         recent_users=recent_users,
                         out_of_stock=out_of_stock,
                         recent_orders=recent_orders)

@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    """Управление пользователями"""
    users = User.query.order_by(User.username).all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_user(user_id):
    """Активация/деактивация пользователя"""
    user = User.query.get_or_404(user_id)
    
    # Нельзя деактивировать себя
    if user.id == current_user.user.id:
        flash('Нельзя деактивировать себя', 'error')
        return redirect(url_for('admin.manage_users'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'активирован' if user.is_active else 'деактивирован'
    flash(f'Пользователь {user.username} {status}', 'success')
    
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Удаление пользователя"""
    user = User.query.get_or_404(user_id)
    
    # Нельзя удалить себя
    if user.id == current_user.user.id:
        flash('Нельзя удалить себя', 'error')
        return redirect(url_for('admin.manage_users'))
    
    # Проверяем, есть ли у пользователя заказы
    if user.orders:
        flash('Нельзя удалить пользователя с заказами', 'error')
        return redirect(url_for('admin.manage_users'))
    
    db.session.delete(user)
    db.session.commit()
    
    flash(f'Пользователь {user.username} удален', 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/users/create', methods=['POST'])
@login_required
@admin_required
def create_user():
    """Создание нового пользователя"""
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()
    role = request.form.get('role', 'storekeeper')
    
    if not username or not password:
        flash('Логин и пароль обязательны', 'error')
        return redirect(url_for('admin.manage_users'))
    
    # Проверяем, не существует ли уже пользователь
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        flash('Пользователь с таким логином уже существует', 'error')
        return redirect(url_for('admin.manage_users'))
    
    user = User(
        username=username,
        full_name=full_name or username,
        email=email,
        role=role
    )
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    flash(f'Пользователь {username} создан', 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/products/export')
@login_required
@admin_required
def export_products():
    """Экспорт товаров в CSV"""
    products = Product.query.order_by(Product.article).all()
    
    # Создаем CSV в памяти
    output = StringIO()
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    
    # Заголовки
    writer.writerow([
        'Артикул', 'Название', 'Производитель', 'Модель', 
        'Количество', 'Цена', 'Категория', 'Описание'
    ])
    
    # Данные
    for product in products:
        writer.writerow([
            product.article,
            product.name,
            product.manufacturer or '',
            product.model or '',
            product.quantity,
            product.price,
            product.category.name if product.category else '',
            product.description or ''
        ])
    
    # Возвращаем файл
    output.seek(0)
    return output.getvalue(), 200, {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': 'attachment; filename=products_export.csv'
    }

@admin_bp.route('/database/backup')
@login_required
@admin_required
def database_backup():
    """Экспорт всей базы данных в SQL"""
    # Этот endpoint будет делать дамп базы данных
    # В реальном приложении здесь будет вызов pg_dump
    flash('Функция резервного копирования требует настройки на сервере', 'info')
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/logs')
@login_required
@admin_required
def view_logs():
    """Просмотр логов системы"""
    # Здесь можно добавить просмотр логов из файла или базы данных
    return render_template('admin/logs.html')